# TODO

- Interactive “Add a Net” CLI
  - Text-based menu to guide net creation and avoid YAML mistakes
  - Prompts for: id, category, name, description (launch $EDITOR for multi-line), start_local, duration_min, rrule, time_zone
  - Optional prompts for connections: AllStar, EchoLink, frequency, mode, DMR (structured: dmr_system + dmr_tg), D-STAR, YSF, WIRES-X, P25, NXDN, talkgroup, peanut, website/location
  - Validates inputs (times, RRULE parts, known time zones), warns on duplicates, and writes to `_data/nets.yml` in sorted order
  - Dry-run preview + save
  - Bonus: `--edit <id>` to update an existing net; `--check` to lint the YAML

