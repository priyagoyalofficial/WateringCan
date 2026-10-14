"""Schedule, water-amount and learning rules for Anaheim, CA (USDA zone 10b)."""
from __future__ import annotations

import copy
import json
import math
import random
import string
import time
from datetime import date, timedelta

from .config import LIBRARY_PATH

SEASON = [1.4, 1.3, 1.1, 1.0, 0.95, 0.85, 0.8, 0.8, 0.85, 0.95, 1.15, 1.4]  # Anaheim, Jan..Dec
POT = {"plastic": 1.0, "terracotta": 0.8, "selfwater": 1.6, "ground": 1.3}
SOIL = {"regular": 1.0, "chunky": 0.8, "cactus": 0.9, "bark": 0.85, "leca": 1.4, "garden": 1.1}
WIDTHS = [3, 4, 5, 6, 8, 10, 12, 14, 16, 20]
STYLES = ["normal", "dry", "moist", "soak"]
DEFAULT_PROFILE = {
    "n": "Plant", "l": "", "w": "in", "days": 7, "dry": "Top 1–2 in dry", "light": "Bright indirect",
    "feed": 30, "tip": "Check the soil with your finger before every watering.", "st": "normal",
}
LOG_LIMIT = 80


def _load_species() -> list[dict]:
    raw = json.loads(LIBRARY_PATH.read_text(encoding="utf-8"))
    return [
        {"k": s["key"], "n": s["name"], "l": s["latin"], "w": s["grown"], "days": s["days"], "dry": s["dry"],
         "light": s["light"], "feed": s["feed"], "st": s["style"], "tip": s["tip"]}
        for s in raw
    ]


SPECIES = _load_species()
SP = {s["k"]: s for s in SPECIES}


# ---------- small helpers ----------
def js_round(x: float) -> int:
    """Round halves up (Python's round() rounds halves to even)."""
    return math.floor(x + 0.5)


def clamp(v: float, lo: float, hi: float) -> float:
    return min(hi, max(lo, v))


def parse(s: str) -> date:
    return date.fromisoformat(s)


def add_days(s: str, n: int) -> str:
    return (parse(s) + timedelta(days=n)).isoformat()


def diff(a: str, b: str) -> int:
    return (parse(b) - parse(a)).days


def fmt(s: str) -> str:
    d = parse(s)
    return f"{d.strftime('%a')}, {d.strftime('%b')} {d.day}"


def new_id() -> str:
    alphabet = string.digits + string.ascii_lowercase
    n, out = int(time.time() * 1000), ""
    while n:
        n, r = divmod(n, 36)
        out = alphabet[r] + out
    return "p" + out + "".join(random.choice(alphabet) for _ in range(4))


def snap_width(inches: float) -> int:
    return min(WIDTHS, key=lambda w: abs(w - inches))


# ---------- care math ----------
def profile(p: dict) -> dict:
    return p.get("custom") or SP.get(p.get("species")) or DEFAULT_PROFILE


def pot_in(p: dict) -> float:
    size = p.get("size")
    legacy = {"s": 5, "m": 8, "l": 12}
    if size in legacy:
        return legacy[size]
    try:
        return float(size) or 6
    except (TypeError, ValueError):
        return 6


def size_factor(p: dict) -> float:
    return clamp(math.sqrt(pot_in(p) / 7), 0.7, 1.5)


def base_interval(p: dict, on: str) -> float:
    sp = profile(p)
    m = parse(on).month - 1
    loc = 1.0
    if p.get("where") == "out" and sp.get("w") == "in":
        loc = 0.7
    if p.get("where") == "in" and sp.get("w") == "out":
        loc = 1.3
    return sp["days"] * SEASON[m] * POT.get(p.get("pot"), 1) * size_factor(p) * SOIL.get(p.get("soil"), 1) * loc


def interval(p: dict, on: str) -> int:
    return max(1, js_round(base_interval(p, on) * (p.get("learned") or 1)))


def water_status(p: dict, today: str) -> dict:
    if not p.get("lastWatered"):
        return {"kind": "new", "due": today, "d": 0, "frac": 0, "iv": interval(p, today)}
    iv = interval(p, today)
    due, snoozed = add_days(p["lastWatered"], iv), False
    if p.get("checkAfter") and p["checkAfter"] > p["lastWatered"]:
        due, snoozed = p["checkAfter"], True
    d = diff(today, due)
    frac = clamp(1 - diff(p["lastWatered"], today) / iv, 0, 1)
    kind = "late" if d < 0 else "today" if d == 0 else "snooze" if snoozed else "ok"
    return {"kind": kind, "due": due, "d": d, "frac": frac, "iv": iv, "snoozed": snoozed}


