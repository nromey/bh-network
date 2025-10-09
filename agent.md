# Blind Hams — Working Brief (Handoff)

This file captures our current setup, conventions, and near‑term roadmap so a new chat (or a teammate) can pick up fast.

---

## 1) Stack & Key Files
- **Static site:** Jekyll (theme: Minima), deployed on Netlify.
- **Data files:**
  - `_data/ncos.yml` — source of truth for BHN Digital NCO rotation (time_zone, start_local, duration_min, rotation, overrides).
  - `_data/bhn_ncos_schedule.yml` — generated schedule consumed by the table include.
  - `_data/nets.yml` — master list of nets (id, category, rrule, …).
- **Generator script:** `scripts/build_bhn_data.py`
  - Emits upcoming Saturdays (N_DATES=12), applies overrides first, then rotation by nth‑Saturday.
  - If no NCO (e.g., 5th Saturday), writes `nco: "TBD"` with `unassigned: true` and a helpful note.
  - **Env flags:**
    - `SKIP_TODAY_AFTER_END=1` (default): if the current Saturday’s net has already ended (by `start_local + duration_min`), skip listing it.
    - `STRICT_NCO=0` (default): do not fail CI on unassigned; when `1`, CI fails if any `unassigned` rows exist.
- **Table include:** `_includes/nco_table.html`
  - Parameters: `title`, `caption`, `schedule`, `items_key`, `show_location`, `location_md`, `time_local`, `tz_full`, or generator mode (`weeks`, `dow`, `roster`).
  - SR caption logic; marks unassigned rows with a CSS class and screen‑reader annotation.
- **CSS snippets:** add to a loaded stylesheet (e.g., `assets/css/site.css`)
  ```css
  .sr-only{position:absolute!important;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;clip:rect(0,0,0,0);white-space:nowrap;border:0}
  .nco-unassigned{background:#fff8e1}
  ```

---

## 2) YAML Conventions & Gotchas
- 2‑space indentation.
- Quote values that contain colons, commas, or special chars.
- Dates as **ISO**: `"YYYY-MM-DD"`.
- Keys are case‑sensitive; prefer lower_snake for new keys.
- For overrides:
  ```yaml
  overrides:
    - date: "2025-11-29"
      callsign: W5MRR
      note: "5th Saturday coverage."
  ```

---

## 3) Netlify / DNS Notes
- `_redirects` and `_headers` are included via Jekyll config:
  ```yaml
  include:
    - _redirects
    - _headers
  ```
- Example `_redirects` (apex → canonical www + HTTPS):
  ```
  https://blindhams.network/*  https://www.blindhams.network/:splat  301!
  http://blindhams.network/*   https://www.blindhams.network/:splat  301!
  http://www.blindhams.network/*  https://www.blindhams.network/:splat  301!
  ```
- Cloudflare DNS: apex & `www` CNAME → Netlify. (Proxy optional.)

---

## 4) Git Tips
- Pull fast‑forward: `git pull --ff-only`
- Smooth merges: `git pull --rebase --autostash`
- Skip CI for bot commits: commit message contains `[skip ci]`.

---

## 5) Accessibility Checklist
- SR‑only caption on tables; announce “Unassigned” via `aria-describedby`.
- Able Player for audio (keyboard + transcripts + chapters support).
- Avoid pure emoji for critical meaning; use text or `alt` where possible.
- Color + text for state (e.g., yellow row **and** “Unassigned”).

---

## 6) Roadmap (Near‑Term)
1) **Multi‑net scheduler**  
   - Introduce per‑net NCO pools & rules (by id) in `_data/ncos.yml` or split files per net.  
   - Output `next_nets.json` (rolling 7 days) for the homepage widget.

2) **Transcripts & Chapters**  
   - Whisper → VTT + JSON chapters.  
   - Per‑episode pages: transcript, chapters, primary links (Apple/YouTube), download.

3) **Homepage polish**  
   - “Up next” widget: consumes `next_nets.json`.  
   - Solar/MUF block with text equivalents.

4) **Mascot Logo**  
   - Left hand holding **HT**, right hand holding **white cane**; pink pig (“ham”) motif.  
   - Create SVG + monochrome variant; provide alt:  
     > “Pink pig mascot in headphones; left hand holding a handheld radio, right hand a white cane; friendly ‘Blind Hams’ wordmark.”

5) **CW/QSO Trainer (phase 0 sketch)**  
   - API stubs for prompt → two‑party QSO; playback; copy challenges; scoring.

---

