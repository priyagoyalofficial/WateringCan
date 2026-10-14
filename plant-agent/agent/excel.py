"""data/plants.xlsx: a read-only Excel copy of the plants, rewritten on every save.

Standard library only, because the web app's server.py imports it too and runs without the agent's packages.
"""
from __future__ import annotations

import json
import os
import tempfile
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

LIBRARY_PATH = Path(__file__).resolve().parent.parent / "library" / "species.json"
POT = {"plastic": "Plastic / glazed", "terracotta": "Terracotta", "selfwater": "Self-watering", "ground": "In the ground"}
ACTION = {"water": "Watered", "feed": "Fertilized", "skip": "Still damp, skipped", "note": "Note"}


def _species_names() -> dict:
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


def write_xlsx(plants: list[dict], path: Path) -> None:
    """Write the workbook atomically. Raises PermissionError if the file is open in Excel."""
    names = _species_names()
    kind = lambda p: (p.get("custom") or {}).get("n") or names.get(p.get("species"), p.get("species", ""))
    plant_rows = [["Name", "Type", "Indoor/Outdoor", "Spot", "Pot", "Pot width (in)", "Soil",
                   "Last watered", "Last fertilized", "Added", "Learned factor"]]
    log_rows = [["Date", "Plant", "Action", "Note"]]
    for p in sorted(plants, key=lambda p: p.get("name", "").lower()):
        plant_rows.append([p.get("name"), kind(p), "Outdoor" if p.get("where") == "out" else "Indoor", p.get("spot"),
                           POT.get(p.get("pot"), p.get("pot")), p.get("size"), p.get("soil"),
                           p.get("lastWatered"), p.get("lastFed"), p.get("created"), p.get("learned")])
        for e in p.get("log") or []:
            log_rows.append([e.get("d"), p.get("name"), ACTION.get(e.get("t"), e.get("t")), e.get("note")])
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
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix="plants-", suffix=".xlsx.tmp")
    os.close(fd)
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as z:
        for name, body in files.items():
            z.writestr(name, body)
    try:
        os.replace(tmp, path)
    except PermissionError:
        os.remove(tmp)
        raise
