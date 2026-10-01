#!/usr/bin/env python3
"""Royal Canin price list (2026-09-30) -> product payloads for production.

Rows: runs/2026-09-30-rc/rows.json (file rows with a number in column E; price = column C
"Վաճառքի Գին" (sale), cost = column B, stock 10 each). Content: extracted.json (royalcanin.com).
Writes plan.json (+ plan.md) and payloads/<key>.json in the create-product.sh shape.
Nothing is written to any server here.
"""
import html, json, os, re

R = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(R))
rows = {r["row"]: r for r in json.load(open(f"{R}/rows.json"))}
ex = {x["row"]: x for x in json.load(open(f"{R}/extracted.json"))}
menu = json.load(open(f"{ROOT}/reference/attribute-values.json"))
BRAND = 7            # Royal Canin (same id on demo and production)
DRY, WET = 1, 2      # product types

# --- products: key -> (name, species, type, [(row, texture, flavor)])
P = {
 "maxi-adult-5": ("Maxi Adult 5+", "dog", DRY, [(24, None, None)]),
 "maxi-adult": ("Maxi Adult", "dog", DRY, [(25, None, None)]),
 "maxi-puppy": ("Maxi Puppy", "dog", DRY, [(26, None, None)]),
 "maxi-starter": ("Maxi Starter Mother & Babydog", "dog", DRY, [(27, None, None)]),
 "medium-adult": ("Medium Adult", "dog", DRY, [(28, None, None)]),
 "medium-puppy": ("Medium Puppy", "dog", DRY, [(29, None, None)]),
 "mini-adult": ("Mini Adult", "dog", DRY, [(30, None, None)]),
 "mini-puppy": ("Mini Puppy", "dog", DRY, [(31, None, None)]),
 "mini-adult-8": ("Mini Adult 8+", "dog", DRY, [(36, None, None)]),
 "maxi-joint-care": ("Maxi Joint Care", "dog", DRY, [(45, None, None)]),
 "mini-starter": ("Mini Starter Mother & Babydog", "dog", DRY, [(52, None, None)]),
 "medium-starter": ("Medium Starter Mother & Babydog", "dog", DRY, [(54, None, None)]),
 "fit-32": ("Fit 32", "cat", DRY, [(58, None, None)]),
 "kitten-dry": ("Kitten", "cat", DRY, [(60, None, None)]),
 "sterilised-37": ("Sterilised 37", "cat", DRY, [(61, None, None)]),
 "hairball-care": ("Hairball Care", "cat", DRY, [(65, None, None)]),
 "indoor-27": ("Indoor 27", "cat", DRY, [(66, None, None)]),
 "vet-hypoallergenic-cat": ("Hypoallergenic Cat", "cat", DRY, [(70, None, None)]),
 "vet-urinary-so-cat": ("Urinary S/O Cat", "cat", DRY, [(72, None, None)]),
 "vet-hypoallergenic-dog": ("Hypoallergenic Dog", "dog", DRY, [(141, None, None)]),
 "vet-gastrointestinal-dog": ("Gastrointestinal Dog", "dog", DRY, [(143, None, None)]),
 "vet-cardiac-dog": ("Cardiac Dog", "dog", DRY, [(144, None, None)]),
 "vet-urinary-so-dog": ("Urinary S/O Dog", "dog", DRY, [(145, None, None)]),
 "vet-renal-dog": ("Renal Dog", "dog", DRY, [(148, None, None)]),
 "vet-hepatic-dog": ("Hepatic Dog", "dog", DRY, [(149, None, None)]),
 "vet-mobility-dog": ("Mobility Support Dog", "dog", DRY, [(155, None, None)]),
 "vet-gi-puppy": ("Gastrointestinal Puppy", "dog", DRY, [(157, None, None)]),
 "vet-skin-care-dog": ("Skin Care Dog", "dog", DRY, [(158, None, None)]),
 # wet (cat) — texture / flavour variants of one recipe are one product (data-tables §2)
 "hair-skin-wet": ("Hair & Skin Care Thin Slices", "cat", WET, [(180, "Chunks in Gravy", None), (189, "Chunks in Jelly", None)]),
 "vet-sensitivity-control-cat-wet": ("Sensitivity Control Chicken with Rice", "cat", WET, [(181, None, "Chicken")]),
 "digestive-care-wet": ("Digestive Care Thin Slices in Gravy", "cat", WET, [(182, None, None)]),
 "instinctive-wet": ("Instinctive Thin Slices", "cat", WET, [(183, "Chunks in Gravy", None), (191, "Chunks in Jelly", None)]),
 "kitten-wet": ("Kitten Wet", "cat", WET, [(184, "Chunks in Gravy", None), (192, "Chunks in Jelly", None), (206, "Pate", None)]),
 "instinctive-7-wet": ("Instinctive 7+ Chunks in Gravy", "cat", WET, [(185, None, None)]),
 "light-weight-wet": ("Light Weight Care Thin Slices", "cat", WET, [(187, "Chunks in Gravy", None), (195, "Chunks in Jelly", None)]),
 "ageing-12-wet": ("Ageing 12+ Chunks in Jelly", "cat", WET, [(194, None, None)]),
 "sterilised-wet": ("Sterilised Wet", "cat", WET, [(196, "Chunks in Jelly", None), (208, "Pate", None)]),
 "vet-urinary-so-cat-wet": ("Urinary S/O Morsels in Gravy", "cat", WET, [(197, None, None)]),
 "vet-renal-cat-wet": ("Renal Thin Slices in Gravy", "cat", WET, [(200, None, "Chicken"), (213, None, "Fish")]),
 "urinary-care-wet": ("Urinary Care in Gravy", "cat", WET, [(201, None, None)]),
 "sensory-smell": ("Sensory Smell Chunks in Gravy", "cat", WET, [(221, None, None)]),
 "sensory-taste": ("Sensory Taste Chunks in Gravy", "cat", WET, [(222, None, None)]),
 "sensory-feel": ("Sensory Feel Morsels in Gravy", "cat", WET, [(223, None, None)]),
 # one case of 12 × 195 g cans (user, 2026-09-30)
 "mother-babycat-wet": ("Mother & Babycat Ultra Soft Mousse", "cat", WET, [(188, "Mousse", None)]),
}
HELD = {82: "no cost / sale price in the file (Indoor 27 10+2 kg promo bag) — not imported (user, 2026-09-30)"}
# Column D "Վաճառքի Գին կիլոգրամով" (user, 2026-09-30): each priced row also gets a variant sold loose.
# Dry: a `weight` variant (price = D per kg, grams chosen by the customer, stock in grams).
# Wet: D (750) is far below cost per kg, so it is the price of ONE pouch — a 1 × 85 g pack variant.
WEIGHT_STEP_G, WEIGHT_MIN_G, WEIGHT_STOCK_G = 1000, 1000, 10000   # 1 kg minimum, 1 kg steps (user, 2026-10-01)

