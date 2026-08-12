#!/usr/bin/env bash
# Does this product already exist? Run this BEFORE creating anything — a match
# means the CSV row is a new variant of that product (see add-variant.sh), not
# a new product.
#
#   scripts/find-product.sh "royal canin mini"
#
# Note: only ?search= filters; q/name/keyword are silently ignored by the API
# and return the whole catalog.
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

[[ $# -ge 1 ]] || die "usage: $0 <search text>"

body=$(api GET "/products?search=$(urlencode "$*")")
count=$(jq '.data | length' <<<"$body")

if (( count == 0 )); then
  echo "no match — safe to create a new product"
  exit 0
fi

echo "$count match(es):"
jq -r '.data[] | "  \(.id)\t\(.name)\tbrand=\(.brand // "-")\tcategories=\((.categories // []) | join(","))"' <<<"$body"
echo
echo "→ if the identity matches (brand + line + breed size + food form + diet +"
echo "  health feature), add the row as a variant:"
jq -r '.data[0] | "     scripts/show-product.sh \(.id)\n     scripts/add-variant.sh \(.id) variant.json"' <<<"$body"
