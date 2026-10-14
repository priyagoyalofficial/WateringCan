# Watering Can agent

The agent version of Watering Can, kept separate from the web app in the folder above. A Claude-powered plant-care agent for indoor and outdoor plants in Anaheim, CA (USDA zone 10b). Talk to it in the terminal:

```
you> Watered the monstera and the pothos. The snake plant was still damp.
assistant> Logged all three. The snake plant will wait a few more days; I'll check it again Tuesday.
  ✓ Watered: Monstera
  ✓ Watered: Kitchen pothos
  ✓ Still damp, recheck Tue, Sep 29: Snake plant
```

What it does:

- **Tracks each plant's soil-check date and water amount**, based on the plant type, pot, soil, Anaheim's seasons and your own watering history.
- **Logs care from plain language:** watered, still damp, bone dry, fertilized, including "yesterday".
- **Adds new plants**, and looks up care needs on the web for plants it doesn't know.
- **Diagnoses problems from a photo** together with that plant's watering history, and saves a note.
- **Checks today's weather** when it matters, for example heat or Santa Ana winds drying outdoor pots.
- **Emails you a morning reminder** of what to check, with a weather note.

## Setup (Windows)

1. Install Python 3.10 or newer.
2. Double-click **`chat.bat`** in this `plant-agent` folder. The first run creates `.venv`, installs dependencies, and opens `.env` in Notepad.
3. Paste your Claude API key into `.env` (get one at https://console.anthropic.com/settings/keys):
   ```
   ANTHROPIC_API_KEY=sk-ant-...
   ```
4. Run `chat.bat` again.

Manual setup on any OS:

```
cd plant-agent
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt   # macOS/Linux: .venv/bin/python
.venv/Scripts/python -m agent.chat
```

## Chat commands

| Command | What it does |
|---|---|
| `/photo PATH [message]` | Send a photo, e.g. `/photo C:\pics\fig.jpg brown spots on my fiddle leaf` (under 5 MB) |
| `/plants` | Quick list of what's due, without calling Claude |
| `/new` | Start a new conversation |
| `/quit` | Exit |

To load plants from a backup file downloaded from the web app (the **Download backup** button): `chat.bat --import watering-can-backup-2026-09-26.json`

## Daily reminder

`daily.bat` works out what's due today, asks Claude for a short note based on the Anaheim forecast, and emails it.

To set up email, fill in the `SMTP_*` and `REMINDER_TO` lines in `.env`. Gmail needs an [app password](https://myaccount.google.com/apppasswords). Without email set up, reminders are saved to `data/reminders/`.

Try it first:

```
.venv\Scripts\python -m agent.daily --dry-run
```

Then schedule it for 7:30 every morning (run once in a terminal):

```
schtasks /Create /SC DAILY /ST 07:30 /TN "Watering Can reminder" /TR "\"C:\Projects\Hobbies\Gardening\plant-agent\daily.bat\""
```

The PC has to be on at that time. To stop the reminder: `schtasks /Delete /TN "Watering Can reminder"`.

## How it works

- **The date is when to check the soil, not when to water.** Do the finger test:
  - **Dry:** water it, and tell the agent whether the soil was just dry or bone dry.
  - **Still damp:** tell the agent, and it schedules a recheck in a couple of days.
- **It learns.** "Still damp" lengthens that plant's schedule, "bone dry" shortens it, and on-time waterings pull it toward your real pattern.
- **The schedule** starts from the plant's base interval, then adjusts for:
  - month (Anaheim seasons)
  - pot material and width
  - soil mix
  - indoor or outdoor
  - what it has learned about that plant
- **Water amount** is about 25% of the pot's soil volume, from pot width. Orchids, self-watering pots, LECA and in-ground plants get method-specific instructions instead.
- **Fertilizer** runs on each plant's own interval from March through September, half as often in October and November, and pauses December through February.

### The agent

`agent/assistant.py` runs a tool-use loop on Claude Opus 5 with adaptive thinking.

- **Its tools** (`agent/tools.py`) are its only way to read or change plant data:
  - `list_plants`, `get_plant`
  - `log_care`, `add_plant`, `update_plant`, `add_note`
  - `remove_plant`, which only runs after you confirm
- **Web search** runs on Anthropic's servers. The agent uses it for plant research and the Anaheim weather check.
- **Refusal fallback** (`fallbacks: "default"`) is on: if Claude declines a request on policy grounds, the API retries it on a recommended fallback model instead of failing.

## Data

- **Plants** are saved in `data/plants.json` in the project folder above this one, the same file the web app uses, so both always show the same plants. The previous version is kept as `plants.json.bak`, so an unwanted change can be undone.
- **Reminders** are saved in that same `data/reminders/` folder.
- **`data/` and `.env` are git-ignored.** Your plants and your API key stay out of the repo.

## Project layout

```
agent/
  chat.py          terminal chat (chat.bat)
  assistant.py     Claude agent loop and system prompt
  tools.py         agent tools
  care.py          schedule, water-amount and learning rules
  storage.py       ../data/plants.json with atomic, revision-checked writes
  daily.py         morning reminder (daily.bat)
  config.py        settings from .env
library/species.json   plant library (36 houseplants and patio plants)
tests/                 pytest
```

Run tests with `.venv\Scripts\python -m pytest`.

## Customizing

- **Add a plant type:** add an entry to `library/species.json`.
  - `days`: spring watering interval for a 6-inch plastic pot of regular mix
  - `style`: `normal`, `dry`, `moist` or `soak`
- **Change the care rules:** edit `agent/care.py`.
- **Change the model:** set `WATERING_CAN_MODEL` in `.env`.

## Cost

The agent uses Claude Opus 5, which costs $5 per million input tokens and $25 per million output tokens. A typical chat message costs a few cents; photos and web searches cost a little more. The daily reminder is about one short request a day.
