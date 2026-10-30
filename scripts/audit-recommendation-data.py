#!/usr/bin/env python3
"""Read-only audit of the data the storefront's recommendations are computed from.

    scripts/audit-recommendation-data.py --run runs/<date>          # from the dump, no API writes
    scripts/audit-recommendation-data.py --run runs/<date> --recs   # + read every product's live
                                                                   #   "Related items" (public API, paced)
    … --ids 1200 1201                                              # findings for these products only

Since siruk-web fff688a3 / cd4dce3c (2026-10-09) nothing links products by hand — PDP "Related
items", the cart's "goes well with" / free-delivery / suggestion rails and the listing order are
all computed from category leaves, product type, brand, price, net content and stock
(CLAUDE.local.md has the algorithms). This finds the products whose data puts them in the wrong
rails, or in none:

  no-type, no-category, parent-category, accessories-13, no-brand, unknown-category
  invisible        no purchasable variant with a price → never in any rail or related list
  no-size          sized product type, pack variant without measure_type/content → related items
                   compare it by shelf price instead of per kg / per l
  universal+specific  "All Breeds"/"All Lifestages" next to a specific value on one variant
                   (is_universal: the universal value already matches every filter value)
  kg-sku           a 1 kg variant whose SKU is not "<bag sku>-KG" (the code backfill keys on it)
  lifestage-species  Puppy on a cat product / Kitten on a dog product (561 "Junior Clouds", fixed 2026-10-12)
  multi-species    in more than one pet tree (info — check it is meant; it widens both rails)
  --recs: related-other-species (a related product shares none of this product's pet trees),
          related-few (<4), related-siblings (all related share brand + first name word)

Inputs: .siruk-cache/live/products/ (scripts/dump-products.py), the live category tree and
reference/product-types.json. Writes <run>/recommendation-audit.csv and recommendation-audit.md.
"""
import csv, json, os, subprocess, sys, time, urllib.request
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIVE = os.path.join(ROOT, ".siruk-cache", "live")
PUBLIC = os.environ.get("SIRUK_PUBLIC_API", "https://api.siruk.am/api")
UNIVERSAL = {"breed-size": "All Breeds", "lifestage": "All Lifestages"}   # value labels (is_universal)


def admin_get(path):
    r = subprocess.run(["bash", os.path.join(ROOT, "scripts/api.sh"), "GET", path],
                       capture_output=True, text=True, cwd=ROOT, timeout=180)
    return json.loads(r.stdout[r.stdout.find("{"):])


def category_tree():
    path = os.path.join(LIVE, "categories.json")
    data = admin_get("/categories")["data"]
    json.dump(data, open(path, "w"), ensure_ascii=False)
    cats = {}

    def walk(n, root, trail):
        cats[n["id"]] = {"name": n["name"], "root": root, "path": " > ".join(trail + [n["name"]]),
                         "leaf": not n.get("children"), "complements": n.get("complement_category_ids") or []}
        for c in n.get("children") or []:
            walk(c, root, trail + [n["name"]])
    for n in data:
        walk(n, n["name"], [])
    return cats


def attribute_codes():
    """code → {id, values: label → value id} from reference/attribute-values.json."""
    menu = json.load(open(os.path.join(ROOT, "reference", "attribute-values.json")))
    return {code: {"id": a["attribute_id"], "values": dict(a.get("values") or {})}
            for code, a in menu.items() if isinstance(a, dict) and "attribute_id" in a}


