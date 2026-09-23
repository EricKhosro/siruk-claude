#!/usr/bin/env bash
# Sequential import runner for the 2026-09-11 batch (resumable: re-run continues).
cd "$(dirname "$0")/.."
echo "=== TRIXIE $(date)"; scripts/import-plan.py .siruk-cache/trixie-plan.json
echo "=== MONGE $(date)";  scripts/import-plan.py .siruk-cache/monge-plan.json
echo "=== DONE $(date)"
