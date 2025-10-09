# Nets Data: Authoring and JSON Generation

This guide explains how to enter nets in `_data/nets.yml` and how a JSON generator should read that file to produce the live `next_nets.json` used on the home page.

It focuses on time fields, time zones, and output ISO formats so that both “Net time” and “My time” displays work accurately across DST and different locales.

---

## 1) Authoring `_data/nets.yml`

Required per‑net fields (typical):

- `id` — short, stable, URL‑friendly identifier (e.g., `friday-night-net`).
- `name` — human‑readable net name (Markdown allowed in descriptions only, not here).
- `category` — one of: `bhn`, `disability`, `general`.
- `start_local` — start time in 24‑hour format (HH:MM), local to the net’s own time zone.
- `duration_min` — integer minutes.
- `rrule` — recurrence rule (RFC‑5545 subset), e.g.:
  - Weekly: `FREQ=WEEKLY;BYDAY=FR`
  - Monthly nth weekday: `FREQ=MONTHLY;BYDAY=TH;BYSETPOS=1`
  - Daily: `FREQ=DAILY`
- `time_zone` — IANA timezone for the net’s local clock (e.g., `America/New_York`, `America/Los_Angeles`, `Australia/Sydney`).

Recommended optional fields:

- Connections: `allstar`, `echolink`, `frequency`, `mode`, `talkgroup`, `dmr`, `dmr_system`, `dmr_tg`, `peanut`, `dstar`, `ysf`, `wiresx`/`wires_x`, `p25`, `nxdn`.
- `location` — Markdown string for repeater/system notes.
- `website` — external link for more info.
- `schedule_text` — override display phrase (rarely needed; generator still relies on `rrule`).

Example:

```yaml
- id: friday-night-net
  category: bhn
  name: "The Friday Night Blind Hams Allstar and Echolink Net"
  description: "Join KY2D, Jim…"
  start_local: "20:00"       # 8:00 PM in the net’s local zone
  duration_min: 60
  rrule: "FREQ=WEEKLY;BYDAY=FR"
  time_zone: America/New_York
  allstar: "blind hams allstar or KY2D node 2396"
  echolink: "*blind* conference or ky2d-r"
```

Key rule: `start_local` must be the local wall‑clock time for the net’s `time_zone`. If your net runs in Australia/Sydney, set `time_zone: Australia/Sydney` and author `start_local` in Sydney time.

Note on BHN default timezone

- For Blind Hams (BHN) category pages, the site assumes a default timezone of `America/New_York` (Eastern) when a net does not specify `time_zone`. This is only a display default for schedule phrases. For accuracy across DST and conversions, always include an explicit `time_zone` per net even if it is Eastern.

Related UI behavior

- The site supports a global “Net time vs My time” toggle and an optional “Show UTC” setting for hydrated views. See docs/live-data-hydration.md for details on how labels and UTC suffixes are rendered.

---

## 2) JSON Generator Requirements (next_nets.json)

The home page hydrates from `https://data.blindhams.network/next_nets.json`. The client supports two shapes:

- Legacy: `week[]` with `start_local_iso`
- Current: `items[]` with `start_iso`

Preferred output (current shape):

```json
{
  "updated_at": "2025-10-09T17:20:01Z",
  "items": [
    {
      "id": "friday-night-net",
      "name": "The Friday Night…",
      "category": "bhn",
      "duration_min": 60,
      "start_iso": "2025-10-10T20:00:00-04:00",   // ISO 8601 with local offset
      "end_iso":   "2025-10-10T21:00:00-04:00",   // optional but recommended
      "time_zone": "America/New_York",            // optional but recommended
      "connections": { "allstar": "…", "echolink": "…" }
    }
  ],
  "next_net": { /* optional; treated as a candidate only */ }
}
```

How to compute `start_iso`/`end_iso`:

1. For each net, parse `start_local` and `duration_min`.
2. Expand `rrule` into actual dates for a rolling window (e.g., the next 7–10 days).
3. For each occurrence date, combine `YYYY‑MM‑DD` + `start_local` in the net’s `time_zone` using a zone‑aware library (Python `zoneinfo`/`pytz`, JS `Intl/Temporal`, etc.).
4. Serialize as ISO 8601 including the local offset for that date (e.g., `-04:00` for EDT, `-05:00` for EST).
5. Derive `end_iso` as `start_iso + duration_min` if not otherwise provided.

In the same feed you may include:

- `next_net`: the earliest upcoming occurrence (optionally filtered to BHN). The client will prefer the earliest BHN from the full list anyway.
- `updated_at`: ISO timestamp for data freshness.

The client already supports both shapes; no client changes are required if you output `start_iso` with offsets. Including `end_iso` and `updated_at` is encouraged for best UX.

---

## 3) How the UI Displays Time

- “Net time” (event‑local): shows the time/date exactly as written in `start_iso` without converting zones; labels the event zone (e.g., “Eastern”).
- “My time” (viewer‑local): converts to the viewer’s locale/timezone and shows “Local”; day/date will roll forward/back as appropriate (e.g., US Friday evening → AU Saturday midday).
- If `time_zone` is omitted, the UI derives a readable label from the ISO offset (e.g., `UTC+10:00`).

Cross‑DST behavior is handled by the local offset embedded in `start_iso`/`end_iso`.

---

## 4) Category Pages (Future Extension)

Category pages (Blind Hams/Disability/General) currently show schedule phrases (e.g., “Saturdays at 10:00 AM Eastern”) computed from `rrule + start_local + time_zone`.

To display “My time” for these schedules, we plan to compute each net’s next occurrence (date) at runtime (or via a helper feed), then format as we do on the home page. Authoring guidance in `_data/nets.yml` will not change.

---

## 5) Summary (TL;DR)

- In `_data/nets.yml`, always provide:
  - `start_local` in the net’s IANA `time_zone`
  - `duration_min`, `rrule`, and `category`
- In JSON, emit rolling `items[]` with:
  - `start_iso` (with offset), `end_iso` (optional), `duration_min`, `category`, and optionally `time_zone`
- The UI already supports this; no repo‑side code changes are needed to adopt `start_iso`.
