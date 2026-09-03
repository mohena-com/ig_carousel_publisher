#!/bin/bash
set -euo pipefail
DIR="${1:?Usage: $0 /path/to/job-directory}"
for i in 1 2 3 4 5 6; do test -f "$DIR/slide_${i}.png" || { echo "Missing slide_${i}.png"; exit 1; }; done
echo "OK: six slides found in $DIR"