## 7) Useful Include Snippet (page usage)
```liquid
{% include nco_table.html
   schedule=site.data.bhn_ncos_schedule
   items_key="items"
   title="Blind Hams Digital Net — NCO Schedule"
   caption="Table of upcoming net control operators; ‘Unassigned’ highlights dates without an assigned NCO."
   show_location=true %}
```

---

## 8) Troubleshooting Quicklist
- Jekyll “could not find expected ':'” → YAML indentation/quotes.
- Data file not found in CI → confirm path `_data/…` and `actions/checkout` depth.
- Unassigned (5th Sat) is OK unless `STRICT_NCO=1`.
- Saturday display after the net: set `SKIP_TODAY_AFTER_END=1` (default).

---

**73, and happy building!**

## 9) Toolchain & Local Setup
- Ruby: 3.3 (Jekyll 4.x)
- Node: 18.x
- Python: 3.11+
- Netlify CLI (optional, for local previews)
- Bundler & Jekyll:
  ```bash
  gem install bundler jekyll
  bundle install
  bundle exec jekyll serve
  ```
- Python deps for generators:
  ```bash
  python -m pip install --upgrade pip
  pip install pyyaml
  ```
- Node deps (if/when used for JSON builders):
  ```bash
  npm init -y
  # add packages as needed
  ```

## 10) Time Zones & Scheduling
- Canonical time zone for generation and display is the Netlify `TZ` environment (currently `America/New_York`).  
- Store event-local times in data (`start_local`, `duration_min`) and compute ISO output in scripts using zone-aware libraries.  
- Daylight Saving Time (DST):
  - Always convert using the named zone; do **not** hardcode offsets.
  - Post-event visibility: use `SKIP_TODAY_AFTER_END=1` to hide expired events for the same day.

## 11) Future CI / Automation Plan

This section outlines proposed continuous-integration (CI) and automation improvements for the Blind Hams Network repository.
All automation must prioritize accessibility, reproducibility, and clear text-based output suitable for blind developers using screen readers.

### 11.1 Build Trigger Optimization
- **Goal:** Reduce unnecessary Netlify or GitHub Actions builds.
- **Approach:** Use conditional workflows to regenerate derived data only when related inputs change.
```yaml
on:
  push:
    paths:
      - "_data/ncos.yml"
      - "_data/nets.yml"
      - "scripts/**"
      - ".github/workflows/**"
  schedule:
    - cron: "0 12 * * 6"   # Weekly rebuild (Saturday 12 UTC)
```
When commits contain `[skip ci]`, the workflow must respect that flag to avoid redundant runs.

### 11.2 Automated YAML Linting
- Add a **pre-commit** or CI validation step to confirm:
  - Proper two-space indentation
  - ISO-formatted dates (`YYYY-MM-DD`)
  - Presence of required keys (`id`, `category`, `start_local`, `duration_min`, etc.)
  - No unescaped special characters (`:` or `,` in values)
- Failure output must be concise, plain-text, and screen-reader friendly.

### 11.3 Scheduled Data Generation
- A weekly job should run `scripts/build_bhn_data.py` to regenerate:
  - `_data/bhn_ncos_schedule.yml`
  - `assets/data/next_nets.json`
- Use environment variables:
```bash
SKIP_TODAY_AFTER_END=1
STRICT_NCO=0
```
- Artifacts can be committed automatically with the message:
  `chore(ci): weekly data refresh [skip ci]`.

### 11.4 Accessibility QA
- Integrate automated accessibility tests (e.g., **axe-core**, **pa11y**, or **lighthouse-ci**) in headless mode.
- Verify compliance with **WCAG 2.2 AA** at minimum, and target **AAA** where feasible.
- Core checks:
  - Proper heading hierarchy and ARIA landmarks
  - Alt text present and meaningful
  - Color contrast ratio compliance
  - Focus order and keyboard operability
- Output results as Markdown tables or plain text (no screenshots or graphical reports).

### 11.5 Deploy & Cache
- Deploy previews generated by Netlify for each pull request.
- Cache dependencies to reduce build time:
  - Python (`pip`)
  - Ruby (`bundle`)
  - Node (`npm`)
- Retain cache for 7 days to balance speed and reliability.

### 11.6 Notification Hooks
- Optional GitHub Action to post status updates when:
  - A build completes successfully
  - Accessibility QA fails
  - New data such as the NCO schedule or next-nets JSON is published

## 12) Security, Secrets & Privacy
- No PII should be committed to the repo.
- Secrets are stored in GitHub Actions Secrets:
  - `NETLIFY_BUILD_HOOK_URL` (used by the build-hook workflow)
