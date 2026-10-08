# GONTOBBO Travel Backend Service

A high-performance, modular Python FastAPI travel backend integrating with SerpApi to provide live search results for Google Hotels and Google Flights, designed specifically for the GONTOBBO travel platform.

---

## ⚠️ Important Teammate Handoff & Architecture Boundaries

> **CORS was not implemented because it is handled by another teammate.**  
> The FastAPI application in `app/main.py` is clean and does not include `CORSMiddleware`. When integrating into production, the teammate handling CORS can attach `CORSMiddleware` with allowed origins directly in `app/main.py`.

> **Authentication/OTP was not implemented because it is handled by another teammate.**  
> The travel API endpoints are completely decoupled from user authentication, JWT, cookies, or OTP flow. The existing Node.js OTP server in `server.js` remains intact. The travel search service can be placed behind an API gateway, authentication middleware, or reverse proxy as needed.

---

## Architecture Overview

```
Frontend (gontobbo-home-search.html)
    │
    ├── Hotel Search (inline-05.js) ─────────► POST /api/travel/hotels
    │                                                   │
    └── Flight Search (inline-13.js) ────────► POST /api/travel/flights
                                                        │
FastAPI Travel Backend (app/main.py)                    │
    ├── models/ (hotel.py, flight.py, travel.py)        ▼
    ├── services/                                 SerpApi Client
    │     ├── airport_resolver.py                       │
    │     ├── hotels.py  ───────────────────────────────┤ engine=google_hotels
    │     ├── flights.py ───────────────────────────────┤ engine=google_flights
    │     └── travel_search.py (concurrent search)      ▼
    └── utils/normalization.py ◄────────────── Live SerpApi Results
          │
          ▼
    Normalized Responses (Cheapest + Recommended + All Options)
```

### Directory Structure