def feed_status(p: dict, today: str) -> dict:
    sp = profile(p)
    if not sp.get("feed"):
        return {"kind": "none"}
    m = parse(today).month - 1
    if m == 11 or m <= 1:
        return {"kind": "rest"}
    fi = sp["feed"] * (2 if m in (9, 10) else 1)
    if not p.get("lastFed"):
        return {"kind": "due", "due": today, "fi": fi}
    due = add_days(p["lastFed"], fi)
    return {"kind": "due" if due <= today else "ok", "due": due, "fi": fi}


def water_style(p: dict) -> str:
    return profile(p).get("st") or "normal"


def cups_text(c: float) -> str:
    ml = js_round(c * 237 / 10) * 10
    if c >= 8:
        qt = js_round(c / 4 * 2) / 2
        return f"{qt:g} quarts ({ml / 1000:.1f} L)"
    q = max(0.25, js_round(c * 4) / 4)
    w = math.floor(q)
    frac = q - w
    fr = {0.25: "¼", 0.5: "½", 0.75: "¾"}.get(frac, "")
    return f"{w or ''}{fr or ('' if w else '¼')} cup{'s' if q > 1 else ''} ({ml} ml)"


def amount(p: dict) -> dict:
    """How much to water. Rough pot volume: tapered pot, height ≈ width → ~0.0326·d³ cups; a soak is ~25%."""
    d, st = pot_in(p), water_style(p)
    if p.get("pot") == "ground":
        return {"short": "2–3 gallons, slowly at the base" if d >= 12 else "1–2 gallons, slowly at the base",
                "how": "Let a hose trickle at the base for 10–15 minutes so the water sinks deep instead of running off."}
    if p.get("soil") == "leca":
        return {"short": "Top up the reservoir to ⅓ of the pot height",
                "how": "Keep water only in the bottom third. Let it run out for a day or two before topping up."}
    if p.get("pot") == "selfwater":
        return {"short": "Fill the reservoir",
                "how": "Refill only once the reservoir has been empty for a day or two."}
    if st == "soak":
        return {"short": "Soak the pot 10 min, then drain",
                "how": "Set the pot in room-temperature water for 10 minutes, then drain it completely."}
    frac = 0.22 if st == "dry" else 0.18 if st == "moist" else 0.25
    c = 0.0326 * d ** 3 * frac * (1.1 if p.get("soil") == "chunky" or p.get("pot") == "terracotta" else 1)
    how = {
        "dry": "Soak thoroughly once the soil is fully dry, then leave it alone.",
        "moist": "Give smaller drinks more often so the soil stays evenly damp, never soggy.",
    }.get(st, "Pour slowly until about 10–20% runs out the drainage hole.")
    how += " Empty the saucer after 15 minutes."
    if p.get("soil") == "chunky":
        how += " Chunky mix drains fast. Pour half, wait 5 minutes, then pour the rest."
    return {"short": f"About {cups_text(c)}", "how": how}


# ---------- actions ----------
def _push_log(p: dict, entry: dict) -> None:
    p["log"] = [entry, *(p.get("log") or [])][:LOG_LIMIT]


def log_watering(p: dict, today: str, bone_dry: bool = False, when: str | None = None) -> dict:
    np = copy.deepcopy(p)
    if when and when < today:  # a watering logged after the fact: recorded, but the schedule does not learn from it
        _push_log(np, {"t": "water", "d": when, "note": "logged later"})
        np["log"].sort(key=lambda e: e["d"], reverse=True)
        if not np.get("lastWatered") or when > np["lastWatered"]:
            np["lastWatered"] = when
            if np.get("checkAfter") and np["checkAfter"] <= when:
                np.pop("checkAfter")
        return np
    if np.get("lastWatered"):
        actual = diff(np["lastWatered"], today)
        had_skip = any(e.get("t") == "skip" and e.get("d", "") > np["lastWatered"] for e in np.get("log") or [])
        base = base_interval(np, today)
        L = np.get("learned") or 1
        if bone_dry:
            L *= 0.85
        elif not had_skip and actual > 0 and actual <= interval(np, today) + 1:
            L = 0.75 * L + 0.25 * (actual / base)
        np["learned"] = round(clamp(L, 0.5, 2), 3)
    np["lastWatered"] = today
    np.pop("checkAfter", None)
    _push_log(np, {"t": "water", "d": today, "note": "bone dry" if bone_dry else ""})
    return np


def log_still_damp(p: dict, today: str) -> dict:
    np = copy.deepcopy(p)
    iv = interval(np, today)
    np["learned"] = round(clamp((np.get("learned") or 1) * 1.1, 0.5, 2), 3)
    np["checkAfter"] = add_days(today, max(1, js_round(iv * 0.25)))
    _push_log(np, {"t": "skip", "d": today, "note": "soil still damp"})
    return np


def log_feeding(p: dict, today: str, when: str | None = None) -> dict:
    np = copy.deepcopy(p)
    day = when if when and when < today else today
    _push_log(np, {"t": "feed", "d": day, "note": "logged later" if day != today else ""})
    np["log"].sort(key=lambda e: e["d"], reverse=True)
    if not np.get("lastFed") or day > np["lastFed"]:
        np["lastFed"] = day
    return np


