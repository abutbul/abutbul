#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python3 generator/generate.py
echo "Done. Open preview/index.html in a browser to watch the session."
