# Live Data Hydration (Next Net, Weekly, NCO)

This document explains how the client-side JSON hydration works for:

- Home “Up Next on the Blind Hams Bridge” card
- Home “Week at a glance” list (table/headings toggle + category filter)
- BHN NCO schedule table

It covers JSON formats, selection rules, time handling, diagnostics, failure modes, and extension points.

---

## 1) Files and Entry Points

- JavaScript
  - `assets/js/json-widgets.js` — fetches JSON and hydrates DOM blocks
  - `assets/js/net-view.js` — toggles table/headings views for nets sections
  - `assets/js/home-week-filter.js` — category filter for the home weekly list

- HTML includes
  - Home widgets: `_includes/home_next_nets.html`
    - Adds `data-next-net-json="https://data.blindhams.network/next_nets.json"`
    - Injects `<script>` tags for the three scripts above (with cache-busting `?v=`)
  - “Next Net” subset: `_includes/next_net_card.html`
    - Also includes `data-next-net-json` + loads `json-widgets.js`
  - NCO page: `nets/blind-hams/bhn-schedule.md`
    - Adds `data-nco-json="https://data.blindhams.network/bhn_nco_12w.json"` and loads `json-widgets.js`

Hydration is a progressive enhancement; server-rendered Liquid/YAML remains as fallback.

---

## 2) Supported JSON Shapes

Next Net + Weekly (same endpoint): `https://data.blindhams.network/next_nets.json`

Supported structures (both accepted):

- Legacy
  - `week`: array of occurrences
  - Each occurrence contains `start_local_iso` and (optional) `time_zone`
  - Optional `next_net` object shaped like an occurrence

- Current
  - `items`: array of occurrences
  - Each occurrence contains `start_iso` (with offset), `end_iso` (optional), `duration_min`
  - Optional `categories` array and `category` string

NCO Schedule: `https://data.blindhams.network/bhn_nco_12w.json`

- `items`: array with `{ date, nco, notes, unassigned }`
- Optional `time_local`, `tz_full`, `updated_at`

Example (current weekly shape):

```json
{
  "generated_at": "2025-10-09T17:20:01Z",
  "items": [
    {
      "id": "friday-night-net",
      "name": "The Friday Night Blind Hams Allstar and Echolink Net",
      "category": "bhn",
      "duration_min": 60,
      "start_iso": "2025-10-10T20:00:00-04:00",
      "end_iso": "2025-10-10T21:00:00-04:00"
    }
  ]
}
```

---

## 3) Selection Rules

### Next Net (home card)

1) Prefer earliest upcoming BHN occurrence from `week[]` or `items[]`.
2) If none found, fall back to earliest upcoming in any category.
3) If the feed provides `next_net`, it’s treated as a candidate only (not authoritative) to avoid staleness.

This behavior matches the desired “always show BHN next if available, else something upcoming” policy.

### Weekly List (home)

- Populates from `week[]` or `items[]`.
- Filters out past occurrences (start < now).
- Sorts ascending by start time.
- Respects category filters via `[data-category-toggle]` checkboxes.

### NCO Schedule

- Replaces the server-rendered `<tbody>` rows with `items[]` from the schedule JSON.
- Updates “Time (TZ)” header if `tz_full` is present.

---

## 4) Time and Time Zone Handling

- Start time is read from `start_local_iso` (legacy) or `start_iso` (current).
- Display time: locale-formatted date + time.
- Time zone label:
  - Prefer `time_zone` if provided (e.g., `America/New_York` → “Eastern”).
  - Else derive from ISO offset (−04:00 → “Eastern”, etc.); otherwise display `UTC±HH:MM`.

### Global Time View + UTC Option

- Global toggle persists in `localStorage` under `timeView:global` with values `net` (default) or `my`.
  - Net time: show time “as written” in the event’s configured zone; label uses a friendly name and DST-aware abbreviation (e.g., “Eastern (EDT)” or “Eastern (EST)”).
  - My time: convert to the viewer’s local timezone and label as “Local”.
- A global “Show UTC” checkbox is available on time-related sections and persists as `timeView:showUTC` (`'1'` to enable).
  - When enabled, appends a concise UTC suffix to hydrated times: `· UTC HH:MM` (24‑hour).
  - Applied consistently to: the Next Net card, the weekly list (both table and headings views), and category pages’ “— Next: …” lines.
  - The checkbox state is synchronized across sections and pages and announced via the existing aria-live status.
  - CSS hook: appended UTC chip uses `span.next-net-utc` if you need to restyle.

### In-Progress Detection

- If `end_iso` is present, compare `now` within `[start, end)`.
- Else compute end = start + `duration_min`.
- Weekly list shows:
  - Table view: visible “(Live now!)” after the net name; also “· Live now” next to the time.
  - Headings view: “· Live now” in the meta line.

---

## 5) Categories and Normalization

The client maps common labels to canonical codes for filtering and selection:

- “Blind Hams”, “Blind Hams Network”, “blind-hams” → `bhn`
- “Disabilities” → `disability`
- “General Interest”, “gen” → `general`

This allows data sources to use human-friendly labels without breaking filters.

---

## 6) Diagnostics

- Append `?diag=1` to any page URL to show SR-visible status lines:
  - “Live data loaded. Picked Next Net: …”
  - “Live data loaded. Weekly items: N.”
  - “Live data loaded. NCO items: N.”
  - “… fetch failed …” or “… no array found …” for error cases

These are announced via `role=status` and `aria-live=polite`.

---

## 7) Failure Modes and Fallbacks

- If fetch fails (network/CORS), or expected arrays are missing, the script leaves the server-rendered Liquid content in place.
- The “Data updated …” badge (or “Live data loaded”) is only shown when client hydration succeeded.

Common causes and fixes:

- No requests to JSON → JS not loaded: ensure `json-widgets.js` is present with a `?v=` cache buster.
- CORS blocked → set `Access-Control-Allow-Origin: *` on the data hosts.
- Stale browser cache → hard reload or test in a private window.

---

## 8) Cache Busting

- All JSON widget scripts include `?v={{ site.github.build_revision | default: site.time | date: '%s' }}`
- This avoids stale branch deploys serving old JS.

---

## 9) Extending the Model

- To display new connection modes or fields:
  - Update the helpers in `json-widgets.js` (e.g., extend `buildOtherModes()`), and/or the Liquid fallback in `_includes/home_next_nets.html`.
- To change selection policy:
  - Adjust BHN-first logic in `enhanceNextNet()`.
- To add a new widget:
  - Add a container with a `data-...-json` attribute and mirror the pattern from existing sections.

---

## 10) Local Testing

- Run Jekyll locally:
  ```bash
  bundle exec jekyll serve
  ```
- Test hydration and diagnostics:
  - Open `http://127.0.0.1:4000/?diag=1`
  - Ensure the console shows no CORS or CSP errors.
  - Verify “Live data loaded …” messages appear under relevant sections.

Tip: If you need to test against a local JSON file, you can temporarily point `data-next-net-json`/`data-nco-json` to a raw file served by Jekyll under `assets/data/…`.

---

## 11) Accessibility Notes

- Live status (‘Live now!’) appears as visible text in the Net column for reliable table navigation.
- Announcements for view toggles, filters, and hydration status use `aria-live` and `role=status`.
- Table headings and structure are preserved in hydration to maintain predictable SR reading order.
