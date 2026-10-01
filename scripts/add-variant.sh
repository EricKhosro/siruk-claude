#!/usr/bin/env bash
# Add a variant to a product that already exists.
#
#   scripts/add-variant.sh 14 variant.json
#
# variant.json is ONE variant object (no "id") in the catalog-model shape — see
# scripts/siruk_payload.py for every field:
# { "name": "Puppy 8 kg", "sku": "1002080", "price": 24000, "cost_price": 18000,
#   "measure_type": "mass", "content": 8000, "pack_count": 1, "initial_stock": 10,
#   "images": [], "attribute_values": {"lifestage": [25]} }
# The size is measure_type + content (g/ml/pcs), never an attribute; stock is
# initial_stock (new variants only). The body is checked against the live
# product type before the PUT (siruk_payload.py).
#
# Why this script exists: PUT /products/<id> REPLACES the whole variants array.
# A variant left out of the payload is deleted — silently (200) for a non-default
# one, 422 if it was the default. So: GET fresh → append → verify nothing was
# dropped → PUT → read back. Never hand-write the PUT body.
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

[[ $# -ge 2 ]] || die "usage: $0 <product-id> <variant.json>"
id=$1 vfile=$2
[[ -f $vfile ]] || die "no such file: $vfile"
jq -e 'type == "object"' "$vfile" >/dev/null || die "$vfile must be a single variant object"
jq -e '.sku and (.price // 0) > 0' "$vfile" >/dev/null || die "variant needs sku and price (the pack price)"
price_guard "$(jq -c '[.]' "$vfile")"

before=$(api GET "/products/$id")
printf '%s\n' "$before" > "$CACHE/product-$id-before.json"

# No product ships without at least one image on at least one variant
# (user rule 2026-09-23). ALLOW_NO_IMAGE=1 is a rare, explicit override.
if [[ $(jq '(.images // []) | length' "$vfile") == 0 ]] \
   && ! jq -e '.data.variants[] | (.images // []) | length > 0' <<<"$before" >/dev/null; then
  [[ ${ALLOW_NO_IMAGE:-} == 1 ]] || die "new variant has no images, and product $id has none on any variant either — every product needs at least one (set ALLOW_NO_IMAGE=1 to override)"
fi

# Build the PUT body from the fresh GET: every existing variant re-sent in the
# shape the API accepts, plus the new one; checked against the product type.
printf '%s\n' "$before" | sed -n '/^{/,$p' > "$CACHE/product-$id-get.json"
payload=$(python3 "$ROOT/scripts/siruk_payload.py" put-body "$CACHE/product-$id-get.json" "$vfile") \
  || die "payload refused before writing (see above)"

# Guard rails before writing: exactly one more variant, and no existing id lost.
jq -e --argjson n "$(jq '.data.variants | length' <<<"$before")" \
      '.variants | length == ($n + 1)' <<<"$payload" >/dev/null \
  || die "internal: variant count did not grow by exactly 1"
jq -e --argjson old "$(jq -c '[.data.variants[].id]' <<<"$before")" \
      '([.variants[].id // empty]) as $now | ($old - $now) | length == 0' <<<"$payload" >/dev/null \
  || die "internal: an existing variant id would be dropped — refusing to PUT"
jq -e '[.variants[] | select(.is_default)] | length == 1' <<<"$payload" >/dev/null \
  || die "internal: payload must have exactly one default variant"

printf '%s\n' "$payload" > "$CACHE/product-$id-put.json"
note "adding variant '$(jq -r '.name // .sku' "$vfile")' to product $id ($(jq '.data.variants | length' <<<"$before") → $(jq '.variants | length' <<<"$payload") variants)"

api PUT "/products/$id" "$CACHE/product-$id-put.json" >/dev/null
api GET "/products/$id" | tee "$CACHE/product-$id-after.json" | variant_table
