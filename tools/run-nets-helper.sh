#!/usr/bin/env bash
# Helper to launch the Blind Hams nets-helper Flask app with the local repo data.

set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
APP_DIR="$ROOT/tools/nets-helper"
VENV_DIR="$APP_DIR/.venv"

if [[ ! -d "$VENV_DIR" ]]; then
  echo "Virtual environment not found at $VENV_DIR" >&2
  echo "Create it first: python3 -m venv tools/nets-helper/.venv" >&2
  exit 1
fi

cd "$APP_DIR"

# shellcheck disable=SC1091
. "$VENV_DIR/bin/activate"

export BHN_NETS_FILE="$ROOT/_data/nets.yml"
export BHN_NETS_OUTPUT_DIR="$ROOT/_data"

exec flask --app app run --debug "$@"
