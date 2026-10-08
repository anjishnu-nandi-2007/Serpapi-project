import asyncio
import logging
from typing import Optional
import httpx

from app.models.flight import FlightResultsPayload
from app.models.hotel import HotelResultsPayload
from app.models.travel import TravelSearchRequest, TravelSearchResponse
from app.services.flights import search_flights
from app.services.hotels import search_hotels
from app.utils.normalization import get_current_utc_timestamp

logger = logging.getLogger("gontobbo.travel_search")


async def execute_combined_travel_search(
    req: TravelSearchRequest,
    client: Optional[httpx.AsyncClient] = None,
) -> TravelSearchResponse:
    """
    Execute concurrent flight and hotel searches using asyncio.gather.
    Ensures neither service blocks the other unnecessarily.
    """
    hotel_task = None
    flight_task = None
    warnings = []

    if req.hotels:
        hotel_task = asyncio.create_task(search_hotels(req.hotels, client=client))
    if req.flights:
        flight_task = asyncio.create_task(search_flights(req.flights, client=client))

    hotels_res: Optional[HotelResultsPayload] = None
    flights_res: Optional[FlightResultsPayload] = None

    tasks = []
    task_keys = []
    if hotel_task:
        tasks.append(hotel_task)
        task_keys.append("hotels")
    if flight_task:
        tasks.append(flight_task)
        task_keys.append("flights")

    if not tasks:
        return TravelSearchResponse(
            success=True,
            searched_at=get_current_utc_timestamp(),
            warnings=["No hotel or flight criteria provided."],
        )

    results = await asyncio.gather(*tasks, return_exceptions=True)

    for key, result in zip(task_keys, results):
        if isinstance(result, Exception):
            err_msg = f"{key.capitalize()} search encountered an issue: {str(result)}"
            logger.warning(err_msg)
            warnings.append(err_msg)
        else:
            if key == "hotels":
                hotels_res = result
            elif key == "flights":
                flights_res = result

    return TravelSearchResponse(
        success=True,
        searched_at=get_current_utc_timestamp(),
        flights=flights_res,
        hotels=hotels_res,
        warnings=warnings,
    )
