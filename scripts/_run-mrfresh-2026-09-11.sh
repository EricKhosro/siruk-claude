#!/usr/bin/env bash
# Wait for the Supplies/Trixie import to finish, then import the 7 Mr. Fresh
# sprays (they share the same API pacing budget — don't run them in parallel).
set -uo pipefail
cd "$(dirname "$0")/.."
while pgrep -f "import-plan.py .siruk-cache/trixie-plan.json" >/dev/null; do sleep 20; done
echo "=== trixie import finished, starting Mr. Fresh"
python3 scripts/import-plan.py .siruk-cache/mrfresh-plan.json
echo "=== MRFRESH DONE"