LEAF = {("dog", DRY): 3, ("cat", DRY): 10, ("dog", WET): 4, ("cat", WET): 11}


def val(code, label):
    v = (menu.get(code) or {}).get("values", {}).get(label)
    if v is None:
        raise SystemExit(f"'{label}' is not a {code} value")
    return v


def facts(x, species, name):
    """Attribute picks with the page text that supports each (evidence rule 8)."""
    t = " ".join(filter(None, [x.get("title"), x.get("description"), x.get("details")] +
                     [f"{a} {b}" for a, b in x.get("benefits") or []])).lower()
    n = name.lower()
    out = {}
    def pick(code, label, why):
        out[code] = (label, why)
    # lifestage — our bands (data-tables table 1): senior = dog 8+, cat 10+
    if re.search(r"puppy|starter|junior", n): pick("lifestage", "Puppy", name)
    elif re.search(r"kitten|mother & babycat", n): pick("lifestage", "Kitten", name)
    elif re.search(r"\b8\+", n) and species == "dog": pick("lifestage", "Senior", name)
    elif re.search(r"12\+", n): pick("lifestage", "Senior", name)
    elif "adult" in t or re.search(r"\b(5|7)\+", n): pick("lifestage", "Adult", "adult" if "adult" in t else name)
    # breed size (dogs) from the line name
    for w, lab in (("mini", "Small Breeds"), ("medium", "Medium Breeds"), ("maxi", "Large Breeds"), ("giant", "Giant Breeds")):
        if species == "dog" and re.search(rf"\b{w}\b", n):
            pick("breed-size", lab, name); break
    vet = x.get("vet")
    if vet: pick("special-diet", "Veterinary Diet", "veterinary diet (Royal Canin Veterinary range)")
    elif "sterilised" in n: pick("special-diet", "Sterilised", name)
    elif "light weight" in n: pick("special-diet", "Weight Control", name)
    elif "indoor" in n: pick("special-diet", "Indoor", name)
    HF = [("urinary", "Urinary Tract Health"), ("renal", "Kidney Care"), ("cardiac", "Heart Care"), ("hepatic", "Liver Care"),
          ("gastro", "Digestive Health"), ("digest", "Sensitive Digestion"), ("hypoallergenic", "Allergy Relief"),
          ("sensitivity control", "Allergy Relief"), ("joint", "Hip & Joint Support"), ("mobility", "Hip & Joint Support"),
          ("skin", "Skin & Coat Health"), ("hairball", "Hairball Control"), ("light weight", "Weight Management"),
          ("mother", "Reproduction & Nursing")]
    for w, lab in HF:
        if w in n:
            pick("health-feature", lab, name); break
    return out


