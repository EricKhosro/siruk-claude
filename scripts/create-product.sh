#!/usr/bin/env bash
# Create a product from a payload file, then verify it by reading it back.
#
#   scripts/create-product.sh payloads/rc-mini.json
#
# Payload shape (see CLAUDE.md for the full variant field list):
# {
#   "name": "Royal Canin Mini", "slug": "royal-canin-mini",
#   "category_ids": [3], "brand_id": 7, "attribute_family_id": 1,
#   "is_best_seller": false, "is_on_sale": false,
#   "variants": [{ "name": "Adult 8 kg", "pricing_type": "fixed",
#                  "sku": "1024080", "price": 26500, "cost_price": 20000,
#                  "stock": 10, "is_default": true, "sort_order": 0,
#                  "images": [], "attribute_value_ids": {"product-weight": 12, "lifestage": 27} }]
# }
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

[[ $# -ge 1 ]] || die "usage: $0 <payload.json>"
payload=$1
[[ -f $payload ]] || die "no such file: $payload"
jq -e . "$payload" >/dev/null || die "$payload is not valid JSON"

# Pre-flight: the three hard requirements, plus the exists-check.
jq -e '.name and .slug and (.category_ids | type == "array" and length > 0)' "$payload" >/dev/null \
  || die "payload needs name, slug and a non-empty category_ids array"
jq -e '(.variants // []) | all(
        .sku and (
          (.pricing_type == "fixed"  and (.price // 0) > 0) or
          (.pricing_type == "per_kg" and (.price_per_kg // 0) > 0 and (.weight // 0) > 0)))' "$payload" >/dev/null \
  || die "every variant needs sku plus either pricing_type:\"fixed\" + price, or pricing_type:\"per_kg\" + price_per_kg + weight"

name=$(jq -r .name "$payload")
existing=$(api GET "/products?search=$(urlencode "$name")" | jq -r '.data[] | "\(.id)\t\(.name)"')
if [[ -n $existing ]]; then
  note "⚠ the catalog already has a similar product:"
  printf '%s\n' "$existing" >&2
  note "→ if it is the same product, stop and use scripts/add-variant.sh instead."
  note "  set FORCE=1 to create a separate product anyway."
  [[ ${FORCE:-} == 1 ]] || exit 1
fi

id=$(api POST /products "$payload" | jq -r '.data.id')
note "created product $id"
api GET "/products/$id" | variant_table
