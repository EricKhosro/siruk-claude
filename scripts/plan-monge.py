#!/usr/bin/env python3
"""Plan the Monge-group import (Monge, Gemon, Lechat, Special Dog): CSV row +
hafo price + monge.shop page (EAN-joined) + a hand-written grouping table ->
plan for scripts/import-plan.py.

Grouping table .siruk-cache/monge-groups.json, one entry per article code:
  {"<code>": {"product": "<Name without brand>", "label": "<variant label>",
              "brand_id": 5, "family": 2, "cat_ids": [11], "ptype": "wet",
              "images": [..optional override urls..], "attrs": {..optional overrides..},
              "page": "<optional monge.it/monge.shop url for texts>"}}
Rows without an entry are reported, not planned. Prices only from hafo
(variant row, wholesale == cost, price > cost) or the sibling fallback.
"""
import json, os, re, sys, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, ".siruk-cache")
MENU = json.load(open(os.path.join(ROOT, "reference/attribute-values.json")))
VAL = {code: {k.lower(): v for k, v in d["values"].items()} for code, d in MENU.items()}
BRAND_SLUG = {5: "monge", 18: "gemon", 20: "lechat", 21: "special-dog", 19: "simba"}


ALIAS = {"product-weight": {"85 g": "85 gr"}}


def vid(code, label):
    label = ALIAS.get(code, {}).get(label, label)
    return VAL.get(code, {}).get((label or "").lower())


def slugify(s):
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", s.lower())).strip("-")


def stock_of(q):
    q = int(float(q or 0) or 0)
    return 10 if q <= 1 else q


def weight_of(text):
    m = re.search(r"(\d+[.,]?\d*)\s*(kg|g|ml|l)\b", text or "", re.I)
    if not m:
        return None, None
    n, u = m.group(1).replace(",", "."), m.group(2).lower()
    n = n.rstrip("0").rstrip(".") if "." in n else n
    return f"{n} {u}", (float(n) * (1000 if u == "kg" else 1))


FLAVOR = {"cod": "Cod", "codfish": "Cod", "salmon": "Salmon", "tuna": "Tuna", "chicken": "Chicken", "turkey": "Turkey",
          "pork": "Pork", "rabbit": "Rabbit", "hare": "Rabbit", "lamb": "Lamb", "cockerel": "Chicken", "veal": "Veal",
          "trout": "Trout", "beef": "Beef", "duck": "Duck", "herring": "Herring", "buffalo": "Buffalo", "anchovies": "Anchovies",
          "śledź": "Herring", "game": "Wild Game", "wild game": "Wild Game", "fish": "Fish", "ocean fish": "Fish", "shrimp": "Shrimp",
          "prawns": "Shrimp", "liver": "Liver", "egg": "Egg", "cheese": "Cheese", "deer": "Venison", "boar": "Boar", "wild boar": "Boar", "anchovy": "Anchovies"}
TEXTURE = {"pieces of meat in sauce": "Chunks in Gravy", "pieces of meat in jelly": "Chunks in Jelly", "pate": "Pate",
           "pate with meat pieces": "Pate", "mousse": "Mousse", "chunks": "Chunks in Gravy", "shreds": "Shredded",
           "fillets": "Fillets", "flakes": "Shredded"}
AGE = {"for adults": "Adult", "for puppies": "Puppy", "for kittens": "Kitten", "for seniors": "Senior", "adult": "Adult",
       "puppy": "Puppy", "kitten": "Kitten", "senior": "Senior"}
DIET = {"grain-free diet": "Grain-Free", "grain free": "Grain-Free", "sterilised": "Sterilised", "sterilized": "Sterilised",
        "monoprotein": "Monoprotein", "hypoallergenic": "Hypoallergenic", "weight control": "Weight Control",
        "veterinary": "Veterinary Diet"}
