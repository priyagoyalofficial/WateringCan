"""Tools the agent can call. Each one reads or changes data/plants.json through storage.py."""
from __future__ import annotations

import json
from typing import Any

from . import care, storage

WHERE = ["in", "out"]
POTS = ["plastic", "terracotta", "selfwater", "ground"]
SOILS = ["regular", "chunky", "cactus", "bark", "leca", "garden"]

_date = {"type": "string", "description": "ISO date YYYY-MM-DD. Omit for today."}

TOOLS: list[dict] = [
    {
        "name": "list_plants",
        "description": "List every plant with its watering status, next soil-check date, water amount and fertilizer status. "
                       "Call this first whenever you need plant ids or need to know what's due.",
        "input_schema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "get_plant",
        "description": "Full details for one plant: care profile (light, when to water, tip), pot and soil, "
                       "how much and how to water, and its recent history of waterings, 'still damp' checks, feedings and notes. "
                       "Use this before diagnosing a problem.",
        "input_schema": {
            "type": "object",
            "properties": {"plant_id": {"type": "string"}},
            "required": ["plant_id"],
            "additionalProperties": False,
        },
    },
    {
        "name": "log_care",
        "description": "Record what the gardener did or found for one plant. "
                       "'watered' = they watered it (set soil to 'bone_dry' if it was bone dry or drooping, otherwise 'dry'). "
                       "'still_damp' = they checked and the soil was still damp so they did NOT water; this pushes the next check out "
                       "and teaches the schedule to wait longer. 'fertilized' = they fed it. "
                       "Past dates are allowed for 'watered' and 'fertilized' only.",
        "input_schema": {
            "type": "object",
            "properties": {
                "plant_id": {"type": "string"},
                "action": {"type": "string", "enum": ["watered", "still_damp", "fertilized"]},
                "soil": {"type": "string", "enum": ["dry", "bone_dry"], "description": "Only for 'watered'."},
                "date": _date,
            },
            "required": ["plant_id", "action"],
            "additionalProperties": False,
        },
    },
    {
        "name": "add_plant",
        "description": "Add a new plant. Use a species key from the library when one fits. Otherwise use species 'other' "
                       "and give a custom_profile, researched with web search when you are not sure of its needs.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Nickname, e.g. 'Kitchen pothos'."},
                "species": {"type": "string", "description": "Library key (see system prompt) or 'other'."},
                "where": {"type": "string", "enum": WHERE},
                "spot": {"type": "string", "description": "e.g. 'east window'. Empty if unknown."},
                "pot": {"type": "string", "enum": POTS},
                "pot_width_in": {"type": "number", "description": "Pot width in inches. Default 6 if unknown."},
                "soil": {"type": "string", "enum": SOILS},
                "last_watered": _date,
                "custom_profile": {
                    "type": "object",
                    "description": "Required when species is 'other'.",
                    "properties": {
                        "common_name": {"type": "string"},
                        "botanical_name": {"type": "string"},
                        "grown": {"type": "string", "enum": WHERE, "description": "Where it's usually grown."},
                        "days": {"type": "integer", "description": "Typical days between waterings in spring, 6-inch plastic pot, regular mix."},
                        "dry": {"type": "string", "description": "How dry before watering, e.g. 'Top 2 in dry'."},
                        "light": {"type": "string"},
                        "feed": {"type": "integer", "description": "Days between feedings in the growing season; 0 if it rarely needs it."},
                        "style": {"type": "string", "enum": care.STYLES,
                                  "description": "dry = let dry fully (succulents); moist = keep evenly damp; soak = bark-grown epiphytes; else normal."},
                        "tip": {"type": "string", "description": "One practical sentence."},
                    },
                    "required": ["common_name", "grown", "days", "dry", "light", "feed", "style", "tip"],
                    "additionalProperties": False,
                },
            },
            "required": ["name", "species", "where", "pot", "pot_width_in", "soil"],
            "additionalProperties": False,
        },
    },
    {
        "name": "update_plant",
        "description": "Change a plant's details after repotting, moving it, or renaming it. Only include fields that change. "
                       "Set reset_learning after a repot or a big move, because the old schedule no longer applies.",
        "input_schema": {
            "type": "object",
            "properties": {
                "plant_id": {"type": "string"},
                "name": {"type": "string"},
                "where": {"type": "string", "enum": WHERE},
                "spot": {"type": "string"},
                "pot": {"type": "string", "enum": POTS},
                "pot_width_in": {"type": "number"},
                "soil": {"type": "string", "enum": SOILS},
                "reset_learning": {"type": "boolean"},
            },
            "required": ["plant_id"],
            "additionalProperties": False,
        },
    },
    {
        "name": "remove_plant",
        "description": "Permanently remove a plant and its history. Only call this after the gardener has explicitly "
                       "confirmed, in this conversation, that this specific plant should be removed.",
        "input_schema": {
            "type": "object",
            "properties": {
                "plant_id": {"type": "string"},
                "confirmed": {"type": "boolean", "description": "True only if the gardener explicitly confirmed."},
            },
            "required": ["plant_id", "confirmed"],
            "additionalProperties": False,
        },
    },
    {
        "name": "add_note",
        "description": "Save a short dated note to a plant's history, e.g. a diagnosis from a photo, a pest found, or a repot. "
                       "Keep it under 200 characters.",
        "input_schema": {
            "type": "object",
            "properties": {"plant_id": {"type": "string"}, "text": {"type": "string"}},
            "required": ["plant_id", "text"],
            "additionalProperties": False,
        },
    },
]


