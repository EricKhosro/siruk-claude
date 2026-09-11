#!/usr/bin/env bash
# Render an SVG logo to a tight PNG at a given width, using headless Chrome.
#
#   scripts/rasterize-svg.sh logo.svg               # 1200px wide
#   scripts/rasterize-svg.sh logo.svg 800 out.png
#
# The media library cannot serve SVG, and several brands (Bewital's Belcando /
# Leonardo / Bewi, Agras' Schesir / Stuzzy) publish their logo only as one. This
# renders the official vector at print-ish resolution instead of settling for a
# ~120px header bitmap. `qlmanage` is not a substitute: it renders into a square
# canvas anchored top-left, so a wide logo comes out padded or clipped.
#
# Prints the output path. Look at the result before uploading it.
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

[[ $# -ge 1 ]] || die "usage: $0 <file.svg> [width] [out.png]"
svg=$1 width=${2:-1200} out=${3:-}
[[ -f $svg ]] || die "no such file: $svg"
[[ $(file -b --mime-type "$svg") == image/svg* ]] || die "$svg is not an SVG"

CHROME=${CHROME:-/Applications/Google Chrome.app/Contents/MacOS/Google Chrome}
[[ -x $CHROME ]] || die "Google Chrome not found — set CHROME=/path/to/chrome"

svg=$(cd "$(dirname "$svg")" && printf '%s/%s' "$PWD" "$(basename "$svg")")
[[ -n $out ]] || out="${svg%.svg}-${width}.png"

# aspect from width/height attributes, else from the viewBox
read -r w h < <(perl -0777 -ne '
  my ($w, $h);
  ($w, $h) = ($1, $2) if /<svg[^>]*\bwidth="([\d.]+)(?:px)?"[^>]*\bheight="([\d.]+)(?:px)?"/s;
  unless ($w && $h) {
    ($w, $h) = ($3, $4) if /viewBox="\s*([\d.-]+)[,\s]+([\d.-]+)[,\s]+([\d.]+)[,\s]+([\d.]+)/s;
  }
  printf "%s %s\n", $w || 0, $h || 0;' "$svg")
[[ ${w:-0} != 0 && ${h:-0} != 0 ]] || die "cannot read the SVG's dimensions — no width/height or viewBox"

height=$(awk -v w="$w" -v h="$h" -v W="$width" 'BEGIN{ printf "%.0f", W * h / w }')
note "$(basename "$svg"): ${w}x${h} → ${width}x${height}"

html=$(mktemp -t rasterize).html
cat > "$html" <<HTML
<!doctype html><meta charset="utf-8">
<style>html,body{margin:0;padding:0;background:#fff}
img{display:block;width:${width}px;height:${height}px}</style>
<img src="file://$svg">
HTML

"$CHROME" --headless --disable-gpu --hide-scrollbars --force-device-scale-factor=1 \
  --screenshot="$out" --window-size="${width},${height}" \
  --default-background-color=FFFFFFFF "file://$html" >/dev/null 2>&1 \
  || die "chrome failed to render $svg"
rm -f "$html"
[[ -s $out ]] || die "chrome produced no image"

note "→ $out ($(sips -g pixelWidth -g pixelHeight "$out" | awk '/pixel/{printf "%s", $2 (NR==1?"x":"")}'))"
printf '%s\n' "$out"
