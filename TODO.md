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

- Interactive “Add a Net” CLI
  - Text-based menu to guide net creation and avoid YAML mistakes
  - Prompts for: id, category, name, description (launch $EDITOR for multi-line), start_local, duration_min, rrule, time_zone
  - Optional prompts for connections: AllStar, EchoLink, frequency, mode, DMR (structured: dmr_system + dmr_tg), D-STAR, YSF, WIRES-X, P25, NXDN, talkgroup, peanut, website/location
  - Validates inputs (times, RRULE parts, known time zones), warns on duplicates, and writes to `_data/nets.yml` in sorted order
  - Dry-run preview + save
  - Bonus: `--edit <id>` to update an existing net; `--check` to lint the YAML
