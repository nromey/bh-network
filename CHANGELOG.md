# Changelog

All notable changes to this project are documented here.

## 2025-10-15

- Solar snapshot and dashboard scaffolding
  - Added `_includes/home_solar_card.html` and `assets/js/solar-card.js` to hydrate live solar indices with accessible headings/table views, a persistent hide toggle, time-view integration, and `?diag=1` diagnostics.
  - Updated `index.md` and `assets/css/extra.css` so the home page surfaces the solar card with high-contrast styling alongside the nets widgets.
  - Created the `/solar/` landing page plus plain-language reference pages for SFI, Kp/Ap, sunspots, X-ray flux, solar wind, and flare forecasts to backstop the new card.

- Data utilities and sample payloads
  - Added `scripts/build_solar_json.py` to fetch NOAA SWPC feeds (SFI, global & Boulder K, solar wind, X-ray, sunspot, flare probabilities) and emit `data/solar.json` plus a text-to-speech summary.
  - Seeded `data/solar.json`, `data/solar_voice.txt`, and `solar/voice_report.txt` as development fixtures until the automated cron/hosting pipeline is wired up.
  - Checked in `netlify/functions/manifest.json` stub to quiet Netlify CLI warnings while iterating on future serverless hooks.

## 2025-10-11

- Home page stats counter (Netlify Functions + Blobs)
  - Added a serverless function `netlify/functions/counter-home.js` backed by Netlify Blobs that tracks both total visits and a month bucket (YYYY-MM in `COUNTER_TZ`, default `America/New_York`).
  - New client helper `assets/js/visit-counter.js` updates a concise “Site Stats” section near the bottom of the home page (`index.md`).
  - Display: “Home visits: X • This month: Y”. The section is a landmark region for easy skipping, and is static (no live announcements).
  - Config: `netlify.toml` declares `[functions] directory = "netlify/functions"` and uses `esbuild`; function `package.json` depends on `@netlify/blobs` and sets `"type":"module"`.
  - Fix: Converted functions to ESM and switched bundler to `esbuild` to resolve `@netlify/blobs` ESM/CJS errors.
  - Fallback config: When Blobs isn’t auto‑configured for the site, the function can use manual credentials via env vars: set `BLOBS_TOKEN` (RW) and optionally `BLOBS_SITE_ID` (or rely on `NETLIFY_SITE_ID`).
  - No Ruby gems or third-party calls required; CountAPI was removed in favor of Netlify-native storage.
  - CQ Blind Hams page was not modified; if a counter appears live there, remove any Netlify “Snippet injection”.

## 2025-10-12

- Blobs counter stabilized and enabled on main
  - Function now prefers Edge binding when available: uses `event.blobs` (edge URL + token) with `x-nf-site-id` header; falls back to API (`NETLIFY_SITE_ID` + `NETLIFY_BLOBS_TOKEN`) or auto-binding.
  - Updated JSON reads for `@netlify/blobs` v10: replaced `getJSON` with `getWithMetadata(..., { type: 'json' })`.
  - `list`/`purge` switched to the paginate iterator for compatibility across versions.
  - Client always sends `key=home`; dev sets `ns=dev` so dev keys are isolated (`dev:home`, `dev:home:YYYY-MM`).
  - Widget enabled on main (`_config.yml`), dev continues to namespace automatically.

## 2025-10-10

- NCO hydration fixes and endpoint normalization
  - Switched NCO schedule to `https://data.blindhams.network/bhn_nco_12w.json` (was `.net`).
  - Centralized data endpoints in `_config.yml` under `data_endpoints` with an optional `use_proxy` switch.
  - Added visible diagnostics for NCO hydration failures and empty data; improved fallback UX.
  - Guarded Liquid fallback date formatting to avoid epoch artifacts (no more “Dec 31, 1969”).
- Proxy and headers
  - Added Netlify rewrite `/data/* -> https://data.blindhams.network/:splat` to support same-origin fetch when enabled.
  - Introduced CSP `connect-src 'self' https://data.blindhams.network`.
  - Defaulted to direct endpoints after confirming CORS headers on the data host.
- Docs
  - Added `docs/data-server-setup.md` with Apache/NGINX/S3 examples for CORS and caching.
  - Removed `docs/pr-dev-to-main.md` (obsolete dev note).

## 2025-10-09

- JSON-powered nets (progressive enhancement)
  - Home “Up Next” card and weekly list hydrate from external JSON: `https://data.blindhams.network/next_nets.json`.
  - NCO schedule page hydrates from `https://data.blindhams.net/bhn_nco_12w.json`.
  - Fully backwards compatible: Liquid/YAML fallback remains for no‑JS and outage scenarios.
- Data model compatibility
  - Supports both legacy shape (`week[]`, `start_local_iso`) and new shape (`items[]`, `start_iso`).
  - Time zone label auto‑derived from ISO offset when `time_zone` is absent.
