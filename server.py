"""Local server for Watering Can: serves the web app and saves plants to data/plants.json.

Run it with start.bat (or `python server.py`). Standard library only, so any Python 3.10+ works.
The plant agent (plant-agent/) reads and writes the same data/plants.json, so both stay in sync.
Every save also writes data/plants.xlsx, a read-only Excel copy of your plants and their history.
"""
from __future__ import annotations

import json
import os
import shutil
import socket
import sys
import tempfile
import threading
import webbrowser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "plant-agent"))
from agent.excel import write_xlsx as _write_xlsx  # noqa: E402  (shared with the plant agent)

DATA_DIR = ROOT / "data"
PLANTS_PATH = DATA_DIR / "plants.json"
XLSX_PATH = DATA_DIR / "plants.xlsx"
HOST, PORT = "127.0.0.1", 8765
STATIC = {"index.html", "css", "js"}  # only the app itself is served, never data/ or .env

_lock = threading.Lock()


# ---------- plants.json (same format and revision rules as plant-agent/agent/storage.py) ----------
def read() -> dict:
    if not PLANTS_PATH.exists():
        return {"rev": 0, "plants": []}
    data = json.loads(PLANTS_PATH.read_text(encoding="utf-8"))
    return {"rev": int(data.get("rev", 0)), "plants": list(data.get("plants", []))}


def write(plants: list[dict], expected_rev: int) -> tuple[bool, dict]:
    """Save the full list if nobody else saved since expected_rev. Returns (saved, current state)."""
    with _lock:
        current = read()
        if expected_rev != current["rev"]:
            return False, current
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        if PLANTS_PATH.exists():
            shutil.copyfile(PLANTS_PATH, PLANTS_PATH.with_suffix(".json.bak"))
        rev = current["rev"] + 1
        fd, tmp = tempfile.mkstemp(dir=DATA_DIR, prefix="plants-", suffix=".tmp")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump({"rev": rev, "plants": plants}, f, ensure_ascii=False, indent=1)
        os.replace(tmp, PLANTS_PATH)
        return True, {"rev": rev, "plants": plants}


def write_xlsx(plants: list[dict]) -> None:
    _write_xlsx(plants, XLSX_PATH)


# ---------- HTTP ----------
class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=str(ROOT), **kw)

    def log_message(self, fmt, *args):  # keep the console quiet apart from errors
        if args and str(args[1]).startswith(("4", "5")):
            super().log_message(fmt, *args)

    def _json(self, code: int, body: dict) -> None:
        raw = json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        path = self.path.split("?", 1)[0]
        if path == "/api/plants":
            return self._json(200, read())
        first = path.lstrip("/").split("/", 1)[0]
        if path != "/" and first not in STATIC:
            return self.send_error(404)
        return super().do_GET()

    def do_PUT(self):
        if self.path.split("?", 1)[0] != "/api/plants":
            return self.send_error(404)
        try:
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
            plants, rev = body["plants"], int(body["rev"])
            if not isinstance(plants, list):
                raise ValueError
        except (ValueError, KeyError, TypeError):
            return self._json(400, {"error": "Expected {rev, plants}."})
        saved, state = write(plants, rev)
        if not saved:
            return self._json(409, state)
        excel = True
        try:
            write_xlsx(plants)
        except PermissionError:
            excel = False  # plants.xlsx is open in Excel; plants.json is still saved
        return self._json(200, {"rev": state["rev"], "excel": excel})


def main() -> int:
    url = f"http://localhost:{PORT}/"
    with socket.socket() as s:
        if s.connect_ex((HOST, PORT)) == 0:
            print(f"Watering Can is already running. Opening {url}")
            webbrowser.open(url)
            return 0
    DATA_DIR.mkdir(exist_ok=True)
    if PLANTS_PATH.exists() and not XLSX_PATH.exists():
        try:
            write_xlsx(read()["plants"])
        except PermissionError:
            pass
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"Watering Can is running at {url}\nYour plants are saved in {PLANTS_PATH}\nClose this window to stop it.")
    webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
