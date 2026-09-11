#!/usr/bin/env python3
"""Plan the toy import: CSV row + hafo price + trixie.de page -> create payload.

Every attribute pick has to be evidenced (CLAUDE.md's closed-menu rule), so:
  * toy-type  comes from Trixie's OWN breadcrumb (…/toys/plush-toys/…), which is
    their classification of the product, not our inference;
  * material  comes from the material bullet the page publishes;
  * toy-feature comes from the feature bullets;
  * lifestage is set only when the breadcrumb or name says "puppy"/"kitten".
Anything without evidence is left unset and reported.

Usage:  plan-toys.py [--out .siruk-cache/toy-plan.json]
"""
import argparse, csv, json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, ".siruk-cache")

BRAND_TRIXIE = 8
CAT_DOG_TOYS, CAT_CAT_TOYS = 15, 16
FAMILY_TOYS = 5

# A product belongs in a LEAF category, the way a kibble sits in "Dry Food"
# rather than in "Food" (user rule 2026-09-09: every category we add gets real
# subcategories; flat buckets with the detail hidden in attributes are wrong).
# toy-type value id -> leaf category id, per species.
LEAF_CATEGORY = {
    "dog": {192: 17, 193: 18, 194: 19, 196: 20, 197: 21, 198: 22},
    "cat": {200: 23, 195: 24, 199: 25, 198: 26},
}

TOY_TYPE = {                      # breadcrumb segment -> value id
    "plush-toys": 192, "latex-rubber-toys": 193, "tugging-rope-toys": 194,
    "throwing-retrieving-toys": 196, "chewing-toys-dental-care": 197,
    "intelligence-activity-toys": 198, "catnip-attractants": 199,
    "play-mice-animals-balls": 200,          # refined to Ball by name below
}
BALL = 195
MATERIAL = [                      # ordered: first match wins (longest first)
    ("thermoplastic rubber (tpr)", 205), ("plastic/tpr", 205), ("tpr", 205),
    ("plush/rope", 201), ("plush with rope", 201), ("plush/fabric", 201),
    ("plush (polyester)", 201), ("plush", 201),
    ("fabric (polyester)", 202),
    ("cotton/polyester", 207), ("cotton", 206),
    ("natural rubber", 204), ("latex", 203),
    ("paper cord", 211), ("vinyl", 209), ("wood", 210), ("foam", 212),
    ("plastic", 208), ("polyester", 202),
]
FEATURE = [                       # substring in any bullet -> value id
    ("squeak", 213), ("with bell", 214), ("catnip", 215), ("mint", 216),
    ("massages the gums", 217), ("float", 218),
    ("light up", 219), ("glow", 219),
    ("inner rope", 220), ("with rope", 220),
    ("shock absorber", 221),
]


SIZE_RE = re.compile(r"(\d+[.,]?\d*)\s*(?:սմ|см|cm)")
SIZE_VALUE_ID = {}          # "22 cm" -> value id, filled from the live menu

# Trixie's <h1> appends the material ("Flashing Ball, TPR"). Material is its own
# attribute here, so the suffix is stripped from the product name (user decision
# 2026-09-09) -- otherwise every title repeats an attribute.
MATERIAL_SUFFIX = re.compile(
    r",\s*(plush|fabric|latex|natural rubber|rubber|thermoplastic rubber|tpr|"
    r"cotton(?:/polyester)?|polyester|plastic(?:/tpr)?|vinyl|wood|paper cord|foam|"
    r"felt(?:/wood)?)\s*(?:\([^)]*\))?\s*$", re.I)


def clean_name(name):
    prev = None
    while prev != name:
        prev = name
        name = MATERIAL_SUFFIX.sub("", name).strip()
    return name


def size_of(invoice_name):
    """Pack/toy size in cm, from OUR invoice line (the brand page rarely states
    it). '5.5/ 30սմ' -> '30': the regex anchors on the unit, so the trailing
    number (the length) wins over a leading diameter."""
    m = SIZE_RE.findall(invoice_name or "")
    return m[-1].replace(",", ".") if m else None


def norm(s):
    return re.sub(r"\s+", " ", (s or "").strip().lower())


def breadcrumb(url):
    try:
        return url.split("/en/productworld/")[1].split("?")[0].split("/")
    except IndexError:
        return []


def pick_type(url, name):
    seg = breadcrumb(url)
    key = seg[2] if len(seg) >= 3 else ""
    vid = TOY_TYPE.get(key)
    if vid == 200 and re.search(r"\bball", name, re.I):
        return BALL, f"breadcrumb '{key}' + name says ball"
    return (vid, f"breadcrumb '{key}'") if vid else (None, "")


def pick_material(bullets):
    for b in bullets:
        nb = norm(b)
        for token, vid in MATERIAL:
            if nb.startswith(token) or nb == token:
                return vid, b
    return None, ""


def pick_features(bullets):
    out, ev = [], []
    for b in bullets:
        nb = norm(b)
        for token, vid in FEATURE:
            if token in nb and vid not in out:
                out.append(vid); ev.append(b)
    return out, ev


def pick_lifestage(url, name, arm_name):
    blob = f"{url} {name} {arm_name}".lower()
    if "puppy" in blob:
        return 25, "puppy in breadcrumb/name"
    if "kitten" in blob:
        return 26, "kitten in breadcrumb/name"
    return None, ""


