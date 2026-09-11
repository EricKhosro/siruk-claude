#!/usr/bin/env bash
# Check that every image referenced by a product actually resolves, and
# optionally repair the dead ones.
#
#   scripts/verify-media.sh              # whole catalog
#   scripts/verify-media.sh 71 72        # just these products
#   scripts/verify-media.sh --fix        # re-upload + relink whatever is broken
#
# Why: the media endpoint can return an id whose file was never written. The
# product saves happily and the storefront shows a dead image (found
# 2026-08-13: media 621 on product 71, its storage urls all 404). Run this after
# every import.
#
# --fix re-uploads from the source url recorded in .siruk-cache/media-cache.json
# (that's the brand-site url the image came from). A broken media with no
# recorded source is reported, not guessed at.
#
# Report: .siruk-cache/media-check.json. Exits 1 if anything is still broken.
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

FIX=0
BRANDS_ONLY=0
declare -a ids=()
for arg in "$@"; do
  case $arg in
    --fix) FIX=1 ;;
    --brands) BRANDS_ONLY=1 ;;
    -h|--help) note "usage: $0 [--fix] [--brands] [product-id ...]"; exit 0 ;;
    *[!0-9]*) die "unexpected argument: $arg" ;;
    *) ids+=("$arg") ;;
  esac
done

MEDIA_CACHE="$CACHE/media-cache.json"
REPORT="$CACHE/media-check.json"
BRAND_REPORT="$CACHE/brand-logo-check.json"

