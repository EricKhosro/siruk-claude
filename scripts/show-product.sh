#!/usr/bin/env bash
# Read a product back. Default output is a one-line-per-variant summary (cheap
# to eyeball); --json dumps the full re-postable body.
#
#   scripts/show-product.sh 14
#   scripts/show-product.sh 14 --json > product-14.json
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

[[ $# -ge 1 ]] || die "usage: $0 <product-id> [--json]"
id=$1

body=$(api GET "/products/$id")
if [[ ${2:-} == --json ]]; then
  jq . <<<"$body"
else
  variant_table <<<"$body"
fi
