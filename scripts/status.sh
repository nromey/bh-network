#!/usr/bin/env bash
set -euo pipefail

title() { printf "\n==== %s ====\n" "$1"; }

title "Repo status"
git --version >/dev/null 2>&1 || { echo "git not found"; exit 1; }
git status --short --branch || true

title "Recent commits (last 3)"
git log --oneline -n 3 || true

title "Changed files (staged + unstaged)"
git diff --name-only || true
git diff --name-only --cached || true

title "Posts breakdown"
printf "Total posts: %s\n" "$(ls -1 _posts/*.md 2>/dev/null | wc -l | tr -d ' ')"
printf "CQBH posts:  %s\n" "$(rg -n "^categories:.*\bcqbh\b" -S _posts 2>/dev/null | wc -l | tr -d ' ')"
printf "Site news:   %s\n" "$(rg -n "^categories:.*\bbhdn\b" -S _posts 2>/dev/null | wc -l | tr -d ' ')"

title "Build snapshot"
if [ -d _site ]; then
  files=$(find _site -type f 2>/dev/null | wc -l | tr -d ' ')
  newest=$(find _site -type f -printf '%TY-%Tm-%Td %TH:%TM:%TS %p\n' 2>/dev/null | sort | tail -1 | cut -d' ' -f1-2)
  echo "_site exists: ${files} files; newest mtime: ${newest:-unknown}"
else
  echo "_site/ not found (no build yet)"
fi

title "Key pages to check"
cat <<EOF
- News:                /news/
- CQ Blind Hams:       /cq-blind-hams/
- Nets (BHN):          /nets/blind-hams/
- Nets (Disabilities): /nets/disabilities/
EOF

title "Common commands"
cat <<'EOF'
# Clear terminal + scrollback (Linux shells)
clear && printf '\e[3J'
# Serve locally with live reload
bundle exec jekyll serve --livereload
# One-off build
JEKYLL_ENV=production bundle exec jekyll build
EOF

echo
echo "Tip: run with 'bash scripts/status.sh' (no execute bit needed)."

