from unittest.mock import AsyncMock, patch
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.services.serpapi_client import SerpApiConfigError, SerpApiError, SerpApiTimeoutError


@pytest.fixture
def mock_hotels_payload():
    return {
        "properties": [
            {
                "name": "The Oberoi Grand",
                "hotel_class": 5,
                "overall_rating": 4.9,
                "reviews": 1200,
                "rate_per_night": {"extracted_lowest": 6500},
                "amenities": ["Free Wi-Fi", "Swimming pool", "Breakfast"],
            }
        ]
    }


@pytest.fixture
def mock_flights_payload():
    return {
        "best_flights": [
            {
                "flights": [
                    {
                        "airline": "IndiGo",
                        "flight_number": "6E 218",
                        "departure_airport": {"id": "CCU", "name": "Kolkata", "time": "08:20"},
                        "arrival_airport": {"id": "DEL", "name": "Delhi", "time": "10:40"},
                        "duration": 140,
                    }
                ],
                "total_duration": 140,
                "price": 5499,
            }
        ],
        "other_flights": [],
    }


@pytest.mark.asyncio
async def test_health_check_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.get("/api/health")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "ok"
        assert data["service"] == "gontobbo-travel-backend"
        assert "timestamp" in data


@pytest.mark.asyncio
async def test_api_hotels_success(mock_hotels_payload):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        with patch("app.services.hotels.serpapi_search", new_callable=AsyncMock) as mock_search:
            mock_search.return_value = mock_hotels_payload

            payload = {
                "city": "Kolkata",
                "state": "West Bengal",
                "check_in_date": "2026-10-01",
                "check_out_date": "2026-10-03",
                "adults": 2,
                "children": 0,
                "rooms": 1,
            }
            res = await client.post("/api/travel/hotels", json=payload)
            assert res.status_code == 200
            data = res.json()
            assert data["success"] is True
            assert "searched_at" in data
            assert len(data["hotels"]["options"]) == 1
            assert data["hotels"]["cheapest"]["name"] == "The Oberoi Grand"


@pytest.mark.asyncio
async def test_api_flights_success(mock_flights_payload):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        with patch("app.services.flights.serpapi_search", new_callable=AsyncMock) as mock_search:
            mock_search.return_value = mock_flights_payload

            payload = {
                "from_location": "Kolkata",
                "to_location": "Delhi",
                "departure_date": "2026-10-01",
                "adults": 1,
            }
            res = await client.post("/api/travel/flights", json=payload)
            assert res.status_code == 200
            data = res.json()
            assert data["success"] is True
            assert len(data["flights"]["options"]) == 1
            assert data["flights"]["cheapest"]["airline"] == "IndiGo"


@pytest.mark.asyncio
async def test_api_flights_unresolvable_location():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        payload = {
            "from_location": "RandomFakeCity12345",
            "to_location": "Delhi",
            "departure_date": "2026-10-01",
        }
        res = await client.post("/api/travel/flights", json=payload)
        assert res.status_code == 400
        data = res.json()
        assert data["success"] is False
        assert data["error"]["code"] == "LOCATION_RESOLUTION_ERROR"


@pytest.mark.asyncio
async def test_api_validation_error():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Missing check_in_date and check_out_date
        payload = {"city": "Kolkata"}
        res = await client.post("/api/travel/hotels", json=payload)
        assert res.status_code == 400
        data = res.json()
        assert data["success"] is False
        assert data["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_api_missing_api_key():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        with patch("app.services.hotels.serpapi_search", new_callable=AsyncMock) as mock_search:
            mock_search.side_effect = SerpApiConfigError()

            payload = {
                "city": "Kolkata",
                "check_in_date": "2026-10-01",
                "check_out_date": "2026-10-03",
            }
            res = await client.post("/api/travel/hotels", json=payload)
            assert res.status_code == 500
            data = res.json()
            assert data["success"] is False
            assert data["error"]["code"] == "MISSING_API_KEY"


@pytest.mark.asyncio
async def test_api_upstream_timeout():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        with patch("app.services.hotels.serpapi_search", new_callable=AsyncMock) as mock_search:
            mock_search.side_effect = SerpApiTimeoutError()

            payload = {
                "city": "Kolkata",
                "check_in_date": "2026-10-01",
                "check_out_date": "2026-10-03",
            }
            res = await client.post("/api/travel/hotels", json=payload)
            assert res.status_code == 504
            data = res.json()
            assert data["success"] is False
            assert data["error"]["code"] == "UPSTREAM_TIMEOUT"


@pytest.mark.asyncio
async def test_api_upstream_serpapi_error():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        with patch("app.services.flights.serpapi_search", new_callable=AsyncMock) as mock_search:
            mock_search.side_effect = SerpApiError(message="SerpApi account limit reached", code="SERPAPI_ERROR", status_code=502)

            payload = {
                "from_location": "Kolkata",
                "to_location": "Delhi",
                "departure_date": "2026-10-01",
            }
            res = await client.post("/api/travel/flights", json=payload)
            assert res.status_code == 502
            data = res.json()
            assert data["success"] is False
            assert data["error"]["code"] == "SERPAPI_ERROR"


@pytest.mark.asyncio
async def test_api_combined_search_concurrent(mock_hotels_payload, mock_flights_payload):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        with patch("app.services.hotels.serpapi_search", new_callable=AsyncMock) as mock_h_search, \
             patch("app.services.flights.serpapi_search", new_callable=AsyncMock) as mock_f_search:

            mock_h_search.return_value = mock_hotels_payload
            mock_f_search.return_value = mock_flights_payload

            payload = {
                "hotels": {
                    "city": "Kolkata",
                    "check_in_date": "2026-10-01",
                    "check_out_date": "2026-10-03",
                },
                "flights": {
                    "from_location": "Kolkata",
                    "to_location": "Delhi",
                    "departure_date": "2026-10-01",
                },
            }
            res = await client.post("/api/travel/search", json=payload)
            assert res.status_code == 200
            data = res.json()
            assert data["success"] is True
            assert data["hotels"] is not None
            assert data["flights"] is not None
            assert len(data["hotels"]["options"]) == 1
            assert len(data["flights"]["options"]) == 1
