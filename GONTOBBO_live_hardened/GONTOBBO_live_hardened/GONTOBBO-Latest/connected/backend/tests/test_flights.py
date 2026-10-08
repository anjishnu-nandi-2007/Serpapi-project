from unittest.mock import AsyncMock, patch
import pytest
from pydantic import ValidationError

from app.models.flight import FlightSearchRequest
from app.services.airport_resolver import (
    LocationResolutionError,
    resolve_location_to_airport,
)
from app.services.flights import normalize_serpapi_flight, search_flights


@pytest.fixture
def sample_serpapi_flights_response():
    return {
        "best_flights": [
            {
                "flights": [
                    {
                        "airline": "IndiGo",
                        "airline_logo": "https://example.com/indigo.png",
                        "flight_number": "6E 218",
                        "departure_airport": {"id": "CCU", "name": "Netaji Subhas Chandra Bose Intl", "time": "2026-10-01 08:20"},
                        "arrival_airport": {"id": "DEL", "name": "Indira Gandhi Intl", "time": "2026-10-01 10:40"},
                        "duration": 140,
                        "travel_class": "Economy",
                    }
                ],
                "total_duration": 140,
                "price": 5499,
                "departure_token": "token-dep-indigo-123",
            }
        ],
        "other_flights": [
            {
                "flights": [
                    {
                        "airline": "Air India",
                        "airline_logo": "https://example.com/airindia.png",
                        "flight_number": "AI 768",
                        "departure_airport": {"id": "CCU", "name": "Netaji Subhas Chandra Bose Intl", "time": "2026-10-01 09:15"},
                        "arrival_airport": {"id": "DEL", "name": "Indira Gandhi Intl", "time": "2026-10-01 11:55"},
                        "duration": 160,
                        "travel_class": "Economy",
                    }
                ],
                "total_duration": 160,
                "price": 4899,  # cheaper in other_flights!
            },
            {
                # Malformed / missing price option
                "flights": [
                    {
                        "airline": "SpiceJet",
                        "flight_number": "SG 123",
                    }
                ],
                # No price
            },
        ],
    }


def test_airport_resolver_known_locations():
    # Metro cities
    assert resolve_location_to_airport("Kolkata").iata_code == "CCU"
    assert resolve_location_to_airport("Delhi").iata_code == "DEL"
    assert resolve_location_to_airport("New Delhi").iata_code == "DEL"
    assert resolve_location_to_airport("Mumbai").iata_code == "BOM"
    assert resolve_location_to_airport("Bengaluru").iata_code == "BLR"
    assert resolve_location_to_airport("Chennai").iata_code == "MAA"
    assert resolve_location_to_airport("Goa").iata_code == "GOI"
    assert resolve_location_to_airport("Jaipur").iata_code == "JAI"

    # State fallbacks
    assert resolve_location_to_airport("West Bengal").iata_code == "CCU"
    assert resolve_location_to_airport("Maharashtra").iata_code == "BOM"

    # Direct 3-letter IATA code
    assert resolve_location_to_airport("ccu").iata_code == "CCU"
    assert resolve_location_to_airport("DEL").iata_code == "DEL"


def test_airport_resolver_unsupported():
    with pytest.raises(LocationResolutionError):
        resolve_location_to_airport("NonExistentAtlantisLandXYZ")


@pytest.mark.asyncio
async def test_search_flights_combines_best_and_other_cheapest_selection(sample_serpapi_flights_response):
    req = FlightSearchRequest(
        from_location="Kolkata",
        to_location="Delhi",
        departure_date="2026-10-01",
        adults=1,
    )

    with patch("app.services.flights.serpapi_search", new_callable=AsyncMock) as mock_search:
        mock_search.return_value = sample_serpapi_flights_response

        res = await search_flights(req)

        # 2 valid flights (one from best_flights, one from other_flights; unpriced one discarded)
        assert len(res.options) == 2

        # Air India at 4899 should be identified as cheapest even though it was in other_flights
        assert res.cheapest is not None
        assert res.cheapest.airline == "Air India"
        assert res.cheapest.price == 4899.0
        assert res.cheapest.duration_text == "2h 40m"
        assert res.cheapest.stops_text == "Non-stop"

        # Check IndiGo option
        indigo = [f for f in res.options if f.airline == "IndiGo"][0]
        assert indigo.price == 5499.0
        assert indigo.flight_number == "6E 218"
        assert indigo.departure_token == "token-dep-indigo-123"


def test_flight_normalization_multi_leg():
    raw_itinerary = {
        "flights": [
            {
                "airline": "Vistara",
                "flight_number": "UK 707",
                "departure_airport": {"id": "CCU", "name": "Kolkata", "time": "2026-10-01 06:00"},
                "arrival_airport": {"id": "BOM", "name": "Mumbai", "time": "2026-10-01 08:30"},
                "duration": 150,
            },
            {
                "airline": "Vistara",
                "flight_number": "UK 812",
                "departure_airport": {"id": "BOM", "name": "Mumbai", "time": "2026-10-01 10:00"},
                "arrival_airport": {"id": "DEL", "name": "Delhi", "time": "2026-10-01 12:15"},
                "duration": 135,
            },
        ],
        "layovers": [{"duration": 90, "name": "Chhatrapati Shivaji Maharaj Intl", "id": "BOM"}],
        "total_duration": 375,
        "price": 8200,
    }

    norm = normalize_serpapi_flight(
        itinerary=raw_itinerary,
        fallback_dep_code="CCU",
        fallback_dep_name="Kolkata",
        fallback_arr_code="DEL",
        fallback_arr_name="Delhi",
    )

    assert norm is not None
    assert norm.airline == "Vistara"
    assert norm.flight_number == "UK 707 / UK 812"
    assert norm.stops == 1
    assert norm.stops_text == "1 stop"
    assert norm.duration_minutes == 375
    assert norm.departure.airport == "CCU"
    assert norm.arrival.airport == "DEL"
    assert norm.price == 8200.0


def test_flight_request_validation():
    with pytest.raises(ValidationError):
        # Return date before departure date
        FlightSearchRequest(
            from_location="Kolkata",
            to_location="Delhi",
            departure_date="2026-10-05",
            return_date="2026-10-02",
        )

    with pytest.raises(ValidationError):
        # Same origin and destination
        FlightSearchRequest(
            from_location="Delhi",
            to_location="Delhi",
            departure_date="2026-10-05",
        )
