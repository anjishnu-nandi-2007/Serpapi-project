# Serpapi-project
# GONTOBBO — Smart Travel Discovery Platform

GONTOBBO is a travel discovery platform that helps users compare hotel and flight options in one place using live SerpApi-powered search results. The app is designed for fast, intuitive travel planning and supports hotel searches, flight searches, and combined travel discovery flows.

Live Demo: [Add your deployment URL here]
Project Type: Hackathon / Full-stack web app

## Why this project
Travel planning usually means jumping between separate hotel and flight search tools. GONTOBBO brings the experience into one dashboard, reducing friction and helping users discover the best available options faster.

## Key Features
- Live hotel search using SerpApi Google Hotels
- Live flight search using SerpApi Google Flights
- Combined travel search API
- Hotel filtering and comparison UI
- Airport and city resolution for Indian locations
- FastAPI backend with modular service architecture
- Responsive frontend for desktop/mobile
- Mocked test coverage for backend services

## Tech Stack
- Frontend: HTML, CSS, JavaScript
- Backend: Python, FastAPI
- Search API: SerpApi
- Data validation: Pydantic
- Async client: httpx
- Tests: pytest

## Architecture
The app follows a simple frontend + backend separation.

- Frontend: user-facing travel dashboard and search experience
- Backend: FastAPI application handling requests, validation, and SerpApi calls
- Services:
  - hotel service
  - flight service
  - airport resolver
  - normalization layer
- Data flow:
  1. User enters travel details in the frontend
  2. Frontend sends request to FastAPI backend
  3. Backend selects the appropriate SerpApi engine
  4. Response is normalized and returned to UI

## Project Structure

```bash
.
├── GONTOBBO_live_hardened/
│   └── GONTOBBO_live_hardened/
│       └── GONTOBBO-Latest/
│           └── connected/
│               ├── backend/
│               │   ├── app/
│               │   ├── tests/
│               │   ├── requirements.txt
│               │   └── .env.example
│               ├── frontend/
│               ├── start.sh
│               ├── start.bat
│               ├── setup-api-key.sh
│               ├── setup-email.sh
│               └── README.md
├── README.md
├── Project description.txt
├── How Project uses SerpApi.txt
└── frontendbackendload.txt
