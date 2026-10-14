# Watering Can

A small web app for keeping indoor and outdoor plants alive. You log waterings and fertilizing. It tells you when to check each plant's soil and how much water to give, and it adjusts each plant's schedule to your home as you log.

Tuned for Anaheim, CA (USDA zone 10b): hot, dry summers, Santa Ana winds in fall, mild winters.

## Run it

There's no build step, nothing to install and no API key needed. Open `index.html` in a browser.

To use it on your phone, host the folder on any static host, such as GitHub Pages (Settings → Pages → deploy from branch).

## How it works

- **Two tabs:**
  - **Plants:** what needs you today, all your plants, and the add form.
  - **Calendar:** a month view. Past days show what you logged; upcoming days show planned soil checks and feedings.
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

Plants are stored in the browser's `localStorage`. Your data stays in that one browser, so use **Download backup** and **Restore from backup** (in the Plants tab) to move it between devices or keep a copy. Backup files are plain JSON.

## Project layout

```
index.html        page markup
css/styles.css    styles, light and dark themes
js/store.js       localStorage persistence, backup/restore
js/care.js        plant library, seasons, water amounts, schedule math
js/app.js         UI: plant cards, month calendar, detail panel, forms
plant-agent/      optional Claude-powered agent version (separate; see its README)
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

`plant-agent/` has a separate, terminal-based version where you chat with a Claude agent. It logs care from plain language, diagnoses photos, researches unfamiliar plants and emails a daily reminder. It needs a Claude API key, and API use is billed. It doesn't share data with this web app.
