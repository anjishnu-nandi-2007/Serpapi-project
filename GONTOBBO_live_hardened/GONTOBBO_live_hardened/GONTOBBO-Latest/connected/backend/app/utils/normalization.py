from datetime import datetime, timezone
import hashlib
import re
from typing import Any, List, Optional


def get_current_utc_timestamp() -> str:
    """Return the current time formatted as an ISO-8601 UTC string."""
    return datetime.now(timezone.utc).isoformat()


def extract_numeric_price(val: Any) -> Optional[float]:
    """
    Defensively extract a numeric float price from integers, floats,
    or currency-formatted strings (e.g., '₹4,500', '4,500', 4500).
    """
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return float(val) if val >= 0 else None
    if isinstance(val, str):
        cleaned = re.sub(r"[^\d.]", "", val)
        if not cleaned:
            return None
        try:
            parsed = float(cleaned)
            return parsed if parsed >= 0 else None
        except ValueError:
            return None
    return None


def parse_star_rating(raw_class: Any) -> int:
    """
    Extract a 1-5 integer star rating from hotel_class fields
    such as '4-star hotel', 4, '4', etc.
    """
    if raw_class is None:
        return 3
    if isinstance(raw_class, int):
        return max(1, min(5, raw_class))
    if isinstance(raw_class, str):
        match = re.search(r"\b([1-5])\b", raw_class)
        if match:
            return int(match.group(1))
    return 3


def parse_guest_rating(raw_rating: Any) -> float:
    """Safely parse 0.0 to 5.0 guest rating."""
    if raw_rating is None:
        return 4.0
    try:
        val = float(raw_rating)
        return round(max(0.0, min(5.0, val)), 1)
    except (ValueError, TypeError):
        return 4.0


def parse_review_count(raw_reviews: Any) -> int:
    """Safely parse review count."""
    if raw_reviews is None:
        return 0
    if isinstance(raw_reviews, int):
        return max(0, raw_reviews)
    if isinstance(raw_reviews, str):
        cleaned = re.sub(r"[^\d]", "", raw_reviews)
        if cleaned:
            try:
                return max(0, int(cleaned))
            except ValueError:
                return 0
    return 0


def determine_comfort(stars: int, name: str = "", amenities: Optional[List[str]] = None) -> str:
    """
    Determine comfort level consistent with GONTOBBO UI tags:
    Luxury (5-star), Premium (4-star), Comfort (3-star), Value (<= 2-star).
    """
    if stars >= 5:
        return "Luxury"
    if stars == 4:
        return "Premium"
    if stars == 3:
        return "Comfort"
    return "Value"


def determine_property_type(name: str = "", raw_type: str = "") -> str:
    """
    Classify property as Hotel, Resort, Boutique, or Heritage.
    """
    combined = f"{name} {raw_type}".lower()
    if "heritage" in combined or "palace" in combined or "haveli" in combined:
        return "Heritage"
    if "resort" in combined or "retreat" in combined or "villas" in combined:
        return "Resort"
    if "boutique" in combined or "suites" in combined:
        return "Boutique"
    return "Hotel"


def determine_meal_plan(amenities: List[str]) -> str:
    """Determine meal plan from hotel amenities."""
    amenities_lower = [a.lower() for a in amenities]
    has_breakfast = any("breakfast" in a for a in amenities_lower)
    has_half_board = any("half board" in a or "dinner" in a for a in amenities_lower)

    if has_half_board:
        return "Half Board"
    if has_breakfast:
        return "Breakfast"
    return "Room Only"


def normalize_facilities(amenities: List[str]) -> List[str]:
    """
    Map raw amenity names to standardized frontend facility filter values:
    'Free Wi-Fi', 'Pool', 'Breakfast', 'Parking', 'Spa', 'AC'
    """
    normalized: List[str] = []
    amenities_str = " ".join(amenities).lower()

    if any(k in amenities_str for k in ("wi-fi", "wifi", "internet")):
        normalized.append("Free Wi-Fi")
    if any(k in amenities_str for k in ("pool", "swimming")):
        normalized.append("Pool")
    if "breakfast" in amenities_str:
        normalized.append("Breakfast")
    if any(k in amenities_str for k in ("parking", "valet")):
        normalized.append("Parking")
    if any(k in amenities_str for k in ("spa", "massage", "wellness")):
        normalized.append("Spa")
    if any(k in amenities_str for k in ("air conditioning", "air-conditioned", "ac", "a/c")):
        normalized.append("AC")

    # If few facilities were matched, guarantee at least Wi-Fi or AC if common
    if not normalized:
        normalized = ["Free Wi-Fi"]
    return normalized


def generate_stable_hotel_id(name: str, city: str, property_token: Optional[str] = None) -> str:
    """Generate a deterministic identifier for a hotel."""
    if property_token:
        # Use property token safely formatted
        clean_token = re.sub(r"[^\w-]", "", property_token)
        if clean_token:
            return f"prop-{clean_token[:24]}"

    seed = f"{name.strip().lower()}-{city.strip().lower()}"
    digest = hashlib.md5(seed.encode("utf-8")).hexdigest()[:10]
    safe_city = re.sub(r"[^\w]", "", city.lower()) or "hotel"
    return f"{safe_city}-{digest}"