def public_related(pid):
    req = urllib.request.Request(f"{PUBLIC}/products/{pid}/recommendations",
                                 headers={"Accept": "application/json", "User-Agent": "curl/8"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r).get("relatedProducts") or []


def main(argv):
    if "--run" not in argv:
        sys.exit(__doc__)
    run = os.path.join(ROOT, argv[argv.index("--run") + 1])
    os.makedirs(run, exist_ok=True)
    ids = json.load(open(os.path.join(LIVE, "products", "index.json")))
    only = {int(a) for a in argv[argv.index("--ids") + 1:] if a.isdigit()} if "--ids" in argv else None
    ids = sorted(set(ids) | (only or set()))
    products = {i: json.load(open(os.path.join(LIVE, "products", f"{i}.json")))
                for i in ids if os.path.exists(os.path.join(LIVE, "products", f"{i}.json"))}
    if len(products) < len(ids):
        print(f"⚠ {len(ids) - len(products)} products not dumped yet — audit is partial", file=sys.stderr)
    cats = category_tree()
    types = {t["id"]: t for t in json.load(open(os.path.join(ROOT, "reference", "product-types.json")))}
    attrs = attribute_codes()
    uni_ids = {}
    for code, val in UNIVERSAL.items():
        a = attrs.get(code)
        if a and val in a["values"]:
            uni_ids[str(a["id"])] = a["values"][val]

    findings = []

    def flag(p, kind, detail="", variant=None):
        findings.append({"product_id": p["id"], "product": p["name"], "variant_id": (variant or {}).get("id", ""),
                         "sku": (variant or {}).get("sku", ""), "kind": kind, "detail": detail,
                         "categories": " | ".join(cats.get(c, {}).get("path", str(c)) for c in p.get("category_ids") or [])})

    roots_of = {}
    for p in products.values():
        roots_of[p["id"]] = {cats[c]["root"] for c in p.get("category_ids") or [] if c in cats}
    targets = [p for p in products.values() if only is None or p["id"] in only]
    for p in targets:
        cids = p.get("category_ids") or []
        if not (p.get("attribute_family_id") or 0):
            flag(p, "no-type")
        if not cids:
            flag(p, "no-category")
        for c in cids:
            if c not in cats:
                flag(p, "unknown-category", str(c))
            elif c == 13:
                flag(p, "accessories-13")
            elif not cats[c]["leaf"]:
                flag(p, "parent-category", cats[c]["path"])
        if not p.get("brand_id"):
            flag(p, "no-brand")
        if len(roots_of[p["id"]]) > 1:
            flag(p, "multi-species", ", ".join(sorted(roots_of[p["id"]])))
        if p.get("is_discontinued"):
            flag(p, "discontinued")
        if not any(v.get("is_purchasable") and (v.get("price") or 0) > 0 for v in p["variants"]):
            flag(p, "invisible", "no purchasable priced variant")
        ptype = types.get(p.get("attribute_family_id")) or {}
        skus = {v["sku"] for v in p["variants"]}
        for v in p["variants"]:
            if v.get("sale_mode") == "pack" and ptype.get("measureType") and v.get("content") is None:
                flag(p, "no-size", f"type {ptype.get('name')} is {ptype['measureType']}", v)
            for aid, uval in uni_ids.items():
                vals = (v.get("attribute_values") or {}).get(aid) or []
                if uval in vals and len(vals) > 1:
                    flag(p, "universal+specific", f"attribute {aid}: {vals}", v)
            stages = {l["label"] for l in v.get("attribute_value_labels") or [] if l.get("attributeName") == "Lifestage"}
            if ("Puppy" in stages and "Cat" in roots_of[p["id"]]) or ("Kitten" in stages and "Dog" in roots_of[p["id"]]):
                flag(p, "lifestage-species", f"{', '.join(sorted(stages))} on a {'/'.join(sorted(roots_of[p['id']]))} product "
                     "(it shows in the other species' filter)", v)
            label = (v.get("size_label") or v.get("name") or "").strip().lower()
            if label == "1 kg" and len(p["variants"]) > 1 and not str(v["sku"]).upper().endswith("-KG"):
                flag(p, "kg-sku", f"1 kg variant sku {v['sku']}", v)
            if str(v["sku"]).upper().endswith("-KG") and v["sku"][:-3] not in skus:
                flag(p, "kg-sku", f"{v['sku']} has no bag variant {v['sku'][:-3]}", v)

    if "--recs" in argv:
        for n, p in enumerate(targets, 1):
            try:
                rel = public_related(p["id"])
            except Exception as e:
                flag(p, "related-error", str(e)[:120])
                continue
            mine = roots_of[p["id"]]
            if len(rel) < 4:
                flag(p, "related-few", f"{len(rel)} related")
            for r in rel:
                theirs = roots_of.get(r["id"], set())
                if mine and theirs and not (mine & theirs):
                    flag(p, "related-other-species", f"{r['id']} {r.get('displayName') or r.get('name')}")
            if len(rel) >= 3:
                brands = {(r.get("brand") or {}).get("name") if isinstance(r.get("brand"), dict) else r.get("brand") for r in rel}
                words = {(r.get("name") or "").split(" ")[0].lower() for r in rel}
                if len(brands) == 1 and len(words) == 1:
                    flag(p, "related-siblings", "; ".join(r.get("name") or "" for r in rel))
            time.sleep(0.4)
            if n % 100 == 0:
                print(f"  related {n}/{len(products)}", file=sys.stderr)

    cols = ["kind", "product_id", "product", "variant_id", "sku", "detail", "categories"]
    with open(os.path.join(run, "recommendation-audit.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, cols)
        w.writeheader()
        w.writerows(sorted(findings, key=lambda r: (r["kind"], r["product_id"])))
    by_kind = defaultdict(set)
    for r in findings:
        by_kind[r["kind"]].add(r["product_id"])
    rows = Counter(r["kind"] for r in findings)
    rep = ["# Recommendation data audit", "", f"{len(targets)} products checked.", "",
           "| finding | products | rows |", "|---|---|---|"] + \
          [f"| {k} | {len(by_kind[k])} | {rows[k]} |" for k in sorted(by_kind)] + \
          ["", "Detail: `recommendation-audit.csv`.",
           f"Categories with a complement list: {sum(1 for c in cats.values() if c['complements'])}"]
    open(os.path.join(run, "recommendation-audit.md"), "w").write("\n".join(rep) + "\n")
    print("\n".join(rep))


if __name__ == "__main__":
    main(sys.argv[1:])
