import logging
from typing import Any, Dict, List, Optional
import httpx

from app.models.hotel import (
    HotelResultsPayload,
    HotelSearchRequest,
    NormalizedHotel,
)
from app.services.serpapi_client import serpapi_search
from app.utils.normalization import (
    determine_comfort,
    determine_meal_plan,
    determine_property_type,
    extract_numeric_price,
    generate_stable_hotel_id,
    normalize_facilities,
    parse_guest_rating,
    parse_review_count,
    parse_star_rating,
)

logger = logging.getLogger("gontobbo.hotels")

DEFAULT_HOTEL_PLACEHOLDER = "https://images.unsplash.com/photo-1566073771259-6a8506099945?auto=format&fit=crop&w=900&q=80"
CITY_HOTEL_FALLBACKS = {
    "goa": "https://images.unsplash.com/photo-1540541338287-41700207dee6?auto=format&fit=crop&w=900&q=85",
    "mumbai": "https://images.unsplash.com/photo-1564501049412-61c2a3083791?auto=format&fit=crop&w=900&q=85",
    "jaipur": "https://images.unsplash.com/photo-1600607687920-4e2a09cf159d?auto=format&fit=crop&w=900&q=85",
    "kolkata": "https://images.unsplash.com/photo-1584132967334-10e028bd69f7?auto=format&fit=crop&w=900&q=85",
    "delhi": "https://images.unsplash.com/photo-1582719478250-c89cae4dc85b?auto=format&fit=crop&w=900&q=85",
    "guwahati": "https://images.unsplash.com/photo-1566073771259-6a8506099945?auto=format&fit=crop&w=900&q=85",
    "chennai": "https://images.unsplash.com/photo-1571896349842-33c89424de2d?auto=format&fit=crop&w=900&q=85",
}


def normalize_serpapi_hotel(
    prop: Dict[str, Any],
    city: str,
    state: str,
    currency: str = "INR",
) -> Optional[NormalizedHotel]:
    """
    Parse and normalize a single SerpApi property item into the NormalizedHotel schema.
    Defensively inspects nested objects without throwing exceptions.
    """
    name = (prop.get("name") or "").strip()
    if not name:
        return None

    # Extract nightly rate
    rate_info = prop.get("rate_per_night") or {}
    if not isinstance(rate_info, dict):
        rate_info = {}
    candidates = [
        rate_info.get("extracted_lowest"), rate_info.get("extracted_before_taxes_fees"),
        rate_info.get("lowest"), prop.get("extracted_price"), prop.get("price"),
    ]
    price = next((candidate for candidate in (extract_numeric_price(v) for v in candidates) if candidate and candidate > 0), None)

    # If prices array is provided, check for lowest rate
    if price is None and isinstance(prop.get("prices"), list) and prop["prices"]:
        for p_item in prop["prices"]:
            if isinstance(p_item, dict):
                nested_rate = p_item.get("rate_per_night") or {}
                if not isinstance(nested_rate, dict):
                    nested_rate = {}
                cand = next((candidate for candidate in (extract_numeric_price(v) for v in [nested_rate.get("extracted_lowest"), nested_rate.get("lowest"), p_item.get("price")]) if candidate and candidate > 0), None)
                if cand is not None:
                    price = cand
                    break

    # Google Hotels can return a property without a rate when availability or room pricing is unavailable.
    # Keep the API's explicit zero sentinel for compatibility; the frontend removes these from visible cards.
    if price is None:
        price = 0.0

    # Extract total stay rate if provided
    total_rate_info = prop.get("total_rate") or {}
    total_price = (
        extract_numeric_price(total_rate_info.get("extracted_lowest"))
        or extract_numeric_price(total_rate_info.get("lowest"))
    )

    # Stars
    stars = parse_star_rating(prop.get("hotel_class") or prop.get("extracted_hotel_class"))

    # Rating & Reviews
    rating = parse_guest_rating(prop.get("overall_rating") or prop.get("rating"))
    reviews = parse_review_count(prop.get("reviews") or prop.get("reviews_count"))

    # Images
    img_url = ""
    thumbnail_url = ""
    image_urls: List[str] = []
    images = prop.get("images")
    if isinstance(images, list) and images:
        for raw_img in images:
            candidate = ""
            if isinstance(raw_img, dict):
                thumb = raw_img.get("thumbnail") or ""
                if thumb and not thumbnail_url:
                    thumbnail_url = str(thumb)
                candidate = raw_img.get("original_image") or raw_img.get("original") or thumb or ""
            elif isinstance(raw_img, str):
                candidate = raw_img
            if candidate and candidate not in image_urls:
                image_urls.append(candidate)
        img_url = image_urls[0] if image_urls else ""

    if not img_url:
        img_url = CITY_HOTEL_FALLBACKS.get(city.strip().lower(), DEFAULT_HOTEL_PLACEHOLDER)
        image_urls = [img_url]
        thumbnail_url = img_url

    # Amenities & Facilities
    raw_amenities = prop.get("amenities") or []
    if not isinstance(raw_amenities, list):
        raw_amenities = []
    facilities = normalize_facilities([str(a) for a in raw_amenities])

    # Classifications
    raw_type = str(prop.get("type") or "")
    prop_type = determine_property_type(name, raw_type)
    comfort = determine_comfort(stars, name, [str(a) for a in raw_amenities])
    meal = determine_meal_plan([str(a) for a in raw_amenities])

    # GPS coordinates
    gps = prop.get("gps_coordinates") or {}
    lat = gps.get("latitude") if isinstance(gps, dict) else None
    lng = gps.get("longitude") if isinstance(gps, dict) else None

    # Property token
    token = prop.get("property_token")
    stable_id = generate_stable_hotel_id(name, city, token)
    phone = prop.get("phone") or prop.get("telephone") or prop.get("contact_phone")
    phone = str(phone).strip() if phone else None

    return NormalizedHotel(
        id=stable_id,
        name=name,
        img=img_url,
        thumbnail=thumbnail_url or img_url,
        images=image_urls,
        city=city,
        state=state,
        stars=stars,
        price=price,
        currency=currency,
        total_price=total_price,
        rating=rating,
        reviews=reviews,
        comfort=comfort,
        type=prop_type,
        meal=meal,
        facilities=facilities,
        address=prop.get("address") or prop.get("neighborhood"),
        description=prop.get("description"),
        booking_url=prop.get("link"),
        phone=phone,
        latitude=float(lat) if lat is not None else None,
        longitude=float(lng) if lng is not None else None,
        property_token=token,
    )


