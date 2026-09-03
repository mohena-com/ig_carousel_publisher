#!/bin/bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON="$ROOT/.venv/bin/python"
if [[ ! -x "$PYTHON" ]]; then
  echo "ERROR: .venv not found. Run ./scripts/setup.sh"
  exit 1
fi
exec "$PYTHON" -m src.cli "$@"
