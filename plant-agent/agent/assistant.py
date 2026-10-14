"""The plant-care agent: Claude plus the tools in tools.py, run in a manual tool-use loop.
The terminal chat (chat.py) and the daily reminder (daily.py) both call into this module.

A manual loop (instead of the SDK's beta tool runner) lets us resume `pause_turn` from the
server-side web search tool and handle refusal fallbacks explicitly.
"""
from __future__ import annotations

import json
from datetime import date

import anthropic

from . import care, config
from .tools import TOOLS, Toolbox, ToolError

FALLBACK_BETA = "server-side-fallback-2026-07-01"  # re-runs a policy-declined request on a recommended model
MAX_STEPS = 15

WEB_SEARCH = {
    "type": "web_search_20260209",
    "name": "web_search",
    "max_uses": 5,
    "user_location": {"type": "approximate", "city": "Anaheim", "region": "California", "country": "US",
                      "timezone": "America/Los_Angeles"},
}

_species_list = "\n".join(f"- {s['k']}: {s['n']} ({'outdoor' if s['w'] == 'out' else 'indoor'})" for s in care.SPECIES)

SYSTEM_PROMPT = f"""You are Watering Can, a plant-care agent for one gardener in Anaheim, California (ZIP 92801, USDA zone 10b). Summers are hot and dry, fall brings Santa Ana winds, winters are mild. They keep indoor and outdoor plants and have killed several by both overwatering and underwatering, so your main job is helping them water the right amount at the right time.

How the schedule works (explain in these terms when useful):
- Each plant has a date to CHECK the soil, not to water blindly. They do the finger test: if the soil is dry to the depth the plant needs, they water; if it's still damp, they tell you and you log "still damp", which schedules a recheck in a couple of days.
- Logging teaches the schedule. "Still damp" makes that plant wait longer next time; "bone dry" shortens it; on-time waterings pull it toward their real pattern.
- Water amount comes from pot width (about a quarter of the pot's soil volume for most plants). Always empty the saucer after 15 minutes.
- Schedules shift by month for Anaheim's seasons. Fertilizing pauses December to February.
- Their chunky aroid mix tends to go hydrophobic when bone dry: bottom-soak it or water in two passes.

How to work:
- When they tell you what they did ("watered the monstera", "the snake plant was still wet"), log it with log_care right away, one call per plant, and then confirm briefly. Resolve relative dates ("yesterday") against today's date given in the message. Call list_plants first to get plant ids. If a name matches more than one plant, or none, ask which one they mean instead of guessing.
- When they add a plant, pick the closest library key below. If nothing fits, use web_search to check its needs, then add it as species "other" with a custom_profile. Fill unknown details with sensible defaults (plastic pot, 6 inches, regular mix) and tell them what you assumed so they can correct it.
- For "what needs attention" questions, use list_plants. When weather matters (heat, wind, rain, cold nights), search for today's Anaheim forecast and say how it changes the advice, especially for outdoor pots.
- For a photo or a described problem: identify the plant from their words or list_plants, read its history with get_plant, and weigh the photo against that history. Give the most likely cause first, what to check to confirm it, and what to do. Say how sure you are. Watering history is strong evidence: frequent waterings plus yellowing points to overwatering; long gaps plus crispy leaves points to underwatering. Save a one-line diagnosis with add_note.
- Never invent plants, dates or history. Only change data through the tools. Remove a plant only after they have clearly confirmed which plant to remove in this conversation; if they just say a plant died, ask before removing it.
- Replies are shown in a terminal: keep them short and plain, a few sentences or a short list. Give water amounts in cups and ml. No headers, tables or bold.

Plant library keys (species key: name):
{_species_list}"""


def _client() -> anthropic.Anthropic:
    return anthropic.Anthropic()


def _echoable(content: list) -> list:
    """Blocks to send back on the next request. After a mid-output fallback, model-internal blocks
    from before the switch point must be dropped (see the refusal-fallback docs)."""
    boundary = max((i for i, b in enumerate(content) if b.type == "fallback"), default=None)
    if boundary is None:
        return list(content)
    result_ids = {getattr(b, "tool_use_id", None) for b in content if b.type.endswith("_tool_result")}
    kept = []
    for i, b in enumerate(content):
        if b.type == "fallback":
            continue
        if i < boundary and b.type in ("thinking", "redacted_thinking", "tool_use"):
            continue
        if i < boundary and b.type == "server_tool_use" and b.id not in result_ids:
            continue
        kept.append(b)
    return kept


