#!/usr/bin/env python3
"""Turn the duplicate groups into a merge plan: one product per group.

Reads .siruk-cache/dedup/groups.json (scripts/find-duplicate-products.py) and
writes runs/<date>/merge-plan.json plus a readable merge-plan.md.

For each group it decides
  * the surviving product (most variants, then lowest id — the oldest link),
  * the product name (the shared base name; a descriptor from the brand's own
    page where two groups would otherwise be named the same) and its slug,
  * the union of the group's categories and its brand/family,
  * the variant list, keeping every variant's own sku, prices, stock, images
    and texts, and
  * the VARIANT AXIS each variant needs.  The storefront builds its variant
    selector from attributes, not from the label (a 2-variant product whose
    variants share one attribute set renders only its default and hides the
    other), so every merged product must carry an axis whose value differs
    per variant.

It never writes to the API — scripts/merge-products.py does that.
"""
import argparse, collections, datetime, json, os, pathlib, re, sys

ROOT = pathlib.Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CACHE = ROOT / ".siruk-cache" / "dedup"

# ----------------------------------------------------------------- vocabulary
# Trixie colour words → our Color Family value.  Compound "x/y" names take the
# first colour, which is the one the pack leads with.
COLOUR = {
    "black": "Black", "royal blue": "Blue", "blue": "Blue", "dark blue": "Dark Blue",
    "neon blue": "Blue", "indigo": "Blue", "red": "Red", "fuchsia": "Pink",
    "pink": "Pink", "neon pink": "Pink", "blush": "Pink", "orchid": "Purple",
    "light lilac": "Purple", "purple": "Purple", "olive green": "Green",
    "green": "Green", "sage": "Green", "grey": "Grey", "dark grey": "Grey",
    "graphite": "Grey", "silver grey": "Silver", "silver": "Silver",
    "chrome": "Silver", "gold": "Gold", "white": "White", "cream": "Ivory",
    "dark brown": "Brown", "brown": "Brown", "orange": "Orange",
    "petrol": "Teal", "sand": "Beige", "beige": "Beige", "curry": "Yellow",
    "yellow": "Yellow", "sorted": "Color Varies", "various": "Color Varies",
}
COLOUR_RE = re.compile(
    r",\s*((?:" + "|".join(sorted((re.escape(c) for c in COLOUR), key=len, reverse=True)) +
    r")(?:\s*/\s*[a-z ]+)?)\s*$", re.I)

WEIGHT_RE = re.compile(r"^\d+(?:[.,]\d+)?\s*(?:g|kg|ml|l)$", re.I)
PETKG_RE = re.compile(r"^\d+(?:[.,]\d+)?\s*[–-]\s*\d+(?:[.,]\d+)?\s*kg$", re.I)
TOYDIM_RE = re.compile(r"^\d+(?:[–-]\d+)?\s*cm$", re.I)
# A label that opens with one or more letter sizes: "XS–S, 22–35 cm/10 mm",
# "M: 40 cm", "XS, S, S–M, 10 pcs.".  The letter run is the size; the rest is
# the measurement, which stays in the variant label and out of the filter menu.
LETTER = r"(?:XXS|XS|S|M|L|XL|XXL)"
LETTER_RUN_RE = re.compile(
    rf"^({LETTER}(?:\s*[–-]\s*{LETTER})?(?:,\s*{LETTER}(?:\s*[–-]\s*{LETTER})?)*)"
    r"\s*(?:[,:]|$)")


def letter_size(s):
    """'XS–S, 22–35 cm/10 mm' -> 'XS–S'; None when the label has no letter size."""
    m = LETTER_RUN_RE.match((s or "").strip())
    return m.group(1).strip() if m else None

TOY_CATS = set(range(17, 27))
PHARMA_CATS = {42, 43, 46, 47, 51, 52, 55}
FOOD_CATS = {3, 4, 5, 10, 11} | {6, 7, 14} | set(range(82, 95))

