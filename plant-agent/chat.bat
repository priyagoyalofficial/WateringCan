@echo off
rem Opens a chat with the Watering Can plant-care agent.
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Setting up for the first time...
  python -m venv .venv || goto :error
  ".venv\Scripts\python.exe" -m pip install -r requirements.txt || goto :error
)
if not exist ".env" (
  copy ".env.example" ".env" >nul
  echo Created .env. Add your ANTHROPIC_API_KEY to it, then run chat.bat again.
  notepad .env
  goto :eof
)
".venv\Scripts\python.exe" -m agent.chat %*
goto :eof

:error
echo Setup failed. Make sure Python 3.10 or newer is installed and on your PATH.
pause