def _create(**kwargs):
    return _client().beta.messages.create(
        model=config.MODEL,
        max_tokens=16000,
        thinking={"type": "adaptive"},
        betas=[FALLBACK_BETA],
        fallbacks="default",
        **kwargs,
    )


def _text(content: list) -> str:
    return "\n\n".join(b.text.strip() for b in content if b.type == "text" and b.text.strip())


def chat(history: list[dict], image: dict | None = None, today: str | None = None) -> dict:
    """Run one turn. `history` is [{role, text}] ending with the user's new message.
    Returns {reply, actions, changed}."""
    today = today or date.today().isoformat()
    d = care.parse(today)
    messages: list[dict] = [{"role": m["role"], "content": m["text"]} for m in history[:-1]]
    latest: list[dict] = []
    if image:
        latest.append({"type": "image", "source": {"type": "base64", "media_type": image["media_type"], "data": image["data"]}})
    latest.append({"type": "text", "text": f"(Today is {d.strftime('%A')}, {today}.)\n\n{history[-1]['text']}"})
    messages.append({"role": "user", "content": latest})

    box = Toolbox(today)
    reply = ""
    for _ in range(MAX_STEPS):
        response = _create(
            system=[{"type": "text", "text": SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}}],
            tools=[*TOOLS, WEB_SEARCH],
            messages=messages,
            cache_control={"type": "ephemeral"},
        )
        if response.stop_reason == "refusal":
            reply = "I can't help with that one. Try asking about your plants in a different way."
            break
        content = _echoable(response.content)
        messages.append({"role": "assistant", "content": content})
        reply = _text(content) or reply

        if response.stop_reason == "pause_turn":  # server-side web search paused; send it back to continue
            continue
        if response.stop_reason != "tool_use":
            if response.stop_reason == "max_tokens":
                reply += "\n\n(My answer was cut off. Ask me to continue.)"
            break

        results = []
        for block in content:
            if block.type != "tool_use":
                continue
            try:
                output = box.run(block.name, dict(block.input))
                results.append({"type": "tool_result", "tool_use_id": block.id, "content": output})
            except (ToolError, TypeError, ValueError, KeyError) as e:
                results.append({"type": "tool_result", "tool_use_id": block.id, "content": f"Error: {e}", "is_error": True})
        messages.append({"role": "user", "content": results})
    else:
        reply = (reply + "\n\n" if reply else "") + "(I stopped after too many steps. Check the plant list to see what was saved.)"

    return {"reply": reply or "Done.", "actions": box.actions, "changed": box.changed}


def morning_note(summary: str, today: str) -> str:
    """Short weather-aware reminder for the daily script. Uses web search for the Anaheim forecast."""
    d = care.parse(today)
    messages: list[dict] = [{"role": "user", "content": (
        f"Today is {d.strftime('%A')}, {today}. Write my morning plant reminder.\n\n"
        f"Here is what the app says is due:\n{summary}\n\n"
        "Search for today's Anaheim, CA forecast (high temperature, wind, rain). Then write at most 120 words: "
        "one line on the weather and what it means for my plants (hot or windy days dry outdoor pots fast; "
        "rain means skip watering outdoor pots), then the plants to check today with how much water each needs. "
        "Remind me to do the finger test before watering. Plain text, no headers, no markdown."
    )}]
    for _ in range(6):
        response = _create(
            system="You write short, practical daily plant-care reminders for a gardener in Anaheim, California (zone 10b).",
            tools=[{**WEB_SEARCH, "max_uses": 2}],
            messages=messages,
            output_config={"effort": "medium"},
        )
        if response.stop_reason == "refusal":
            raise RuntimeError("The reminder request was declined.")
        content = _echoable(response.content)
        if response.stop_reason == "pause_turn":
            messages.append({"role": "assistant", "content": content})
            continue
        return _text(content)
    raise RuntimeError("The weather lookup didn't finish.")


if __name__ == "__main__":  # quick manual test: python -m agent.assistant "what needs water today?"
    import sys
    out = chat([{"role": "user", "text": " ".join(sys.argv[1:]) or "What needs attention today?"}])
    print(out["reply"])
    print(json.dumps(out["actions"], indent=1))
