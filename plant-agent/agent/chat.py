"""Chat with the Watering Can agent in the terminal.

    python -m agent.chat                     start chatting
    python -m agent.chat --import FILE.json  load plants from a Watering Can backup file

In the chat:
    /photo PATH [message]   send a photo of a plant, e.g. /photo C:\\pics\\fig.jpg brown spots on my fiddle leaf
    /plants                 quick list of what's due (no AI call)
    /new                    start a new conversation
    /quit                   exit
"""
from __future__ import annotations

import argparse
import base64
import json
import shlex
import sys
from datetime import date
from pathlib import Path

import anthropic

from . import care, config, storage
from .assistant import chat

IMAGE_TYPES = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp", ".gif": "image/gif"}
MAX_IMAGE_BYTES = 5 * 1024 * 1024  # Claude API limit per image


def load_photo(path_text: str) -> dict:
    path = Path(path_text.strip('"')).expanduser()
    if not path.is_file():
        raise ValueError(f"No file at {path}")
    media_type = IMAGE_TYPES.get(path.suffix.lower())
    if not media_type:
        raise ValueError("Use a .jpg, .png, .webp or .gif photo.")
    data = path.read_bytes()
    if len(data) > MAX_IMAGE_BYTES:
        raise ValueError(f"That photo is {len(data) / 1e6:.1f} MB. Photos must be under 5 MB, so resize it first.")
    return {"media_type": media_type, "data": base64.standard_b64encode(data).decode("ascii")}


def print_due() -> None:
    today = date.today().isoformat()
    plants = storage.read()["plants"]
    if not plants:
        print("No plants yet. Tell me about one, e.g. 'I have a pothos in a 6-inch plastic pot by the kitchen window.'")
        return
    rows = sorted(plants, key=lambda p: care.water_status(p, today)["d"])
    for p in rows:
        fed = care.feed_status(p, today)["kind"] == "due"
        print(f"  {p['name']}: {care.status_text(p, today)}; {care.amount(p)['short'].lower()}" + ("; fertilizer due" if fed else ""))


def import_backup(file: str) -> int:
    try:
        data = json.loads(Path(file).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        print(f"Couldn't read {file}: {e}")
        return 1
    plants = data if isinstance(data, list) else data.get("plants") if isinstance(data, dict) else None
    if not isinstance(plants, list) or not all(isinstance(p, dict) and p.get("id") and p.get("name") and p.get("species") for p in plants):
        print("That file doesn't look like a Watering Can backup.")
        return 1
    existing = storage.read()["plants"]
    if existing and input(f"Replace your {len(existing)} saved plants with the {len(plants)} in this file? [y/N] ").strip().lower() != "y":
        print("Nothing changed.")
        return 0
    storage.write(plants)
    print(f"Imported {len(plants)} plants.")
    return 0


def main() -> int:
    for stream in (sys.stdout, sys.stdin):
        stream.reconfigure(encoding="utf-8")  # Windows consoles default to cp1252, which garbles ¾ and ½
    ap = argparse.ArgumentParser(description="Chat with the Watering Can plant-care agent.")
    ap.add_argument("--import", dest="import_file", metavar="FILE", help="load plants from a backup JSON file")
    args = ap.parse_args()
    if args.import_file:
        return import_backup(args.import_file)

    if not config.api_key_configured():
        print("Add your Claude API key to .env as ANTHROPIC_API_KEY=... (see .env.example), then run this again.")
        return 1

    print("Watering Can. Tell me what you did or ask about your plants.")
    print("Commands: /photo PATH [message], /plants, /new, /quit\n")
    history: list[dict] = []
    while True:
        try:
            line = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        if not line:
            continue
        if line in ("/quit", "/exit"):
            return 0
        if line == "/new":
            history = []
            print("Started a new conversation.\n")
            continue
        if line == "/plants":
            print_due()
            print()
            continue

        image = None
        if line.startswith("/photo"):
            try:
                parts = shlex.split(line[len("/photo"):], posix=False)
                if not parts:
                    raise ValueError("Usage: /photo PATH [message]")
                image = load_photo(parts[0])
                line = " ".join(parts[1:]) or "What do you see in this photo? Is anything wrong with this plant?"
            except ValueError as e:
                print(f"{e}\n")
                continue

        history.append({"role": "user", "text": line})
        print("…thinking")
        try:
            result = chat(history, image)
        except anthropic.AuthenticationError:
            print("Claude rejected the API key. Check ANTHROPIC_API_KEY in .env.\n")
            history.pop()
            continue
        except anthropic.RateLimitError:
            print("Too many requests right now. Wait a minute and try again.\n")
            history.pop()
            continue
        except anthropic.APIStatusError as e:
            print(f"Claude had a problem ({e.status_code}): {e.message}\n")
            history.pop()
            continue
        except anthropic.APIConnectionError:
            print("Couldn't reach Claude. Check your internet connection.\n")
            history.pop()
            continue

        if image:  # later turns don't re-send the photo; just note it was shared
            history[-1]["text"] += "\n[A photo was attached to this message.]"
        history.append({"role": "assistant", "text": result["reply"]})
        print(f"\nassistant> {result['reply']}")
        for action in result["actions"]:
            print(f"  ✓ {action}")
        print()


if __name__ == "__main__":
    sys.exit(main())
