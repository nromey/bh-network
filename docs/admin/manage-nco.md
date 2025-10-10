---
title: Manage NCOs (Blind Hams Net)
layout: default
---

# Manage NCOs (Blind Hams Net)

Use this guide to change who’s Net Control (NCO) for upcoming Saturdays.

Where to edit
- File: `_data/ncos.yml`
- This file defines the weekly rotation and any date-specific overrides.

Key parts of `_data/ncos.yml`
```yaml
time_zone: America/New_York
start_local: "10:00"
duration_min: 60
net_id: bh-digital

roster:
  - callsign: N2DYI
    first_name: Patrick
  - callsign: K5NER
    first_name: Noel
  # ...

rotation:         # week-of-month → callsign (Saturdays)
  1: N2DYI
  2: K5NER
  3: W5MRR
  4: VE3RWJ

overrides:        # specific dates when someone swaps/covers
  - date: "2025-10-11"
    callsign: VE3RWJ
    note: "Covering for Noel who is traveling."
```

How to change NCO
1) One-off swap or coverage (preferred)
   - Add a row under `overrides` with:
     - `date`: YYYY-MM-DD (a Saturday)
     - `callsign`: who will be NCO
     - `note`: optional short explanation
   - Keep history — don’t delete past overrides.

2) Permanent rotation change
   - Update the `rotation:` section (1–4). Use overrides for any special 5th Saturday or exceptions.

3) 5th Saturday
   - Add an `overrides` entry for the 5th Saturday date. Rotation intentionally leaves 5th unassigned so it’s explicit.

Verify on the site
1) Serve locally: `bundle exec jekyll serve`
2) Open the NCO page: `/nets/blind-hams/nco-schedule/?diag=1`
   - Look for the status line: “Live data loaded. NCO items: …”.
   - Confirm the right callsign appears for the specific date.

If changes don’t show up
- Live JSON is fetched from `https://data.blindhams.network/bhn_nco_12w.json`.
  - There can be a short delay while the data host regenerates and caches update.
  - Check headers:
    - `curl -I https://data.blindhams.network/bhn_nco_12w.json` (see `Last-Modified`)
  - Hard refresh or try a private window.
- If you see a failure notice, the data host may be down or blocked; the table will show the fallback (without your changes). Try again shortly.

Safety tips
- Prefer `overrides` for swaps; keep rotation stable.
- Use valid dates (`YYYY-MM-DD`).
- Keep notes short and neutral; they appear on the page.

