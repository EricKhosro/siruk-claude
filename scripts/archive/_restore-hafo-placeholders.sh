#!/usr/bin/env bash
# Waits for the running image pass, then re-applies the 132 products whose gallery
# should carry a watermarked hafo placeholder (CLAUDE.md rule 7a, PM decision).
cd "$(dirname "$0")/.."
RUN=runs/2026-09-11
while pgrep -f "enrich-images.py --apply" >/dev/null; do sleep 20; done
export SIRUK_MEDIA_DELAY=0.5 SIRUK_CHUNK_PAUSE=6
ids=$(cat .siruk-cache/hafo-placeholder-ids.txt)
echo "=== PLACEHOLDERS $(date) — $(echo $ids | tr ',' ' ' | wc -w | tr -d ' ') products"
python3 - <<'PY'
import json
s = json.load(open(".siruk-cache/enrich-images.state.json"))
keep = {int(x) for x in open(".siruk-cache/hafo-placeholder-ids.txt").read().split(",")}
s["done"] = [i for i in s["done"] if i not in keep]
json.dump(s, open(".siruk-cache/enrich-images.state.json", "w"), indent=0)
print("state: re-queued", len(keep), "products")
PY
scripts/enrich-images.py --apply --only "$ids" >> $RUN/image-apply.log 2>&1
echo "=== PLACEHOLDERS DONE $(date)"
