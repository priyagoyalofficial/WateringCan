"""data/plants.json: where plants are stored, shared with the web app (server.py).

Writes are atomic (temp file + rename), keep the previous version as plants.json.bak,
and carry a revision number so a stale writer can be refused instead of overwriting newer changes.
Every write also refreshes data/plants.xlsx, the Excel copy.
"""
from __future__ import annotations

import json
import os
import shutil
import tempfile
import threading
from typing import Callable

from .config import DATA_DIR, PLANTS_PATH
from .excel import write_xlsx

_lock = threading.RLock()


class Conflict(Exception):
    """The caller's copy is older than what's on disk."""


def read() -> dict:
    with _lock:
        if not PLANTS_PATH.exists():
            return {"rev": 0, "plants": []}
        data = json.loads(PLANTS_PATH.read_text(encoding="utf-8"))
        return {"rev": int(data.get("rev", 0)), "plants": list(data.get("plants", []))}


def write(plants: list[dict], expected_rev: int | None = None) -> int:
    """Save the full plant list. Returns the new revision."""
    with _lock:
        current = read()["rev"]
        if expected_rev is not None and expected_rev != current:
            raise Conflict(f"expected revision {expected_rev}, found {current}")
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        if PLANTS_PATH.exists():
            shutil.copyfile(PLANTS_PATH, PLANTS_PATH.with_suffix(".json.bak"))
        rev = current + 1
        fd, tmp = tempfile.mkstemp(dir=DATA_DIR, prefix="plants-", suffix=".tmp")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump({"rev": rev, "plants": plants}, f, ensure_ascii=False, indent=1)
        os.replace(tmp, PLANTS_PATH)
        try:
            write_xlsx(plants, DATA_DIR / "plants.xlsx")
        except PermissionError:
            pass  # open in Excel; plants.json is saved and the next write refreshes the copy
        return rev


def update(fn: Callable[[list[dict]], list[dict]]) -> int:
    """Read-modify-write under the lock, so agent changes never race each other."""
    with _lock:
        plants = read()["plants"]
        return write(fn(plants))
