Title: Switch nets to live JSON + time toggle + diagnostics; remove YAML generators and artifacts

Summary
- Home “Next Net” card, 7‑day list, and NCO schedule now hydrate from external JSON:
  - https://data.blindhams.network/next_nets.json (supports week/items; start_local_iso/start_iso)
  - https://data.blindhams.net/bhn_nco_12w.json
- Replaced generated YAML with scaffolds to eliminate merge conflicts; JSON hydration fills content at runtime.

UX and accessibility
- Time toggle (persistent): “Net time” vs “My time” on home and category nets pages.
  - Net time shows event‑local time as written; My time converts to the viewer’s zone; label becomes “Local”.
- Category pages show “ — Next: …” for each net using JSON occurrences (per‑id), with the same Net/My time conversion.
- “Live now!” indicator for in‑progress weekly entries.
- Diagnostics: add `?diag=1` to see SR‑visible hydration messages and picked items.
- Headings/table toggle works on home weekly (net‑view.js loaded).
- Cache‑busted scripts avoid stale branch deploys.

Data compatibility and display
- Supports both legacy and current JSON shapes:
  - Legacy `week[]` + `start_local_iso`
  - Current `items[]` + `start_iso`/`end_iso` (+ `duration_min`)
- Time zones:
  - Uses `time_zone` when present; otherwise derives from ISO offset.
  - “My time” labeled “Local”.
- Next Net selection:
  - Earliest future BHN; falls back to any category only when none found.
- Category normalization:
  - “Blind Hams” variants → `bhn`; “Disabilities” → `disability`; “General Interest” → `general`.

CI and repo cleanup
- Removed Actions:
  - `.github/workflows/build_sched.yml`
  - `.github/workflows/netlify_build_hook.yml`
- Deleted generated artifacts:
  - `_data/next_net.yml`
  - `_data/bhn_ncos_schedule.yml`
- Pages now render scaffolds; hydration populates content.

Backups and LFS
- `scripts/pull_opt_bhn.sh`: safely archive remote `/opt/bhn` (via sudo tar over SSH) to `backups/bhn_opt_*.tar.gz`.
- Git LFS enabled for `backups/*.tar.{gz,xz,bz2}`.

Docs
- `docs/live-data-hydration.md` — JSON hydration, selection, time handling, diagnostics.
- `docs/nets-data.md` — nets.yml authoring (start_local + time_zone + rrule) and JSON output spec (start_iso/end_iso with offsets).

Test plan
- Branch deploy with diagnostics: https://dev--bh-network.netlify.app/?diag=1
  - “Live data loaded …” shown under Next Net and weekly; NCO count visible on its page.
  - Net/My time toggle updates times and labels; persists.
  - Weekly “(Live now!)” and category filters work.
- Category nets pages:
  - Net/My time toggle and “ — Next: …” appended per net.

After merge
- No more YAML merge conflicts. Pages hydrate from JSON only.
- Optional: update `agent.md` to reflect JSON hydration; link to the new docs.

