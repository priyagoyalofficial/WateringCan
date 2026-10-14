# Watering Can

A small web app for keeping indoor and outdoor plants alive. You log waterings and fertilizing. It tells you when to check each plant's soil and how much water to give, and it adjusts each plant's schedule to your home as you log.

Tuned for Anaheim, CA (USDA zone 10b): hot, dry summers, Santa Ana winds in fall, mild winters.

## Run it

Double-click **`start.bat`**. It starts a small local server (`server.py`) and opens the app at http://localhost:8765/. Keep its window open while you use the app; close it to stop. It needs Python 3.10 or newer, with no extra packages and no API key.

Opening `index.html` directly still shows the app, but nothing is saved. A banner tells you to use `start.bat` instead.

## How it works

- **Three tabs:**
  - **Plants:** what needs you today, all your plants, and the add form.
  - **Calendar:** a month view. Past days show what you logged; upcoming days show planned soil checks and feedings.
  - **Dashboard:** what share of your plants are hydrated, drying, overdue or not tracked yet, moisture left per plant, and what needs attention.
- **The date is when to check the soil, not when to water.** Each card says how dry the soil should be (for example, "Top 2 in dry"). Do the finger test:
  - **Dry:** tap **Watered**, then say whether the soil was just dry or bone dry and drooping.
  - **Still damp:** tap **Still damp**. The app checks back in a couple of days.
- **It learns.** "Still damp" lengthens that plant's schedule, and "bone dry" shortens it. On-time waterings pull the schedule toward your real pattern.
- **Water amount** comes from pot width: about 25% of the pot's soil volume for most plants, less for succulents and keep-moist plants. Orchids, self-watering pots, LECA and in-ground plants get method-specific instructions instead.
- **The schedule** starts from each plant's base interval, then adjusts for:
  - month (Anaheim seasons)
  - pot material and width
  - soil mix
  - indoor or outdoor
  - what the app has learned about that plant
- **Fertilizer:** each plant has its own interval from March through September, half as often in October and November, and paused December through February.

## Data

- **Plants** are saved in `data/plants.json` after every change. The previous version is kept as `plants.json.bak`.
- **`data/plants.xlsx`** is an Excel copy, rewritten on every save, with a Plants sheet and a Log sheet of every watering and feeding. It's for reading only: changes made in Excel aren't loaded back. If it's open in Excel when you save, the app saves `plants.json` and says the Excel copy wasn't updated.
- **The plant agent uses the same file**, so plants you log in chat show up in the app, and the other way around. Each save is checked against the latest version, so one can't silently overwrite the other.
- **`data/` is git-ignored**, so your plants stay out of the repo. To keep a copy elsewhere or move to another computer, use **Download backup** and **Restore from backup**.

## Project layout

```
start.bat         starts the app
server.py         local server: serves the app, saves data/plants.json and data/plants.xlsx
index.html        page markup
css/styles.css    styles, light and dark themes
js/store.js       saving through the server, backup/restore
js/care.js        plant library, seasons, water amounts, schedule math
js/dash.js        Dashboard tab: hydration donut, moisture bars, attention list
js/app.js         UI: plant cards, month calendar, detail panel, forms
plant-agent/      optional Claude-powered agent (see its README)
data/             your plants (created on first run, not in git)
```

## Customizing

- **Add a plant type:** add an entry to `SPECIES` in `js/care.js`.
  - `days`: spring watering interval for a 6-inch plastic pot of regular mix
  - `dry`: when to water
  - `feed`: fertilizing interval in days, `0` = rarely
  - `w`: `'in'` or `'out'`
  - If it likes to dry out completely, add its key to `DRY_KEYS`. If it likes to stay moist, add it to `MOIST_KEYS`.
- **Different climate:** edit `SEASON` in `js/care.js`. It has one multiplier per month, January to December. Below 1 means drier weather and shorter schedules.

## The agent version

`plant-agent/` has a separate, terminal-based version where you chat with a Claude agent. It logs care from plain language, diagnoses photos, researches unfamiliar plants and emails a daily reminder. It needs a Claude API key, and API use is billed. It shares `data/plants.json` with this web app.