# Hand decisions, each with the evidence that backs it.  Keyed by the group's
# lowest product id.
OVERRIDES = {
    815: {"name": "Stainless Steel Bowl, heavy weight",
          "why": "trixie.de page 1001441312 bullet 'heavy weight version' — three "
                 "different bowl lines would otherwise share one name"},
    826: {"name": "Stainless Steel Bowl, non-slip",
          "why": "trixie.de page 1001441303 bullet 'non-slip due to rubber base'"},
    845: {"name": "Stainless Steel Bowl, varnished",
          "why": "trixie.de page 1001441291 bullet 'varnished'"},
    450: {"name": "Soft Brush, bamboo",
          "why": "trixie.de page 1001467013 bullet 'bamboo'"},
    491: {"name": "Soft Brush, rubber handle",
          "why": "trixie.de page 1001466607 bullet 'plastic handle with rubber grip/metal'"},
    470: {"name": "Soft Brush with Brush Cleaner, wooden handle",
          "why": "trixie.de page for 2353/2354, bullets 'with brush cleaner', "
                 "'with wooden handle/metal'"},
    420: {"name": "Longie, latex/polyester fleece",
          "why": "trixiecz pages for 35031/35061 name the line 'Longie, latex/"
                 "polyester fleece … sorted'; 'Animals, latex' was an import guess"},
    1020: {"name": "Chain Collar, chrome-plated",
           "why": "trixie.shop 'Kettenhalsband' carries 2154 (XL, 70 cm) and 2155 "
                  "(XXL, 78 cm) as two sizes of one product"},
    432: {"labels": {"40534": "M, with mesh"},
          "why": "trixie.de lists 4050 and 40534 both as size M; 40534 is the "
                 "mesh version (our own product name said so)"},
    610: {"axis": "flavor", "values": {"2549": "Tea Tree Oil", "2557": "Mint"},
          "why": "the two variants differ only in flavour"},
}

# Food rows the earlier imports left without a flavour, because the value did
# not exist in the closed menu yet.  The value is the pack's own wording.
FLAVOUR_FILL = {
    "041537": "Meat", "041567": "Meat",          # Gran Bonta Adult Dog, Meat
    "013647": "Veal", "013657": "Trout",         # Grill Sterilised Cat
    "014457": "Veal", "014497": "Trout",         # Fresh Adult Dog
    "143015": "Veal",                            # Club 4 Paws Premium Adult Cat
    # 013037 carries flavour "Chicken", which collides with 013067's plain
    # Chicken inside the merged product; the pack says chicken WITH vegetables.
    "013067": None,
    "013037": "Chicken and Vegetables",
}
TEXTURE_FILL = {"143015": "Chunks in Gravy"}
WEIGHT_RE_TAIL = re.compile(r"(\d+(?:[.,]\d+)?\s*(?:g|kg|ml|l))\s*$", re.I)


def base_name(p):
    n = p["name"]
    for v in p["variants"]:
        lbl = (v.get("name") or "").strip()
        if lbl and n.endswith(lbl) and len(n) > len(lbl):
            return n[: len(n) - len(lbl)].rstrip(" ,–-")
    return n


def split_colour(label):
    """('XS–S, 22–35 cm/10 mm', 'Black') — the size part and the Color Family."""
    m = COLOUR_RE.search(label or "")
    if not m:
        lab = (label or "").strip().lower()
        if lab in COLOUR:
            return "", COLOUR[lab]
        return label or "", None
    word = m.group(1).lower().split("/")[0].strip()
    return label[: m.start()].rstrip(" ,"), COLOUR.get(word)


