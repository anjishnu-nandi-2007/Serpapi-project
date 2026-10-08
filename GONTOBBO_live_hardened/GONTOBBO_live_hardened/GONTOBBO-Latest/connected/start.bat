@echo off
setlocal
cd /d "%~dp0backend"
if not exist .env copy .env.example .env >nul
if not exist .venv python -m venv .venv
call .venv\Scripts\activate.bat
python -m pip install -q -r requirements.txt
findstr /R /C:"^SERPAPI_API_KEY=.[^=]*" .env >nul
if errorlevel 1 (
  echo Add your SerpApi key to backend\.env before starting live hotel and flight searches.
  notepad .env
)
echo GONTOBBO is running at http://localhost:8000
timeout /t 2 /nobreak >nul
start "" "http://127.0.0.1:8000/"
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
pause
