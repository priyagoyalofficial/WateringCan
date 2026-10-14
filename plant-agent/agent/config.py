"""Paths and settings. Values come from environment variables, optionally loaded from .env."""
import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

DATA_DIR = ROOT / "data"
PLANTS_PATH = DATA_DIR / "plants.json"
REMINDERS_DIR = DATA_DIR / "reminders"
LIBRARY_PATH = ROOT / "library" / "species.json"

MODEL = os.getenv("WATERING_CAN_MODEL", "claude-opus-5")

# Daily reminder email (optional). Gmail needs an app password: https://myaccount.google.com/apppasswords
SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
REMINDER_TO = os.getenv("REMINDER_TO", SMTP_USER)


def api_key_configured() -> bool:
    return bool(os.getenv("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_AUTH_TOKEN"))


def email_configured() -> bool:
    return bool(SMTP_HOST and SMTP_USER and SMTP_PASSWORD and REMINDER_TO)