def add_note(p: dict, today: str, text: str) -> dict:
    np = copy.deepcopy(p)
    _push_log(np, {"t": "note", "d": today, "note": text})
    return np


# ---------- hydration, filters and overview (same rules as the web app's header boxes and Dashboard tab) ----------
HYDRATION = {"ok": "hydrated", "snooze": "hydrated", "today": "drying", "late": "dehydrated", "new": "not_tracked"}
HYDRATION_LABEL = {"hydrated": "Hydrated", "drying": "Drying, check today",
                   "dehydrated": "Dehydrated, overdue", "not_tracked": "Not tracked yet"}
FILTERS = {  # the web app's clickable Overdue / Check today / To fertilize boxes
    "overdue": lambda p, today: water_status(p, today)["kind"] == "late",
    "check_today": lambda p, today: water_status(p, today)["kind"] in ("today", "new"),
    "fertilize": lambda p, today: feed_status(p, today)["kind"] == "due",
}


def hydration(p: dict, today: str) -> str:
    """hydrated (incl. 'still damp' rechecks), drying (check today), dehydrated (overdue) or not_tracked."""
    return HYDRATION[water_status(p, today)["kind"]]


def needs_attention(p: dict, today: str) -> bool:
    return water_status(p, today)["kind"] in ("late", "today", "new") or feed_status(p, today)["kind"] == "due"


def percent(n: int, total: int) -> int:
    return js_round(n / total * 100) if total else 0


def overview(plants: list[dict], today: str) -> dict:
    """The numbers on the web app's Dashboard tab."""
    total = len(plants)
    counts = {k: sum(hydration(p, today) == k for p in plants) for k in HYDRATION_LABEL}
    tracked = [ws["frac"] for ws in (water_status(p, today) for p in plants) if ws["kind"] != "new"]
    attention = sum(needs_attention(p, today) for p in plants)
    return {
        "total_plants": total,
        "hydrated_percent": percent(counts["hydrated"], total),
        "hydration": [{"status": k, "label": HYDRATION_LABEL[k], "plants": counts[k], "percent": percent(counts[k], total)}
                      for k in HYDRATION_LABEL],
        "need_attention": attention,
        "need_attention_percent": percent(attention, total),
        "overdue": sum(FILTERS["overdue"](p, today) for p in plants),
        "check_today": sum(FILTERS["check_today"](p, today) for p in plants),
        "to_fertilize": sum(FILTERS["fertilize"](p, today) for p in plants),
        "avg_moisture_left_percent": js_round(sum(tracked) / len(tracked) * 100) if tracked else None,
    }


# ---------- descriptions for the agent ----------
def status_text(p: dict, today: str) -> str:
    ws = water_status(p, today)
    if ws["kind"] == "new":
        return "no watering logged yet"
    if ws["d"] < 0:
        return f"overdue by {-ws['d']} day{'s' if ws['d'] < -1 else ''} (check soil now)"
    if ws["d"] == 0:
        return "due for a soil check today"
    prefix = "rechecking after 'still damp'" if ws["kind"] == "snooze" else "next soil check"
    return f"{prefix} {fmt(ws['due'])} (in {ws['d']} day{'s' if ws['d'] > 1 else ''})"


def feed_text(p: dict, today: str) -> str:
    fs = feed_status(p, today)
    if fs["kind"] == "none":
        return "rarely needs fertilizer"
    if fs["kind"] == "rest":
        return "fertilizer paused for winter (Dec–Feb)"
    if fs["kind"] == "due":
        return f"fertilizer due now (every ~{fs['fi']} days this month)"
    return f"next fertilizer {fmt(fs['due'])} (every ~{fs['fi']} days this month)"


def summarize(p: dict, today: str) -> dict:
    sp = profile(p)
    learned = p.get("learned") or 1
    ws = water_status(p, today)
    return {
        "id": p["id"],
        "name": p["name"],
        "type": sp["n"],
        "where": "outdoors" if p.get("where") == "out" else "indoors",
        "spot": p.get("spot") or "",
        "pot": f"{pot_in(p):g}-inch {p.get('pot', 'plastic')}",
        "soil": p.get("soil", "regular"),
        "last_watered": p.get("lastWatered"),
        "watering": status_text(p, today),
        "hydration": HYDRATION_LABEL[hydration(p, today)],
        "moisture_left_percent": None if ws["kind"] == "new" else js_round(ws["frac"] * 100),
        "interval_days_now": ws["iv"],
        "water_when": sp["dry"],
        "water_amount": amount(p)["short"],
        "fertilizer": feed_text(p, today),
        "tuned_to_home": "following the care guide" if abs(learned - 1) < 0.04
        else f"goes {round(abs(learned - 1) * 100)}% {'faster' if learned < 1 else 'longer'} between waterings than the guide",
    }
