#!/usr/bin/env bash
# Resolve ALL official TRIXIE gallery images for an article number.
#
#   scripts/trixie-image.sh <article-number>        -> every image URL, one per line, best first
#   scripts/trixie-image.sh <article-number> --first -> only the first (old behaviour)
#
# Source of truth is the product page (server-rendered, ~100 KB), found through the
# cached catalogue (`scripts/trixie-catalogue.py --lookup`). Its gallery references
# the 1600mx1200m CDN renditions, and every file name carries the article number:
#   PHO_PRO_CLIP_<art>-<n>   packshot            PHO_PAC_CLIP_<art>-<n>   pack
#   PHO_PRO_DOG/CAT_<art>-<n> lifestyle          PHO_PRO_GROUP_CLIP_<a>-<b>-… group shot
#   GRA_PRO_<art>-<n>        drawing/graphic
# Only images keyed to THIS article (or a group shot naming it) are returned, in
# that order — the first one becomes the storefront thumbnail, and it MUST be a
# clean product shot (CLAUDE.md rule 7). Product pages sometimes list only the
# lifestyle/group photos and omit the PHO_PRO_CLIP packshot that the CDN does
# serve (45558, 2026-09-10), so whenever the page gives no CLIP image the CDN is
# probed for PHO_PRO_CLIP / PHO_PAC_CLIP and the hits are merged in. The same
# probe is the fallback when the article has no catalogue page (e.g. litter
# 4020); it returns every hit, not just the lowest number.
# Rewritten 2026-09-10: the old version returned one image (the lowest n it hit),
# which is why every imported toy had a single picture.
set -uo pipefail
UA="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
n="${1:?article number}"; first="${2:-}"
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
tmp="$(mktemp)"; trap 'rm -f "$tmp"' EXIT

rank() {  # print "<rank>\t<url>" so sort gives packshot, pack, lifestyle, group, graphic
  local u=$1 f; f=${u##*/}
  case "$f" in
    PHO_PRO_CLIP_*) echo "1	$u";; PHO_PAC_CLIP_*) echo "2	$u";;
    PHO_PRO_GROUP*) echo "4	$u";; GRA_*) echo "5	$u";; *) echo "3	$u";;
  esac
}

merge_sources() {  # stdin: urls from any Trixie source → ranked, deduped by file
  while read -r u; do
    [ -n "$u" ] || continue
    f=${u##*/}; key=${f%%_%23*}; key=${key%.jpg}; key=${key%.jpeg}; key=${key%.png}
    case "$u" in *cdn.trixie.de*) s=0;; *) s=1;; esac   # .de wins a tie
    printf '%s\t%s\t%s\n' "$(rank "$u" | cut -f1)" "$key	$s" "$u"
  done | sort -t'	' -k1,1n -k3,3n -k2,2 | awk -F'\t' '!seen[$2]++' | cut -f4
}

page=$("$here/trixie-catalogue.py" --lookup "$n" 2>/dev/null | jq -r '.url // empty')
if [ -n "$page" ]; then
  curl -sS -A "$UA" -L --max-time 90 "$page" 2>/dev/null \
    | grep -oE "https://cdn\.trixie\.de/assets/img/1600mx1200m/[^\"' )]*\.(jpg|jpeg|png|webp)" \
    | sort -u \
    | while read -r u; do
        f=${u##*/}
        # this article's own images, or a group shot that names it: _<art>-<n>_ / _<a>-<art>-<b>…
        if printf '%s' "$f" | grep -qE "_(${n}|[0-9-]*-${n}|${n}-[0-9-]*|[0-9-]*-${n}-[0-9-]*)-[0-9]+_"; then rank "$u"; fi
      done | sort -t'	' -k1,1n -k2,2 | cut -f2 > "$tmp"
fi

probe() {  # CDN probe for the clean shots; appends "<rank>\t<url>" lines to $tmp.p
  for pfx in PHO_PRO_CLIP PHO_PAC_CLIP; do
    for i in 1 2 3 4 5 6 7 8; do
      u="https://cdn.trixie.de/assets/img/1600mx1200m/${pfx}_${n}-${i}_%23SALL_%23AWK_%23V1.jpg"
      ( c=$(curl -sS -A "$UA" -o /dev/null -w '%{http_code}' --max-time 25 "$u" 2>/dev/null)
        [ "$c" = 200 ] && rank "$u" >> "$tmp.p" ) &
    done
  done
  wait
}

# no page at all → the probe is the whole gallery; page without a packshot →
# probe and merge, so a clean shot can lead
if [ ! -s "$tmp" ] || ! grep -q '/PHO_PRO_CLIP_' "$tmp"; then
  probe
  if [ -f "$tmp.p" ]; then
    { [ -s "$tmp" ] && while read -r u; do rank "$u"; done < "$tmp"; cat "$tmp.p"; } \
      | sort -u | sort -t'	' -k1,1n -k2,2 | cut -f2 > "$tmp.m"
    mv "$tmp.m" "$tmp"; rm -f "$tmp.p"
  fi
fi

# Thin or unclean result? trixie.de drops discontinued articles from both the
# catalogue and the CDN, and even a live page often keeps a single photo — the
# country shops host their own copies (1500x1500) under the same article-keyed
# file names. trixie.es is the one with an article ("Ref.") search, so it is the
# fallback: consulted when .de gave no packshot or fewer than 3 pictures, and
# merged in behind the .de files (same file → the .de copy wins). TRIXIE_ES=0
# skips it, TRIXIE_ES=always asks it for every article. Answers are cached in
# .siruk-cache/trixie-es.json, so a second run costs nothing.
if [ "${TRIXIE_ES:-1}" != 0 ] && { [ "${TRIXIE_ES:-1}" = always ] || [ ! -s "$tmp" ] \
     || ! grep -q '/PHO_PRO_CLIP_' "$tmp" || [ "$(wc -l < "$tmp")" -lt 3 ]; }; then
  "$here/trixie-es.py" --images "$n" > "$tmp.es" 2>/dev/null || :
  if [ -s "$tmp.es" ]; then
    cat "$tmp" "$tmp.es" 2>/dev/null | merge_sources > "$tmp.m" && mv "$tmp.m" "$tmp"
  fi
  rm -f "$tmp.es"
fi

[ -s "$tmp" ] || exit 0
if [ "$first" = "--first" ]; then head -1 "$tmp"; else cat "$tmp"; fi
