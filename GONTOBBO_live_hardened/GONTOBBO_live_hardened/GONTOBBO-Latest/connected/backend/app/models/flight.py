from datetime import date
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, model_validator


class FlightSearchRequest(BaseModel):
    """Flight search request parameters."""

    from_location: str = Field(..., min_length=1, description="Origin city, state, or IATA code")
    to_location: str = Field(..., min_length=1, description="Destination city, state, or IATA code")
    departure_date: str = Field(..., description="Departure date formatted as YYYY-MM-DD")
    return_date: Optional[str] = Field(None, description="Optional return date formatted as YYYY-MM-DD")
    adults: int = Field(default=1, ge=1, description="Number of adult passengers (>= 1)")
    children: int = Field(default=0, ge=0, description="Number of children (>= 0)")
    travel_class: Optional[str] = Field(default="Economy", description="Cabin class: Economy, Premium Economy, Business, First")
    currency: str = Field(default="INR", description="Currency code (e.g., INR, USD)")
    departure_token: Optional[str] = Field(None, description="Optional token for round-trip return leg searches")

    @model_validator(mode="after")
    def validate_flight_dates(self) -> "FlightSearchRequest":
        try:
            dep = date.fromisoformat(self.departure_date)
        except ValueError as exc:
            raise ValueError("Departure date must be a valid ISO format (YYYY-MM-DD)") from exc

        if self.return_date:
            try:
                ret = date.fromisoformat(self.return_date)
            except ValueError as exc:
                raise ValueError("Return date must be a valid ISO format (YYYY-MM-DD)") from exc
            if ret < dep:
                raise ValueError("Return date cannot be earlier than departure date")

        if self.from_location.strip().lower() == self.to_location.strip().lower():
            raise ValueError("Origin and destination cannot be the same location")

        return self


class FlightAirportInfo(BaseModel):
    """Airport details for departure and arrival endpoints."""

    airport: str = Field(..., description="IATA 3-letter airport code")
    name: str = Field(default="", description="Airport or city display name")
    time: str = Field(default="", description="Departure or arrival time string")


class NormalizedFlight(BaseModel):
    """Normalized flight route card matching existing frontend UI expectations."""

    id: str = Field(..., description="Unique deterministic identifier for flight itinerary")
    airline: str = Field(..., description="Operating airline name (e.g., IndiGo, Air India)")
    airline_logo: Optional[str] = Field(None, description="Airline logo image URL")
    flight_number: str = Field(default="", description="Flight number or composite numbers (e.g. 6E 218)")
    price: float = Field(..., ge=0, description="Itinerary ticket price")
    currency: str = Field(default="INR", description="Price currency code")
    departure: FlightAirportInfo = Field(..., description="Departure airport, name, and time")
    arrival: FlightAirportInfo = Field(..., description="Arrival airport, name, and time")
    duration_minutes: int = Field(default=0, ge=0, description="Flight duration in minutes")
    duration_text: str = Field(default="", description="Formatted duration text (e.g., 2h 20m)")
    stops: int = Field(default=0, ge=0, description="Number of stops/layovers (0 = Non-stop)")
    stops_text: str = Field(default="Non-stop", description="Stops text label (e.g. Non-stop, 1 stop)")
    travel_class: str = Field(default="Economy", description="Cabin class")
    layovers: List[Dict[str, Any]] = Field(default_factory=list, description="Layover details if applicable")
    emissions: Optional[Dict[str, Any]] = Field(None, description="Carbon emission estimates if provided")
    departure_token: Optional[str] = Field(None, description="Token to request return legs in round-trip searches")
    booking_token: Optional[str] = Field(None, description="Direct booking token if returned by SerpApi")


class FlightResultsPayload(BaseModel):
    """Flight search result collection."""

    cheapest: Optional[NormalizedFlight] = Field(None, description="Cheapest valid flight option")
    options: List[NormalizedFlight] = Field(default_factory=list, description="Normalized flight options list")


class FlightSearchResponse(BaseModel):
    """API response for flight searches."""

    success: bool = True
    searched_at: str = Field(..., description="Server UTC ISO-8601 timestamp")
    flights: FlightResultsPayload
    warnings: List[str] = Field(default_factory=list)
