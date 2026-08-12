#!/usr/bin/env bash
# Ad-hoc admin API call — the escape hatch for anything the other scripts don't cover.
#
#   scripts/api.sh GET  '/products?search=brit'
#   scripts/api.sh GET  '/attributes?forProducts=true'
#   scripts/api.sh POST /brands payload.json
#   echo '{"code":"x","name":"X"}' | scripts/api.sh PUT /attributes/1 -
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

[[ $# -ge 2 ]] || die "usage: $0 <METHOD> <PATH> [payload.json|-]"
method=$1 path=$2 data=${3:-}

if [[ $data == - ]]; then
  tmp=$(mktemp); trap 'rm -f "$tmp"' EXIT; cat > "$tmp"; data=$tmp
fi

api "$method" "$path" "$data" | jq .
