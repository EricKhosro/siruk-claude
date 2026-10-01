#!/usr/bin/env bash
# Patch one existing variant of a product, in place, leaving the others alone.
#
#   scripts/set-variant.sh 23 RC-STERILISED-37-15KG '{"name":"15 kg","price":60000}'
#   scripts/set-variant.sh 23 RC-STERILISED-37-15KG '{"measure_type":"mass","content":15000}'
#   scripts/set-variant.sh 23 RC-STERILISED-37-15KG '{"attribute_values":{"lifestage":[25]}}'
#
# The patch is merged into the variant; attribute_values (keyed by attribute
# id or code) merge attribute-by-attribute. REPLACE_ATTRS=1 replaces the whole
# attribute_values map instead — needed to REMOVE an attribute ({"x": []} also
# clears one). Stock is not patchable here: it is a ledger now, changed only
# through /stock/variants/<id> (reference/admin-api.md → Stock).
# PUT /products/<id> replaces the whole variants array, so the body is rebuilt
# from a fresh GET (scripts/siruk_payload.py, checked against the product type)
# and refused if a variant would be lost or the default count changes.
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

[[ $# -ge 3 ]] || die "usage: $0 <product-id> <sku> '<json patch>'"
id=$1 sku=$2 patch=$3
jq -e 'type == "object"' <<<"$patch" >/dev/null 2>&1 || die "patch must be a JSON object"

before=$(api GET "/products/$id")
printf '%s\n' "$before" > "$CACHE/product-$id-before.json"

jq -e --arg s "$sku" '.data.variants[] | select(.sku == $s)' <<<"$before" >/dev/null \
  || die "product $id has no variant with sku $sku"

printf '%s\n' "$before" | sed -n '/^{/,$p' > "$CACHE/product-$id-get.json"
payload=$(python3 "$ROOT/scripts/siruk_payload.py" put-body "$CACHE/product-$id-get.json" \
            --patch-sku "$sku" --patch "$patch" $([[ ${REPLACE_ATTRS:-} == 1 ]] && echo --replace-attrs)) \
  || die "patch refused before writing (see above)"

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
