Ripgrep (rg) Quick Recipes

Basics
- rg "text" — fast recursive search (respects .gitignore)
- rg -n "text" path1 path2 — show line numbers, restrict to paths
- rg -i "text" — case-insensitive
- rg -F "literal text" — treat pattern as plain text
- rg -w "word" — whole-word match

Scope control
- rg -uu "text" — include hidden + ignored files
- rg -g '!_site/**' "text" — exclude generated site output
- rg -t md "text" — only Markdown; -t html for HTML; -T md to exclude

Context and file lists
- rg -C 2 "text" — 2 lines of context around matches (use -A/-B for after/before)
- rg -l "text" — list files with matches (use -L for files without)
- rg --files — list tracked files (respects .gitignore)

Regex power
- rg -P "(?<=href=\").*mastodon.*(?=\")" — PCRE2 lookarounds
- rg -U "multiline pattern" — allow patterns to span newlines
- rg -U --multiline-dotall -P ".*" — dot matches newlines (use sparingly)

Repo-specific handy searches
- Find social/footer includes
  - rg -n "include social\.html|footer-col-2|social-media-list" _includes _layouts
- Find Mastodon and rel="me" wiring
  - rg -n "mastodon|rel=\"me\"" _config.yml _includes _layouts
- Inspect NCO schedule bits
  - rg -n "NCO|schedule|bhn_ncos_schedule|next_net" _includes nets scripts _data
- Ignore generated site when searching
  - rg -n -g '!_site/**' "pattern"

Examples used recently
- Verify Mastodon link renders in built HTML
  - rg -n "social-media-list|mastodon|rel=\"me\"" _site/index.html
- Check live page (with cache-buster) after deploy
  - curl -fsSL "https://www.blindhams.network/index.html?cb=$(date +%s)" | rg -n "mastodon|rel=\"me\""

Tips
- Combine -g globs as needed; order doesn’t matter.
- Use -S to disable smart case if you want exact case behavior.
- Use quotes around patterns with special chars (spaces, ?, *, parentheses).

