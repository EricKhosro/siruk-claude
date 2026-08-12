#!/usr/bin/env bash
# Patch one existing variant of a product, in place, leaving the others alone.
#
#   scripts/set-variant.sh 23 RC-STERILISED-37-10PLUS2KG '{"attribute_value_ids":{"product-weight":14}}'
#   scripts/set-variant.sh 23 RC-STERILISED-37-15KG '{"name":"15 kg","price":60000}'
#
# The patch is a JSON object deep-merged into the variant (so
# attribute_value_ids merges key-by-key rather than being replaced wholesale).
# Set REPLACE_ATTRS=1 to replace attribute_value_ids outright instead of merging —
# needed to REMOVE an attribute from a variant, e.g. dropping product-weight from
# a per_kg variant where the weight is auto-generated from the pack weight.
# PUT /products/<id> replaces the whole variants array, so this rebuilds the body
# from a fresh GET and refuses to write if a variant would be lost or if the
# default flag count changes — same guards as add-variant.sh.
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

[[ $# -ge 3 ]] || die "usage: $0 <product-id> <sku> '<json patch>'"
id=$1 sku=$2 patch=$3
jq -e 'type == "object"' <<<"$patch" >/dev/null 2>&1 || die "patch must be a JSON object"

before=$(api GET "/products/$id")
printf '%s\n' "$before" > "$CACHE/product-$id-before.json"

jq -e --arg s "$sku" '.data.variants[] | select(.sku == $s)' <<<"$before" >/dev/null \
  || die "product $id has no variant with sku $sku"

payload=$(jq --arg s "$sku" --argjson patch "$patch" \
              --argjson replace "$([[ ${REPLACE_ATTRS:-} == 1 ]] && echo true || echo false)" '
  .data as $p
  | { name: $p.name, slug: $p.slug, category_ids: $p.category_ids,
      brand_id: $p.brand_id, attribute_family_id: $p.attribute_family_id,
      is_best_seller: $p.is_best_seller, is_on_sale: $p.is_on_sale,
      is_discontinued: $p.is_discontinued,
      variants: [ $p.variants[]
                  | if .sku == $s
                    then (if $replace and ($patch | has("attribute_value_ids"))
                          then (. * $patch | .attribute_value_ids = $patch.attribute_value_ids)
                          else . * $patch end)
                    else . end ] }' <<<"$before")

jq -e --argjson old "$(jq -c '[.data.variants[].id]' <<<"$before")" \
      '([.variants[].id // empty]) as $now | ($old - $now) | length == 0' <<<"$payload" >/dev/null \
  || die "internal: a variant would be dropped — refusing to PUT"
jq -e --argjson n "$(jq '[.data.variants[]|select(.is_default)]|length' <<<"$before")" \
      '[.variants[]|select(.is_default)]|length == $n' <<<"$payload" >/dev/null \
  || die "internal: default-variant count changed — refusing to PUT"

printf '%s\n' "$payload" > "$CACHE/product-$id-put.json"
note "patching variant $sku of product $id: $patch"

api PUT "/products/$id" "$CACHE/product-$id-put.json" >/dev/null
api GET "/products/$id" | variant_table
