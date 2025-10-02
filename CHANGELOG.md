# Changelog

All notable changes to this project are documented here.

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