# --- brand logos -------------------------------------------------------------
# A brand image is a shared reference: one wrong id shows up on every product of
# that brand. Three ways it goes wrong, all seen on 2026-08-13:
#   · no image at all
#   · an image whose file 404s
#   · several brands pointing at the SAME media — which is what "every brand
#     shows the same picture" looks like from the storefront. It is not a
#     storefront fallback; the ids really are identical.
check_brands() {
  local brands rows id name img url status webp dupes
  brands=$(api GET '/brands?forProducts=true')
  rows=""
  while IFS=$'\t' read -r id name img; do
    [[ -n $id ]] || continue
    if [[ $img == null || -z $img ]]; then
      status="no-image"; url=""
      note "✗ brand $id $name — no logo set"
    else
      url=$(media_url "$img") || url=""
      if [[ -z $url ]]; then
        status="no-record"
        note "✗ brand $id $name — image $img has no media record"
      else
        status=$(url_status "$url")
        if [[ $status == 200 ]]; then
          # the storefront serves the webp derivative, not this thumbnail
          webp=$(media_webp_status "$img")
          case $webp in
            200|n/a) ;;
            *) status="webp-$webp"; note "✗ brand $id $name — logo webp → HTTP $webp" ;;
          esac
        else
          note "✗ brand $id $name — image $img → HTTP $status"
        fi
      fi
    fi
    rows+="$id"$'\t'"$name"$'\t'"$img"$'\t'"$status"$'\t'"$url"$'\n'
  done < <(jq -r '.data[] | "\(.id)\t\(.name)\t\(.image // "null")"' <<<"$brands")

  # the shared-image case
  dupes=$(printf '%s' "$rows" | awk -F'\t' '$3 != "null" {c[$3]++; n[$3] = n[$3] ", " $2}
                                            END {for (i in c) if (c[i] > 1) printf "%s\t%d\t%s\n", i, c[i], substr(n[i], 3)}')
  if [[ -n $dupes ]]; then
    note ""
    while IFS=$'\t' read -r img count names; do
      [[ -n $img ]] || continue
      note "✗ media $img is the logo of $count brands: $names"
    done <<<"$dupes"
    note "  → each brand needs its own logo (scripts/fetch-logo.sh → look at it → PUT /brands/<id>)"
  fi

  jq -n --arg rows "$rows" --arg dupes "$dupes" '
    def lines: split("\n") | map(select(length > 0));
    { brands: ($rows | lines | map(split("\t") | {id: (.[0]|tonumber), name: .[1],
                                                  image: .[2], status: .[3], url: (.[4] // "")})),
      shared: ($dupes | lines | map(split("\t") | {media: (.[0]|tonumber), brands: (.[1]|tonumber), names: .[2]})) }
    | . + {summary: {brands: (.brands|length),
                     without_logo: ([.brands[] | select(.image == "null")] | length),
                     dead: ([.brands[] | select(.image != "null" and .status != "200")] | length),
                     sharing_a_logo: ([.shared[].brands] | add // 0)}}' > "$BRAND_REPORT"
  jq -r '.summary | "\n\(.brands) brands: \(.without_logo) with no logo, \(.dead) with a dead logo, \(.sharing_a_logo) sharing a logo with another brand"' "$BRAND_REPORT" >&2
  note "brand report: $BRAND_REPORT"
}

if (( BRANDS_ONLY == 1 )); then
  check_brands
  exit 0
fi

# --- which products? ---------------------------------------------------------
if (( ${#ids[@]} == 0 )); then
  note "listing the catalog…"
  page=1
  while :; do
    chunk=$(api GET "/products?perPage=100&page=$page" | jq -r '.data[].id')
    [[ -n $chunk ]] || break
    while read -r pid; do [[ -n $pid ]] && ids+=("$pid"); done <<<"$chunk"
    # a short page means the last one
    (( $(wc -l <<<"$chunk") < 100 )) && break
    page=$((page + 1))
  done
fi
note "checking ${#ids[@]} product(s)"

# --- collect (product, variant, media) triples -------------------------------
rows=""   # "productId variantId mediaId" per line, deduped by media id later
for pid in "${ids[@]}"; do
  body=$(api GET "/products/$pid") || continue
  printf '%s\n' "$body" > "$CACHE/product-$pid-check.json"
  triples=$(jq -r --arg p "$pid" '
    .data
    | (.variants // [])[]
    | . as $v
    | ((.images // [])[] | "\($p) \($v.id // "?") \(.)")' <<<"$body")
  [[ -n $triples ]] && rows+="$triples"$'\n'
done

total=$(printf '%s' "$rows" | grep -c . || true)
note "$total image reference(s) to check"

# --- check each distinct media once ------------------------------------------
checked=""   # "mediaId status url" per line
broken=""    # media ids
while read -r mid; do
  [[ -n $mid ]] || continue
  url=$(media_url "$mid") || url=""
  if [[ -z $url ]]; then
    status="no-record"
  else
    status=$(url_status "$url")
  fi
  checked+="$mid $status $url"$'\n'
  if [[ $status != 200 ]]; then
    broken+="$mid"$'\n'
    note "✗ media $mid  $status  $url"
  fi
done < <(printf '%s' "$rows" | awk '{print $3}' | sort -un)

nbroken=$(printf '%s' "$broken" | grep -c . || true)

# --- repair ------------------------------------------------------------------
fixed=""; unfixable=""
if (( FIX == 1 )) && (( nbroken > 0 )); then
  [[ -f $MEDIA_CACHE ]] || echo '{}' > "$MEDIA_CACHE"
  while read -r mid; do
    [[ -n $mid ]] || continue
    src=$(jq -r --argjson i "$mid" 'to_entries | map(select(.value == $i)) | .[0].key // empty' "$MEDIA_CACHE")
    if [[ -z $src ]]; then
      # no recorded source url — fall back to the copy the original run
      # downloaded into .siruk-cache/, matched on the media's own filename
      fname=$(api GET "/medias/$mid" 2>/dev/null | jq -r '.data.filename // empty') || fname=""
      if [[ -n $fname ]]; then
        for cand in "$CACHE/${fname%.*}".* "$CACHE/flat-${fname%.*}".*; do
          [[ -f $cand ]] || continue
          [[ $cand == *-adminThumbnail* ]] && continue
          src=$cand
          note "media $mid: no source url — using the local copy $(basename "$cand")"
          break
        done
      fi
    fi
    if [[ -z $src ]]; then
      note "media $mid: no source url recorded — re-import this product's images by hand"
      unfixable+="$mid"$'\n'
      continue
    fi
    note "media $mid ← re-uploading $src"
    new=$("$(dirname "${BASH_SOURCE[0]}")/upload-media.sh" "$src") || { unfixable+="$mid"$'\n'; continue; }

    # relink every product that referenced the dead id
    while read -r pid; do
      [[ -n $pid ]] || continue
      before=$(api GET "/products/$pid")
      payload=$(jq --argjson old "$mid" --argjson new "$new" '
        .data as $p
        | { name: $p.name, slug: $p.slug, category_ids: $p.category_ids,
            brand_id: $p.brand_id, attribute_family_id: $p.attribute_family_id,
            is_best_seller: $p.is_best_seller, is_on_sale: $p.is_on_sale,
            is_discontinued: $p.is_discontinued,
            variants: [ $p.variants[]
                        | .images = ((.images // []) | map(if . == $old then $new else . end)) ] }
        ' <<<"$before")
      # same guard as add-variant.sh: never let a PUT drop a variant
      jq -e --argjson old "$(jq -c '[.data.variants[].id]' <<<"$before")" \
            '([.variants[].id // empty]) as $now | ($old - $now) | length == 0' <<<"$payload" >/dev/null \
        || die "internal: product $pid PUT would drop a variant — refusing"
      jq -e '[.variants[] | select(.is_default)] | length == 1' <<<"$payload" >/dev/null \
        || die "internal: product $pid PUT must keep exactly one default variant"
      printf '%s\n' "$payload" > "$CACHE/product-$pid-relink.json"
      api PUT "/products/$pid" "$CACHE/product-$pid-relink.json" >/dev/null
      note "product $pid: media $mid → $new"
    done < <(printf '%s' "$rows" | awk -v m="$mid" '$3 == m {print $1}' | sort -un)
    fixed+="$mid $new"$'\n'
  done <<<"$broken"
fi

# --- report ------------------------------------------------------------------
jq -n --arg checked "$checked" --arg rows "$rows" --arg fixed "$fixed" --arg unfixable "$unfixable" '
  def lines: split("\n") | map(select(length > 0));
  { checked: ($checked | lines | map(split(" ") | {media: (.[0]|tonumber), status: .[1], url: (.[2] // "")})),
    references: ($rows | lines | map(split(" ") | {product: (.[0]|tonumber), variant: .[1], media: (.[2]|tonumber)})),
    fixed: ($fixed | lines | map(split(" ") | {old: (.[0]|tonumber), new: (.[1]|tonumber)})),
    unfixable: ($unfixable | lines | map(tonumber)) }
  | ([.checked[] | select(.status != "200")] | length) as $broken
  | . + {summary: {references: (.references|length), media: (.checked|length),
                   broken: $broken, fixed: (.fixed|length),
                   still_broken: ($broken - (.fixed|length))}}' > "$REPORT"

jq -r '.summary | "\n\(.references) references, \(.media) distinct media, \(.broken) broken, \(.fixed) repaired, \(.still_broken) still broken"' "$REPORT" >&2
note "report: $REPORT"

still=$(jq -r '.summary.still_broken' "$REPORT")
(( still > 0 )) && exit 1 || exit 0
