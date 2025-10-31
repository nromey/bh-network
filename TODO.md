# TODO

- Data endpoints and health
  - Add staging vs production endpoints in `_config.yml` with a simple switch (via `JEKYLL_ENV` or a `site.env` var) to avoid manual edits.
  - Add a lightweight health-check widget/page that surfaces data freshness and connectivity (shows `updated_at`/`generated_at`, CORS status, and endpoint in use). Expose at `/status/`.
  - Add a CI/Lint check that flags any lingering `data.blindhams.net` references; ensure all new code uses `site.data_endpoints`.

- Add Able Player for live audio stream. this has been completed.
  - Optional: transcript link if available; test keyboard + screen reader flow

- Nets helper review + publishing
  - Provide a diff preview for each pending bundle (highlight field-level changes vs. live data).
  - Surface who staged each pending file and when (pull from auth header and embed in the summary).
  - Add a “reject/archive” action so reviewers can clear stale bundles without deleting backups.
  - Emit an optional Telegram notification when a new pending bundle is ready for review (later phase; wire up bot token + chat ID).
- Nets helper UI polish
  - Replace free-form mode fields with checkbox-driven sections (DMR, AllStar, EchoLink, HF, etc.) that expose their inputs only when selected; validate/announce when data is removed.
  - Add polite announcements for key actions (saving pending file, expanding mode sections, clearing data) and improve RRULE prose (“repeats every day”, “second Thursday”, etc.).
  - Continue RRULE prose polish and snapshot accessibility checks.

- Connect page anchors
  - Add stable IDs to key sections in `nets/blind-hams/connect/index.md` for jump links
    - Example: `## Tips and Etiquette {#etiquette}` (already added)
    - Consider: `{#allstar}`, `{#dmr}`, `{#d-star}`, `{#ysf}`, `{#alexa-audio}`

- Interactive “Add a Net” CLI
  - Text-based menu to guide net creation and avoid YAML mistakes
  - Prompts for: id, category, name, description (launch $EDITOR for multi-line), start_local, duration_min, rrule, time_zone
  - Optional prompts for connections: AllStar, EchoLink, frequency, mode, DMR (structured: dmr_system + dmr_tg), D-STAR, YSF, WIRES-X, P25, NXDN, talkgroup, peanut, website/location
  - Validates inputs (times, RRULE parts, known time zones), warns on duplicates, and writes to `_data/nets.yml` in sorted order
  - Dry-run preview + save
  - Bonus: `--edit <id>` to update an existing net; `--check` to lint the YAML

- Search enhancements (CQBH and site-wide)
  - Add the same keyword search UI to News → “CQ Blind Hams” section (currently on the CQBH page only).
  - Highlight matched terms in filtered results using `<mark>` with high-contrast, accessible styling.
  - Support deep-linking filters (e.g., `?q=nanovna`) and initialize the filter from URL params.
  - Persist last search query per section (localStorage) without being disruptive to new visitors.
  - Consider a site‑wide search index using Fuse.js or Lunr.js (no external services); ensure:
    - Progressive enhancement (works without JS by default lists/pages).
    - Good SR UX: labeled search, no keyboard trap, polite ARIA updates (“N results for ‘term’”).
    - Respect privacy: no screen reader detection; offer tips for Browse/Forms Mode usage.
  - Review shortcut interactions: when shortcuts are disabled (default), keep help text hidden; when enabled, announce keys via `aria-keyshortcuts`.