def slugify(s):
    s = s.lower().replace("’", "").replace("'", "")
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return re.sub(r"-+", "-", s).strip("-")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=None)
    a = ap.parse_args()

    prod = {}
    for f in (CACHE / "detail").glob("*.json"):
        d = json.load(open(f))["data"]
        prod[d["id"]] = d
    tr = {}
    for lang in ("ru", "hy"):
        tr[lang] = {}
        for f in (CACHE / lang).glob("*.json"):
            d = json.load(open(f))["data"]
            tr[lang][d["id"]] = d
    brands = {r["id"]: r.get("brand") for r in json.load(open(CACHE / "list.json"))}
    groups = json.load(open(CACHE / "groups.json"))
    attrs = json.load(open(ROOT / "reference/attribute-values.json"))

    taken_slugs = {p["slug"] for p in prod.values()}
    names_used = collections.Counter()
    for g in groups:
        names_used[(prod[g[0]]["brand_id"], base_name(prod[g[0]]))] += 1

    plan, vocab = [], collections.defaultdict(set)
    for g in groups:
        gid = min(g)
        ov = OVERRIDES.get(gid, {})
        members = sorted(g, key=lambda i: (-len(prod[i]["variants"]), i))
        target = members[0]
        cats = sorted({c for i in g for c in prod[i]["category_ids"]})
        toy = bool(set(cats) & TOY_CATS)
        pharma = bool(set(cats) & PHARMA_CATS)
        food = bool(set(cats) & FOOD_CATS)

        name = ov.get("name") or collections.Counter(base_name(prod[i]) for i in g).most_common(1)[0][0]

        # --- variants, in a stable order ------------------------------------
        vs = []
        for i in sorted(g):
            for v in sorted(prod[i]["variants"], key=lambda v: v.get("sort_order") or 0):
                lbl = (ov.get("labels") or {}).get(v["sku"]) or (v.get("name") or "").strip()
                size, colour = split_colour(lbl)
                vs.append({"from_product": i, "old_variant_id": v["id"], "sku": v["sku"],
                           "label": lbl, "_size": size, "_colour": colour,
                           "existing": dict(v.get("attribute_value_ids") or {})})

        # --- pick the axis attributes ---------------------------------------
        sizes = [v["_size"] for v in vs]
        colours = [v["_colour"] for v in vs]
        axis_size = None
        if len(set(sizes)) > 1:
            if ov.get("axis") == "flavor":
                axis_size = "flavor"
                for v in vs: v["_size"] = ov["values"][v["sku"]]
            elif pharma and all(PETKG_RE.match(s) for s in sizes):
                axis_size = "pet-weight-range"
            elif toy and all(TOYDIM_RE.match(s) for s in sizes):
                axis_size = "toy-size"
            elif all(WEIGHT_RE.match(s) for s in sizes):
                axis_size = "product-weight"
            elif food and all(re.match(r"^.+\s\d+(?:[.,]\d+)?\s*(?:g|kg|ml|l)$", s) for s in sizes):
                axis_size = None            # flavour + weight already separate these
            else:
                axis_size = "size"
                # Prefer the bare letter size ("XS–S") over the whole
                # "XS–S, 22–35 cm/10 mm" string, as long as it still tells the
                # variants apart once colour is taken into account.
                short = [letter_size(s) or s for s in sizes]
                pairs_long = list(zip(sizes, colours))
                pairs_short = list(zip(short, colours))
                if len(set(pairs_short)) == len(set(pairs_long)):
                    for v, s2 in zip(vs, short): v["_size"] = s2
                    sizes = short
        axis_colour = "color-family" if len(set(c for c in colours if c)) > 1 else None

        # Food groups lean on flavour/weight/texture that the import already
        # wrote; fill the holes it left so no variant is told apart by a
        # MISSING value (that renders as a selector with one option).
        if not axis_size and not axis_colour:
            for v in vs:
                fl = FLAVOUR_FILL.get(v["sku"], "")
                if fl:
                    v["fill"] = {"flavor": fl}
                    vocab["flavor"].add(fl)
                tx = TEXTURE_FILL.get(v["sku"])
                if tx:
                    v.setdefault("fill", {})["texture"] = tx
                    vocab["texture"].add(tx)
                m = WEIGHT_RE_TAIL.search(v["label"])
                if m and "product-weight" not in v["existing"]:
                    w = m.group(1).replace(",", ".")
                    v.setdefault("fill", {})["product-weight"] = w
                    vocab["product-weight"].add(w)

        for v in vs:
            av = dict(v["existing"])
            if axis_size:
                av[axis_size] = v["_size"]
                vocab[axis_size].add(v["_size"])
            if axis_colour and v["_colour"]:
                av["color-family"] = v["_colour"]
                vocab["color-family"].add(v["_colour"])
            v["axes"] = dict(v.get("fill") or {})
            if axis_size: v["axes"][axis_size] = v["_size"]
            if axis_colour and v["_colour"]:
                v["axes"]["color-family"] = v["_colour"]

        brand = brands.get(target) or ""
        slug = slugify(f"{brand} {name}")
        if slug in taken_slugs and slug != prod[target]["slug"]:
            slug = slug + "-" + str(target)
        taken_slugs.add(slug)

        # --- translations: the shared prefix of the group's translated names --
        def common(lang):
            ns = [tr[lang][i]["name"] for i in g if i in tr[lang]]
            if not ns: return None
            pre = os.path.commonprefix(ns).rstrip()
            return pre.rstrip(" ,–-") or None

        plan.append({
            "group": sorted(g), "target": target, "absorb": sorted(set(g) - {target}),
            "name": name, "name_ru": common("ru"), "name_hy": common("hy"),
            "slug": slug, "old_slug": prod[target]["slug"],
            "brand_id": prod[target]["brand_id"], "brand": brand,
            "category_ids": cats,
            "attribute_family_id": next((prod[i]["attribute_family_id"] for i in sorted(g)
                                         if prod[i]["attribute_family_id"]), None),
            "axis": [x for x in (axis_size, axis_colour) if x],
            "why_name": ov.get("why"),
            "variants": vs,
        })

    # --- what the vocabulary still lacks ------------------------------------
    missing = {}
    for code, vals in sorted(vocab.items()):
        have = set(attrs.get(code, {}).get("values", {}))
        need = sorted(v for v in vals if v not in have)
        if need: missing[code] = need

    day = datetime.date.today().isoformat()
    out = pathlib.Path(a.out or (ROOT / "runs" / day))
    out.mkdir(parents=True, exist_ok=True)
    json.dump({"plan": plan, "missing_values": missing},
              open(out / "merge-plan.json", "w"), ensure_ascii=False, indent=1)

    dupes = sum(len(p["absorb"]) for p in plan)
    print(f"{len(plan)} merged products, {dupes} duplicates folded away", file=sys.stderr)
    for code, need in missing.items():
        print(f"  {code}: {len(need)} new values", file=sys.stderr)
    print(f"wrote {out/'merge-plan.json'}", file=sys.stderr)


if __name__ == "__main__":
    main()
