Blind Hams — Working Brief (Agent Guide)
=======================================

This brief helps contributors (and AI agents) work effectively in this repo.
It replaces older notes that referenced generated YAML; the site now hydrates from external JSON at runtime.

---

1) Stack & Where Things Live
- Static site: Jekyll (Minima), deployed on Netlify
- Authoring data: `_data/nets.yml` and `_data/ncos.yml`
- Live JSON feeds (rendered at runtime):
  - Next + 7‑day: https://data.blindhams.network/next_nets.json
  - NCO 12‑week: https://data.blindhams.network/bhn_nco_12w.json
- Client scripts: `assets/js/json-widgets.js`, `assets/js/time-view.js`, `assets/js/net-view.js`, `assets/js/home-week-filter.js`
- Styles: `assets/css/extra.css`, `assets/css/nets.css`

2) Hydration Model
- Pages render a scaffold and hydrate from JSON when JS runs.
- Supported shapes: legacy `week[]/start_local_iso` and current `items[]/start_iso(+end_iso)`.
- NCO uses `items[]` with `{ date, nco, notes, unassigned }`.
  - Canonical: `date` (YYYY-MM-DD in the BHN net time zone), `notes`.
  - Accepted aliases (back-compat): `local_date` for `date`, `note` for `notes`.
  - Recommended top-level fields: `time_local` (HH:MM) and `tz_full` (e.g., "Eastern").
- Diagnostics: add `?diag=1` to see SR-visible status lines.

3) Time Handling
- Global toggle (persistent): “Net time” vs “My time” via `timeView:global`.
- Net time: display as written; label event zone. My time: convert to viewer’s local; label “Local”.
- Category pages append “— Next: …” per net using the JSON feed (by id). 

4) Authoring Nets (YAML)
- `_data/nets.yml`: `id`, `name`, `category`, `start_local` (HH:MM), `duration_min`, `rrule`, `time_zone` (IANA); plus connections.
- See docs/nets-data.md for examples and the generator output spec.

5) JSON Output (Reference)
- Prefer: `items[]` with `id,name,category,duration_min,start_iso(+offset),end_iso?,time_zone?`, `connections{}`; optional `next_net`, `updated_at`.
  - NCO feed (12-week): `items[]` should include `date,nco,notes,unassigned`; also include top-level `time_local` and `tz_full` for display. Accept aliases `local_date`→`date`, `note`→`notes` during transition.
- Backward compatible with `week[] + start_local_iso`.
- See docs/live-data-hydration.md for details.

6) Removed CI & Generated Files
- Removed: `.github/workflows/build_sched.yml`, `.github/workflows/netlify_build_hook.yml`
- Removed: `_data/next_net.yml`, `_data/bhn_ncos_schedule.yml` (now hydrated at runtime)

7) Backups & LFS
- `scripts/pull_opt_bhn.sh ner@andrel` → `backups/bhn_opt_YYYYMMDD_HHMMSS.tar.gz`
- Git LFS enabled for `backups/*.tar.{gz,xz,bz2}`; run `git lfs install` before committing archives.

8) Local Dev
- `bundle exec jekyll serve`; open `/?diag=1`.
- Verify hydration, time toggle, headings/table toggle, and weekly filters.

9) Accessibility
- Live status and toggles use `aria-live`; weekly table includes visible “(Live now!)” for SR table navigation.

10) Useful Links
- docs/live-data-hydration.md — hydration behavior and formats
- docs/nets-data.md — authoring nets + generator output spec
 - docs/blobs-setup.md — Netlify Blobs visit counter, diagnostics, and reset

11) Hydration & Sorting Updates (2025-10)
- Weekly list ordering: starts at the next upcoming item, then wraps through remaining future items and finally shows recent past items within the feed window. Implemented in `assets/js/json-widgets.js`.
- Category pages ordering: nets are ordered by their next upcoming occurrence (soonest → latest). Nets with no future occurrence in the window appear after, ordered by most recent past first. Robust ID normalization handles minor ID mismatches between YAML and the live feed.
- Descriptions: when the live feed omits `description`, the UI hydrates description text from `_data/nets.yml` via a pre-rendered id→HTML map injected by `_includes/home_next_nets.html` and `_includes/next_net_card.html`.
- Dev vs Prod data source:
  - Dev (JEKYLL_ENV=development): `_includes/nets_page.html` points to `/.netlify/functions/proxy-next-nets` to avoid CORS on Branch Deploys.
  - Fallback (all envs): if a direct fetch fails, `json-widgets.js` retries via `/.netlify/functions/proxy-next-nets?url=…`.
- Time toggle initialization: `assets/js/time-view.js` applies the initial view silently (no initial `bhn:timeview-change` broadcast) to avoid duplicate hydration on load.
- Script init guard: `assets/js/json-widgets.js` sets `window.BHN_JSON_WIDGETS_INIT` to prevent double-initialization when the script is included from multiple includes on the same page.
- Diagnostics: with `?diag=1`, additional messages appear (fetch URLs, item counts, and computed ordering) to aid troubleshooting.

12) Known Pages/Permalinks
- Blind Hams: `/nets/blind-hams/`
- Disabilities: `/nets/disabilities/` (permalink corrected from `/nets/disability/`)
- General Interest: `/nets/general/`
