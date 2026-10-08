# GONTOBBO Connected App

This ZIP contains the GONTOBBO frontend and FastAPI backend. **Do not open `frontend/index.html` directly**: live hotel, flight, contact lookup, OTP, account, and map-related API flows require the backend server. The train section provides the travel flow and official IRCTC redirect; train schedules are not retrieved from SerpApi.

## Quick start on Linux, macOS, or Android Termux

1. Install Python 3.10 or newer.
2. Extract this ZIP.
3. Open a terminal in the extracted `connected` folder.
4. Run:

```bash
chmod +x start.sh setup-api-key.sh setup-email.sh
./start.sh
```

The first run creates `backend/.env`, creates a Python virtual environment, installs the complete dependency set, and asks for your **SerpApi API key** with hidden input. The launcher performs an import check before opening the app. The key is required for live hotel, flight, and hotel contact/phone results and is intentionally not included in the ZIP.

Open **http://localhost:8000/** after the server starts. Keep the terminal open while using the website. Press `Ctrl+C` to stop it.

## If you see “Unexpected token '<', "<!DOCTYPE" … is not valid JSON”

This means the frontend was opened through a static server instead of the FastAPI backend. Do not use a VS Code Live Server URL and do not double-click the HTML file. Run `start.bat`; it now opens Chrome automatically at `http://127.0.0.1:8000/`.

If you keep a separate frontend server open, close it and use the port-8000 URL.
If you must use a separate frontend server, the bundled frontend now automatically sends API calls to `http://127.0.0.1:8000`. For another computer or backend port, open the frontend with `?api=http://YOUR-HOST:8000`.

To diagnose terminal/CORS setup, run `./check-cors.sh` from the `connected` folder while the backend is running.

## Windows

Double-click `setup-api-key.bat`, enter your key in `backend\\.env`, save it, and then double-click `start.bat`.

## Manual start

```bash
cd backend
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
# Edit backend/.env and set SERPAPI_API_KEY=your_key
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Important configuration

```env
SERPAPI_API_KEY=your_serpapi_key
```

A private SerpApi key is the one requirement that cannot be bundled into a public ZIP. Without it, the app will start safely but real hotel and flight searches cannot be performed. The ZIP does not contain private credentials for security; the launcher asks for the key before starting.

You can configure the key separately on Linux/Android with:

```bash
./setup-api-key.sh
./start.sh
```

The key is stored only in your local private `backend/.env` file. Never open the HTML file with `file://` and expect live results.

For real email OTP delivery, run the included setup helper. It asks for the Gmail address and Google App Password locally, with the password hidden while typing:

```bash
chmod +x setup-email.sh
./setup-email.sh
```

It configures Gmail SMTP with a Google App Password in `backend/.env`:

```env
EMAIL_USER=you@gmail.com
EMAIL_PASS=your_google_app_password
EMAIL_FROM=you@gmail.com
```

Without SMTP configuration, development mode returns an OTP in the API response for local testing.

## Connected flows

- Hotel search: frontend → `POST /api/travel/hotels`
- Hotel provider contact lookup: `GET /api/travel/hotels/contact`
- Flight search: frontend → `POST /api/travel/flights`
- Combined search: `POST /api/travel/search`
- Health: `GET /api/health`
- Email OTP: `POST /api/send-otp` and `POST /api/verify-otp`
- Static frontend is served by FastAPI at `/`

The ZIP excludes private `.env` files, API keys, Gmail passwords, databases, and virtual environments. Configure your own SerpApi and SMTP credentials locally before starting the application.

## What is included
The running app uses its built-in email OTP/account flow and SQLite activity storage. Legacy unused authentication modules and their undeclared dependencies were removed so a fresh ZIP install does not fail on unrelated SQLAlchemy/FastAPI-Users imports.
