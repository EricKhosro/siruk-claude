#!/usr/bin/env bash
# Download candidate brand logos so they can be LOOKED AT before one is uploaded.
#
#   scripts/fetch-logo.sh 'https://brand.com/logo.png' 'https://…/logo2.png'
#   scripts/fetch-logo.sh ./downloaded-logo.png
#
# Nothing is uploaded and nothing is created — this only fetches, measures and
# screens candidates. It prints one local path per accepted candidate on stdout
# and a verdict table on stderr. **Open every accepted path with the Read tool
# and confirm with your own eyes that it is that brand's logo** before passing it
# to create-brand.sh. A 200 and a plausible filename are not evidence: a CDN
# returns placeholders, sprite sheets and other brands' art with equal success,
# and that is exactly how a wrong logo ended up on a brand before.
#
# Env: MIN_PX=400  below this the candidate is accepted but flagged low-res
#      HARD_MIN=160 below this it is rejected outright (favicon / sprite slice)
#      LOGO_DIR=<dir> where to put the files.
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

[[ $# -ge 1 ]] || die "usage: $0 <url|file> [url|file …]"

UA='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36'
MIN_PX=${MIN_PX:-400}
HARD_MIN=${HARD_MIN:-160}
DIR=${LOGO_DIR:-$CACHE/logos}
mkdir -p "$DIR"

slug() { printf '%s' "$1" | LC_ALL=C tr -c 'A-Za-z0-9._-' '-' | sed -e 's/--*/-/g' -e 's/^[-.]*//' -e 's/-*$//'; }

accepted=()
lowres=()
i=0
for src in "$@"; do
  i=$((i + 1))
  reasons=()

  if [[ $src == *.svg || $src == *.svg\?* ]]; then
    note "[$i] REJECT  $src"
    note "         svg — the media library cannot serve it; find the png the press kit ships"
    continue
  fi

  if [[ $src == http*://* ]]; then
    name=$(basename "${src%%\?*}")
    name=$(printf '%s' "$name" | perl -pe 's/%([0-9A-Fa-f]{2})/chr(hex($1))/ge')
    name=$(slug "$name"); [[ -n $name ]] || name="logo-$i"
    path="$DIR/$i-$name"
    if ! ctype=$(curl -sSL -A "$UA" -o "$path" -w '%{content_type}' "$src"); then
      note "[$i] REJECT  $src"
      note "         download failed"
      continue
    fi
    if [[ $path != *.* ]]; then
      case $ctype in
        *png*) ext=png ;; *jpeg*|*jpg*) ext=jpg ;; *webp*) ext=webp ;;
        *avif*) ext=avif ;; *gif*) ext=gif ;; *svg*) ext=svg ;; *) ext=bin ;;
      esac
      mv "$path" "$path.$ext"; path="$path.$ext"
    fi
  else
    [[ -f $src ]] || { note "[$i] REJECT  $src"; note "         no such file"; continue; }
    path=$src; ctype=$(file -b --mime-type "$src")
  fi

  kind=$(file -b --mime-type "$path" 2>/dev/null || echo unknown)
  bytes=$(wc -c < "$path" | tr -d ' ')

  case $kind in
    image/svg*)  note "[$i] REJECT  $src"; note "         svg — not supported by the media library"; continue ;;
    image/*)     ;;
    *)           note "[$i] REJECT  $src"; note "         not an image ($kind, $bytes bytes) — probably an html error page"; continue ;;
  esac

  w=$(sips -g pixelWidth  "$path" 2>/dev/null | awk '/pixelWidth/{print $2}')
  h=$(sips -g pixelHeight "$path" 2>/dev/null | awk '/pixelHeight/{print $2}')
  alpha=$(sips -g hasAlpha "$path" 2>/dev/null | awk '/hasAlpha/{print $2}')
  long=0
  [[ -n ${w:-} && -n ${h:-} ]] && long=$(( w > h ? w : h ))

  (( long >= HARD_MIN )) || reasons+=("only ${w:-?}x${h:-?} — that is a favicon or a sprite slice, not a logo")
  (( bytes > 1000 ))     || reasons+=("$bytes bytes — too small to be a real logo")

  if (( ${#reasons[@]} )); then
    note "[$i] REJECT  $src"
    for r in "${reasons[@]}"; do note "         $r"; done
    continue
  fi

  verdict=ok
  if (( long < MIN_PX )); then
    verdict="LOW-RES"
    lowres+=("$path")
  fi

  note "[$i] $verdict  ${w}x${h} ${kind#image/} ${bytes}b alpha=${alpha:-?}  $path"
  note "            ← $src"
  accepted+=("$path")
done

if (( ${#accepted[@]} == 0 )); then
  note ""
  die "no candidate passed the mechanical screen — keep looking (press kit / Wikimedia / another official page). Never draw or approximate a logo."
fi

note ""
if (( ${#lowres[@]} )); then
  note "⚠ ${#lowres[@]} candidate(s) are under ${MIN_PX}px on the long side — a site header"
  note "  asset. Usable, but look for a bigger one first: the press kit, the @2x/"
  note "  full-size version of the same file, or Wikimedia. Use a low-res logo only"
  note "  if nothing better exists, and say so in the report."
  note ""
fi
note "→ now Read each path above as an image and confirm it is THIS brand's logo"
note "  (right brand, a logo and not a packshot, not a retailer badge, uncropped),"
note "  then: scripts/create-brand.sh \"<Brand>\" <the chosen path>"
printf '%s\n' "${accepted[@]}"
