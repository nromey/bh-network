---
title: How To Add a Net
layout: default
---

# How To Add a Net

This guide shows how to add or update a net in plain steps.

Where to edit
- File: `_data/nets.json`
- Each net is an object inside the top-level `nets` array with fields like `id`, `name`, `category`, time info, and optional connection details.

Add a new net (example object inside `nets` array)
```json
{
  "id": "friday-night-net",
  "name": "The Friday Night Blind Hams Allstar and Echolink Net",
  "category": "bhn",
  "description": "Weekly roundtable. Everyone welcome. Tips and help encouraged.",
  "start_local": "20:00",
  "duration_min": 60,
  "rrule": "FREQ=WEEKLY;BYDAY=FR",
  "time_zone": "America/New_York",
  "allstar": "50631",
  "echolink": "*KV3T-L",
  "dmr_system": "BrandMeister",
  "dmr_tg": "31672"
  /* Optional extras:
     "frequency": "146.520",
     "mode": "FM",
     "ysf": "BHN-ROOM",
     "wiresx": "12345" */
}
```

Field reference
- `id`: short unique slug, lowercase with dashes.
- `name`: human-friendly title shown on pages.
- `category`: `bhn`, `disability`, or `general` (use these exact words).
- `description`: optional text (Markdown accepted).
- `start_local`: HH:MM (24‑hour) at the net’s local time.
- `duration_min`: minutes (integer).
- `rrule`: recurrence rule; common weekly examples:
  - Every Monday: `FREQ=WEEKLY;BYDAY=MO`
  - First Thursday monthly: `FREQ=MONTHLY;BYDAY=TH;BYSETPOS=1`
- `time_zone`: IANA time zone (e.g., `America/Chicago`). This controls DST correctly.
- `connections`: optional keys shown on pages (AllStar, EchoLink, DMR, YSF, WIRES‑X, etc.).

Checklist (before commit)
- Unique `id` (no duplicates).
- Time is quoted (`"HH:MM"`).
- `category` is one of the three values.
- Valid `time_zone` (IANA name).
- JSON is valid (run through `jq` or your editor’s formatter to be sure).

Verify locally
1) Run: `bundle exec jekyll serve`
2) Open home: `/?diag=1`
   - The “Week at a glance” list should include your net on the upcoming date.
   - The “Next Net” card picks the earliest upcoming BHN net.
3) Category page for your net (e.g., `/nets/blind-hams/` or `/nets/disabilities/`):
   - Each net heading shows a “ — Next: …” line once live data loads.

Common gotchas
- Use a proper IANA time zone; avoid abbreviations like `EST`.
- If the net won’t show up soon (e.g., monthly), it won’t appear until the upcoming window includes it. That’s expected.
- For DMR, either provide `dmr` combined (e.g., `BrandMeister 31672`) or the structured pair `dmr_system` + `dmr_tg`.
