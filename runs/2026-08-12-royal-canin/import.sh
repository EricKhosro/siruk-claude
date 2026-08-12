#!/usr/bin/env bash
# Drive the Royal Canin import: plan.tsv + the Royal Canin extract → products.
#
#   runs/2026-08-12-royal-canin/import.sh            # all rows
#   runs/2026-08-12-royal-canin/import.sh mini maxi  # only these product_keys
#
# Resumable: created product ids are recorded in .siruk-cache/rc-created.json,
# so a re-run adds only what is missing (image uploads are cached too).
# Rich text comes from the extract (.siruk-cache/rc-extract.json), prices/stock
# from plan.tsv (CSV wins), and each row's attrs are passed through as-is.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"
cd "$ROOT"

PLAN="$HERE/plan.tsv"
EXTRACT=.siruk-cache/rc-extract.json
STATE=.siruk-cache/rc-created.json
PAYDIR=.siruk-cache/rc-payloads
BRAND_ID=7          # Royal Canin (scripts/ids.sh)
IMAGES_PER_PRODUCT=3

mkdir -p "$PAYDIR"
[[ -f $STATE ]] || echo '{}' > "$STATE"
[[ -f $EXTRACT ]] || { echo "missing $EXTRACT — re-run the browser extraction" >&2; exit 1; }

only=("$@")
wanted() { (( ${#only[@]} == 0 )) && return 0; for k in "${only[@]}"; do [[ $k == "$1" ]] && return 0; done; return 1; }

state_get() { jq -r --arg k "$1" '.[$k] // empty' "$STATE"; }
state_set() { local t; t=$(mktemp); jq --arg k "$1" --argjson v "$2" '.[$k] = $v' "$STATE" > "$t" && mv "$t" "$STATE"; }

# Rich-text blocks for one mainItem, as JSON {about, ingredients, feeding}.
richtext() {
  jq --arg mi "$1" '
    def clean_label: gsub("^\\s*\\d[A-Z]?-\\s*"; "");
    def junk: test("NUTRIENT|CLAIM|PROVEN RESULTS|FOP|Formulation update"; "i");
    [.results[] | select(.mainItem == $mi)][0] as $p
    | ($p.benefits // [] | map(select((.label // "") | junk | not))) as $b
    | { about:
          ((if ($p.description // "") != "" then "<p>" + $p.description + "</p>" else "" end)
           + (if ($p.detailsDescription // "") != "" then "<p>" + $p.detailsDescription + "</p>" else "" end)
           + (if ($b | length) > 0
              then "<ul>" + ($b | map("<li><strong>" + ((.label // "") | clean_label) + "</strong>"
                                      + (if (.description // "") != "" then " — " + .description else "" end)
                                      + "</li>") | join("")) + "</ul>"
              else "" end)),
        ingredients:
          ([ $p.nutritionalInfo.composition, $p.nutritionalInfo.additives,
             $p.nutritionalInfo.analyticalConstituants, $p.nutritionalInfo.lipStatement ]
           | map(select(. != null and . != "")) | map("<p>" + . + "</p>") | join("")),
        feeding:
          ([ $p.nutritionalInfo.feedingInstructions, $p.nutritionalInfo.nutritionalInformationFeedingGuide,
             $p.nutritionalInfo.parnutsStatement, $p.nutritionalInfo.dvpStatement, $p.nutritionalInfo.rsaStatement ]
           | map(select(. != null and . != "")) | map("<p>" + . + "</p>") | join("")) }
  ' "$EXTRACT"
}

# Media ids for one mainItem (first N images), newline separated.
media_ids() {
  local mi=$1 url id
  while read -r url; do
    [[ -n $url ]] || continue
    # a single unusable image must not sink the product — log and carry on
    id=$(scripts/upload-media.sh "$url" 2>/dev/null | tail -1) || { echo "    !! image upload failed: $url" >&2; continue; }
    if [[ $id =~ ^[0-9]+$ ]]; then printf '%s\n' "$id"; else echo "    !! no media id for: $url" >&2; fi
  done < <(jq -r --arg mi "$mi" --argjson n "$IMAGES_PER_PRODUCT" \
             '[.results[] | select(.mainItem == $mi)][0].images[0:$n][]' "$EXTRACT")
}

grep -v '^#' "$PLAN" | grep -v '^[[:space:]]*$' | while IFS=$'\t' read -r key name slug cat fam main label sku price cost stock weight pricing attrs row; do
  wanted "$key" || continue

  echo "─── row $row  $key / $label"

  # resumable: if the product exists and already carries this sku, this row is done
  existing=$(state_get "$key")
  if [[ -n $existing ]] && scripts/show-product.sh "$existing" --json 2>/dev/null \
       | jq -e --arg s "$sku" '.data.variants[] | select(.sku == $s)' >/dev/null; then
    echo "    already present (sku $sku) — skipping"
    continue
  fi

  imgs=$(media_ids "$main" | jq -Rn '[inputs | tonumber]')
  rt=$(richtext "$main")

  # pricing_type "per_kg" = sold by weight: the API takes price_per_kg + weight and
  # ignores `price`, so the rate must reproduce the CSV pack price (2dp is all it
  # stores — worst-case drift is well under 1 AMD).
  variant=$(jq -n --arg label "$label" --arg sku "$sku" --argjson price "$price" \
                  --argjson cost "$cost" --argjson stock "$stock" --argjson weight "$weight" \
                  --arg pricing "$pricing" \
                  --argjson attrs "$attrs" --argjson imgs "$imgs" --argjson rt "$rt" '
    { name: $label, pricing_type: $pricing, sku: $sku, cost_price: $cost,
      stock: $stock, weight: $weight, vendor_stock: false, images: $imgs,
      about_this_item: $rt.about, ingredient_information: $rt.ingredients,
      feeding_instructions: $rt.feeding, attribute_value_ids: $attrs }
    + (if $pricing == "per_kg"
       then { price_per_kg: (($price / $weight * 100) | round / 100) }
       else { price: $price } end)')

  if [[ -z $existing ]]; then
    jq -n --arg name "$name" --arg slug "$slug" --argjson cat "[$cat]" \
          --argjson brand "$BRAND_ID" --argjson fam "$fam" --argjson v "$variant" '
      { name: $name, slug: $slug, category_ids: $cat, brand_id: $brand,
        attribute_family_id: $fam, is_best_seller: false, is_on_sale: false,
        variants: [ $v + {is_default: true, sort_order: 0} ] }' > "$PAYDIR/$key.json"
    id=$(scripts/create-product.sh "$PAYDIR/$key.json" 2>&1 | tee /dev/stderr | sed -n 's/^created product \([0-9]*\)$/\1/p')
    if [[ ! $id =~ ^[0-9]+$ ]]; then echo "!! create FAILED for $key (row $row)" >&2; continue; fi
    state_set "$key" "$id"
  else
    printf '%s\n' "$variant" > "$PAYDIR/$key-$row.json"
    # one bad row must not abort the run
    scripts/add-variant.sh "$existing" "$PAYDIR/$key-$row.json" \
      || echo "!! add-variant FAILED for $key row $row (payload: $PAYDIR/$key-$row.json)" >&2
  fi
done

echo
echo "── created products:"
jq -r 'to_entries[] | "  \(.value)\t\(.key)"' "$STATE"
