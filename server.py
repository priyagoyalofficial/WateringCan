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
import zipfile
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
PLANTS_PATH = DATA_DIR / "plants.json"
XLSX_PATH = DATA_DIR / "plants.xlsx"
LIBRARY_PATH = ROOT / "plant-agent" / "library" / "species.json"
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


# ---------- plants.xlsx (a minimal Office Open XML workbook, no extra packages needed) ----------
def species_names() -> dict:
    try:
        return {s["key"]: s["name"] for s in json.loads(LIBRARY_PATH.read_text(encoding="utf-8"))}
    except (OSError, ValueError, KeyError):
        return {}


def _col(i: int) -> str:
    s = ""
    i += 1
    while i:
        i, r = divmod(i - 1, 26)
        s = chr(65 + r) + s
    return s


def _sheet(rows: list[list], widths: list[int]) -> str:
    cols = "".join(f'<col min="{i+1}" max="{i+1}" width="{w}" customWidth="1"/>' for i, w in enumerate(widths))
    out = []
    for r, row in enumerate(rows, start=1):
        cells = []
        for c, v in enumerate(row):
            ref, style = f"{_col(c)}{r}", ' s="1"' if r == 1 else ""
            if v is None or v == "":
                continue
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                cells.append(f'<c r="{ref}"{style}><v>{v}</v></c>')
            else:
                cells.append(f'<c r="{ref}" t="inlineStr"{style}><is><t xml:space="preserve">{escape(str(v))}</t></is></c>')
        out.append(f'<row r="{r}">{"".join(cells)}</row>')
    return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            '<sheetViews><sheetView workbookViewId="0"><pane ySplit="1" topLeftCell="A2" state="frozen"/></sheetView></sheetViews>'
            f'<cols>{cols}</cols><sheetData>{"".join(out)}</sheetData></worksheet>')


def write_xlsx(plants: list[dict]) -> None:
    names = species_names()
    kind = lambda p: (p.get("custom") or {}).get("n") or names.get(p.get("species"), p.get("species", ""))
    pot = {"plastic": "Plastic / glazed", "terracotta": "Terracotta", "selfwater": "Self-watering", "ground": "In the ground"}
    action = {"water": "Watered", "feed": "Fertilized", "skip": "Still damp, skipped"}
    plant_rows = [["Name", "Type", "Indoor/Outdoor", "Spot", "Pot", "Pot width (in)", "Soil",
                   "Last watered", "Last fertilized", "Added", "Learned factor"]]
    log_rows = [["Date", "Plant", "Action", "Note"]]
    for p in sorted(plants, key=lambda p: p.get("name", "").lower()):
        plant_rows.append([p.get("name"), kind(p), "Outdoor" if p.get("where") == "out" else "Indoor", p.get("spot"),
                           pot.get(p.get("pot"), p.get("pot")), p.get("size"), p.get("soil"),
                           p.get("lastWatered"), p.get("lastFed"), p.get("created"), p.get("learned")])
        for e in p.get("log") or []:
            log_rows.append([e.get("d"), p.get("name"), action.get(e.get("t"), e.get("t")), e.get("note")])
    log_rows[1:] = sorted(log_rows[1:], key=lambda r: r[0] or "", reverse=True)

    files = {
        "[Content_Types].xml": '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/><Override PartName="/xl/worksheets/sheet2.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/><Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/></Types>',
        "_rels/.rels": '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>',
        "xl/workbook.xml": '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Plants" sheetId="1" r:id="rId1"/><sheet name="Log" sheetId="2" r:id="rId2"/></sheets></workbook>',
        "xl/_rels/workbook.xml.rels": '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/><Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet2.xml"/><Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/></Relationships>',
        "xl/styles.xml": '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><fonts count="2"><font><sz val="11"/><name val="Calibri"/></font><font><b/><sz val="11"/><name val="Calibri"/></font></fonts><fills count="2"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill></fills><borders count="1"><border/></borders><cellStyleXfs count="1"><xf/></cellStyleXfs><cellXfs count="2"><xf/><xf fontId="1" applyFont="1"/></cellXfs></styleSheet>',
        "xl/worksheets/sheet1.xml": _sheet(plant_rows, [22, 24, 14, 20, 18, 14, 12, 14, 15, 12, 14]),
        "xl/worksheets/sheet2.xml": _sheet(log_rows, [12, 22, 20, 30]),
    }
    fd, tmp = tempfile.mkstemp(dir=DATA_DIR, prefix="plants-", suffix=".xlsx.tmp")
    os.close(fd)
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as z:
        for name, body in files.items():
            z.writestr(name, body)
    try:
        os.replace(tmp, XLSX_PATH)
    except PermissionError:
        os.remove(tmp)
        raise


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