- Selection and display improvements
  - Next Net prefers earliest future BHN occurrence; falls back to any category if none.
  - Category normalization: "Blind Hams" → `bhn`, "Disabilities" → `disability`, "General Interest" → `general`.
  - Weekly list gained an in‑progress indicator: visible “(Live now!)” in the Net column, and “· Live now” next to the time; headings view shows “· Live now”.
  - Added SR-visible diagnostics mode `?diag=1` that announces hydration status and picked items.
- Resilience and UX
  - Cache-busting on JSON widget scripts to avoid stale branch deploys.
  - “Data updated …” badge (or “Live data loaded”) appears when live data is applied.
  - Fixed headings/table toggle on home weekly block by including `assets/js/net-view.js`.
- Data hygiene
  - Removed stray `$` prefix from “Absolute Tech Net” in `_data/next_net.yml`.
- CI cleanup
  - Removed obsolete GitHub Actions that generated local YAML and triggered Netlify hooks (now superseded by client hydration):
    - `.github/workflows/build_sched.yml`
    - `.github/workflows/netlify_build_hook.yml`
  - Removed generated YAML artifacts and switched to skeleton fallbacks so JSON can hydrate without conflicts:
    - `_data/next_net.yml` (home widgets now render a placeholder and hydrate)
    - `_data/bhn_ncos_schedule.yml` (NCO table renders an empty scaffold for hydration)

## 2025-10-02

- Nets data rendering
  - Markdown links inside `_data/nets.yml` descriptions now render correctly by piping through `markdownify` in `_includes/nets_page.html` (both table and headings views).
  - Fixed Handi Hams link syntax and URL in `_data/nets.yml`.
- “Next Net” widgets
  - Markdown-enabled descriptions in `_includes/next_net.html` and the home weekly card (`_includes/home_next_nets.html`).
- News information architecture
  - Split “News” into two clearly separated, screen‑reader friendly sections on `news.md`:
    - “Site News” (posts with `categories: [news, bhdn]`).
    - “CQ Blind Hams” (posts with `categories: [news, cqbh]`).
  - Home page News preview now shows latest Site News and, when present, a succinct “Latest CQ Blind Hams Episode” link.
  - Retagged welcome post as `categories: [news, bhdn]` so it appears under Site News.
- Accessible pagination system (no plugins)
  - Introduced a reusable client‑side pager (`assets/js/pager.js`) used on `news.md` and `cq-blind-hams/index.md`.
  - Features:
    - Page size buttons (5/10/20/All) with pressed state; persists per section.
    - First/Prev/numbered/Next/Last controls; compact page number set with ellipses.
    - ARIA live updates (polite) and visible status (“Page X of Y”).
    - Skip links to jump to the pager or the list.
    - Keyboard shortcuts (ArrowLeft/Right, PageUp/Down, Home/End) — opt‑in via a toggle; default OFF. When enabled, `aria-keyshortcuts` is announced and a short help tip is shown.
    - Section focus behavior after paging is configurable (`data-pager-focus`), defaulting to the section heading for predictable SR navigation.
    - Deep‑linking: size/page and optional search/categories encode into per‑section URL params.
- Search + category filtering
  - CQ Blind Hams page (`/cq-blind-hams/`): added labeled keyword search and AND‑ed category filtering with removable chips; integrates with pagination and announces filtered counts.
  - News → “CQ Blind Hams”: same search + category filters for consistency.
  - News → “Site News”: same search + category filters for consistency (categories exclude the base labels `news`/`bhdn`).
- Heading structure for lists
  - Article titles in CQBH and News lists are rendered as `<h3>` under each section `<h2>`, enabling fast “jump by heading” navigation (e.g., H/3 in SRs).
- CQ Blind Hams backfill
  - Used `scripts/fetch_cqbh.py` to import all CQBH episodes from the RSS feed (2020→present), writing Jekyll posts with Able Player embeds and `categories: [news, cqbh]`.
  - The importer de‑duplicates via `cqbh_guid`/title and sets file date from RSS `pubDate`.
- Dev ergonomics
  - Added `scripts/status.sh` to summarize repo state, recent commits, changed files, posts counts, and key pages; includes common serve/build commands and a terminal clear recipe.
- TODO updates
  - Documented follow‑ups for search UX: adding search to other sections, match highlighting, deep‑linking defaults, and (optionally) a site‑wide Fuse.js/Lunr.js index with accessible behavior.
 - Able Player hardening
   - CDN‑first loading for js‑cookie, jQuery, and Able Player CSS/JS with local fallbacks.
   - Defensive initializer `assets/js/able-init.js` that dynamically loads missing deps and upgrades players; adds a minimal js‑cookie shim and simple diagnostics.
   - Switched the Connect page stream to HTTPS (`https://laca.borris.me/blind-hams`) to avoid mixed content.
   - Added a monthly workflow to auto‑bump Able Player CDN version via PR: `.github/workflows/bump_ableplayer.yml`.

## 2025-09-29

