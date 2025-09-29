#!/usr/bin/env bash
# Fix gem stub shebangs to use env ruby instead of version-specific paths.
set -euo pipefail

BIN_DIR="${HOME}/.gems/bin"
NEW_SHEBANG='#!/usr/bin/env ruby'

if [[ ! -d "$BIN_DIR" ]]; then
  echo "[error] Gem bin directory not found: $BIN_DIR" >&2
  exit 1
fi

updated=0
while IFS= read -r -d '' file; do
  first_line=$(head -n 1 "$file") || continue
  if [[ "$first_line" == "#!/usr/bin/ruby"* || "$first_line" == "#!/usr/bin/ruby3."* ]]; then
    { printf '%s
' "$NEW_SHEBANG"; tail -n +2 "$file"; } >"$file.tmp"
    mv "$file.tmp" "$file"
    chmod +x "$file"
    echo "[info] Updated shebang: $file"
    ((updated++))
  fi
done < <(find "$BIN_DIR" -maxdepth 1 -type f -print0)

if [[ $updated -eq 0 ]]; then
  echo "[info] No shebangs needed changes."
fi