FIX_DOG = [(r"\byour cat's\b", "your dog's"), (r"\byour kitten\b", "your puppy"), (r"\bgrowing kittens\b", "growing puppies")]


def clean(t, species):
    """Royal Canin's page data: drop CMS label prefixes ("4B- ", "Nutrient 1-Fop:"), and fix the
    cat wording copied into two dog vet diets (their product page is unambiguously for dogs)."""
    t = re.sub(r"^\s*\d[A-Z]-\s*", "", t or "")
    t = re.sub(r"^\s*Nutrient \d+-Fop\s*", "", t, flags=re.I)
    t = re.sub(r"^\s*Claim \d+\s*-\s*", "", t, flags=re.I)
    t = re.sub(r"\s*Long Text\s*$", "", t, flags=re.I)
    if species == "dog":
        for a, b in FIX_DOG:
            t = re.sub(a, b, t)
    return t


def html_text(x, species):
    x = dict(x, details=clean(x.get("details"), species), description=clean(x.get("description"), species),
             benefits=[(clean(a, species), clean(b, species)) for a, b in x.get("benefits") or []])
    p = [f"<p>{html.escape(x['details'])}</p>".replace("\n\n", "</p><p>").replace("\n", " ")] if x.get("details") else \
        ([f"<p>{html.escape(x['description'])}</p>"] if x.get("description") else [])
    if x.get("benefits"):
        p.append("<ul>" + "".join((f"<li><strong>{html.escape(a.title())}</strong>: {html.escape(b or '')}</li>" if (a or "").strip()
                                  else f"<li>{html.escape(b or '')}</li>") for a, b in x["benefits"]) + "</ul>")
    about = "".join(p)
    nut = x.get("nutrition") or {}
    ing = "".join(f"<p>{html.escape(nut[k])}</p>" for k in ("composition", "additives", "analyticalConstituants") if nut.get(k))
    return about, ing