- Added GitHub Actions workflow `Generate NCO + Build & Deploy` to auto-generate data, build, and deploy Pages.
- Introduced Python generators:
  - `scripts/build_next_net.py` to build `_data/next_net.yml` with upcoming occurrences and weekly window.
  - `scripts/build_bhn_data.py` to compile the NCO rotation into `_data/bhn_ncos_schedule.yml` with notices for TBD slots.
- Initial home “Up Next” widget and weekly accordion wired to `_data/next_net.yml`.
- Initial nets views and data model: `_includes/nets_page.html` and `_data/nets.yml`.

- Accessibility/UI polish:
  - Added narration when switching between table/headings views on nets pages; refined with toggle buttons for predictable NVDA/JAWS output.
  - Hid decorative down-arrow next to the “See NCO schedule” link from assistive tech.
  - Added `docs/TODO.md` to track future accessibility enhancements (e.g., keyboard shortcuts for the view toggle).
  - Added `scripts/oai_lkoginmethod` helper to switch between ChatGPT subscription tokens and encrypted OpenAI API key usage for the Codex CLI.


## 2025-09-27

- Initial Jekyll site scaffold (Minima, feed plugin), basic pages and navigation.
- Seeded `_data/ncos.yml` and `_data/nets.yml` with core Blind Hams nets.

## 2025-09-30

- Weekly nets on home page are now sorted chronologically (by `start_local_iso`).
- Added reusable next-up card include and placed it on all category nets pages:
  - `nets/blind-hams/index.md`, `nets/disabilities/index.md`, `nets/general/index.md`.
- Nets tables refactor:
  - Split connection info into dedicated columns: AllStar, EchoLink, Other modes.
  - Added a dedicated Description column (wraps long text cleanly).
  - Headings view now shows a compact “Connections” line mirroring the table.
- Home widgets refactor:
  - Next-up card and Week-at-a-glance table/headings now show AllStar, EchoLink, and Other modes.
  - “Other modes” aggregates Frequency/Mode, Talkgroup, Peanut, D‑STAR, YSF, WIRES‑X, P25, NXDN, and custom location/website when present.
- Per-net time zone presentation:
  - Category nets pages now respect each net’s `time_zone` label instead of assuming Eastern.
- Structured DMR support (backward-compatible):
  - New optional fields: `dmr_system` (e.g., BrandMeister/TGIF) and `dmr_tg` (e.g., "53085").
  - Rendering precedence: `dmr_system`+`dmr_tg` → “DMR {system} TG {tg}”; else `dmr` free‑form; else `mode: DMR`.
  - Generator (`scripts/build_next_net.py`) now emits these under `connections` in `next_net.yml`.
  - Migrated Active Elements net to structured DMR fields and `time_zone: UTC`.
- Extended `net_location.html` to recognize Peanut, D‑STAR (`dstar`/`DStar`), YSF, WIRES‑X (`wiresx`/`wires_x`), P25, NXDN.
- YAML hygiene: fixed syntax issues in `_data/nets.yml` and quoted values with special characters.

## Notes
- Sass deprecation warnings are from the theme; builds are otherwise clean.
## 2025-10-01

- A rediculous amount of tiny yet crucial changes that both future proof and make the site *that* much better.
- Completed writing connecting information  on how to connect to the Blind Hams Network
- Added the new information to the main home page in a now less obtrusive banner which
  * The banner shows Allstar node numbers and where they are
 * Also explain that you can connect to BHN by other means but that you should jump over to another page where we'll ggive you the deets.
  * The index page describes each connection method, I may explain further if I'm bored and want to be 
educational.
  * Included info from [N2DYI(https://www.qrz.com/db/N2DYI)] with details on connecting to Amazon skill that plays the live audio for the network
-  Added link for the icecast stream with a uRL that is https to match shared page, and also include the audio in an AblePlayer widget, a player that is super accessible and also looks awesome (Request from [N6RXT(www.qrz.com/db/N6RXT)], Started import of CQ Blind Hams from Apple Podcast summary pages to allow us to create news pages retroactively and to allow for display of easy to use CQBH pages. On blindhams.com there is no way to link directly to CQBH so that link is now out there. Right now it lists last 6 of the episodes. Plan is to drag the rest of them down for display and processiong.
  * Each episode page  gives a description, supplied by producers and Joel, [W0CAS(https://www.qrz.com/db/W0CAS)], as well as tthe audio, streamed within a spiffy AblePlayer container in case you want to jack up the speed of these  doohickeys, yep I said doohickeys.
  * Plan to add a paginator for these content, a way for users to filter/display an ascending or descending date order. Basically, it's wway more than you need but why not?
- Cleaned up and compacted other files i.e. this changelog.
- What's more fun than removing staples using a staple remover called your thumbnail--which you just chomped off earlier today due to stress? You guessed it, debugging code written by an over-zealous AI coding companion that comments in way more places than necessary, and does absolutely nothing in the places where you need comments.
- Lots more planned, and we're getting there. If I could see the light at the end of the preverbial tunnel, I'd be seeing that bitch but it's so far ahead that it doesn't look like the white light you absolutely shouldn't walk into at the end unless yo're ready. It was a productive dayu in the BHDN web sweat shop.
