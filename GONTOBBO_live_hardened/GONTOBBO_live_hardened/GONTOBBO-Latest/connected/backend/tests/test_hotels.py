from unittest.mock import AsyncMock, patch
import pytest
from pydantic import ValidationError

from app.models.hotel import HotelSearchRequest
from app.services.hotels import (
    DEFAULT_HOTEL_PLACEHOLDER,
    normalize_serpapi_hotel,
    search_hotels,
)


@pytest.fixture
def sample_serpapi_hotels_response():
    return {
        "properties": [
            {
                "name": "The Oberoi Grand Kolkata",
                "hotel_class": "5-star hotel",
                "overall_rating": 4.8,
                "reviews": 1250,
                "rate_per_night": {
                    "lowest": "₹7,500",
                    "extracted_lowest": 7500,
                },
                "total_rate": {
                    "lowest": "₹15,000",
                    "extracted_lowest": 15000,
                },
                "images": [
                    {
                        "thumbnail": "https://example.com/oberoi_thumb.jpg",
                        "original_image": "https://example.com/oberoi_large.jpg",
                    }
                ],
                "amenities": ["Free Wi-Fi", "Swimming pool", "Free breakfast", "Spa", "Air conditioning"],
                "type": "Heritage Hotel",
                "property_token": "token-oberoi-kolkata-123",
                "gps_coordinates": {"latitude": 22.56, "longitude": 88.35},
                "link": "https://example.com/book-oberoi",
                "address": "15 Jawaharlal Nehru Road, Kolkata",
                "description": "Luxury heritage property in central Kolkata.",
            },
            {
                "name": "Budget Inn Kolkata",
                "hotel_class": 3,
                "overall_rating": 3.9,
                "reviews": 85,
                "rate_per_night": {
                    "extracted_lowest": 2100,
                },
                "images": [],
                "amenities": ["Free Wi-Fi", "Free parking"],
                "type": "Hotel",
            },
            {
                "name": "Kolkata City Suites",
                "hotel_class": "4-star hotel",
                "overall_rating": 4.4,
                "reviews": 430,
                "rate_per_night": {
                    "extracted_lowest": 4200,
                },
                "images": [{"thumbnail": "https://example.com/suites.jpg"}],
                "amenities": ["Free Wi-Fi", "Breakfast", "AC"],
                "type": "Boutique",
            },
            {
                # Hotel missing price
                "name": "Unpriced Guest House",
                "hotel_class": 2,
                "overall_rating": 4.0,
                "reviews": 10,
                "amenities": [],
            },
        ]
    }


@pytest.mark.asyncio
async def test_search_hotels_success(sample_serpapi_hotels_response):
    req = HotelSearchRequest(
        city="Kolkata",
        state="West Bengal",
        check_in_date="2026-10-01",
        check_out_date="2026-10-03",
        adults=2,
        children=0,
        rooms=1,
    )

    with patch("app.services.hotels.serpapi_search", new_callable=AsyncMock) as mock_search:
        mock_search.return_value = sample_serpapi_hotels_response

        res = await search_hotels(req)

        assert len(res.options) == 4
        # Verify cheapest hotel was selected correctly (Budget Inn: ₹2100)
        assert res.cheapest is not None
        assert res.cheapest.name == "Budget Inn Kolkata"
        assert res.cheapest.price == 2100.0

        # Verify recommended hotels (Oberoi Grand with high rating & reviews should rank top)
        assert len(res.recommended) > 0
        assert res.recommended[0].name == "The Oberoi Grand Kolkata"


def test_hotel_normalization_complete_fields():
    raw_prop = {
        "name": "Taj Bengal",
        "hotel_class": "5-star hotel",
        "overall_rating": 4.7,
        "reviews": 980,
        "rate_per_night": {"extracted_lowest": 6800},
        "total_rate": {"extracted_lowest": 13600},
        "images": [{"original_image": "https://example.com/taj.jpg"}],
        "amenities": ["Free Wi-Fi", "Swimming pool", "Spa", "Breakfast", "Air conditioning"],
        "type": "Hotel",
        "property_token": "taj-bengal-tok-999",
        "gps_coordinates": {"latitude": 22.53, "longitude": 88.33},
        "link": "https://example.com/taj-bengal",
        "address": "Alipore, Kolkata",
    }

    hotel = normalize_serpapi_hotel(raw_prop, city="Kolkata", state="West Bengal", currency="INR")
    assert hotel is not None
    assert hotel.name == "Taj Bengal"
    assert hotel.stars == 5
    assert hotel.price == 6800.0
    assert hotel.total_price == 13600.0
    assert hotel.rating == 4.7
    assert hotel.reviews == 980
    assert hotel.comfort == "Luxury"
    assert hotel.type == "Hotel"
    assert hotel.meal == "Breakfast"
    assert "Pool" in hotel.facilities
    assert "Spa" in hotel.facilities
    assert "Free Wi-Fi" in hotel.facilities
    assert hotel.img == "https://example.com/taj.jpg"
    assert hotel.latitude == 22.53
    assert hotel.longitude == 88.33
    assert hotel.property_token == "taj-bengal-tok-999"


def test_hotel_normalization_missing_fields():
    """Defensive parsing when image, amenities, rating, price are missing."""
    sparse_prop = {"name": "Simple Homestay"}
    hotel = normalize_serpapi_hotel(sparse_prop, city="Darjeeling", state="West Bengal")

    assert hotel is not None
    assert hotel.name == "Simple Homestay"
    assert hotel.img == DEFAULT_HOTEL_PLACEHOLDER
    assert hotel.price == 0.0
    assert hotel.total_price is None
    assert hotel.stars == 3  # default fallback
    assert hotel.rating == 4.0  # safe default
    assert hotel.reviews == 0
    assert hotel.comfort == "Comfort"
    assert hotel.facilities == ["Free Wi-Fi"]
    assert hotel.meal == "Room Only"


@pytest.mark.asyncio
async def test_search_hotels_empty_results():
    req = HotelSearchRequest(
        city="UnknownCity",
        check_in_date="2026-10-01",
        check_out_date="2026-10-03",
    )

    with patch("app.services.hotels.serpapi_search", new_callable=AsyncMock) as mock_search:
        mock_search.return_value = {"properties": []}
        res = await search_hotels(req)

        assert res.options == []
        assert res.cheapest is None
        assert res.recommended == []


def test_invalid_date_range():
    with pytest.raises(ValidationError):
        HotelSearchRequest(
            city="Goa",
            check_in_date="2026-10-05",
            check_out_date="2026-10-02",  # check_out before check_in
        )

    with pytest.raises(ValidationError):
        HotelSearchRequest(
            city="Goa",
            check_in_date="invalid-date",
            check_out_date="2026-10-05",
        )
