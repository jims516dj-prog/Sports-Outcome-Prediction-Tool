@echo off
rem Double-click to start the Astrological Football Match Analyzer (Windows).
rem Opens two windows - the astrology service and the website - then your browser.
rem To stop the app, close those two windows.
setlocal
title Astro Football - starting
cd /d "%~dp0"
set "ROOT=%~dp0"

rem Already running? Just open the browser.
curl -s -o nul http://localhost:3000/api/stats && goto open

if not exist ".venv\Scripts\python.exe" (
  echo The Python environment is missing. Run these once in this folder, then try again:
  echo     py -3.11 -m venv .venv
  echo     .venv\Scripts\pip install -r services\python-astro\requirements.txt
  pause
  exit /b 1
)
if not exist "node_modules" (
  echo The website packages are missing. Run this once in this folder, then try again:
  echo     npm install
  pause
  exit /b 1
)
if not exist ".env" copy ".env.example" ".env" >nul

start "Astro service (keep open)" /D "%ROOT%services\python-astro" cmd /k ""%ROOT%.venv\Scripts\python.exe" -m uvicorn main:app --host 127.0.0.1 --port 8001"
start "Astro website (keep open)" /D "%ROOT%" cmd /k "npm run dev"

echo Starting the app - this takes about half a minute the first time...
set /a TRIES=0
:wait
curl -s -o nul http://localhost:3000/api/stats && goto open
set /a TRIES+=1
if %TRIES% GEQ 90 goto slow
timeout /t 2 /nobreak >nul
goto wait

:slow
echo The website has not answered after 3 minutes. Check the two app windows for an error message.
pause
exit /b 1

:open
start "" http://localhost:3000
exit /b 0
