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
- NCO uses `items[]` with `{ date, nco, notes, unassigned }` (+ optional `time_local`, `tz_full`).
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

8.1) Branch Deploy URL config
- `_config.yml` sets `url: https://www.blindhams.network` for production.
- `_config_dev.yml` overrides `url: https://dev.blindhams.network`.
- `netlify.toml` overrides the build command for the `dev` branch to use both configs: `bundle exec jekyll build --config _config.yml,_config_dev.yml`.

9) Accessibility
- Live status and toggles use `aria-live`; weekly table includes visible “(Live now!)” for SR table navigation.

10) Useful Links
- docs/live-data-hydration.md — hydration behavior and formats
- docs/nets-data.md — authoring nets + generator output spec

---

11) Dev‑Only Visit Counter (Netlify Blobs)
- Purpose: A small page visit counter shown only on the `dev` branch deploys and local dev to avoid any credits usage in production.
- Gating:
  - `index.md` renders the counter only when `jekyll.environment == 'development'`.
  - `netlify.toml` sets `JEKYLL_ENV=development` only for `[context."dev".environment]`. Production and Deploy Previews stay `production`.
  - On `main`, the Site Stats section is removed entirely.
- Namespacing:
  - `index.md` sets `window.BHN_COUNTER_NS = 'dev'` in dev; `assets/js/visit-counter.js` appends `ns=dev` so dev data is isolated from any future prod usage.
- Functions:
  - Path: `netlify/functions/counter-home.js` (ESM).
  - Uses `@netlify/blobs` with automatic Netlify Function runtime credentials; no UI toggle or tokens required.
  - Store defaults: `STORE_NAME=counters`, `DEFAULT_KEY=home`, monthly bucket uses `COUNTER_TZ` (default `America/New_York`).
  - Modes:
    - `mode=inc`: increments total and month and returns counts.
    - `mode=get`: returns counts without incrementing.
    - `mode=list` (diag only): lists blob keys; supports `ns` or `key` prefix.
    - `mode=purge` (diag only): deletes keys by prefix; requires `ns` or `key`.
  - Diagnostics: add `diag=1` to include extra fields and enable list/purge.
- Verify on dev Branch Deploy:
  - List keys: `/.netlify/functions/counter-home?mode=list&diag=1&ns=dev`
  - Get counts: `/.netlify/functions/counter-home?mode=get&diag=1&ns=dev&key=home`
  - Increment: `/.netlify/functions/counter-home?mode=inc&diag=1&ns=dev`
  - Purge: `/.netlify/functions/counter-home?mode=purge&diag=1&ns=dev`
- Local testing: `bundle exec jekyll serve` shows the section but functions are not available; use `netlify dev` to run functions locally if needed.
