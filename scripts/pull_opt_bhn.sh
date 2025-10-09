#!/usr/bin/env bash
set -euo pipefail

# Pull /opt/bhn from a remote host via SSH+sudo tar, writing a date-stamped backup.
# Usage: scripts/pull_opt_bhn.sh ner@andrel [dest_dir]

REMOTE="${1:-}"
DEST_DIR="${2:-backups}"

if [[ -z "$REMOTE" ]]; then
  echo "Usage: $0 user@host [dest_dir]" >&2
  exit 2
fi

mkdir -p "$DEST_DIR"
STAMP=$(date +%Y%m%d_%H%M%S)
OUT="$DEST_DIR/bhn_opt_${STAMP}.tar.gz"

echo "[info] Creating $OUT from $REMOTE:/opt/bhn ..."
echo "[info] You may be prompted for the SSH password and then sudo password."

# Exclude common secrets; adjust as needed.
EXCLUDES=(
  "--exclude=**/*.env" "--exclude=**/*secret*" "--exclude=**/*token*" "--exclude=**/.git" "--exclude=**/node_modules" "--exclude=**/__pycache__"
)

# Create a tar stream on the remote with sudo, send to stdout, and save locally
ssh -o BatchMode=no "$REMOTE" "sudo tar -C / -czf - opt/bhn ${EXCLUDES[*]}" > "$OUT"

echo "[ok] Wrote: $OUT"
echo "Tip: Inspect with 'tar -tzf $OUT | head' before committing."

