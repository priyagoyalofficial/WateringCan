"""Daily reminder: works out what's due, adds a weather-aware note from Claude, and emails it.

Run by Windows Task Scheduler via daily.bat (see README), or by hand:
    python -m agent.daily --dry-run
"""
from __future__ import annotations

import argparse
import smtplib
import sys
from datetime import date
from email.message import EmailMessage

from . import care, config, storage
from .assistant import morning_note


def due_lists(plants: list[dict], today: str) -> tuple[list[str], list[str], list[str]]:
    check, feed, tomorrow = [], [], []
    for p in plants:
        ws, fs = care.water_status(p, today), care.feed_status(p, today)
        where = "outdoor" if p.get("where") == "out" else "indoor"
        line = f"{p['name']} ({where}): {care.profile(p)['dry'].lower()}, then {care.amount(p)['short'].lower()}"
        if ws["kind"] in ("late", "today", "new"):
            late = f" [{-ws['d']} days overdue]" if ws["d"] < 0 else ""
            check.append(line + late)
        elif ws["d"] == 1:
            tomorrow.append(p["name"])
        if fs["kind"] == "due":
            feed.append(p["name"])
    return check, feed, tomorrow


def plain_summary(check: list[str], feed: list[str], tomorrow: list[str]) -> str:
    parts = []
    parts.append("Check the soil today:\n" + "\n".join(f"- {c}" for c in check) if check else "Nothing needs a soil check today.")
    if feed:
        parts.append("Fertilize (half strength, onto damp soil): " + ", ".join(feed))
    if tomorrow:
        parts.append("Coming up tomorrow: " + ", ".join(tomorrow))
    return "\n\n".join(parts)


def send_email(subject: str, body: str) -> None:
    msg = EmailMessage()
    msg["Subject"], msg["From"], msg["To"] = subject, config.SMTP_USER, config.REMINDER_TO
    msg.set_content(body)
    with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT, timeout=30) as s:
        s.starttls()
        s.login(config.SMTP_USER, config.SMTP_PASSWORD)
        s.send_message(msg)


def main() -> int:
    ap = argparse.ArgumentParser(description="Send today's Watering Can reminder.")
    ap.add_argument("--dry-run", action="store_true", help="print the reminder instead of emailing it")
    ap.add_argument("--no-ai", action="store_true", help="skip Claude and the weather lookup")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")  # Windows consoles default to cp1252, which garbles ¾ and ½

    today = date.today().isoformat()
    plants = storage.read()["plants"]
    if not plants:
        print("No plants saved yet. Nothing to remind about.")
        return 0

    check, feed, tomorrow = due_lists(plants, today)
    summary = plain_summary(check, feed, tomorrow)
    body = summary
    if config.api_key_configured() and not args.no_ai:
        try:
            body = f"{morning_note(summary, today)}\n\n---\n{summary}"
        except Exception as e:  # the plain summary is still useful without the weather note
            body = f"{summary}\n\n(Weather note unavailable: {e})"

    n = len(check)
    subject = f"Watering Can: {n} plant{'s' if n != 1 else ''} to check today" if n else "Watering Can: nothing due today"
    body += "\n\nTell the assistant what you did: run chat.bat"

    config.REMINDERS_DIR.mkdir(parents=True, exist_ok=True)
    saved = config.REMINDERS_DIR / f"{today}.txt"
    saved.write_text(f"{subject}\n\n{body}\n", encoding="utf-8")

    if args.dry_run or not config.email_configured():
        print(f"{subject}\n\n{body}\n")
        if not args.dry_run:
            print("Email isn't set up in .env, so the reminder was only saved to", saved)
        return 0
    try:
        send_email(subject, body)
    except (smtplib.SMTPException, OSError) as e:
        print(f"Couldn't send the email: {e}. The reminder is saved at {saved}", file=sys.stderr)
        return 1
    print(f"Sent to {config.REMINDER_TO}. Copy saved at {saved}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
