#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -ne 1 ]; then
  echo "Usage: $0 URL" >&2
  exit 2
fi

url="$1"

echo "== HEAD =="
curl -sSIL -L --max-redirs 5 "$url"

echo
echo "== RANGE bytes=0-0 =="
curl -sSL -r 0-0 -o /dev/null -D - "$url"