plan, os_payloads = [], f"{R}/payloads"
os.makedirs(os_payloads, exist_ok=True)
for key, (name, species, ptype, members) in P.items():
    cats = [LEAF[(species, ptype)]]
    variants, notes = [], []
    for i, (rn, texture, flavor) in enumerate(members):
        r, x = rows[rn], ex[rn]
        f = facts(x, species, name)
        attrs = {code: [val(code, lab)] for code, (lab, _) in f.items()}
        attrs["packaging"] = [val("packaging", "Bag" if ptype == DRY else "Pouch")]
        if texture: attrs["texture"] = [val("texture", texture)]
        if flavor: attrs["flavor"] = [val("flavor", flavor)]
        if x.get("vet") and species == "dog" and ptype == DRY and 5 not in cats: cats.append(5)
        pk = r["pack"]
        size = (f"{pk['pack_count']} × {pk['content']:g} g" if pk["pack_count"] > 1 else
                (f"{pk['content'] / 1000:g} kg" if pk["content"] >= 1000 else f"{pk['content']:g} g"))
        label = " ".join(filter(None, [flavor if flavor else None,
                                       {"Chunks in Gravy": "In Gravy", "Chunks in Jelly": "In Jelly", "Pate": "Loaf"}.get(texture, texture) if texture else None, size]))
        about, ing = html_text(x, species)
        sku = x.get("ean") or f"RC-{key.upper()}-{int(pk['content'])}G"
        if not x.get("ean"): notes.append(f"row {rn}: no barcode for this size — SKU {sku}")
        variants.append({"sku": sku, "name": label, "price": r["price"], "cost_price": r["cost"],
                         "sale_mode": "pack", "measure_type": "mass", "content": pk["content"], "pack_count": pk["pack_count"],
                         "initial_stock": 10, "attribute_values": attrs, "images": [],
                         "about_this_item": about, "ingredient_information": ing, "feeding_instructions": "",
                         "is_default": i == 0,
                         "_row": rn, "_file_name": r["name_file"], "_ean": x.get("ean"), "_ean_url": x.get("ean_url"),
                         "_source": x["url"], "_image_urls": [u for u in x.get("images") or [] if u],
                         "_evidence": {c: w for c, (_, w) in f.items()}})
        base = variants[-1]
        d = r.get("price_per_kg")
        if d and ptype == DRY:
            kg = pk["content"] * pk["pack_count"] / 1000
            variants.append(dict(base, sku=f"{sku}-KG", name=" ".join(filter(None, [flavor, "By weight"])),
                                 price=d, cost_price=round(r["cost"] / kg), sale_mode="weight",
                                 measure_type=None, content=None, pack_count=None,
                                 qty_step=WEIGHT_STEP_G, qty_min=WEIGHT_MIN_G, initial_stock=WEIGHT_STOCK_G,
                                 is_default=False, _ean=None, _twin_of=base["sku"], _loose="per kg"))
        elif d and ptype == WET and pk["pack_count"] > 1:
            single = [e for sz, e in (x.get("packs") or []) if sz and re.fullmatch(rf"(1\s*x\s*)?{pk['content']:g}\s*g", sz.strip(), re.I)]
            variants.append(dict(base, sku=single[0] if single else f"{sku}-1",
                                 name=label.replace(size, f"{pk['content']:g} g"),
                                 price=d, cost_price=round(r["cost"] / pk["pack_count"]), pack_count=1,
                                 is_default=False, _ean=single[0] if single else None,
                                 _twin_of=base["sku"], _loose="single pouch"))
    slug = "royal-canin-" + re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    body = {"name": name, "slug": slug, "brand_id": BRAND, "attribute_family_id": ptype, "category_ids": cats,
            "is_best_seller": False, "is_on_sale": False,
            "variants": [{k: v for k, v in vv.items() if not k.startswith("_") and not (v is None and k in ("measure_type", "content", "pack_count"))}
                         for vv in variants]}
    json.dump(body, open(f"{os_payloads}/{key}.json", "w"), ensure_ascii=False, indent=1)
    plan.append({"key": key, "name": name, "slug": slug, "type": ptype, "categories": cats, "variants": variants, "notes": notes})
json.dump({"products": plan, "held": HELD}, open(f"{R}/plan.json", "w"), ensure_ascii=False, indent=1)

used = {v["_row"] for p in plan for v in p["variants"]}
missing = sorted(set(rows) - used - set(HELD))
print(f"{len(plan)} products, {len(used)} rows planned, {len(HELD)} held, unplanned rows: {missing}")