def species_of(url):
    seg = breadcrumb(url)
    return "cat" if seg and seg[0] == "cat" else "dog"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(CACHE, "toy-plan.json"))
    a = ap.parse_args()

    idx = json.load(open(os.path.join(CACHE, "trixie-catalogue.json")))
    pages = json.load(open(os.path.join(CACHE, "trixie-toy-pages.json")))
    hafo = {d["csv"]["Article Code"]: d
            for d in json.load(open(os.path.join(CACHE, "hafo-trixie-fixed.json")))}

    by_article = {}                       # article -> page record (incl. siblings)
    for rec in pages.values():
        for art in rec["variants"]:
            by_article.setdefault(art, rec)

    rows = [r for r in csv.DictReader(open(os.path.join(ROOT, "csv/products.csv"),
                                           newline="", encoding="utf-8"))
            if r["Category"].strip().lower() == "toys"
            and r["Brand"].strip().lower() == "trixie"]

    menu = json.load(open(os.path.join(ROOT, "reference/attribute-values.json")))
    SIZE_VALUE_ID.update(menu.get("toy-size", {}).get("values", {}))

    # Group by PRODUCT PAGE, not by article: sibling articles on one Trixie page
    # are size variants of a single product. Grouping by article instead would
    # emit near-duplicate products with colliding slugs.
    groups, skipped = {}, []
    for r in rows:
        code = r["Article Code"].strip()
        h = hafo.get(code)
        if not (h and h.get("confirmed") and h.get("price_amd")):
            skipped.append({**r, "reason": "no confirmed hafo price"}); continue
        art = re.sub(r"[^0-9]", "", code)
        page = by_article.get(art) or by_article.get(art.lstrip("0"))
        if not page:
            hit = idx.get(art) or idx.get(art.lstrip("0"))
            skipped.append({**r, "reason": "not in trixie.de current range"
                            if not hit else "page not fetched"})
            continue
        groups.setdefault(page["url"], {"page": page, "rows": []})["rows"].append((r, h, art))

    planned = []
    for url, g in groups.items():
        page, members = g["page"], g["rows"]
        raw_name = page["name"]
        name = clean_name(raw_name)
        tv, tev = pick_type(url, raw_name)
        mv, mev = pick_material(page["bullets"])
        fv, fev = pick_features(page["bullets"])
        sp = species_of(url)

        variants = []
        for i, (r, h, art) in enumerate(sorted(members, key=lambda x: x[2])):
            inv = r["Product Name (as printed)"]
            sz = size_of(inv)
            attrs = {}
            if tv: attrs["toy-type"] = tv
            if mv: attrs["material"] = mv
            if fv: attrs["toy-feature"] = fv[0]        # single-valued for now
            lv, lev = pick_lifestage(url, raw_name, inv)
            if lv: attrs["lifestage"] = lv
            if sz and f"{sz} cm" in SIZE_VALUE_ID:
                attrs["toy-size"] = SIZE_VALUE_ID[f"{sz} cm"]
            variants.append({
                "sku": art, "code": r["Article Code"].strip(),
                "label": f"{sz} cm" if sz else name,
                "price": h["price_amd"],
                "cost_price": int(re.sub(r"[^0-9]", "", r["Buy Price (AMD)"] or "0") or 0),
                "stock": int(re.sub(r"[^0-9]", "", r["Qty Received"] or "0") or 0) or 1,
                "is_default": i == 0, "sort_order": i,
                "size": sz, "invoice_name": inv,
                "attribute_value_ids": attrs,
            })

        planned.append({
            "url": url, "species": sp, "name": name, "raw_name": raw_name,
            "slug": "trixie-" + re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-"),
            # leaf category from the toy type; the parent is only the fallback
            # for the one product whose breadcrumb gave no type
            "category_id": LEAF_CATEGORY[sp].get(
                tv, CAT_CAT_TOYS if sp == "cat" else CAT_DOG_TOYS),
            "attribute_family_id": FAMILY_TOYS,
            "bullets": page["bullets"], "description": page["description"],
            "variants": variants,
            "evidence": {"toy-type": tev, "material": mev, "toy-feature": fev[:1]},
            "extra_features": fv[1:],
        })

    # Distinct Trixie pages can share a title ("Playing Rope, cotton/polyester"),
    # and slugs are global -- disambiguate with the default variant's article.
    seen = {}
    for p in sorted(planned, key=lambda x: x["variants"][0]["sku"]):
        seen.setdefault(p["slug"], []).append(p)
    for slug, ps in seen.items():
        if len(ps) > 1:
            for p in ps:
                p["slug"] = f"{slug}-{p['variants'][0]['sku']}"

    json.dump({"planned": planned, "skipped": skipped},
              open(a.out, "w"), ensure_ascii=False, indent=1)
    nvar = sum(len(p["variants"]) for p in planned)
    print(f"planned {len(planned)} products / {nvar} variants   "
          f"skipped {len(skipped)} rows   -> {a.out}", file=sys.stderr)
    print(f"  multi-variant products: {sum(1 for p in planned if len(p['variants'])>1)}",
          file=sys.stderr)
    print(f"  without material: {sum(1 for p in planned if not p['variants'][0]['attribute_value_ids'].get('material'))}",
          file=sys.stderr)
    print(f"  without toy-type: {sum(1 for p in planned if not p['variants'][0]['attribute_value_ids'].get('toy-type'))}",
          file=sys.stderr)
    dup = [s for s, ps in
           __import__("collections").Counter(p["slug"] for p in planned).items() if ps > 1]
    print(f"  duplicate slugs remaining: {len(dup)}", file=sys.stderr)
    bad = [p["name"] for p in planned if len(p["variants"]) > 1 and
           len({json.dumps(v["attribute_value_ids"], sort_keys=True) for v in p["variants"]}) != len(p["variants"])]
    print(f"  multi-variant products with NON-unique attribute combos: {len(bad)} {bad[:5]}",
          file=sys.stderr)


if __name__ == "__main__":
    main()
