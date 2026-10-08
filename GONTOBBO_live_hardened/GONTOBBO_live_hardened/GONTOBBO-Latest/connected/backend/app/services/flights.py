import logging
from typing import Any, Dict, List, Optional
import httpx

from app.models.flight import (
    FlightAirportInfo,
    FlightResultsPayload,
    FlightSearchRequest,
    NormalizedFlight,
)
from app.services.airport_resolver import resolve_location_to_airport
from app.services.serpapi_client import serpapi_search
from app.utils.normalization import extract_numeric_price

logger = logging.getLogger("gontobbo.flights")


def format_duration(minutes: int) -> str:
    """Format total flight minutes into human-readable text (e.g. 2h 20m)."""
    if minutes <= 0:
        return "N/A"
    hours = minutes // 60
    mins = minutes % 60
    if hours > 0 and mins > 0:
        return f"{hours}h {mins:02d}m"
    if hours > 0:
        return f"{hours}h"
    return f"{mins}m"


def normalize_serpapi_flight(
    itinerary: Dict[str, Any],
    fallback_dep_code: str,
    fallback_dep_name: str,
    fallback_arr_code: str,
    fallback_arr_name: str,
    currency: str = "INR",
) -> Optional[NormalizedFlight]:
    """
    Normalize a SerpApi Google Flights itinerary item into NormalizedFlight.
    Defensively validates all fields and excludes invalid items.
    """
    price = extract_numeric_price(itinerary.get("price"))
    if price is None or price <= 0:
        # Per requirement 18: discard options without usable numeric price
        return None

    legs = itinerary.get("flights")
    if not isinstance(legs, list) or not legs:
        return None

    first_leg = legs[0] if isinstance(legs[0], dict) else {}
    last_leg = legs[-1] if isinstance(legs[-1], dict) else {}

    airline = str(first_leg.get("airline") or "Airline").strip()
    airline_logo = first_leg.get("airline_logo")

    # Combine flight numbers (e.g. '6E 218', or 'AI 101, AI 202' for multi-leg)
    flight_nums = [
        str(leg.get("flight_number")).strip()
        for leg in legs
        if isinstance(leg, dict) and leg.get("flight_number")
    ]
    flight_number_str = " / ".join(flight_nums) if flight_nums else str(first_leg.get("flight_number") or "")

    # Departure airport details
    dep_airport_data = first_leg.get("departure_airport") or {}
    dep_code = str(dep_airport_data.get("id") or fallback_dep_code).upper()
    dep_name = str(dep_airport_data.get("name") or fallback_dep_name)
    dep_time_raw = str(dep_airport_data.get("time") or "")

    # Arrival airport details
    arr_airport_data = last_leg.get("arrival_airport") or {}
    arr_code = str(arr_airport_data.get("id") or fallback_arr_code).upper()
    arr_name = str(arr_airport_data.get("name") or fallback_arr_name)
    arr_time_raw = str(arr_airport_data.get("time") or "")

    # Duration calculation
    total_duration = itinerary.get("total_duration")
    if not isinstance(total_duration, int) or total_duration <= 0:
        # Sum individual leg durations if total_duration is missing
        leg_durations = [
            leg.get("duration")
            for leg in legs
            if isinstance(leg, dict) and isinstance(leg.get("duration"), int)
        ]
        total_duration = sum(leg_durations) if leg_durations else 0

    duration_text = format_duration(total_duration)

    # Stops and layovers
    layovers = itinerary.get("layovers")
    layover_list = layovers if isinstance(layovers, list) else []
    stops_count = max(0, len(legs) - 1)
    if stops_count == 0:
        stops_text = "Non-stop"
    elif stops_count == 1:
        stops_text = "1 stop"
    else:
        stops_text = f"{stops_count} stops"

    # Travel class
    travel_class = str(first_leg.get("travel_class") or "Economy").strip()

    # Tokens for round-trip flows
    dep_token = itinerary.get("departure_token")
    booking_token = itinerary.get("booking_token")

    # Stable deterministic ID
    dep_clean_time = dep_time_raw.replace(" ", "_")
    flight_id = f"fl-{dep_code}-{arr_code}-{flight_nums[0] if flight_nums else 'opt'}-{dep_clean_time or total_duration}"

    return NormalizedFlight(
        id=flight_id,
        airline=airline,
        airline_logo=airline_logo,
        flight_number=flight_number_str,
        price=price,
        currency=currency,
        departure=FlightAirportInfo(airport=dep_code, name=dep_name, time=dep_time_raw),
        arrival=FlightAirportInfo(airport=arr_code, name=arr_name, time=arr_time_raw),
        duration_minutes=total_duration,
        duration_text=duration_text,
        stops=stops_count,
        stops_text=stops_text,
        travel_class=travel_class,
        layovers=layover_list,
        emissions=itinerary.get("carbon_emissions"),
        departure_token=dep_token,
        booking_token=booking_token,
    )


