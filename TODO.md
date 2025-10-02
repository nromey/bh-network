# TODO

- Add “How to connect” banner content
  - Paste Patrick’s copy into `_includes/how_to_connect.md` (use Markdown table)
  - Include a caption via kramdown IAL to aid accessibility
    `{: .connect-table data-caption="How to connect to the Blind Hams Network" aria-label="How to connect to the Blind Hams Network" }`
  - Verify banner renders on `index.md` and is dismissible; leave `site.widgets.connect_banner: true`
  - Fine-tune CSS spacing/contrast after real copy is in

- Add Able Player for live audio stream
  - Decide stream type: MP3 (Icecast/Shoutcast, audio/mpeg) or HLS (.m3u8)
  - Ensure HTTPS + CORS headers on the stream origin
  - Include Able Player assets (CSS/JS) gated by `page.has_audio: true`
  - Add `<audio data-able-player>` markup with `<source>` for stream URL
  - If HLS: include hls.js and attach to the player for non‑Safari browsers
  - Add a visible “Live” label and an external player fallback link
  - Optional: transcript link if available; test keyboard + screen reader flow

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
