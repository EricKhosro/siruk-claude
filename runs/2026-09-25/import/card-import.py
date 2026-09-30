#!/usr/bin/env python3
"""Write one validated card to the admin (run-local helper, 2026-09-25).

    card-import.py <code>            # dry run: uploads nothing, prints the payload it would send
    card-import.py <code> --write    # upload the gallery, then create-product.sh / add-variant.sh

Price, cost, stock and sku come from rows.jsonl (prepare-run.py decided them);
name, label, categories, attributes, images and texts from cards/<code>.json.
Every write goes through scripts/ (rule 10).
"""
import json, os, re, subprocess, sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
RUN = os.path.dirname(os.path.abspath(__file__))
code, write = sys.argv[1], "--write" in sys.argv

card = json.load(open(f"{RUN}/cards/{code}.json"))
row = next(json.loads(l) for l in open(f"{RUN}/rows.jsonl") if json.loads(l)["code"] == code)
assert card.get("status") == "ready", f"{code}: card is {card.get('status')}"
v = subprocess.run([sys.executable, f"{ROOT}/scripts/validate-card.py", "--run", RUN, code],
                   capture_output=True, text=True, cwd=ROOT)
assert v.returncode == 0, v.stdout + v.stderr

menu = json.load(open(f"{ROOT}/reference/attribute-values.json"))
types = json.load(open(f"{ROOT}/reference/types.json"))
ids = json.load(open(f"{ROOT}/.siruk-cache/live-ids.json"))
t = types[card["type"]]
brand = ids["brands"][str(card["brand_id"])]
bslug = re.sub(r"[^a-z0-9]+", "-", brand.lower()).strip("-")

attrs = {}
for a, pick in (card.get("attributes") or {}).items():
    attrs[a] = menu[a]["values"][pick["value"]]          # KeyError = not in the closed menu

texts = card.get("texts") or json.load(open(os.path.join(RUN, card["texts_file"])))
def html(s):
    if not s:
        return ""
    if s.lstrip().startswith("<"):
        return s
    out, items = [], []
    def flush():
        if items:
            out.append("<ul>" + "".join(f"<li>{i}</li>" for i in items) + "</ul>"); items.clear()
    for line in (l.strip() for l in s.split("\n")):
        if re.match(r"^[-•*]\s+", line):
            items.append(re.sub(r"^[-•*]\s+", "", line))
        else:
            flush()
            if line:
                out.append(f"<p>{line}</p>")
    flush()
    return "".join(out)

price = row["price"]["amount"]
assert price and price > row["cost"], f"{code}: price {price} vs cost {row['cost']}"
variant = {"sku": code, "name": card["label"], "pricing_type": "fixed", "price": price,
           "cost_price": row["cost"], "stock": row["stock"], "attribute_value_ids": attrs,
           "about_this_item": html(texts.get("about_this_item")),
           "ingredient_information": html(texts.get("ingredient_information")),
           "feeding_instructions": html(texts.get("feeding_instructions")),
           "images": [], "vendor_stock": False,
           # backend change seen 2026-09-25: pricing_type comes back null and the API
           # requires sale_mode; live fixed-price variants carry "pack" plus unit /
           # net_quantity when the pack prints a weight or volume (none for tablets, leads)
           "sale_mode": "pack"}
net = card.get("net_quantity") or (row.get("pack") or {})
if net.get("unit") in ("g", "ml") and net.get("value"):
    variant["unit"], variant["net_quantity"] = net["unit"], net["value"] * (net.get("count") or 1)

if write:
    media = []
    for url in card["images"]:
        r = subprocess.run([f"{ROOT}/scripts/upload-media.sh", url, f"products/{bslug}/{card['type']}"],
                           capture_output=True, text=True, cwd=ROOT)
        mid = r.stdout.strip().splitlines()[-1] if r.returncode == 0 and r.stdout.strip() else ""
        if not mid.isdigit():
            print(f"  image FAILED, skipped: {url}\n{r.stderr[-400:]}", file=sys.stderr)
            continue
        media.append(int(mid))
    assert media, f"{code}: no image uploaded"
    variant["images"] = media

if card.get("existing_id"):
    path = f"{ROOT}/.siruk-cache/variant-{code}.json"
    json.dump(variant, open(path, "w"), ensure_ascii=False, indent=1)
    cmd = [f"{ROOT}/scripts/add-variant.sh", str(card["existing_id"]), path]
else:
    slug = bslug + "-" + re.sub(r"[^a-z0-9]+", "-", card["name"].lower()).strip("-")
    payload = {"name": card["name"], "slug": slug, "category_ids": card["category_ids"],
               "brand_id": card["brand_id"], "attribute_family_id": t["family"],
               "is_best_seller": False, "is_on_sale": False,
               "variants": [dict(variant, is_default=True, sort_order=0)]}
    path = f"{ROOT}/.siruk-cache/payload-{code}.json"
    json.dump(payload, open(path, "w"), ensure_ascii=False, indent=1)
    cmd = [f"{ROOT}/scripts/create-product.sh", path]

print(open(path).read() if not write else f"payload: {path}")
if write:
    r = subprocess.run(cmd, text=True, cwd=ROOT, capture_output=True)
    print(r.stdout); print(r.stderr, file=sys.stderr)
    sys.exit(r.returncode)
