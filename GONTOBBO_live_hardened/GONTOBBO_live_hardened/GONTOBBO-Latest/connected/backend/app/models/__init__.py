from app.models.flight import (
    FlightAirportInfo,
    FlightResultsPayload,
    FlightSearchRequest,
    FlightSearchResponse,
    NormalizedFlight,
)
from app.models.hotel import (
    HotelResultsPayload,
    HotelSearchRequest,
    HotelSearchResponse,
    NormalizedHotel,
)
from app.models.travel import (
    ErrorDetail,
    ErrorResponse,
    TravelSearchRequest,
    TravelSearchResponse,
)

__all__ = [
    "FlightAirportInfo",
    "FlightResultsPayload",
    "FlightSearchRequest",
    "FlightSearchResponse",
    "NormalizedFlight",
    "HotelResultsPayload",
    "HotelSearchRequest",
    "HotelSearchResponse",
    "NormalizedHotel",
    "ErrorDetail",
    "ErrorResponse",
    "TravelSearchRequest",
    "TravelSearchResponse",
]
