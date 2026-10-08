from typing import List, Optional
from pydantic import BaseModel, Field

from app.models.flight import FlightResultsPayload, FlightSearchRequest
from app.models.hotel import HotelResultsPayload, HotelSearchRequest


class TravelSearchRequest(BaseModel):
    """Combined travel search request for flights and hotels."""

    hotels: Optional[HotelSearchRequest] = Field(None, description="Hotel search criteria")
    flights: Optional[FlightSearchRequest] = Field(None, description="Flight search criteria")


class TravelSearchResponse(BaseModel):
    """Combined response returning both flight and hotel options."""

    success: bool = True
    searched_at: str = Field(..., description="Server UTC ISO-8601 timestamp")
    flights: Optional[FlightResultsPayload] = Field(None, description="Flight results if requested")
    hotels: Optional[HotelResultsPayload] = Field(None, description="Hotel results if requested")
    warnings: List[str] = Field(default_factory=list)


class ErrorDetail(BaseModel):
    """Structured error descriptor."""

    code: str = Field(..., description="Error code identifier (e.g. VALIDATION_ERROR, NO_RESULTS, SERPAPI_ERROR)")
    message: str = Field(..., description="Human-friendly error message")


class ErrorResponse(BaseModel):
    """Standardized API failure envelope."""

    success: bool = False
    error: ErrorDetail
    warnings: List[str] = Field(default_factory=list)
