#!/usr/bin/env bash
# Print the live reference ids (brands, category tree, attribute families,
# attributes). Run this instead of trusting ids written down in CLAUDE.md —
# the 2026-08-11/12 wipe renumbered everything once already.
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

echo "== brands"
api GET '/brands?forProducts=true' | jq -r '.data | sort_by(.id)[] | "\(.id)\t\(.name)"'

echo
echo "== categories"
api GET '/categories?forProducts=true' | jq -r '
  def walk($d): .[] | ("  " * $d // "") + "\(.id)\t\(.name)", ((.children // []) | walk($d + 1));
  .data | walk(0)'

echo
echo "== attribute families"
api GET '/attribute-families?forProducts=true' | jq -r '
  .data | sort_by(.id)[] | "\(.id)\t\(.name)\t[\([.attributes[]?.code] | join(", "))]"'

echo
echo "== attributes"
api GET '/attributes?forProducts=true' | jq -r '
  .data | sort_by(.id)[] | "\(.id)\t\(.code)\t\(.name)\t\((.values // []) | length) values"'
