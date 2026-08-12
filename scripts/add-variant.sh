#!/usr/bin/env bash
# Add a variant to a product that already exists.
#
#   scripts/add-variant.sh 14 variant.json
#
# variant.json is ONE variant object (no "id"):
# { "name": "Puppy 8 kg", "pricing_type": "fixed", "sku": "1002080",
#   "price": 24000, "cost_price": 18000, "stock": 5, "images": [],
#   "attribute_value_ids": {"product-weight": 12, "lifestage": 25} }
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
jq -e '.sku and .price' "$vfile" >/dev/null || die "variant needs at least sku and price"
jq -e 'has("id") | not' "$vfile" >/dev/null || die "variant must not carry an \"id\" — that would edit an existing one"

before=$(api GET "/products/$id")
printf '%s\n' "$before" > "$CACHE/product-$id-before.json"

sku=$(jq -r .sku "$vfile")
if jq -e --arg s "$sku" '.data.variants[] | select(.sku == $s)' <<<"$before" >/dev/null; then
  die "product $id already has a variant with sku $sku — nothing to add"
fi

# Build the PUT body from the fresh GET: keep every existing variant (with its
# id) and append the new one.
payload=$(jq --slurpfile new "$vfile" '
  .data as $p
  | ($p.variants | length) as $n
  | { name: $p.name, slug: $p.slug, category_ids: $p.category_ids,
      brand_id: $p.brand_id, attribute_family_id: $p.attribute_family_id,
      is_best_seller: $p.is_best_seller, is_on_sale: $p.is_on_sale,
      is_discontinued: $p.is_discontinued,
      variants: ($p.variants + [ $new[0]
        | .pricing_type = (.pricing_type // "fixed")
        | .sort_order   = (.sort_order   // $n)
        | .stock        = (.stock        // 0)
        | .images       = (.images       // [])
        # the product keeps its existing default; only a product with none gets one
        | .is_default   = (if ($p.variants | any(.is_default)) then false else true end) ]) }
  ' <<<"$before")

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
