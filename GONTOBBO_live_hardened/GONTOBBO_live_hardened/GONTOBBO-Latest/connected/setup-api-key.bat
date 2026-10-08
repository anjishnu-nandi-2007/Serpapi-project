@echo off
setlocal
cd /d "%~dp0"
if not exist backend\.env copy backend\.env.example backend\.env >nul
notepad backend\.env
echo.
echo Save the file with your SERPAPI_API_KEY, then run start.bat.
pause