- Principle of least privilege: if new APIs are added (e.g., transcripts), prefer scoped keys and read-only tokens.
- Avoid logging secrets; redact in CI output.

## 13) JSON Contract — next_nets.json
**Purpose:** 7-day rolling list of upcoming nets for homepage widgets and other clients.

**Schema (draft):**
```json
{
  "generated_at": "2025-10-05T22:12:00Z",
  "tz": "America/New_York",
  "items": [
    {
      "id": "bhn-sat-morning",
      "name": "Blind Hams Digital Net",
      "start_iso": "2025-10-11T10:00:00-04:00",
      "end_iso": "2025-10-11T11:00:00-04:00",
      "duration_min": 60,
      "local_date": "2025-10-11",
      "local_time": "10:00",
      "location": "AllStar 50631 · DMR TG 31672 · Echolink *KV3T-L",
      "nco": "W5MRR",
      "unassigned": false,
      "note": "Bring a topic!"
    }
  ]
}
```
**Notes:**
- `generated_at` is UTC.
- `tz` is the zone used for `local_*` fields.
- `start_iso`/`end_iso` are RFC 3339/ISO 8601 strings.
- `unassigned=true` when no NCO is set; clients should display an accessible “Unassigned” label.

## 14) Data Subdomain — External JSON Hosting (`data.blindhams.network`)

**Purpose:** Serve small, fast-refreshing JSON (e.g., `next_nets.json`) from a lightweight Nginx host you manage (Andre’s server). This decouples data rollovers from Netlify deploys and reduces build minutes.

### 14.1 DNS & TLS
- **DNS:** `data.blindhams.network` → A/AAAA to Andre’s host (or CNAME if applicable).
- **TLS:** Issue a cert for the subdomain:
  ```bash
  sudo apt-get update
  sudo apt-get install -y certbot python3-certbot-nginx
  sudo certbot --nginx -d data.blindhams.network
  ```

### 14.2 Nginx (minimal)
```nginx
server {
    listen 80;
    server_name data.blindhams.network;
    root /var/www/data;

    location / {
        add_header Cache-Control "public, max-age=30";
        add_header Access-Control-Allow-Origin "*" always;  # if widgets on other origins need it
        try_files $uri =404;
    }
}
# After TLS via certbot, port 443 will be configured automatically.
```

### 14.3 Directory & Atomic Writes
- Directory: `/var/www/data`
- Write JSON atomically to avoid partial reads:
  ```bash
  #!/usr/bin/env bash
  set -euo pipefail
  TMP="/var/www/data/.next_nets.json.$$"
  DEST="/var/www/data/next_nets.json"
  python3 /opt/bhn/scripts/build_next_nets.py > "$TMP"
  jq . "$TMP" > /dev/null  # sanity check; requires jq
  mv -f "$TMP" "$DEST"
  chmod 644 "$DEST"
  ```
- Make script executable: `chmod +x /opt/bhn/bin/update_next_nets.sh`

### 14.4 Cron (refresh cadence)
- Update every 5 minutes (tune as needed):
  ```bash
  */5 * * * * /opt/bhn/bin/update_next_nets.sh >> /var/log/bhn_next_nets.log 2>&1
  ```

### 14.5 JSON Contract (summary)
- File: `/next_nets.json`
- Fields (see §13 for full schema):  
  `generated_at` (UTC), `tz`, `items[]` with `id`, `name`, `start_iso`, `end_iso`, `duration_min`, `local_date`, `local_time`, `location`, `nco`, `unassigned`, `note`.
- Keep stable keys; extend by **adding** fields (don’t rename).

### 14.6 Client Integration (site)
- Add a small fetch in your widget to prefer the subdomain, fallback to local:
  ```js
  async function loadNextNets() {
    const sources = [
      "https://data.blindhams.network/next_nets.json",
      "{{ '/assets/data/next_nets.json' | relative_url }}"
    ];
    for (const url of sources) {
      try {
        const r = await fetch(url, { cache: 'no-store' });
        if (r.ok) return await r.json();
      } catch (e) {}
    }
    return { items: [] }; // accessible empty state
  }
  ```
- **Accessible empty state:** announce “Next nets currently unavailable.”

### 14.7 Caching & Headers
- Default: `Cache-Control: public, max-age=30` (snappy but not chatty).
- Consider adding:
  - `ETag` / `Last-Modified` (Nginx can auto-add if using static files).
  - CORS `Access-Control-Allow-Origin: *` only if other origins will embed it.

### 14.8 Monitoring & Health
- Health check: `HEAD /next_nets.json` returns `200` and small `Content-Length`.
- Log validation failures (`jq` or JSON Schema) and alert if file older than X minutes.

