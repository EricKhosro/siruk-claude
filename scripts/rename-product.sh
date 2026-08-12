#!/usr/bin/env bash
# Rename a product (and optionally its slug) without touching its variants.
#
#   scripts/rename-product.sh 17 "Mini"
#   scripts/rename-product.sh 17 "Mini" royal-canin-mini
#
# PUT /products/<id> replaces the whole variants array, so this rebuilds the body
# from a fresh GET and refuses to write if any variant would be lost — same
# guards as add-variant.sh. Never hand-write the PUT body.
#
# Product names must NOT contain the brand: the storefront prints the brand
# before the name (see CLAUDE.md → Admin product form).
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

[[ $# -ge 2 ]] || die "usage: $0 <product-id> <new name> [new-slug]"
id=$1 newname=$2 newslug=${3:-}

before=$(api GET "/products/$id")
printf '%s\n' "$before" > "$CACHE/product-$id-before.json"

oldname=$(jq -r '.data.name' <<<"$before")
[[ $oldname != "$newname" || -n $newslug ]] || { note "name already '$newname' — nothing to do"; exit 0; }

payload=$(jq --arg n "$newname" --arg s "$newslug" '
  .data as $p
  | { name: $n,
      slug: (if $s == "" then $p.slug else $s end),
      category_ids: $p.category_ids, brand_id: $p.brand_id,
      attribute_family_id: $p.attribute_family_id,
      is_best_seller: $p.is_best_seller, is_on_sale: $p.is_on_sale,
      is_discontinued: $p.is_discontinued,
      variants: $p.variants }' <<<"$before")

jq -e --argjson old "$(jq -c '[.data.variants[].id]' <<<"$before")" \
      '([.variants[].id // empty]) as $now | ($old - $now) | length == 0' <<<"$payload" >/dev/null \
  || die "internal: a variant would be dropped — refusing to PUT"

printf '%s\n' "$payload" > "$CACHE/product-$id-put.json"
note "renaming $id: '$oldname' → '$newname'${newslug:+ (slug → $newslug)}"

api PUT "/products/$id" "$CACHE/product-$id-put.json" >/dev/null
api GET "/products/$id" | variant_table