class ToolError(Exception):
    pass


class Toolbox:
    """Runs tool calls for one conversation turn and records what changed, for the chat UI."""

    def __init__(self, today: str):
        self.today = today
        self.actions: list[str] = []
        self.changed = False

    # --- dispatch ---
    def run(self, name: str, args: dict[str, Any]) -> str:
        handler = getattr(self, f"_{name}", None)
        if handler is None or name not in {t["name"] for t in TOOLS}:
            raise ToolError(f"Unknown tool '{name}'.")
        return json.dumps(handler(**args), ensure_ascii=False)

    # --- helpers ---
    def _find(self, plants: list[dict], plant_id: str) -> dict:
        for p in plants:
            if p.get("id") == plant_id:
                return p
        known = ", ".join(f"{p['id']} ({p['name']})" for p in plants) or "none"
        raise ToolError(f"No plant with id '{plant_id}'. Known plants: {known}.")

    def _check_date(self, value: str | None) -> str | None:
        if not value:
            return None
        try:
            d = care.parse(value).isoformat()
        except ValueError:
            raise ToolError(f"'{value}' is not a date in YYYY-MM-DD form.")
        if d > self.today:
            raise ToolError(f"{value} is in the future. Today is {self.today}.")
        return d

    def _modify(self, plant_id: str, fn) -> dict:
        result: dict = {}

        def apply(plants: list[dict]) -> list[dict]:
            p = self._find(plants, plant_id)
            new = fn(p)
            result["plant"] = new
            return [new if x is p else x for x in plants]

        storage.update(apply)
        self.changed = True
        return result["plant"]

    # --- tools ---
    def _list_plants(self) -> dict:
        plants = storage.read()["plants"]
        return {"today": self.today, "count": len(plants), "plants": [care.summarize(p, self.today) for p in plants]}

    def _get_plant(self, plant_id: str) -> dict:
        p = self._find(storage.read()["plants"], plant_id)
        sp = care.profile(p)
        amt = care.amount(p)
        return {
            **care.summarize(p, self.today),
            "botanical_name": sp.get("l", ""),
            "light": sp["light"],
            "watering_style": care.water_style(p),
            "how_to_water": amt["how"],
            "care_tip": sp["tip"],
            "history_newest_first": (p.get("log") or [])[:25],
        }

    def _log_care(self, plant_id: str, action: str, soil: str | None = None, date: str | None = None) -> dict:
        when = self._check_date(date)
        if action == "watered":
            p = self._modify(plant_id, lambda p: care.log_watering(p, self.today, soil == "bone_dry", when))
            self.actions.append(f"Watered: {p['name']}" + (f" ({care.fmt(when)})" if when and when < self.today else ""))
        elif action == "still_damp":
            if when and when < self.today:
                raise ToolError("'still_damp' can only be logged for today.")
            p = self._modify(plant_id, lambda p: care.log_still_damp(p, self.today))
            self.actions.append(f"Still damp, recheck {care.fmt(p['checkAfter'])}: {p['name']}")
        elif action == "fertilized":
            p = self._modify(plant_id, lambda p: care.log_feeding(p, self.today, when))
            self.actions.append(f"Fertilized: {p['name']}")
        else:
            raise ToolError(f"Unknown action '{action}'.")
        return {"ok": True, "plant": care.summarize(p, self.today)}

    def _add_plant(self, name: str, species: str, where: str, pot: str, pot_width_in: float, soil: str,
                   spot: str = "", last_watered: str | None = None, custom_profile: dict | None = None) -> dict:
        if where not in WHERE or pot not in POTS or soil not in SOILS:
            raise ToolError("where, pot or soil has a value that isn't allowed.")
        custom = None
        if species == "other":
            if not custom_profile:
                raise ToolError("custom_profile is required when species is 'other'.")
            cp = custom_profile
            custom = {
                "n": str(cp["common_name"])[:60], "l": str(cp.get("botanical_name", ""))[:80],
                "w": cp["grown"] if cp["grown"] in WHERE else "in",
                "days": int(care.clamp(int(cp["days"]), 1, 60)), "dry": str(cp["dry"])[:80],
                "light": str(cp["light"])[:80], "feed": int(care.clamp(int(cp["feed"]), 0, 120)),
                "st": cp["style"] if cp["style"] in care.STYLES else "normal", "tip": str(cp["tip"])[:240],
            }
        elif species not in care.SP:
            raise ToolError(f"'{species}' is not a library key. Use one of the keys listed in the system prompt, or 'other'.")
        last = self._check_date(last_watered)
        plant = {
            "id": care.new_id(), "name": name.strip()[:60] or (custom or care.SP[species])["n"],
            "species": species, "where": where, "spot": spot.strip()[:60], "pot": pot,
            "size": care.snap_width(float(pot_width_in)), "soil": soil, "learned": 1,
            "created": self.today, "log": [],
        }
        if custom:
            plant["custom"] = custom
        if last:
            plant["lastWatered"] = last
            plant["log"] = [{"t": "water", "d": last, "note": ""}]
        storage.update(lambda plants: [*plants, plant])
        self.changed = True
        self.actions.append(f"Added: {plant['name']}")
        return {"ok": True, "plant": care.summarize(plant, self.today)}

    def _update_plant(self, plant_id: str, name: str | None = None, where: str | None = None, spot: str | None = None,
                      pot: str | None = None, pot_width_in: float | None = None, soil: str | None = None,
                      reset_learning: bool = False) -> dict:
        if (where and where not in WHERE) or (pot and pot not in POTS) or (soil and soil not in SOILS):
            raise ToolError("where, pot or soil has a value that isn't allowed.")

        def change(p: dict) -> dict:
            np = dict(p)
            if name:
                np["name"] = name.strip()[:60]
            if where:
                np["where"] = where
            if spot is not None:
                np["spot"] = spot.strip()[:60]
            if pot:
                np["pot"] = pot
            if pot_width_in:
                np["size"] = care.snap_width(float(pot_width_in))
            if soil:
                np["soil"] = soil
            if reset_learning:
                np["learned"] = 1
            return np

        p = self._modify(plant_id, change)
        self.actions.append(f"Updated: {p['name']}")
        return {"ok": True, "plant": care.summarize(p, self.today)}

    def _remove_plant(self, plant_id: str, confirmed: bool) -> dict:
        if not confirmed:
            raise ToolError("Ask the gardener to confirm before removing a plant.")
        removed: dict = {}

        def drop(plants: list[dict]) -> list[dict]:
            removed["plant"] = self._find(plants, plant_id)
            return [p for p in plants if p is not removed["plant"]]

        storage.update(drop)
        self.changed = True
        self.actions.append(f"Removed: {removed['plant']['name']}")
        return {"ok": True}

    def _add_note(self, plant_id: str, text: str) -> dict:
        text = " ".join(text.split())[:200]
        if not text:
            raise ToolError("The note is empty.")
        p = self._modify(plant_id, lambda p: care.add_note(p, self.today, text))
        self.actions.append(f"Note saved: {p['name']}")
        return {"ok": True}
