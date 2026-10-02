#!/usr/bin/env python3
"""Write one validated card to the admin (phase C of /add-products).

    scripts/card-import.py --run runs/<date> <code>             # dry run: build + check the payload, print it
    scripts/card-import.py --run runs/<date> <code> --payload   # only write .siruk-cache/payload-<code>.json (phase B --check)
    scripts/card-import.py --run runs/<date> <code> --write     # upload the gallery, then create-product.sh / add-variant.sh
    scripts/card-import.py --run runs/<date> <code> --queue     # upload the gallery, then queue runs/<date>/bulk/<code>.json
                                                                # for scripts/bulk-create.py (new products only)

Price, cost, stock, sku and the pack size come from rows.jsonl (prepare-run.py decided
them); name, label, categories, attributes, images and texts from cards/<code>.json.
The product type is the phase-B agent's pick from runs/<date>/product-types-map.json
({code: type id}) when present, else types.json's for the card's type. The size is the
card's `size`, else the row's parsed `pack` (CLAUDE.md 8a). A register loose twin
(price.twin) goes on as a second variant. Every write goes through scripts/ (rule 10),
and every body through scripts/siruk_payload.py.
--queue folds runs/<date>/tr/<code>-ru.json and -hy.json (set-translation.py's shape, keyed
by sku) into the payload's "translations" block, so the bulk create ships en/ru/hy at once.
A card with existing_id cannot be queued — the bulk endpoint only creates; use --write.
Promoted from runs/2026-09-25/import/card-import.py and ported to the 2026-09-29 model.
"""
import json, os, re, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from siruk_payload import PayloadError, post_body  # noqa: E402

args = sys.argv[1:]
if "--run" not in args or len(args) < 3:
    sys.exit(__doc__)
RUN = os.path.abspath(args[args.index("--run") + 1])
code = [a for a in args if not a.startswith("--") and os.path.abspath(a) != RUN][0]
queue = "--queue" in args
write, only_payload = "--write" in args or queue, "--payload" in args

card = json.load(open(f"{RUN}/cards/{code}.json"))
if queue and card.get("existing_id"):
    sys.exit(f"{code}: existing product {card['existing_id']} — the bulk endpoint only creates; use --write")
row = next(json.loads(l) for l in open(f"{RUN}/rows.jsonl") if json.loads(l)["code"] == code)
assert card.get("status") == "ready", f"{code}: card is {card.get('status')}"
v = subprocess.run([sys.executable, f"{ROOT}/scripts/validate-card.py", "--run", RUN, code],
                   capture_output=True, text=True, cwd=ROOT)
assert v.returncode == 0, v.stdout + v.stderr

menu = json.load(open(f"{ROOT}/reference/attribute-values.json"))
types = json.load(open(f"{ROOT}/reference/types.json"))
ids = json.load(open(f"{ROOT}/.siruk-cache/live-ids.json"))
tmap_path = os.path.join(RUN, "product-types-map.json")
tmap = json.load(open(tmap_path)) if os.path.exists(tmap_path) else {}
type_id = int(tmap.get(code) or types[card["type"]]["family"])
brand = ids["brands"][str(card["brand_id"])]
bslug = re.sub(r"[^a-z0-9]+", "-", brand.lower()).strip("-")

attrs = {}
for a, pick in (card.get("attributes") or {}).items():
    if a == "product-weight":        # retired: the size is the variant's net content
        continue
    attrs[a] = [menu[a]["values"][pick["value"]]]          # KeyError = not in the closed menu

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
variant = {"sku": code, "name": card["label"], "price": price, "cost_price": row["cost"],
           "sale_mode": "pack", "initial_stock": 10, "attribute_values": attrs,   # every variant stocks 10 (user 2026-10-01)
           "about_this_item": html(texts.get("about_this_item")),
           "ingredient_information": html(texts.get("ingredient_information")),
           "feeding_instructions": html(texts.get("feeding_instructions")),
           "images": []}
size = card.get("size") or row.get("pack")
if size and "measure_type" not in size:          # a rows.jsonl written before 2026-09-30
    u, val = size["unit"], size["value"]
    size = {"measure_type": "mass" if u in ("g", "kg") else "volume",
            "content": round(val * 1000 if u in ("kg", "l") else val, 3), "pack_count": size.get("count") or 1}
if size:
    variant.update(measure_type=size["measure_type"], content=size["content"],
                   pack_count=size.get("pack_count") or 1)
twin = (row.get("price") or {}).get("twin")
twin_v = dict(twin, cost_price=twin.get("cost_price"),
              initial_stock=10,  # every variant stocks 10 (user 2026-10-01); the twin is a 1 kg pack
              attribute_values=attrs, images=[]) if twin else None

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
    if twin_v:
        twin_v["images"] = media
else:
    variant["images"] = [0]          # placeholder so the dry run passes the image check; never written

env = dict(os.environ, ALLOW_NO_SIZE="1") if not size else dict(os.environ)
if card.get("existing_id"):
    paths = []
    for i, vv in enumerate([variant] + ([twin_v] if twin_v else [])):
        p = f"{ROOT}/.siruk-cache/variant-{code}{'-twin' if i else ''}.json"
        json.dump(vv, open(p, "w"), ensure_ascii=False, indent=1)
        paths.append(p)
    cmds = [[f"{ROOT}/scripts/add-variant.sh", str(card["existing_id"]), p] for p in paths]
    print("\n".join(open(p).read() for p in paths) if not write else f"variant files: {paths}")
else:
    slug = bslug + "-" + re.sub(r"[^a-z0-9]+", "-", card["name"].lower()).strip("-")
    payload = {"name": card["name"], "slug": slug, "category_ids": card["category_ids"],
               "brand_id": card["brand_id"], "attribute_family_id": type_id,
               "is_best_seller": False, "is_on_sale": False,
               "variants": [dict(variant, is_default=True)] + ([twin_v] if twin_v else [])}
    path = f"{ROOT}/.siruk-cache/payload-{code}.json"
    json.dump(payload, open(path, "w"), ensure_ascii=False, indent=1)
    if not size:
        os.environ["ALLOW_NO_SIZE"] = "1"
    try:
        post_body(payload)           # the product-type check, before anything is uploaded or written
    except PayloadError as e:
        sys.exit(f"{code}: {e}")
    cmds = [[f"{ROOT}/scripts/create-product.sh", path]]
    print(path if only_payload or write else json.dumps(payload, ensure_ascii=False, indent=1))

if queue:
    for lang in ("ru", "hy"):
        tp = os.path.join(RUN, "tr", f"{code}-{lang}.json")
        if os.path.exists(tp):
            payload.setdefault("translations", {})[lang] = json.load(open(tp))
    if not size:
        payload["_allow_no_size"] = True     # bulk-create.py applies ALLOW_NO_SIZE to this item only
    os.makedirs(os.path.join(RUN, "bulk"), exist_ok=True)
    qp = os.path.join(RUN, "bulk", f"{code}.json")
    json.dump(payload, open(qp, "w"), ensure_ascii=False, indent=1)
    print(f"queued {qp}" + ("" if payload.get("translations") else "  (no ru/hy yet: runs/<date>/tr/<code>-ru.json, -hy.json)"))
elif write:
    for cmd in cmds:
        r = subprocess.run(cmd, text=True, cwd=ROOT, capture_output=True, env=env)
        print(r.stdout); print(r.stderr, file=sys.stderr)
        if r.returncode:
            sys.exit(r.returncode)