def calculate_suitability_score(hotel: NormalizedHotel, request: HotelSearchRequest) -> float:
    """
    Compute a suitability score for ranking recommended hotels.

    Scoring weights:
    - Rating: 40% (guest satisfaction, 0-5 scaled to 0-40)
    - Review volume: 25% (credibility, logarithmic capped at 1000 reviews -> 0-25)
    - Star class: 20% (tier quality, 1-5 scaled to 0-20)
    - Price/budget alignment: 15% (rewards having a competitive price without compromising quality)
    """
    rating_score = (hotel.rating / 5.0) * 40.0
    review_score = (min(hotel.reviews, 1000) / 1000.0) * 25.0
    star_score = (hotel.stars / 5.0) * 20.0

    price_score = 15.0
    if hotel.price <= 0:
        price_score = 0.0
    elif request.max_price and hotel.price > request.max_price:
        price_score = 5.0

    return rating_score + review_score + star_score + price_score


async def search_hotels(
    req: HotelSearchRequest,
    client: Optional[httpx.AsyncClient] = None,
) -> HotelResultsPayload:
    """
    Search hotels using SerpApi's Google Hotels engine, normalize results,
    identify the cheapest hotel, and score suitable recommendations.
    """
    # Construct search query
    state_part = f", {req.state}" if req.state else ""
    query = f"Hotels in {req.city}{state_part}"

    params: Dict[str, Any] = {
        "engine": "google_hotels",
        "q": query,
        "check_in_date": req.check_in_date,
        "check_out_date": req.check_out_date,
        "adults": req.adults,
        "currency": req.currency,
        "hl": "en",
        "gl": "in",
    }

    if req.children > 0:
        params["children"] = req.children

    if req.min_price is not None:
        params["min_price"] = int(req.min_price)
    if req.max_price is not None:
        params["max_price"] = int(req.max_price)
    if req.rating is not None:
        params["rating"] = req.rating
    if req.hotel_class is not None:
        params["hotel_class"] = req.hotel_class

    logger.info("Executing hotel search for query: %s", query)
    data = await serpapi_search(params, client=client)

    raw_properties = data.get("properties")
    if not isinstance(raw_properties, list):
        raw_properties = []

    normalized_list: List[NormalizedHotel] = []
    state_display = req.state or req.city

    for prop in raw_properties:
        if isinstance(prop, dict):
            hotel = normalize_serpapi_hotel(
                prop=prop,
                city=req.city,
                state=state_display,
                currency=req.currency,
            )
            if hotel:
                normalized_list.append(hotel)

    # Identify cheapest valid hotel (must have price > 0)
    priced_hotels = [h for h in normalized_list if h.price > 0]
    cheapest = min(priced_hotels, key=lambda h: h.price) if priced_hotels else None

    # Calculate recommendations using suitability ranking
    scored_hotels = sorted(
        normalized_list,
        key=lambda h: calculate_suitability_score(h, req),
        reverse=True,
    )
    recommended = scored_hotels[:8]

    return HotelResultsPayload(
        cheapest=cheapest,
        recommended=recommended,
        options=normalized_list,
    )


async def get_hotel_contact(property_token: Optional[str] = None, query: Optional[str] = None) -> Optional[str]:
    """Fetch a verified public hotel phone from provider property details or Maps."""
    if not property_token and not query:
        return None
    if property_token:
        data = await serpapi_search({"engine": "google_hotels", "property_token": property_token})
        details = data.get("property_details") if isinstance(data, dict) else {}
        if not isinstance(details, dict):
            details = {}
        phone = data.get("phone") or details.get("phone") or details.get("telephone") or details.get("contact_phone")
        return str(phone).strip() if phone else None
    data = await serpapi_search({"engine": "google_maps", "q": query, "type": "search"})
    local_results = data.get("local_results") if isinstance(data, dict) else []
    if not isinstance(local_results, list):
        local_results = []
    first = local_results[0] if local_results and isinstance(local_results[0], dict) else {}
    phone = first.get("phone") or first.get("telephone")
    return str(phone).strip() if phone else None