HEALTH = {"kidney diseases": "Kidney Care", "gastrointestinal": "Digestive Health", "liver problems": "Liver Care",
          "diabetes": "Diabetic Support", "for teeth and gums": "Dental & Breath Care", "hairball": "Hairball Control",
          "urinary": "Urinary Tract Health", "strengthening heart": "Heart Care", "skin": "Skin & Coat Health",
          "weight control": "Weight Management", "high physical activity": "High-Energy", "obesity": "Weight Management",
          "skin infection": "Skin & Coat Health", "lack of appetite": "Appetite Stimulation"}
SIZE = {"mini": "Small Breeds", "small": "Small Breeds", "extra small": "Extra Small Breeds", "medium": "Medium Breeds",
        "maxi": "Large Breeds", "large": "Large Breeds", "all breeds": "All Breeds"}


def pick(code, label, ev, attrs, evd):
    if label and vid(code, label):
        attrs[code] = vid(code, label); evd[code] = ev
        return True
    return False


def main():
    out_path = sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else os.path.join(CACHE, "monge-plan.json")
    rows = [r for r in json.load(open(os.path.join(CACHE, "todo-rows.json"))) if r["Brand"] in ("Monge", "Gemon", "Lechat", "Special Dog")]
    hafo = json.load(open(os.path.join(CACHE, "hafo-all.json")))
    shop = {x["article"]: x for x in json.load(open(os.path.join(CACHE, "mongeshop-group.json")))}
    pages = json.load(open(os.path.join(CACHE, "mongeshop-pages.json")))
    groups = json.load(open(os.path.join(CACHE, "monge-groups.json")))
    oldimg = json.load(open(os.path.join(CACHE, "monge-old-images.json"))) if os.path.exists(os.path.join(CACHE, "monge-old-images.json")) else {}
    mit = {}
    for f in ("mongeit-pages.json", "mongeit-pages2.json", "mongeit-pages3.json"):
        fp = os.path.join(CACHE, f)
        if os.path.exists(fp):
            mit.update(json.load(open(fp)))
    ean2mit = {}
    for u, pg_ in mit.items():
        for img in pg_.get("images") or []:
            for e in re.findall(r"(800947\d{7})", img):
                ean2mit.setdefault(e, u)
    live = json.load(open(os.path.join(CACHE, "live-catalogue.json")))
    live_by_slug = {p["slug"]: pid for pid, p in live.items()}
    wanted, wanted_ev, unpriced, ungrouped, flagged, sibling = collections.Counter(), {}, [], [], [], []
    prods = collections.OrderedDict()

    for r in rows:
        code = r["Article Code"].strip(); inv = r["Product Name (as printed)"]; cost = int(float(r["Buy Price (AMD)"]))
        h = hafo.get(code) or {}
        g = groups.get(code)
        if not g:
            ungrouped.append({**r, "hafo_title": h.get("title_hy"), "hafo_price": h.get("price_amd"), "shop_name": shop.get(code, {}).get("name_en")})
            continue
        price, why, note = None, None, ""
        if h.get("confirmed") and h.get("price_source") == "variant":
            p, w = h.get("price_amd"), h.get("wholesale_price_amd")
            if w == cost and p and p > cost:
                price = int(p)
            else:
                why, note = "wrong row", f"hafo row {h.get('variant_sku')} price {p} wholesale {w} vs cost {cost}"
        elif h.get("hafo_id") and h.get("confirmed"):
            why, note = "on hafo, size missing", f"listing '{(h.get('title_hy') or '')[:60]}' skus {h.get('skus')}"
        else:
            why = "not on hafo"
        s = shop.get(code, {}); pg = pages.get(s.get("url") or "", {}) or {}
        ean = (h.get("barcodes") or [None])[0]
        if not pg:
            mu = g.get("page") or (ean2mit.get(ean) if ean else None)
            if mu and mu in mit:
                pg = dict(mit[mu]); pg["card"] = pg.get("card") or {}
        card = {k.lower(): v for k, v in (pg.get("card") or {}).items()}
        name_en = pg.get("name") or s.get("name_en") or ""
        # ---- attributes (closed menu + evidence)
        attrs, ev = {}, {}
        ptype = g["ptype"]
        wl, grams = weight_of(g.get("label", "")) if weight_of(g.get("label", ""))[0] else weight_of(card.get("libra", "") or name_en)
        if ptype != "dry":
            if wl and not pick("product-weight", wl, f"pack {wl}", attrs, ev):
                wanted[("product-weight", wl)] += 1; wanted_ev[("product-weight", wl)] = name_en or inv
        age = card.get("age", "").lower()
        if not pick("lifestage", AGE.get(age), f"card AGE '{card.get('age')}'", attrs, ev):
            for k, v in AGE.items():
                if re.search(rf"\b{k}\b", (name_en + " " + g["product"]).lower()):
                    pick("lifestage", v, f"name '{name_en or g['product']}'", attrs, ev); break
        mi = card.get("main ingredient", "").lower()
        fl = g.get("flavor") or FLAVOR.get(mi)
        if g.get("attr_labels"):
            pass
        if not fl:
            for k, v in FLAVOR.items():
                if re.search(rf"\b{k}\b", (g.get("label", "") + " " + name_en).lower()):
                    fl = v; break
        if fl and not pick("flavor", fl, f"card MAIN INGREDIENT '{card.get('main ingredient')}' / name '{name_en}'", attrs, ev):
            wanted[("flavor", fl)] += 1; wanted_ev[("flavor", fl)] = name_en or inv
        if ptype == "wet":
            tf = card.get("type of food", "").lower()
            tx = g.get("texture") or TEXTURE.get(tf)
            if tx and not pick("texture", tx, f"card TYPE OF FOOD '{card.get('type of food')}'", attrs, ev):
                wanted[("texture", tx)] += 1; wanted_ev[("texture", tx)] = name_en or inv
            pk = g.get("packaging") or ("Pouch" if re.search(r"pouch|պաուչ|85 ?g|100 ?g", inv + " " + name_en, re.I) and grams and grams <= 100 else ("Can" if grams and grams >= 150 else None))
            if pk:
                pick("packaging", pk, f"format {pk.lower()} ({wl})", attrs, ev)
        if ptype == "dry":
            pick("packaging", "Bag", "dry kibble bag", attrs, ev)
            sz = g.get("breed_size") or next((v for k, v in SIZE.items() if re.search(rf"\b{k}\b", (g["product"] + " " + card.get("size", "")).lower())), None)
            if sz:
                pick("breed-size", sz, f"name/card size '{card.get('size') or g['product']}'", attrs, ev)
        nn = (card.get("nutritional needs", "") + " " + g["product"] + " " + name_en + " " + card.get("line", "")).lower()
        d = g.get("special_diet") or next((v for k, v in DIET.items() if k in nn), None)
        if d:
            pick("special-diet", d, f"'{card.get('nutritional needs') or card.get('line') or g['product']}'", attrs, ev)
        hf = g.get("health_feature") or next((v for k, v in HEALTH.items() if k in nn), None)
        if hf and not pick("health-feature", hf, f"'{card.get('nutritional needs') or g['product']}'", attrs, ev):
            wanted[("health-feature", hf)] += 1; wanted_ev[("health-feature", hf)] = name_en or inv
        comp = pg.get("composition") or ""
        if comp:
            first = comp.split(",")[0].lower()
            first = re.sub(r"\d+[.,]?\d*\s*%", "", first)
            inner = re.search(r"\(([^)]*)", first)
            generic = re.match(r"\s*(meats? and (?:animal )?derivatives|fish and fish derivatives|cereals|vegetable|oils|minerals|meat|fish)\b", first)
            cands = []
            if generic and inner:
                cands.append(inner.group(1))
            cands.append(re.sub(r"\(.*", "", first))
            ING = {"codfish": "Cod", "cod": "Cod", "salmon": "Salmon", "tuna": "Tuna", "chicken": "Chicken", "turkey": "Turkey", "pork": "Pork",
                   "rabbit": "Rabbit", "lamb": "Lamb", "beef": "Beef", "duck": "Duck", "veal": "Veal", "trout": "Trout", "hare": "Rabbit",
                   "buffalo": "Buffalo", "herring": "Herring", "deer": "Venison", "venison": "Venison", "boar": "Boar", "anchovies": "Anchovies",
                   "anchovy": "Anchovies", "rice": "Rice", "maize": "Corn", "corn": "Corn", "potatoes": "Potatoes", "peas": "Peas"}
            ing = None
            for c in cands:
                w = re.sub(r"\b(fresh|dried|dehydrated|meat|meats|of|and|derivatives|derivates|animal|%)\b", " ", c)
                w = re.sub(r"[^a-z ]", " ", w).split()
                for tok in w:
                    if tok in ING:
                        ing = ING[tok]; break
                if ing:
                    break
            if ing and not pick("ingredient", ing, f"composition '{comp[:60]}'", attrs, ev):
                wanted[("ingredient", ing)] += 1; wanted_ev[("ingredient", ing)] = comp[:60]
        attrs.update({k: v for k, v in (g.get("attrs") or {}).items()})
        for k, lab in (g.get("attr_labels") or {}).items():
            if lab is None:
                attrs.pop(k, None); ev.pop(k, None)
            elif vid(k, lab):
                attrs[k] = vid(k, lab); ev[k] = f"override: {lab}"
            else:
                wanted[(k, lab)] += 1; wanted_ev[(k, lab)] = name_en or inv
        # ---- texts
        about = ""
        if pg.get("description"):
            about += f"<p>{pg['description']}</p>"
        ingr = ""
        if comp: ingr += f"<p><strong>Composition:</strong> {comp}</p>"
        if pg.get("analytical"): ingr += f"<p><strong>Analytical constituents:</strong> {pg['analytical']}</p>"
        if pg.get("additives"): ingr += f"<p><strong>Additives:</strong> {pg['additives']}</p>"
        feed = f"<p>{pg['feeding']}</p>" if pg.get("feeding") else ""
        images = g.get("images") or pg.get("images") or ([s["image"]] if s.get("image") else []) or (oldimg.get(code, {}).get("images") or [])
        src = pg.get("url") or s.get("url") or g.get("page") or (oldimg.get(code, {}).get("images") or [None])[0] or "none"
        variant = {"sku": code, "name": g.get("label") or wl or "", "cost_price": cost, "stock": stock_of(r["Qty Received"]),
                   "images": images, "attribute_value_ids": {k: v for k, v in attrs.items() if v},
                   "about_this_item": about, "ingredient_information": ingr, "feeding_instructions": feed,
                   "_ev": ev, "_inv": inv, "_code": code, "_why": why, "_note": note, "_species": r["Species"]}
        if ptype == "dry":
            kg = round((grams or 0) / 1000, 3)
            variant.update({"pricing_type": "per_kg", "weight": kg, "price": price,
                            "price_per_kg": round(price / kg, 2) if price and kg else None})
        else:
            variant.update({"pricing_type": "fixed", "price": price})
        key = (g["brand_id"], g["product"], g["ptype"])
        prods.setdefault(key, {"name": g["product"], "brand_id": g["brand_id"], "family": g["family"], "cat_ids": g["cat_ids"],
                              "ptype": ptype, "src": src, "rows": []})
        prods[key]["rows"].append(variant)

    products = []
    for key, g in prods.items():
        rows_ = g["rows"]; priced = [v for v in rows_ if v["price"]]
        for v in rows_:
            if v["price"]:
                continue
            sibs = [x for x in priced if x["cost_price"] == v["cost_price"]]
            prices = sorted({x["price"] for x in sibs})
            if len(prices) == 1:
                v["price"] = prices[0]; v["_sibling"] = sibs[0]["sku"]
                if v["pricing_type"] == "per_kg" and v.get("weight"):
                    v["price_per_kg"] = round(v["price"] / v["weight"], 2)
                sibling.append({"Article Code": v["sku"], "Brand": BRAND_SLUG.get(g["brand_id"], g["brand_id"]), "Product": g["name"], "Variant": v["name"],
                                "Buy Price (AMD)": v["cost_price"], "Sale Price (AMD)": v["price"], "Priced from (sibling code)": sibs[0]["sku"],
                                "Sibling hafo price": sibs[0]["price"], "Why hafo had no price": v["_why"], "Date": "2026-09-10"})
            elif len(prices) > 1:
                v["_why"] = "sibling prices differ"; v["_note"] = "candidates " + ", ".join(f"{x['sku']}={x['price']}" for x in sibs)
        keep = []
        for v in rows_:
            if v["price"]:
                keep.append(v)
            else:
                unpriced.append({"Article Code": v["sku"], "Brand": BRAND_SLUG.get(g["brand_id"], g["brand_id"]).replace("-", " ").title(), "Official Site": g["src"],
                                 "Proposed Product Name": g["name"], "Proposed Variant": v["name"], "Buy Price (AMD)": v["cost_price"], "Sale Price (AMD)": "",
                                 "Qty": v["stock"], "Species": v["_species"], "Invoice Name (as printed)": v["_inv"],
                                 "Why no price": v["_why"] + (f" — {v['_note']}" if v["_note"] else ""), "Status": "NOT imported — needs a sale price from you"})
        if not keep:
            continue
        # attribute-combination uniqueness: colliding variants become their own product (label in the Name)
        seen, buckets = {}, []
        main = []
        axes = {a for v in keep for a in ("flavor", "texture", "product-weight") if a in v["attribute_value_ids"]} if len(keep) > 1 else set()
        for v in keep:
            k = json.dumps(v["attribute_value_ids"], sort_keys=True)
            if k in seen or (len(keep) > 1 and not v["attribute_value_ids"]) or any(a not in v["attribute_value_ids"] for a in axes):
                buckets.append([v]); flagged.append({"code": v["sku"], "what": f"split from '{g['name']}': attribute combination not distinct ({k})"})
            else:
                seen[k] = v["sku"]; main.append(v)
        buckets = ([main] if main else []) + buckets
        for bi, bucket in enumerate(buckets):
            name = g["name"]
            if (bi > 0 or len(bucket) == 1) and bucket[0]["name"] and bucket[0]["name"].lower() not in name.lower():
                name = f"{name} {bucket[0]['name']}"
            slug = BRAND_SLUG[g["brand_id"]] + "-" + slugify(name)
            existing = live_by_slug.get(slug)
            variants = []
            for i, v in enumerate(bucket):
                variants.append({k: v[k] for k in ("sku", "name", "pricing_type", "price", "cost_price", "stock", "images", "attribute_value_ids",
                                                    "about_this_item", "ingredient_information", "feeding_instructions") if k in v}
                                | ({"price_per_kg": v["price_per_kg"], "weight": v["weight"]} if v["pricing_type"] == "per_kg" else {})
                                | {"is_default": i == 0, "sort_order": i, "_ev": v["_ev"], "_inv": v["_inv"], "_code": v["_code"], "_sibling": v.get("_sibling")})
            products.append({"slug": slug, "name": name, "category_ids": g["cat_ids"], "brand_id": g["brand_id"], "attribute_family_id": g["family"],
                             "variants": variants, "source": g["src"], "ptype": g["ptype"], **({"existing_id": int(existing)} if existing else {})})
    out = {"products": products, "unpriced": unpriced, "ungrouped": ungrouped, "flagged": flagged, "sibling": sibling,
           "wanted": [{"attribute": k[0], "label": k[1], "count": n, "evidence": wanted_ev[k]} for k, n in wanted.most_common()]}
    json.dump(out, open(out_path, "w"), ensure_ascii=False, indent=1)
    print(f"products {len(products)} variants {sum(len(p['variants']) for p in products)} unpriced {len(unpriced)} ungrouped {len(ungrouped)} "
          f"flagged {len(flagged)} sibling {len(sibling)} wanted {len(wanted)}", file=sys.stderr)


if __name__ == "__main__":
    main()
