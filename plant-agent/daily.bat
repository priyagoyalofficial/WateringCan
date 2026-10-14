@echo off
rem Sends today's plant reminder. Scheduled with Windows Task Scheduler (see README).
cd /d "%~dp0"
if not exist "..\data\reminders" mkdir "..\data\reminders"
".venv\Scripts\python.exe" -m agent.daily >> "..\data\reminders\daily.log" 2>&1