async def search_flights(
    req: FlightSearchRequest,
    client: Optional[httpx.AsyncClient] = None,
) -> FlightResultsPayload:
    """
    Search flights using SerpApi Google Flights engine.
    Resolves departure and arrival locations to IATA codes, queries SerpApi,
    combines best_flights and other_flights, eliminates invalid options,
    sorts by price, and identifies the cheapest valid flight.
    """
    # 1. Resolve airports
    dep_resolved = resolve_location_to_airport(req.from_location)
    arr_resolved = resolve_location_to_airport(req.to_location)

    logger.info(
        "Resolved route: %s (%s) -> %s (%s)",
        req.from_location,
        dep_resolved.iata_code,
        req.to_location,
        arr_resolved.iata_code,
    )

    # 2. Build SerpApi parameters
    # Type: 1 = Round trip, 2 = One way
    is_round_trip = bool(req.return_date)
    trip_type = 1 if is_round_trip else 2

    params: Dict[str, Any] = {
        "engine": "google_flights",
        "departure_id": dep_resolved.iata_code,
        "arrival_id": arr_resolved.iata_code,
        "outbound_date": req.departure_date,
        "type": trip_type,
        "adults": req.adults,
        "currency": req.currency,
        "hl": "en",
        "gl": "in",
    }

    if req.children > 0:
        params["children"] = req.children

    if is_round_trip and req.return_date:
        params["return_date"] = req.return_date

    # Use departure_token if provided for round-trip return leg flow
    if req.departure_token:
        params["departure_token"] = req.departure_token

    # Cabin class mapping: Economy (1), Premium Economy (2), Business (3), First (4)
    if req.travel_class:
        tc = req.travel_class.lower()
        if "business" in tc:
            params["travel_class"] = 3
        elif "first" in tc:
            params["travel_class"] = 4
        elif "premium" in tc:
            params["travel_class"] = 2
        else:
            params["travel_class"] = 1

    # Request SerpApi price-sorted results where available
    params["sort_by"] = 1

    logger.info("Executing Google Flights query via SerpApi: %s -> %s", dep_resolved.iata_code, arr_resolved.iata_code)
    data = await serpapi_search(params, client=client)

    # 3. Combine best_flights and other_flights per requirement 18
    raw_options: List[Dict[str, Any]] = []
    best_flights = data.get("best_flights")
    if isinstance(best_flights, list):
        raw_options.extend(best_flights)

    other_flights = data.get("other_flights")
    if isinstance(other_flights, list):
        raw_options.extend(other_flights)

    # 4. Normalize and filter
    normalized_options: List[NormalizedFlight] = []
    seen_ids = set()

    for item in raw_options:
        if isinstance(item, dict):
            flight = normalize_serpapi_flight(
                itinerary=item,
                fallback_dep_code=dep_resolved.iata_code,
                fallback_dep_name=dep_resolved.display_name,
                fallback_arr_code=arr_resolved.iata_code,
                fallback_arr_name=arr_resolved.display_name,
                currency=req.currency,
            )
            if flight and flight.id not in seen_ids:
                seen_ids.add(flight.id)
                normalized_options.append(flight)

    # 5. Sort options ascending by price
    normalized_options.sort(key=lambda f: f.price)

    # 6. Select cheapest
    cheapest = normalized_options[0] if normalized_options else None

    return FlightResultsPayload(
        cheapest=cheapest,
        options=normalized_options,
    )
