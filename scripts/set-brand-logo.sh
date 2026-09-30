#!/usr/bin/env bash
# Replace an EXISTING brand's logo. Name, slug and meta are preserved.
#
#   scripts/set-brand-logo.sh 7 .siruk-cache/logos/3-royal-canin.png
#   scripts/set-brand-logo.sh 7 'https://…/logo.png'
#   scripts/set-brand-logo.sh 7 729                    # an existing media id
#
# The logo must be one you have LOOKED AT (scripts/fetch-logo.sh → Read it).
# A brand image is a shared reference: it renders next to every product of that
# brand, so a wrong file is wrong everywhere.
#
# Refuses if the media is already another brand's logo — several brands sharing
# one image is the bug this script exists to undo (2026-08-13: 12 brands all
# pointed at media 61). FORCE=1 to override, KEEP_ALPHA=1 to keep transparency.
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

[[ $# -ge 2 ]] || die "usage: $0 <brand-id> <logo file|url|mediaId>"
id=$1 logo=$2
[[ $id =~ ^[0-9]+$ ]] || die "brand id must be a number"

before=$(api GET "/brands/$id")
name=$(jq -r '.data.name' <<<"$before")
old=$(jq -r '.data.image // "none"' <<<"$before")
note "brand $id $name — current image: $old"

if [[ $logo =~ ^[0-9]+$ ]]; then
  media=$logo
  media_ok "$media" || die "media $media is not readable — pick another"
else
  [[ $logo == *.svg || $logo == *.svg\?* ]] && \
    die "SVG logos are not supported by the media library — find a PNG/JPEG"
  media=$("$(dirname "${BASH_SOURCE[0]}")/upload-media.sh" "$logo" "${MEDIA_DIR:-logos}") \
    || die "logo upload failed: $logo"
  note "logo → media $media"
fi

# Would this leave two brands sharing one image again?
shared=$(api GET '/brands?forProducts=true' | jq -r --argjson m "$media" --argjson i "$id" '
  .data[] | select(.id != $i and .image == $m) | "\(.id)\t\(.name)"')
if [[ -n $shared ]]; then
  note "⚠ media $media is already the logo of:"
  printf '%s\n' "$shared" >&2
  note "→ every brand needs its own logo. FORCE=1 to do it anyway."
  [[ ${FORCE:-} == 1 ]] || exit 1
fi

payload=$(jq -c --argjson m "$media" '.data
  | {name, slug, image: $m,
     meta: {title: (.meta.title // .name), description: (.meta.description // "")}}' <<<"$before")
printf '%s' "$payload" | api_json PUT "/brands/$id" >/dev/null

after=$(api GET "/brands/$id")
now=$(jq -r '.data.image // "none"' <<<"$after")
[[ $now == "$media" ]] || die "brand $id still points at image $now — the PUT did not take"
url=$(media_url "$media") || url=""
[[ -n $url ]] && status=$(url_status "$url") || status="no-url"
note "brand $id $name → media $media  HTTP $status"
printf '%s\n' "$url"
[[ $status == 200 ]] || die "the new logo url does not resolve — fix before trusting it"
