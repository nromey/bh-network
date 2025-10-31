#!/usr/bin/env bash
# Fetch the current nets-helper HTML so we can confirm the inline script.

set -euo pipefail

OUT="${1:-/tmp/nets-helper.html}"

echo "Fetching http://127.0.0.1:5000/ -> $OUT"
curl -sf http://127.0.0.1:5000/ > "$OUT"
echo "Done. Saved to $OUT"
echo
echo "Snippet around custom_time_zone:"
rg -n "custom_time_zone" "$OUT" || echo "(pattern not found)"

