#!/usr/bin/env python3
"""Contact sheets for the per-size image audit (rule 7, 2026-10-01). Read-only.

Multi-size products: every pack variant's whole gallery, one row per variant
(label + sku on the left). Single-size sized products: first image only, 4 per row.
Images come from storage (originalUrl in media-index.json), cached in img/.

    sheets.py <snapshot dir>      # → sheets/multi-NN.png, sheets/single-NN.png, sheets/index.json
"""
import json, os, sys, urllib.request
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
SNAP = sys.argv[1]
IMG, OUT = os.path.join(HERE, "img"), os.path.join(HERE, "sheets")
os.makedirs(IMG, exist_ok=True); os.makedirs(OUT, exist_ok=True)
idx = {int(k): v for k, v in json.load(open(os.path.join(HERE, "media-index.json"))).items()}
FONT = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 15)
T = 230


def thumb(mid):
    f = os.path.join(IMG, f"{mid}.jpg")
    if not os.path.exists(f):
        url = (idx.get(mid) or {}).get("originalUrl")
        try:
            im = Image.open(BytesIO(urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "curl/8.7.1"}), timeout=30).read())).convert("RGB")
            im.thumbnail((600, 600)); im.save(f, quality=85)
        except Exception:
            Image.new("RGB", (T, T), "pink").save(f)
    im = Image.open(f); im.thumbnail((T, T))
    return im


P = [json.load(open(os.path.join(SNAP, f))) for f in os.listdir(SNAP) if f[0].isdigit()]
P = [p.get("data", p) for p in P if not p.get("is_discontinued")]
def packs(p):
    return [v for v in p["variants"] if v["sale_mode"] == "pack" and not v["sku"].endswith("-1KG")]
multi = sorted([p for p in P if len({(v["content"], v.get("pack_count") or 1) for v in packs(p) if v["content"]}) >= 2],
               key=lambda p: p["id"])
single = sorted([p for p in P if p not in multi and any(v["size_label"] for v in packs(p))], key=lambda p: p["id"])
index = {"multi": [], "single": []}

# multi: rows of (label | up to 8 thumbs), ~14 rows per sheet
rows = [(p, v) for p in multi for v in packs(p)]
for n in range(0, len(rows), 14):
    chunk = rows[n:n + 14]
    sheet = Image.new("RGB", (260 + 8 * (T + 6), len(chunk) * (T + 10)), "white")
    d = ImageDraw.Draw(sheet)
    for r, (p, v) in enumerate(chunk):
        y = r * (T + 10)
        d.text((6, y + 6), f"P{p['id']} V{v['id']}", fill="black", font=FONT)
        d.multiline_text((6, y + 28), f"{p['name'][:28]}\n{(v['size_label'] or '')}\n{v['name'][:28]}\n{v['sku']}", fill="black", font=FONT)
        for i, mid in enumerate(v["images"][:8]):
            sheet.paste(thumb(mid), (260 + i * (T + 6), y))
        d.line([(0, y + T + 5), (sheet.width, y + T + 5)], fill="grey")
        index["multi"].append({"sheet": n // 14, "product": p["id"], "variant": v["id"], "label": v["size_label"]})
    sheet.save(os.path.join(OUT, f"multi-{n // 14:02d}.png"))

# single: first image of each sized pack variant, 5 per row, 4 rows per sheet
cells = [(p, v) for p in single for v in packs(p) if v["size_label"] and v["images"]]
W = T + 40
for n in range(0, len(cells), 20):
    chunk = cells[n:n + 20]
    sheet = Image.new("RGB", (5 * W, 4 * (T + 70)), "white")
    d = ImageDraw.Draw(sheet)
    for i, (p, v) in enumerate(chunk):
        x, y = (i % 5) * W, (i // 5) * (T + 70)
        sheet.paste(thumb(v["images"][0]), (x + 5, y))
        d.multiline_text((x + 5, y + T + 4), f"P{p['id']} V{v['id']} {v['size_label']}\n{p['name'][:30]}", fill="black", font=FONT)
        index["single"].append({"sheet": n // 20, "product": p["id"], "variant": v["id"], "label": v["size_label"]})
    sheet.save(os.path.join(OUT, f"single-{n // 20:02d}.png"))
json.dump(index, open(os.path.join(OUT, "index.json"), "w"))
print(len(multi), "multi-size products,", len(rows), "rows;", len(cells), "single cells")
