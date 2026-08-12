#!/usr/bin/env bash
# Regenerate reference/attribute-values.json (the closed menu the import picks
# from) out of the live admin. Run after the user edits attributes/values.
# Writes atomically, so a failed fetch never truncates the existing menu.
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

out="$ROOT/reference/attribute-values.json"
tmp=$(mktemp); trap 'rm -f "$tmp"' EXIT

api GET '/attributes?forProducts=true' | jq '
  [ .data[]
    | { key: .code,
        value: { attribute_id: .id,
                 name: .name,
                 values: ([ .values[]? | { key: .label, value: .id } ] | from_entries) } } ]
  | from_entries' > "$tmp"

jq -e 'length > 0' "$tmp" >/dev/null || die "refusing to write: API returned no attributes"
mv "$tmp" "$out"

note "wrote $out"
jq -r 'to_entries[] | "  \(.key)\t\(.value.values | length) values"' "$out" >&2
