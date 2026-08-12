#!/usr/bin/env bash
# Upload an image to the media library and print its media id (use that id in
# a variant's "images" array). Accepts a local file or a URL — URLs are
# downloaded first with a browser User-Agent (brand CDNs 403 curl's default).
#
#   scripts/upload-media.sh ./img/rc-mini-adult.jpg
#   scripts/upload-media.sh 'https://www.royalcanin.com/.../packshot.jpg'
#   scripts/upload-media.sh ./a.jpg products   # into a subdirectory
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

[[ $# -ge 1 ]] || die "usage: $0 <file|url> [directory]"
src=$1 dir=${2:-}

UA='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36'

CACHE_FILE="$CACHE/media-cache.json"
[[ -f $CACHE_FILE ]] || echo '{}' > "$CACHE_FILE"

if [[ $src == http*://* ]]; then
  # already uploaded this exact URL? reuse the media id instead of duplicating it
  if cached=$(jq -er --arg u "$src" '.[$u] // empty' "$CACHE_FILE"); then
    note "cache hit: $src → media $cached"
    printf '%s\n' "$cached"
    exit 0
  fi
  name=$(basename "${src%%\?*}")
  path="$CACHE/$name"
  ctype=$(curl -sSL -A "$UA" -o "$path" -w '%{content_type}' "$src") || die "download failed: $src"
  # some CDNs (e.g. Royal Canin weshare) serve images from extension-less URLs;
  # the media library keys off the filename, so give it one
  if [[ $name != *.* ]]; then
    case $ctype in
      *png*) ext=png ;; *jpeg*|*jpg*) ext=jpg ;; *webp*) ext=webp ;;
      *avif*) ext=avif ;; *gif*) ext=gif ;; *) ext=jpg ;;
    esac
    mv "$path" "$path.$ext"; name="$name.$ext"; path="$path.$ext"
  fi
  note "downloaded $name ($(wc -c < "$path" | tr -d ' ') bytes, $ctype)"
else
  path=$src
  [[ -f $path ]] || die "no such file: $path"
  name=$(basename "$path")
fi

# Flatten transparency onto white. Brand packshots are often transparent PNGs;
# the storefront gallery composites them on a dark surface, so the pack ends up
# on a black background (reported 2026-08-12). JPEG has no alpha and `sips`
# mattes onto white, which is what an opaque packshot should look like.
# KEEP_ALPHA=1 skips this (e.g. for a logo meant to stay transparent).
if [[ ${KEEP_ALPHA:-} != 1 ]] \
   && [[ $(sips -g hasAlpha "$path" 2>/dev/null | awk '/hasAlpha/{print $2}') == yes ]]; then
  flat="$CACHE/flat-${name%.*}.jpg"
  if sips -s format jpeg -s formatOptions best "$path" --out "$flat" >/dev/null 2>&1; then
    path=$flat; name="${name%.*}.jpg"
    note "flattened transparency onto white → $name"
  else
    note "⚠ could not flatten $name; uploading with alpha intact"
  fi
fi

# WxH — sips is macOS built-in; empty dimensions are accepted by the API.
dims=""
if w=$(sips -g pixelWidth "$path" 2>/dev/null | awk '/pixelWidth/{print $2}') \
   && h=$(sips -g pixelHeight "$path" 2>/dev/null | awk '/pixelHeight/{print $2}') \
   && [[ -n ${w:-} && -n ${h:-} ]]; then
  # the media endpoint 500s on very large images (verified: a 5000x5000 Royal
  # Canin packshot). Downscale to MAX_PX before uploading — never touching the
  # caller's original file.
  MAX_PX=${MAX_PX:-2000}
  if (( w > MAX_PX || h > MAX_PX )); then
    resized="$CACHE/resized-$name"
    cp "$path" "$resized"
    sips -Z "$MAX_PX" "$resized" >/dev/null 2>&1 || die "resize failed: $name"
    path=$resized
    w=$(sips -g pixelWidth "$path" | awk '/pixelWidth/{print $2}')
    h=$(sips -g pixelHeight "$path" | awk '/pixelHeight/{print $2}')
    note "downscaled to ${w}x${h} (was over ${MAX_PX}px)"
  fi
  dims="${w}x${h}"
fi

base=${name%.*}
info=$(jq -nc --arg f "$name" --arg c "$base" --arg d "$dims" --arg dir "$dir" \
  '{filename: $f, caption: $c, alt: $c, dimensions: $d, directory: $dir}')

# multipart/form-data with exactly two parts: file (binary) + fileInfo (JSON string).
# A JSON body or a missing fileInfo part → 500 "Attempt to read property filename on null".
tok=$(siruk_token) || exit 1
out=$(curl -sS -X POST "$SIRUK_API/medias" \
        -H "Authorization: Bearer $tok" \
        -H 'Accept: application/json' \
        -F "file=@${path};filename=${name}" \
        -F "fileInfo=${info}" \
        -w '\n%{http_code}') || die "upload failed: $name"

code=${out##*$'\n'}; body=${out%$'\n'*}
note "HTTP $code  POST /medias  ($name ${dims:-no-dims})"
(( code < 400 )) || { printf '%s\n' "$body" >&2; exit 1; }

id=$(jq -r '.data.id' <<<"$body")
[[ $id =~ ^[0-9]+$ ]] || die "no media id in response: $body"

if [[ $src == http*://* ]]; then
  tmp=$(mktemp)
  jq --arg u "$src" --argjson i "$id" '.[$u] = $i' "$CACHE_FILE" > "$tmp" && mv "$tmp" "$CACHE_FILE"
fi

printf '%s\n' "$id"
