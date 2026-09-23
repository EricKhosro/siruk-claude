#!/usr/bin/env bash
# Upload an image to the media library and print its media id (use that id in
# a variant's "images" array). Accepts a local file or a URL — URLs are
# downloaded first with a browser User-Agent (brand CDNs 403 curl's default).
#
#   scripts/upload-media.sh ./img/rc-mini-adult.jpg
#   scripts/upload-media.sh 'https://www.royalcanin.com/.../packshot.jpg'
#   scripts/upload-media.sh ./a.jpg products/trixie/toys/   # into a folder
#
# Rule 7: every upload goes in a media-library folder — `products/<brand-slug>/
# <type>/` or `banners/…`, never the root. The folder is the 2nd argument, else
# $MEDIA_DIR (for scripts that call this without one); with neither, it still
# uploads, but says so loudly.
#
# Pacing, retries and the post-upload check are configured in config.json
# (media.* section). The check matters: the server can return a media id whose
# file was never written, so the id looks valid and every url 404s.
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

[[ $# -ge 1 ]] || die "usage: $0 <file|url> [directory]"
src=$1 dir=${2:-${MEDIA_DIR:-}}
[[ -n $dir ]] || note "⚠ no folder given (arg 2 or MEDIA_DIR) — uploading to the media root; rule 7 wants products/<brand>/<type>/ or banners/"

UA='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36'

CACHE_FILE="$CACHE/media-cache.json"
[[ -f $CACHE_FILE ]] || echo '{}' > "$CACHE_FILE"

if [[ $src == http*://* ]]; then
  # already uploaded this exact URL? reuse the media id instead of duplicating it
  if cached=$(jq -er --arg u "$src" '.[$u] // empty' "$CACHE_FILE"); then
    if [[ $CFG_MEDIA_VERIFY != true ]] || media_ok "$cached"; then
      note "cache hit: $src → media $cached"
      printf '%s\n' "$cached"
      exit 0
    fi
    # the cached id points at a file the server never wrote — forget it and
    # upload again rather than handing back a dead image
    note "cached media $cached is broken — dropping it from the cache and re-uploading"
    tmp=$(mktemp)
    jq --arg u "$src" 'del(.[$u])' "$CACHE_FILE" > "$tmp" && mv "$tmp" "$CACHE_FILE"
    [[ $CFG_MEDIA_DELETE_BROKEN != true ]] || api DELETE "/medias/$cached" >/dev/null 2>&1 || true
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
  # caller's original file. (config.json → media.max_pixels, env MAX_PX wins.)
  MAX_PX=${CFG_MEDIA_MAX_PX%.*}
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

# Normalise the filename before it leaves. The media library stores it verbatim
# and serves it back inside a url; a literal '%' (which is what a percent-escaped
# source url like ..._HEALTH%201.png gives you) or a space produces a url the
# server can no longer resolve — the media record is created, the id looks fine
# and every storage url 404s. That is the root cause of the dead images found
# 2026-08-13 (media 621, product 71), not server load.
decoded=$(printf '%s' "$name" | perl -pe 's/%([0-9A-Fa-f]{2})/chr(hex($1))/ge')
safe=$(printf '%s' "$decoded" | LC_ALL=C tr -c 'A-Za-z0-9._-' '-' \
       | sed -e 's/--*/-/g' -e 's/^[-.]*//' -e 's/-*$//')
[[ -n $safe ]] || safe="image-$$.jpg"
if [[ $safe != "$name" ]]; then
  note "filename → $safe (was: $name)"
  name=$safe
fi

base=${name%.*}
caption=$(printf '%s' "${decoded%.*}" | tr -d '\r')
info=$(jq -nc --arg f "$name" --arg c "$caption" --arg d "$dims" --arg dir "$dir" \
  '{filename: $f, caption: $c, alt: $c, dimensions: $d, directory: $dir}')

# multipart/form-data with exactly two parts: file (binary) + fileInfo (JSON string).
# A JSON body or a missing fileInfo part → 500 "Attempt to read property filename on null".
tok=$(siruk_token) || exit 1

post_media() {
  local out code body rc attempt=1 wait
  while :; do
    pace media
    if out=$(curl -sS -X POST "$SIRUK_API/medias" \
                  -H "Authorization: Bearer $tok" \
                  -H 'Accept: application/json' \
                  --connect-timeout "$CFG_REQ_CONNECT_TIMEOUT" \
                  --max-time "$CFG_REQ_TIMEOUT" \
                  -F "file=@${path};filename=${name}" \
                  -F "fileInfo=${info}" \
                  -w '\n%{http_code}'); then rc=0; else rc=$?; fi
    if (( rc == 0 )); then
      code=${out##*$'\n'}; body=${out%$'\n'*}
    else
      code=000; body="curl exited $rc (network/timeout)"
    fi

    if _retryable "$rc" "$code" && (( attempt < ${CFG_RETRY_ATTEMPTS%.*} )); then
      wait=$(_backoff "$attempt")
      note "HTTP $code  POST /medias ($name) — retrying in ${wait}s (attempt $attempt/${CFG_RETRY_ATTEMPTS%.*})"
      sleep "$wait"
      attempt=$((attempt + 1))
      continue
    fi
    break
  done

  note "HTTP $code  POST /medias  ($name ${dims:-no-dims})"
  (( rc == 0 && code < 400 )) || { printf '%s\n' "$body" >&2; return 1; }
  jq -r '.data.id' <<<"$body"
}

# Upload, then prove the file is really there. A media id whose storage url
# 404s is worse than a failed upload: the product saves and the image is dead
# (found 2026-08-13 — media 621 on product 71). The filename above is the known
# cause; the check stays because the api reports success either way.
tries=${CFG_MEDIA_UPLOAD_TRIES%.*}; (( tries >= 1 )) || tries=1
attempt=1
while :; do
  id=$(post_media) || die "upload failed: $name"
  [[ $id =~ ^[0-9]+$ ]] || die "no media id in response for $name"

  if [[ $CFG_MEDIA_VERIFY != true ]]; then break; fi
  sleep "$CFG_MEDIA_VERIFY_WAIT"
  if media_ok "$id"; then break; fi

  # the record is a dud — bin it so it can't be referenced by mistake
  if [[ $CFG_MEDIA_DELETE_BROKEN == true ]]; then
    api DELETE "/medias/$id" >/dev/null 2>&1 || note "could not delete broken media $id"
    note "deleted broken media record $id"
  fi
  if [[ $CFG_MEDIA_RETRY_UPLOAD != true ]] || (( attempt >= tries )); then
    die "media for $name never became readable after $attempt upload(s) — server-side storage failure; slow the pacing in config.json (media.delay_seconds / media.chunk_size) and retry"
  fi
  attempt=$((attempt + 1))
  note "re-uploading $name (attempt $attempt/$tries)"
done

if [[ $src == http*://* ]]; then
  tmp=$(mktemp)
  jq --arg u "$src" --argjson i "$id" '.[$u] = $i' "$CACHE_FILE" > "$tmp" && mv "$tmp" "$CACHE_FILE"
fi

printf '%s\n' "$id"
