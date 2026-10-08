import logging
from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import JSONResponse

from app.models.flight import FlightSearchRequest, FlightSearchResponse
from app.models.hotel import HotelSearchRequest, HotelSearchResponse
from app.models.travel import (
    ErrorDetail,
    ErrorResponse,
    TravelSearchRequest,
    TravelSearchResponse,
)
from app.services.airport_resolver import LocationResolutionError
from app.services.flights import search_flights
from app.services.hotels import get_hotel_contact, search_hotels
from app.services.serpapi_client import (
    SerpApiConfigError,
    SerpApiError,
    SerpApiTimeoutError,
)
from app.services.travel_search import execute_combined_travel_search
from app.utils.normalization import get_current_utc_timestamp

logger = logging.getLogger("gontobbo.routes.travel")

router = APIRouter(prefix="/api", tags=["travel"])


@router.get("/health", status_code=status.HTTP_200_OK)
async def health_check():
    """Health check endpoint confirming service readiness."""
    return {
        "status": "ok",
        "service": "gontobbo-travel-backend",
        "timestamp": get_current_utc_timestamp(),
    }


@router.post(
    "/travel/hotels",
    response_model=HotelSearchResponse,
    responses={
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
        502: {"model": ErrorResponse},
        504: {"model": ErrorResponse},
    },
)
async def search_hotels_endpoint(req: HotelSearchRequest):
    """
    Search and retrieve normalized hotel options matching destination, dates, and guest specifications.
    Identifies the cheapest valid hotel and computes suitability recommendations.
    """
    try:
        results = await search_hotels(req)
        warnings = []
        if not results.options:
            warnings.append(f"No hotel properties were returned for {req.city}.")

        return HotelSearchResponse(
            success=True,
            searched_at=get_current_utc_timestamp(),
            hotels=results,
            warnings=warnings,
        )
    except SerpApiConfigError as exc:
        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse(
                success=False,
                error=ErrorDetail(code=exc.code, message=exc.message),
            ).model_dump(),
        )
    except SerpApiTimeoutError as exc:
        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse(
                success=False,
                error=ErrorDetail(code=exc.code, message=exc.message),
            ).model_dump(),
        )
    except SerpApiError as exc:
        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse(
                success=False,
                error=ErrorDetail(code=exc.code, message=exc.message),
            ).model_dump(),
        )
    except Exception as exc:
        logger.exception("Unexpected error in search_hotels_endpoint: %s", exc)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=ErrorResponse(
                success=False,
                error=ErrorDetail(
                    code="INTERNAL_SERVER_ERROR",
                    message="An unexpected server error occurred while searching hotels.",
                ),
            ).model_dump(),
        )


@router.get("/travel/hotels/contact")
async def hotel_contact_endpoint(property_token: str | None = Query(None, min_length=3), query: str | None = Query(None, min_length=3)):
    """Return a provider-sourced hotel phone number for direct booking contact."""
    if not property_token and not query:
        return {"success": True, "phone": None}
    try:
        return {"success": True, "phone": await get_hotel_contact(property_token=property_token, query=query)}
    except SerpApiError:
        return {"success": True, "phone": None}


@router.post(
    "/travel/flights",
    response_model=FlightSearchResponse,
    responses={
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
        502: {"model": ErrorResponse},
        504: {"model": ErrorResponse},
    },
)
async def search_flights_endpoint(req: FlightSearchRequest):
    """
    Search and retrieve normalized flight options matching route, date, and passenger criteria.
    Resolves city/state locations to IATA airport codes, identifies the cheapest flight option,
    and returns route-card data.
    """
    try:
        results = await search_flights(req)
        warnings = []
        if not results.options:
            warnings.append(f"No flights were found between {req.from_location} and {req.to_location} on {req.departure_date}.")

        return FlightSearchResponse(
            success=True,
            searched_at=get_current_utc_timestamp(),
            flights=results,
            warnings=warnings,
        )
    except LocationResolutionError as exc:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=ErrorResponse(
                success=False,
                error=ErrorDetail(code="LOCATION_RESOLUTION_ERROR", message=exc.message),
            ).model_dump(),
        )
    except SerpApiConfigError as exc:
        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse(
                success=False,
                error=ErrorDetail(code=exc.code, message=exc.message),
            ).model_dump(),
        )
    except SerpApiTimeoutError as exc:
        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse(
                success=False,
                error=ErrorDetail(code=exc.code, message=exc.message),
            ).model_dump(),
        )
    except SerpApiError as exc:
        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse(
                success=False,
                error=ErrorDetail(code=exc.code, message=exc.message),
            ).model_dump(),
        )
    except Exception as exc:
        logger.exception("Unexpected error in search_flights_endpoint: %s", exc)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=ErrorResponse(
                success=False,
                error=ErrorDetail(
                    code="INTERNAL_SERVER_ERROR",
                    message="An unexpected server error occurred while searching flights.",
                ),
            ).model_dump(),
        )


@router.post(
    "/travel/search",
    response_model=TravelSearchResponse,
    responses={
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
        502: {"model": ErrorResponse},
        504: {"model": ErrorResponse},
    },
)
async def combined_travel_search_endpoint(req: TravelSearchRequest):
    """
    Search both flights and hotels concurrently.
    Executes tasks in parallel using asyncio to minimize wait time.
    """
    try:
        return await execute_combined_travel_search(req)
    except Exception as exc:
        logger.exception("Unexpected error in combined_travel_search_endpoint: %s", exc)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=ErrorResponse(
                success=False,
                error=ErrorDetail(
                    code="INTERNAL_SERVER_ERROR",
                    message="An unexpected server error occurred while processing combined travel search.",
                ),
            ).model_dump(),
        )