### 14.9 Security & Ops
- No secrets in the JSON.
- Script runs as a non-root user with write permission to `/var/www/data`.
- Back up last good version: keep `/var/www/data/next_nets.json.bak` on successful writes.

### 14.10 Accessibility Notes
- Time data reflects `tz` (e.g., `America/New_York`) and respects DST.
- Clients should provide SR-only announcements when `unassigned: true` (e.g., “Unassigned NCO”).
- Ensure keyboard-operable refresh controls; no auto-refresh that steals focus.

## 15) PR & Release Process
- Branch naming: `feat/<topic>`, `fix/<topic>`, `ops/<topic>`.
- Commit guidance:
  - Use clear, descriptive messages (avoid `[skip ci]` for data changes that must deploy).
- PR checklist:
  - Pages build locally or Netlify preview loads.
  - YAML validated (no indentation/quote errors).
  - Accessibility spot-check: headings order, focusable controls, alt text present.
  - Generators produce expected output (diff `_data/bhn_ncos_schedule.yml` and `next_nets.json`).
- Release:
  - Merge to `main` triggers Netlify deploy (or explicit build hook).
  - Tag releases as needed for major site milestones.

## 16) JSON Cutover Plan (High‑Level)

**Goal:** Move “next nets” and the rolling schedule to external JSON so data flips don’t trigger site rebuilds.

### 16.1 Phases
- **P1 — Prepare host** (Andre’s server now; LA server later)  
  DNS for `data.blindhams.network`, TLS via Let’s Encrypt (simple) now; Cloudflare Origin Cert optional later. Minimal Nginx: serve `/var/www/data`, `Cache-Control: public, max-age=60`, CORS `*` if needed.
- **P2 — Publish JSON**  
  Files: `/next_nets.json`, `/schedule_week.json`. **Atomic writes** (tmp → mv), world‑readable (644).
- **P3 — Site integration**  
  Remote‑first fetch with fallback to local asset; accessible empty state; `aria-live="polite"` for updates; **no focus stealing**.
- **P4 — CI/Deploy tuning**  
  Keep Netlify **Deploy Previews** for PRs; production builds on code/content changes only. Optional: disable hook once `_data/` is no longer used.
- **P5 — Monitoring**  
  Health: `HEAD /next_nets.json` → 200 and fresh (< X minutes). Log validation failures; alert if stale.
- **P6 — Rollback**  
  Switch widget to fallback asset; re‑enable `_data/` source if needed.

### 16.2 JSON Contracts (summary)
- `next_nets.json` → `generated_at` (UTC), `tz`, `items[]` with `id`, `name`, `start_iso`, `end_iso`, `duration_min`, `local_date`, `local_time`, `location`, `nco`, `unassigned`, `note`.
- `schedule_week.json` → list for 7 days with same item shape + `week_start_iso`.
- **Rule:** extend by adding fields; avoid renaming existing keys.

## 17) Current Decisions Snapshot (2025-10-07)

- **PR workflow:** Small, focused PRs with **Deploy Previews**.
- **Production deploys:** Push‑only Netlify **Build Hook** (guarded + debug).
- **Permissions/Concurrency:** Minimal token scope; cancel overlapping runs.
- **External data:** Serve JSON from `data.blindhams.network` (LE first; Cloudflare Origin Cert later OK).
- **Caching:** Short TTL (30–60s); clients fetch with `cache: 'no-store'`.
- **Fallback:** Keep `assets/data/*.json` in repo.
- **Accessibility:** Target **WCAG 2.2 AA** minimum; aim toward AAA. Announce `unassigned` NCO; keyboard‑only operable; visible focus.
- **Git hygiene:** Ignore `*.Zone.Identifier`; keep `.vscode/` untracked unless intentional.

## 18) To‑Do Before JSON Go‑Live

- [ ] DNS pointed; ports 80/443 open.
- [ ] TLS issued; `curl -I https://data…/health.json` returns 200.
- [ ] Nginx vhost with `Cache-Control` and optional CORS.
- [ ] Generator scripts write JSON atomically; `chmod 644`.
- [ ] Cron/systemd timer every 5–60 minutes.
- [ ] Widget uses remote‑first fetch with fallback.
- [ ] Monitor file age; alert if stale.
- [ ] (Optional) Remove `_data/next_net.yml` dependencies; narrow/disable Netlify hook.

## 19) Change Log

- **2025-10-07:** Added JSON cutover plan, decisions snapshot, and go‑live checklist; reaffirmed WCAG 2.2 AA baseline.
