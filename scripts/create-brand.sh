#!/usr/bin/env bash
# Create a brand: dedupe against the live list, upload the logo, POST, read back.
#
#   scripts/create-brand.sh "Farmina" 'https://www.farmina.com/…/logo.png'
#   scripts/create-brand.sh "Farmina" ./logo.png
#   scripts/create-brand.sh "Farmina" 42                  # an existing media id
#   NO_LOGO=1 scripts/create-brand.sh "Farmina"           # no logo (API allows it,
#                                                         #   the UI marks it required)
#
# The logo should be a file you have already looked at — run it through
# scripts/fetch-logo.sh and Read the image first. A brand is a shared reference:
# a wrong logo shows up on every product of that brand.
#
# Slug defaults to the kebab-cased name; pass a third arg to override.
# Env: FORCE=1 create even though a similar brand exists ·
#      NO_LOGO=1 deliberately create without a logo (to be filled in later) ·
#      KEEP_ALPHA=1 keep logo transparency (default: flattened onto white,
#      because the storefront composites transparent images on black) ·
#      META_DESC="…" meta description (default: "<Name> pet food and products").
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

[[ $# -ge 1 ]] || die "usage: $0 \"<Brand Name>\" [<logo file|url|mediaId>] [slug]"
name=$1 logo=${2:-} slug=${3:-}

slugify() { printf '%s' "$1" | tr '[:upper:]' '[:lower:]' | sed -E 's/[^a-z0-9]+/-/g; s/^-+//; s/-+$//'; }
norm()    { printf '%s' "$1" | tr '[:upper:]' '[:lower:]' | tr -cd '[:alnum:]'; }

[[ -n $slug ]] || slug=$(slugify "$name")
[[ -n $slug ]] || die "cannot derive a slug from \"$name\" — pass one explicitly"

# Already there? A brand is a shared reference — never end up with two of them.
brands=$(api GET '/brands?forProducts=true')
key=$(norm "$name")
dupe=$(jq -r --arg k "$key" --arg s "$slug" '
  .data[] | select((.name | ascii_downcase | gsub("[^a-z0-9]"; "")) == $k or (.slug // "") == $s)
  | "\(.id)\t\(.name)\t\(.slug // "-")"' <<<"$brands")
if [[ -n $dupe ]]; then
  note "brand already exists — use this id, do not create a second one:"
  printf '%s\n' "$dupe" >&2
  exit 1
fi
near=$(jq -r --arg k "$key" '
  .data[] | (.name | ascii_downcase | gsub("[^a-z0-9]"; "")) as $n
  | select(($n | startswith($k)) or ($k | startswith($n)))
  | "\(.id)\t\(.name)"' <<<"$brands")
if [[ -n $near ]]; then
  note "⚠ similar brand(s) already in admin:"
  printf '%s\n' "$near" >&2
  note "→ same brand under another spelling? use that id. FORCE=1 to create anyway."
  [[ ${FORCE:-} == 1 ]] || exit 1
fi

# Logo → media id. Refuse to create a logo-less brand by accident: the field is
# required in the UI, and a brand created blank tends to stay blank.
if [[ -z $logo && ${NO_LOGO:-} != 1 ]]; then
  die "no logo given — find the brand's official logo first (scripts/fetch-logo.sh <url…>, then look at it), or NO_LOGO=1 to create the brand without one and flag it for the user"
fi

media=null
if [[ -n $logo ]]; then
  if [[ $logo =~ ^[0-9]+$ ]]; then
    media=$logo
  else
    [[ $logo == *.svg || $logo == *.svg\?* ]] && \
      die "SVG logos are not supported by the media library — find a PNG/JPEG (≥400px)"
    media=$("$(dirname "${BASH_SOURCE[0]}")/upload-media.sh" "$logo" "${MEDIA_DIR:-}") \
      || die "logo upload failed: $logo"
    note "logo → media $media"
  fi
fi

payload=$(jq -nc --arg n "$name" --arg s "$slug" --argjson m "$media" \
  --arg d "${META_DESC:-$name pet food and products}" \
  '{name: $n, slug: $s, image: $m, meta: {title: $n, description: $d}}')

id=$(printf '%s' "$payload" | api_json POST /brands | jq -r '.data.id')
[[ $id =~ ^[0-9]+$ ]] || die "no brand id in response"
note "created brand $id"

# Read back from the live list — that is what the product form reads.
api GET '/brands?forProducts=true' | jq -r --argjson i "$id" '
  .data[] | select(.id == $i) | "brand \(.id)\t\(.name)\tslug=\(.slug // "-")\timage=\(.image // "none")"'

# …and where the logo actually ended up, so it can be opened and checked.
if [[ $media != null ]]; then
  url=$(media_url "$media") || url=""
  note "logo media $media${url:+  $url}"
fi
