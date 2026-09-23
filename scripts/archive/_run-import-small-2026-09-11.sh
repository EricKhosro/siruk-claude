#!/usr/bin/env bash
# Waits for the Trixie+Monge runner, then imports the small-brand plan.
cd "$(dirname "$0")/.."
while pgrep -f "_run-import-2026-09-11.sh" >/dev/null; do sleep 30; done
echo "=== SMALL $(date)"; scripts/import-plan.py .siruk-cache/small-plan.json
echo "=== SMALL DONE $(date)"