```
back/
├── app/
│   ├── __init__.py
│   ├── main.py                  # FastAPI application entry point
│   ├── config.py                # Environment configuration loader (.env)
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes/
│   │       ├── __init__.py
│   │       └── travel.py        # Travel endpoints (/api/health, /api/travel/...)
│   ├── models/
│   │   ├── __init__.py
│   │   ├── hotel.py             # Hotel request/response Pydantic models
│   │   ├── flight.py            # Flight request/response Pydantic models
│   │   └── travel.py            # Combined search & error models
│   ├── services/
│   │   ├── __init__.py
│   │   ├── serpapi_client.py    # Reusable SerpApi HTTP client (httpx)
│   │   ├── airport_resolver.py  # Maps Indian states/cities/IATA to airport codes
│   │   ├── hotels.py            # Google Hotels query, normalization & ranking
│   │   ├── flights.py           # Google Flights query, normalization & cheapest
│   │   └── travel_search.py     # Concurrent flight & hotel execution
│   └── utils/
│       ├── __init__.py
│       └── normalization.py     # Data sanitization, ratings, comfort & facility mapping
├── tests/
│   ├── __init__.py
│   ├── test_hotels.py           # Hotel service and normalization unit tests
│   ├── test_flights.py          # Flight service and airport resolver tests
│   └── test_travel.py           # End-to-end API route tests with mocked SerpApi
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

---

## SerpApi Engines Used

1. **Google Hotels (`engine="google_hotels"`)**
   - Retrieves live properties matching destination city and state.
   - Supports check-in date, check-out date, adults, children, currency, rating, and hotel class.
   - Extracts nightly rates (`rate_per_night`), total stay prices (`total_rate`), property tokens, amenities, and photos.

2. **Google Flights (`engine="google_flights"`)**
   - Retrieves live flights for route and travel date.
   - Combines `best_flights` and `other_flights` to find the true lowest price.
   - Supports one-way and round-trip searches with `departure_token` preservation.

---

## Key Business Logic & Algorithms

### 1. Airport / Location Resolution (`app/services/airport_resolver.py`)
- The resolver converts user selections (city name, state name, or IATA code) to commercial IATA airport codes without guessing or inventing codes.
- **Priority hierarchy**:
  1. City hint if provided
  2. Exact city name match (e.g. `Kolkata` -> `CCU`, `Delhi` -> `DEL`, `Mumbai` -> `BOM`, `Bengaluru` -> `BLR`, `Goa` -> `GOI`)
  3. Exact state name match (e.g. `West Bengal` -> `CCU`, `Maharashtra` -> `BOM`, `Tamil Nadu` -> `MAA`)
  4. Verified uppercase 3-letter IATA code
  5. Substring / alias resolution
- Unresolvable locations raise `LocationResolutionError`, returning a friendly HTTP 400 error.

### 2. Hotel Normalization & Suitability Scoring (`app/services/hotels.py`)
- **Normalization**: Maps SerpApi property structures to the exact contract expected by GONTOBBO UI:
  - `id`: Stable deterministic hash based on property token or name + city
  - `img`: Verified SerpApi photo URL with fallback to placeholder
  - `stars`, `rating`, `reviews`, `comfort` (`Luxury`, `Premium`, `Comfort`, `Value`), `type` (`Hotel`, `Resort`, `Boutique`, `Heritage`), `meal` (`Breakfast`, `Half Board`, `Room Only`), `facilities` (`Free Wi-Fi`, `Pool`, `Breakfast`, `Parking`, `Spa`, `AC`)
- **Cheapest Hotel Selection**: Scans options with valid numeric prices > 0 and extracts the lowest nightly rate.
- **Suitability Scoring Algorithm**:
  $$\text{Score} = \left(\frac{\text{Rating}}{5.0} \times 40\right) + \left(\frac{\min(\text{Reviews}, 1000)}{1000} \times 25\right) + \left(\frac{\text{Stars}}{5.0} \times 20\right) + \text{PriceScore (up to 15)}$$
  Ensures "recommended" hotels reflect high quality and guest satisfaction rather than purely cheapest price.

### 3. Flight Normalization & Cheapest Selection (`app/services/flights.py`)
- Combines itineraries from both `best_flights` and `other_flights`.
- Discards malformed options or options without usable numeric price.
- Normalizes durations, airline names, flight numbers, stops (`Non-stop`, `1 stop`), departure/arrival airport codes and times.
- Sorts ascending by numeric price and selects `cheapest`.

---

## API Endpoints

### 1. Health Check
`GET /api/health`
```json
{
  "status": "ok",
  "service": "gontobbo-travel-backend",
  "timestamp": "2026-09-27T05:37:29.555430+00:00"
}
```

### 2. Hotel Search
`POST /api/travel/hotels`

**Request:**
```json
{
  "city": "Kolkata",
  "state": "West Bengal",
  "check_in_date": "2026-10-01",
  "check_out_date": "2026-10-03",
  "adults": 2,
  "children": 0,
  "rooms": 1,
  "currency": "INR"
}
```

**Response:**
```json
{
  "success": true,
  "searched_at": "2026-09-27T05:30:00.000000+00:00",
  "hotels": {
    "cheapest": {
      "id": "kolkata-a1b2c3d4e5",
      "name": "Budget Inn Kolkata",
      "img": "https://...",
      "city": "Kolkata",
      "state": "West Bengal",
      "stars": 3,
      "price": 2100.0,
      "currency": "INR",
      "total_price": 4200.0,
      "rating": 4.1,
      "reviews": 180,
      "comfort": "Comfort",
      "type": "Hotel",
      "meal": "Breakfast",
      "facilities": ["Free Wi-Fi", "Breakfast", "AC"]
    },
    "recommended": [ ... ],
    "options": [ ... ]
  },
  "warnings": []
}
```

### 3. Flight Search
`POST /api/travel/flights`

**Request:**
```json
{
  "from_location": "West Bengal",
  "to_location": "Delhi (NCT)",
  "departure_date": "2026-10-01",
  "adults": 1,
  "children": 0,
  "currency": "INR"
}
```

**Response:**
```json
{
  "success": true,
  "searched_at": "2026-09-27T05:30:00.000000+00:00",
  "flights": {
    "cheapest": {
      "id": "fl-CCU-DEL-6E218-08:20",
      "airline": "IndiGo",
      "flight_number": "6E 218",
      "price": 4899.0,
      "currency": "INR",
      "departure": {"airport": "CCU", "name": "Kolkata", "time": "2026-10-01 08:20"},
      "arrival": {"airport": "DEL", "name": "Delhi", "time": "2026-10-01 10:40"},
      "duration_minutes": 140,
      "duration_text": "2h 20m",
      "stops": 0,
      "stops_text": "Non-stop",
      "travel_class": "Economy"
    },
    "options": [ ... ]
  },
  "warnings": []
}
```

### 4. Combined Travel Search
`POST /api/travel/search`
Executes both hotel and flight queries concurrently with `asyncio.gather`.

---

## Setup & Running Locally

### 1. Prerequisites
- Python 3.11+

### 2. Environment Setup
```powershell
cd back
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configure API Key
Copy `.env.example` to `.env`:
```powershell
cp .env.example .env
```
Edit `.env` and add your SerpApi key:
```env
SERPAPI_API_KEY=your_actual_serpapi_key_here
HOST=0.0.0.0
PORT=8000
```

### 4. Run the Server
```powershell
.\.venv\Scripts\python -m uvicorn app.main:app --reload --port 8000
```
Interactive Swagger docs available at: `http://localhost:8000/docs`.

### 5. Run Automated Tests
```powershell
.\.venv\Scripts\python -m pytest -v
```
All tests mock SerpApi responses so no real API quota is consumed during testing.

---

## Frontend Integration Details

- **Configurable Base URL**: Configured via `window.FASTAPI_BASE_URL` (defaults to `http://localhost:8000`).
- **Hotel Search (`js/inline-05.js`)**: Replaced `makeHotels()` demo generator with an asynchronous `fetch()` call to `POST /api/travel/hotels`. Preserves all client-side filter dropdowns, sorting, favorites, recent stays, and side-by-side comparison modal.
- **Flight Search (`js/inline-13.js`)**: Replaced hardcoded flight array with an asynchronous `fetch()` call to `POST /api/travel/flights`. Renders live flights into existing `.route-card` components.
- **Train Search**: Retained demo/preview cards as trains are not part of SerpApi Google Flights and were explicitly outside project scope.
