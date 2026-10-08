from datetime import date
from typing import List, Optional
from pydantic import BaseModel, Field, model_validator


class HotelSearchRequest(BaseModel):
    """Hotel search request parameters."""

    city: str = Field(..., min_length=1, description="Destination city name")
    state: Optional[str] = Field(None, description="Destination state name")
    check_in_date: str = Field(..., description="Check-in date formatted as YYYY-MM-DD")
    check_out_date: str = Field(..., description="Check-out date formatted as YYYY-MM-DD")
    adults: int = Field(default=2, ge=1, description="Number of adult guests (minimum 1)")
    children: int = Field(default=0, ge=0, description="Number of children (>= 0)")
    rooms: int = Field(default=1, ge=1, description="Number of rooms required (>= 1)")
    currency: str = Field(default="INR", description="Currency code (e.g., INR, USD)")
    budget: Optional[str] = Field(None, description="Budget range filter hint (e.g. 0-2500)")
    min_price: Optional[float] = Field(None, ge=0, description="Minimum price filter")
    max_price: Optional[float] = Field(None, ge=0, description="Maximum price filter")
    rating: Optional[float] = Field(None, ge=0, le=5.0, description="Minimum guest rating")
    hotel_class: Optional[int] = Field(None, ge=1, le=5, description="Star category")

    @model_validator(mode="after")
    def validate_dates(self) -> "HotelSearchRequest":
        try:
            ci = date.fromisoformat(self.check_in_date)
            co = date.fromisoformat(self.check_out_date)
        except ValueError as exc:
            raise ValueError("Dates must be valid ISO format (YYYY-MM-DD)") from exc

        if co <= ci:
            raise ValueError("Check-out date must be strictly after check-in date")
        return self


class NormalizedHotel(BaseModel):
    """Normalized hotel model matching frontend display and comparison contract."""

    id: str = Field(..., description="Stable deterministic or SerpApi hotel identifier")
    name: str = Field(..., description="Hotel property name")
    img: str = Field(default="", description="Primary original image URL of hotel")
    thumbnail: Optional[str] = Field(None, description="Lightweight thumbnail URL for search result cards")
    images: List[str] = Field(default_factory=list, description="Original hotel image URLs for the property gallery")
    city: str = Field(default="", description="City location")
    state: str = Field(default="", description="State location")
    stars: int = Field(default=3, ge=1, le=5, description="Star rating (1-5)")
    price: float = Field(..., ge=0, description="Nightly rate in specified currency")
    currency: str = Field(default="INR", description="Price currency code")
    total_price: Optional[float] = Field(None, description="Total stay price if available")
    rating: float = Field(default=4.0, ge=0, le=5.0, description="Guest rating")
    reviews: int = Field(default=0, ge=0, description="Total review count")
    comfort: str = Field(default="Comfort", description="Comfort classification (Luxury, Premium, Comfort, Value)")
    type: str = Field(default="Hotel", description="Property type (Hotel, Resort, Boutique, Heritage)")
    meal: str = Field(default="Room Only", description="Meal plan (Breakfast, Half Board, Room Only)")
    facilities: List[str] = Field(default_factory=list, description="List of recognized amenities/facilities")
    address: Optional[str] = Field(None, description="Physical address or neighborhood")
    description: Optional[str] = Field(None, description="Property description")
    booking_url: Optional[str] = Field(None, description="Booking or detail URL link")
    phone: Optional[str] = Field(None, description="Hotel contact phone number for direct booking")
    latitude: Optional[float] = Field(None, description="GPS latitude")
    longitude: Optional[float] = Field(None, description="GPS longitude")
    property_token: Optional[str] = Field(None, description="SerpApi property token for detailed queries")


class HotelResultsPayload(BaseModel):
    """Hotel search result collection."""

    cheapest: Optional[NormalizedHotel] = Field(None, description="Lowest price hotel found")
    recommended: List[NormalizedHotel] = Field(default_factory=list, description="Top ranked suitable hotels")
    options: List[NormalizedHotel] = Field(default_factory=list, description="All normalized hotel options")


class HotelSearchResponse(BaseModel):
    """API response for hotel searches."""

    success: bool = True
    searched_at: str = Field(..., description="Server UTC ISO-8601 timestamp")
    hotels: HotelResultsPayload
    warnings: List[str] = Field(default_factory=list)
