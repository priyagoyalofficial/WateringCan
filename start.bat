@echo off
rem Starts Watering Can and opens it in your browser. Keep this window open while you use the app.
cd /d "%~dp0"
python server.py
if errorlevel 1 (
  echo.
  echo Couldn't start Watering Can. Make sure Python 3.10 or newer is installed and on your PATH.
  pause
)
