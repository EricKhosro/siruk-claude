#!/usr/bin/env python3
"""Plan the Trixie import: CSV row + hafo price + trixie.de page -> plan for
scripts/import-plan.py, plus the per-run CSV rows (unpriced / not found).

Rules applied (CLAUDE.md): sale price only from hafo's row for the article
(price_source "variant", price > cost) or the
sibling-price fallback (same product group, same cost, siblings agree);
identity from the article code (Tx suffix + trixie.de catalogue); name /
texts / gallery from trixie.de; attributes only from the closed menu with a
quote; products in a leaf category; one product per row for types without
an attribute family (accessories, grooming), grouped by page otherwise.

    scripts/plan-trixie.py --types toys,treats,grooming,accessories,supplements --out plan.json
"""
import argparse, csv, json, os, re, sys, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, ".siruk-cache")
BRAND = 8

# Register price (user rule 2026-09-16): the PM's register `Վաճառքի գին` is the
# sale price and outranks hafo. REGISTER_STATUS=state/register/register-status.json
# turns it on; a register price at or below cost is ignored (rule 5).
_REG = {}
if os.environ.get("REGISTER_STATUS"):
    for _r in json.load(open(os.environ["REGISTER_STATUS"])):
        if _r.get("code") and _r.get("sale_price"):
            _REG[_r["code"].strip()] = float(_r["sale_price"])


def register_price(code, cost):
    p = _REG.get(code.strip())
    return int(p) if p and p > cost else None

MENU = json.load(open(os.path.join(ROOT, "reference/attribute-values.json")))
VAL = {code: {k.lower(): v for k, v in d["values"].items()} for code, d in MENU.items()}


ALIAS = {"product-weight": {"85 g": "85 gr"}}


def vid(code, label):
    label = ALIAS.get(code, {}).get(label, label)
    return VAL.get(code, {}).get((label or "").lower())


def slugify(s):
    s = re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")
    return re.sub(r"-+", "-", s)


def art_of(code):
    return re.sub(r"(Tx|TXN)$", "", code.strip())


MATERIAL_SUFFIX = re.compile(
    r",\s*(plush|fabric|latex|natural rubber|rubber|thermoplastic rubber|tpr|cotton(?:/polyester)?|polyester|"
    r"plastic(?:/tpr)?|vinyl|wood|paper cord|foam|felt(?:/wood)?|nylon|stainless steel|ceramic|melamine|"
    r"silicone|sisal|jute|leather|metal|bamboo|cardboard|polypropylene|pp|abs|glass|microfibre|terry cloth)"
    r"\s*(?:\([^)]*\))?\s*$", re.I)


def clean_name(name):
    name = re.sub(r"^\s*TRIXIE\s+", "", name, flags=re.I)
    prev = None
    while prev != name:
        prev = name
        name = MATERIAL_SUFFIX.sub("", name).strip()
    return name.strip(" ,")



# --------------------------------------------------- accessories (2026-09-16)
# Supplies / Cleaning & Potty / Scratcher leaves (68–81, created 2026-09-11)
# keyed by the trixie.de shelf segment, with the name overrides
# scripts/archive/_recat-blocked-2026-09-11.py used. 13 "Accessories" is not a
# product category any more.
ACC_CAT = {"dog-collars": 69, "dog-bowls": 70, "dog-beds": 71, "dog-clothing": 72, "dog-travel": 73,
           "dog-training": 74, "dog-pads": 76, "dog-poop": 77, "dog-cleaners": 78, "cat-collars": 79,
           "cat-scratchers": 81, "dog-grooming-tools": 30, "litter-acc": 67}
ACC_SHELF = {"dog-collars": "dog-collars", "dog-leashes": "dog-collars", "dog-harnesses": "dog-collars",
             "luminous-items-safety": "dog-collars", "jogging-accessories": "dog-collars",
             "dog-bowls-accessories": "dog-bowls", "travel-bowls-drinking-bottles": "dog-bowls",
             "dog-poop-bags-dispensers": "dog-poop", "textile-cleaning": "dog-cleaners",
             "cat-harnesses-collars": "cat-collars", "scratching-cardboards": "cat-scratchers",
             "scratching-furniture-for-wall-mounting": "cat-scratchers", "cat-litter-tray": "litter-acc",
             "litter-trays": "litter-acc", "litter-tray-accessories": "litter-acc",
             "cat-bowls-accessories": "dog-bowls", "dog-clothing": "dog-clothing", "dog-beds": "dog-beds",
             "cat-beds": "dog-beds", "transport": "dog-travel", "car-accessories": "dog-travel",
             "training": "dog-training", "dog-sport": "dog-training", "hygiene": "dog-pads"}


def acc_bucket(name, seg, lowinv, species):
    n = (name or "").lower()
    if "poisoned bait protection" in n or "muzzle" in n:            return "dog-training"
    if "dog socks" in n or re.search(r"\bcoat\b|jumper|raincoat|sweater", n): return "dog-clothing"
    if "cooling mat" in n or "cushion" in n or "blanket" in n:      return "dog-beds"
    if "car seat cover" in n or "carrier" in n or "transport box" in n: return "dog-travel"
    if "towel with pockets" in n:                                   return "dog-grooming-tools"
    if "poop scoop" in n or "poop bag" in n or "dirt bag" in n:     return "dog-poop"
    if "place mat" in n or "silicone tray" in n:                    return "dog-bowls"
    if re.search(r"\b(nappy|diaper|protective pants|pads for protective)", n): return "dog-pads"
    if "lint" in n or "upholstery" in n or "textile brush" in n:    return "dog-cleaners"
    if "scratching" in n:                                           return "cat-scratchers"
    if re.search(r"litter|dustpan|scoop", n) or re.search(KW[0][0], lowinv): return "litter-acc"
    if seg in ACC_SHELF:
        b = ACC_SHELF[seg]
        if b == "dog-collars" and species.startswith("cat"):
            return "cat-collars"
        return b
    if re.search(r"\b(collar|harness|lead|leash|bandana|choke|chain|i\.d\. tag|address)", n) or re.search(r"վզնոց|ձգափոկ|շլեյկա|մեդալիոն", lowinv):
        return "cat-collars" if (species.startswith("cat") or re.search(r"\b(cat|kitten)\b", n) or "կատ" in lowinv) else "dog-collars"
    if "bowl" in n or "bottle" in n or "կերաման" in lowinv:        return "dog-bowls"
    return None


LETTER = r"(?:XXS|XS|S|M|L|XL|XXL)"
LETTER_RUN_RE = re.compile(rf"^({LETTER}(?:\s*[–-]\s*{LETTER})?(?:,\s*{LETTER}(?:\s*[–-]\s*{LETTER})?)*)\s*(?:[,:]|$)")
CAPACITY_RE = re.compile(r"^(\d+(?:[.,]\d+)?\s*(?:l|ml)\s*/\s*ø\s*\d+(?:[.,]\d+)?\s*cm)", re.I)
ACC_COLOUR = {"black": "Black", "royal blue": "Blue", "blue": "Blue", "dark blue": "Dark Blue", "neon blue": "Blue",
              "indigo": "Blue", "aqua": "Aqua", "ocean": "Blue", "petrol": "Teal", "red": "Red", "coral": "Red",
              "fuchsia": "Pink", "pink": "Pink", "neon pink": "Pink", "blush": "Blush", "antique pink": "Pink",
              "orchid": "Purple", "light lilac": "Purple", "purple": "Purple", "sangria": "Purple", "olive green": "Green",
              "green": "Green", "sage": "Sage", "mint": "Green", "apple": "Green", "khaki": "Green", "grey": "Grey",
              "dark grey": "Grey", "light grey": "Grey", "graphite": "Grey", "silver grey": "Silver", "silver": "Silver",
              "chrome": "Silver", "gold": "Gold", "white": "White", "cream": "Ivory", "dark brown": "Brown", "brown": "Brown",
              "rust": "Brown", "orange": "Orange", "papaya": "Orange", "sand": "Beige", "beige": "Beige", "curry": "Yellow",
              "yellow": "Yellow", "neon yellow": "Yellow", "sorted": "Color Varies", "various": "Color Varies",
              "assorted": "Color Varies", "bronze": "Gold", "anthracite": "Grey"}


def acc_size(label):
    """'XS–S, 22–35 cm/10 mm, black' -> 'XS–S'; '0.25 l/ø 12 cm' -> that; else None."""
    lab = (label or "").strip()
    m = LETTER_RUN_RE.match(lab)
    if m:
        return m.group(1).strip()
    m = CAPACITY_RE.match(lab)
    if m:
        return m.group(1).replace(",", ".").strip()
    return None


def acc_colour(spec_colour, label):
    txt = (spec_colour or "").lower().strip()
    if not txt:
        parts = [x.strip().lower() for x in (label or "").split(",")]
        txt = parts[-1] if len(parts) > 1 else (parts[0] if parts and parts[0] in ACC_COLOUR else "")
    if not txt:
        return None
    first = re.split(r"\s*/\s*", txt)[0].strip()
    for k in sorted(ACC_COLOUR, key=len, reverse=True):
        if first == k or first.endswith(" " + k) or first.startswith(k + " "):
            return ACC_COLOUR[k]
    return None

# ------------------------------------------------------------- categories --
TOY_TYPE = {"plush-toys": "Plush", "latex-rubber-toys": "Latex & Rubber", "tugging-rope-toys": "Rope & Tug",
            "throwing-retrieving-toys": "Fetch & Retrieve", "chewing-toys-dental-care": "Chew & Dental",
            "intelligence-activity-toys": "Activity & Intelligence", "catnip-attractants": "Catnip",
            "play-mice-animals-balls": "Mouse & Animal", "dog-sport": "Fetch & Retrieve", "retrieving": "Fetch & Retrieve",
            "toys": "Plush", "toys-for-cats": "Mouse & Animal"}
TOY_LEAF = {"dog": {"Plush": 17, "Latex & Rubber": 18, "Rope & Tug": 19, "Fetch & Retrieve": 20, "Ball": 20,
                    "Chew & Dental": 21, "Activity & Intelligence": 22},
            "cat": {"Mouse & Animal": 23, "Ball": 24, "Catnip": 25, "Activity & Intelligence": 26, "Plush": 23}}
GROOM_LEAF = {"brushes-combs": (28, 35), "shampoos": (29, 36), "trimmers": (30, 37), "claws-paws": (31, 38),
              "teeth-ears-eyes": None, "bathrobes-towels": (30, 37)}
# Armenian keyword fallbacks (CSV invoice name) for rows without a trixie.de page
KW = [  # (regex on lowercased armenian/latin name, category hint)
    (r"տուալետ|լցանյութի|շերեփ|աղբը|հավաքելու|մատնոց", "litter-acc"),
    (r"լցանյութ", "litter"),
    (r"շամպուն|կոնդիցիոներ|բալզամ", "shampoo"),
    (r"սանր|խոզանակ|ֆուրմինատոր|մազահան|մազ", "brush"),
    (r"մկրատ|մեքենա|տրիմեր|կտրիչ", "tool"),
    (r"ճանկ|եղունգ|թաթ", "paw"),
    (r"ականջ", "ear"),
    (r"ատամ|բերանի", "teeth"),
    (r"աչք", "eye"),
]
TOY_KW = [(r"լատեքս|լաստեքս|լատեկս", "Latex & Rubber", "Latex"), (r"ջերմապլաստիկ|թերմոպլաստիկ|ջերմակայուն", "Latex & Rubber", "Thermoplastic Rubber"),
          (r"ռետին|կաուչուկ|վինիլ", "Latex & Rubber", "Rubber"), (r"պարան|ջութ", "Rope & Tug", "Cotton"),
          (r"գնդակ|գնդ", "Ball", None), (r"պլյուշ|փափուկ|թավշ", "Plush", "Plush"),
          (r"մուկ|մկն", "Mouse & Animal", None), (r"ծամ|ոսկոր", "Chew & Dental", None),
          (r"ձող|կարթ|փետուր", "Mouse & Animal", None)]


def stock_of(q):
    q = int(float(q or 0) or 0)
    return 10 if q <= 1 else q


SIZE_RE = re.compile(r"(\d+[.,]?\d*)\s*(?:սմ|см|cm)\b")


def size_cm(name):
    m = SIZE_RE.findall(name or "")
    return m[-1].replace(",", ".") if m else None


def label_from(spec, invoice):
    parts = []
    if spec.get("Size"):
        parts.append(spec["Size"])
    for k in ("Contents/Weight", "Contents", "Measurements"):
        if spec.get(k):
            parts.append(spec[k]); break
    if spec.get("Sort") and spec["Sort"].lower() not in (invoice or "").lower():
        parts.append(spec["Sort"])
    if spec.get("Colour") and not re.search(r"assorted|various|random|mixed", spec["Colour"], re.I):
        parts.append(spec["Colour"])
    if not parts:
        m = re.search(r"(\d+[.,]?\d*\s*(?:g|գ|կգ|kg|ml|մլ|l|լ)\b)", invoice or "")
        if m:
            u = m.group(1).replace("գ", "g").replace("կգ", "kg").replace("մլ", "ml").replace("լ", "l").replace(",", ".")
            parts.append(re.sub(r"(\d)(\w)", r"\1 \2", u))
        elif size_cm(invoice):
            parts.append(size_cm(invoice) + " cm")
    return ", ".join(parts)


def weight_label(spec, invoice):
    s = spec.get("Contents/Weight") or spec.get("Contents") or ""
    m = re.search(r"(\d+[.,]?\d*)\s*(kg|g|ml|l)\b", s) or re.search(r"(\d+[.,]?\d*)\s*(kg|g|ml|l|գ|կգ|մլ|լ)\b", invoice or "")
    if not m:
        return None
    n, u = m.group(1).replace(",", "."), m.group(2)
    u = {"գ": "g", "կգ": "kg", "մլ": "ml", "լ": "l"}.get(u, u)
    n = n.rstrip("0").rstrip(".") if "." in n else n
    return f"{n} {u}"


# ---------------------------------------------------------------- attrs ----
FLAVOR_WORDS = ["chicken", "beef", "lamb", "duck", "salmon", "turkey", "rabbit", "ostrich", "tuna", "fish", "pork",
                "venison", "cheese", "liver", "peanut butter", "banana", "shrimp", "cod", "trout", "herring", "game",
                "kangaroo", "horse", "goat", "insect", "cranberry", "mint", "vanilla", "honey", "apple", "carrot",
                "pumpkin", "sweet potato", "blueberry", "strawberry", "coconut", "cheese"]
FLAVOR_MAP = {"fish": "Fish", "sweet potato": "Sweet Potato", "peanut butter": "Peanut Butter", "game": "Wild Game"}
HEALTH = [("dental|teeth|tooth|tartar|plaque", "Dental & Breath Care"), ("hairball", "Hairball Control"),
          ("digest", "Digestive Health"), ("skin and coat|skin & coat|coat", "Skin & Coat Health"),
          ("joint", "Hip & Joint Support"), ("calm|relax", "Calming"), ("urinary", "Urinary Tract Health"),
          ("immune", "Immune Support"), ("weight", "Weight Management")]
DIET = [("grain-free|grain free|without grain|no grain", "Grain-Free"), ("gluten-free|gluten free", "Gluten-Free"),
        ("sugar-free|sugar free|no added sugar|without sugar", "Sugar Free"), ("lactose-free|lactose free", "Lactose-Free"),
        ("no artificial colour|without artificial colour|no colourings|free from colourings", "No Artificial Colorants"),
        ("hypoallergenic", "Hypoallergenic"), ("monoprotein|single protein|mono-protein", "Monoprotein"),
        ("low fat|low-fat|reduced fat", "Low Fat"), ("high protein", "High-Protein")]
FORM = [("paste", "Paste"), ("tablet", "Tablet"), ("drops|oil|liquid|syrup", "Liquid"), ("spray", "Spray"),
        ("powder", "Powder"), ("gel", "Gel"), ("wipes|finger pad|cleaning pad", "Wipes"), ("shampoo", "Shampoo"),
        ("toothpaste", "Paste"), ("cream", "Cream"), ("lotion", "Lotion"), ("foam", "Foam"), ("stick", "Stick")]
MATERIAL = [("thermoplastic rubber (tpr)", "Thermoplastic Rubber"), ("plastic/tpr", "Thermoplastic Rubber"), ("tpr", "Thermoplastic Rubber"),
            ("plush/rope", "Plush"), ("plush with rope", "Plush"), ("plush/fabric", "Plush"), ("plush (polyester)", "Plush"), ("plush", "Plush"),
            ("fabric (polyester)", "Synthetic Fabric"), ("cotton/polyester", "Cotton/Polyester"), ("cotton", "Cotton"),
            ("natural rubber", "Rubber"), ("rubber", "Rubber"), ("latex", "Latex"), ("paper cord", "Paper Cord"),
            ("vinyl", "Vinyl / PVC"), ("wood", "Wood"), ("foam", "Foam"), ("plastic", "Plastic"), ("polyester", "Polyester"),
            ("nylon", "Nylon"), ("sisal", "Jute"), ("jute", "Jute"), ("felt", "Felt"), ("fleece", "Fleece"),
            ("silicone", "Silicone"), ("cardboard", "Cardboard / Paper"), ("bamboo", "Bamboo"), ("polypropylene", "Polypropylene"),
            ("microfibre", "Synthetic Fabric"), ("terry cloth", "Cotton")]
FEATURE = [("squeak", "Squeaky"), ("with bell", "With Bell"), ("catnip", "Catnip"), ("mint", "Mint Flavour"),
           ("massages the gums", "Massages Gums"), ("float", "Floats"), ("light up|glow|flash", "Glowing & Light-Up"),
           ("inner rope|with rope", "With Rope"), ("shock absorber", "Shock Absorber"), ("crinkle|rustl", "Crinkle"),
           ("dental|teeth cleaning|for teeth", "Dental"), ("robust|strong chewer|durable", "Tough Chewer"),
           ("intelligence|strategy|puzzle", "Puzzle Toy"), ("water", "Water Toy"), ("bounc", "Bouncy"), ("scratch", "Scratcher")]
COLOURS = ["black", "white", "grey", "gray", "blue", "green", "red", "yellow", "orange", "pink", "purple", "brown",
           "beige", "turquoise", "navy", "gold", "silver", "clear", "multi"]


def first_match(text, table, code):
    for rx, label in table:
        if re.search(rx, text, re.I) and vid(code, label):
            m = re.search(rx, text, re.I)
            return label, text[max(0, m.start() - 30): m.end() + 30].strip()
    return None, None


def colour_family(spec_colour):
    c = (spec_colour or "").lower().strip()
    if not c:
        return None
    if re.search(r"assorted|various|random", c):
        return "Color Varies" if vid("color-family", "Color Varies") else None
    found = [w for w in COLOURS if re.search(rf"\b{w}\b", c)]
    if len(found) >= 2 or "/" in c:
        return "Multi" if vid("color-family", "Multi") else None
    if found:
        w = {"gray": "grey"}.get(found[0], found[0])
        lab = {"grey": "Grey", "multi": "Multi", "navy": "Navy", "clear": "Clear"}.get(w, w.capitalize())
        return lab if vid("color-family", lab) else None
    return None


def ingredient_of(composition):
    if not composition:
        return None, None
    first = re.sub(r"\b(thereof|of which|including|incl\.)\s*", "", composition[0].split(",")[0], flags=re.I)
    generic = re.match(r"\s*(meat and animal derivatives|fish and fish derivatives|cereals|vegetable derivatives|"
                       r"vegetable protein extracts|derivatives of vegetable origin|milk and milk derivatives|oils and fats|"
                       r"meat and animal by-products|meat|fish|poultry)", first, re.I)
    cand = []
    m = re.search(r"\(([^)]*)\)", first)
    if generic and m:
        cand.append(re.sub(r"[\d.,% ]+(?=[a-z])", "", m.group(1), flags=re.I).strip())
    cand.append(re.sub(r"\(.*?\)", "", first).strip())
    for c in cand:
        c = re.sub(r"^\d+[.,]?\d*\s*%\s*", "", c).strip()
        for label in (c, c.rstrip("s"), c.split(" ")[0]):
            hit = {"salmon": "Salmon", "chicken": "Chicken", "beef": "Beef", "lamb": "Lamb", "duck": "Duck", "turkey": "Turkey",
                   "rabbit": "Rabbit", "pork": "Pork", "fish": "Fish", "tuna": "Tuna", "cod": "Cod", "potato": "Potatoes",
                   "potatoes": "Potatoes", "rice": "Rice", "wheat": "Wheat", "oats": "Oats", "peas": "Peas", "corn": "Corn",
                   "maize": "Corn", "cheese": "Cheese", "liver": "Liver", "ostrich": "Ostrich", "venison": "Venison",
                   "horse": "Horse", "goat": "Goat", "poultry": "Poultry", "sweet potato": "Sweet Potatoes"}.get(label.lower(), label)
            if vid("ingredient", hit):
                return hit, composition[0][:120]
    return None, composition[0][:120]


# ----------------------------------------------------------------- main ----
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--types", default="toys,treats,grooming,accessories,supplements,wet,litter")
    ap.add_argument("--out", default=os.path.join(CACHE, "trixie-plan.json"))
    ap.add_argument("--names", default=os.path.join(CACHE, "trixie-names.json"), help="fallback English names for pageless rows")
    a = ap.parse_args()
    types = set(a.types.split(","))

    rows = [r for r in json.load(open(os.environ.get("TODO_ROWS") or os.path.join(CACHE, "todo-rows.json"))) if r["Brand"] == "Trixie"]
    hafo = json.load(open(os.path.join(CACHE, "hafo-all.json")))
    catalogue = json.load(open(os.path.join(CACHE, "trixie-catalogue.json")))
    pages = json.load(open(os.path.join(CACHE, "trixie-todo-pages-parsed.json")))
    gallery = json.load(open(os.path.join(CACHE, "trixie-gallery-urls.json")))
    live = json.load(open(os.path.join(CACHE, "live-catalogue.json")))
    names = json.load(open(a.names)) if os.path.exists(a.names) else {}
    live_by_slug = {p["slug"]: (pid, p) for pid, p in live.items()}
    live_skus = {str(v["sku"]) for p in live.values() for v in p["variants"]}
    # official signal: a live product whose variant sits on the same trixie.de page
    # is THE product a new article of that page belongs to (rule 9, the 2026-09-12
    # dedup rule A); the name/slug rule below is only the fallback.
    tmap = os.path.join(CACHE, "dedup", "trixie-map.json")
    a2p_live = json.load(open(tmap))["a2p"] if os.path.exists(tmap) else {}
    live_by_page = {}
    for pid, p in live.items():
        for v in p["variants"]:
            u = a2p_live.get(str(v["sku"]))
            if u:
                live_by_page.setdefault(u.split("?")[0], pid)

    # article -> page (catalogue link, or a sibling page that lists it as a variant)
    art2page = {}
    for u, p in pages.items():
        for art in p.get("variants", {}):
            art2page.setdefault(art, u)
    for art, e in catalogue.items():
        if e["url"] in pages:
            art2page[art] = e["url"]

    unpriced, notfound, flagged, wanted, needs_name, needs_cat = [], [], [], collections.Counter(), [], []
    wanted_ev = {}
    groups = collections.OrderedDict()      # key -> list of prepared variants

    for r in rows:
        code = r["Article Code"].strip(); art = art_of(code)
        if art[:-1] in live_skus and len(art) >= 5 and art[:-1] == "4026":
            continue      # 40261Tx is hafo's TX 040261 = article 4026, already the 5 l variant of product 199
        inv = r["Product Name (as printed)"]; cost = int(float(r["Buy Price (AMD)"]))
        h = hafo.get(code) or {}
        cat_csv = r["Category"] or ""
        species_csv = (r["Species"] or "").lower()
        page = pages.get(art2page.get(art)) if art in art2page else None
        spec = (page or {}).get("variants", {}).get(art, {}) if page else {}

        # --- identity: Tx suffix or catalogue membership; hafo brand must not contradict
        is_tx = code.endswith(("Tx", "TXN"))
        hb = (h.get("brand") or "").upper()
        if not is_tx and art not in catalogue and not page:
            notfound.append({**r, "Note": f"no Tx suffix, not in trixie.de catalogue; hafo brand '{h.get('brand') or ''}' — not Trixie"})
            continue
        # --- price
        price, why, hafo_note = None, None, ""
        if register_price(code, cost):
            price = register_price(code, cost); hafo_note = "price: register"
        elif h.get("confirmed") and h.get("price_source") == "variant":
            p, w = h.get("price_amd"), h.get("wholesale_price_amd")
            if hb and hb != "TRIXIE" and w != cost:
                why = "wrong row"; hafo_note = f"hafo row {h.get('variant_sku')} is {h.get('brand')} '{(h.get('title_hy') or '')[:50]}'"
            elif not p or p <= cost:
                # only price > cost gates (rule 5); wholesale != cost is not a
                # reason to reject (user, 2026-09-23) — it still helps above, to
                # spot a non-Trixie row
                why = "wrong row"; hafo_note = f"hafo row {h.get('variant_sku')} price {p} at/below cost {cost} — '{(h.get('title_hy') or '')[:50]}'"
            else:
                price = int(p)
        elif h.get("hafo_id") and h.get("confirmed"):
            why = "on hafo, size missing"; hafo_note = f"listing '{(h.get('title_hy') or '')[:60]}' skus {h.get('skus')}"
        else:
            why = "not on hafo"
        # --- species / category
        path = (page or {}).get("path") or []
        species = species_csv if species_csv in ("dog", "cat", "dog & cat") else (path[0] if path else "")
        seg = path[2] if len(path) > 2 else (path[1] if len(path) > 1 else "")
        lowinv = inv.lower()
        ptype, cat_ids, toy_type = None, [], None
        both = species == "dog & cat"
        sp = "cat" if species.startswith("cat") else "dog"

        def pair(dog, cat):
            if both:
                return [dog, cat]
            return [cat if sp == "cat" else dog]

        if path and path[1] in ("toys", "toys-for-cats") or (not path and cat_csv == "Toys") or path[1:2] == ["training-sport"] and cat_csv == "Toys":
            if cat_csv == "Treats" or cat_csv == "Vitamins & supplements" and seg == "catnip-attractants":
                ptype = "treats" if cat_csv == "Treats" else "supplements"
            else:
                ptype = "toys"
        elif seg in ("dog-treats", "cat-treats", "chewing-items", "liver-pate-pastes", "supplementary-feed") or (not path and cat_csv in ("Treats", "Wet food")):
            ptype = "treats"
        elif path and path[1] == "care-health-cleaning" or (not path and cat_csv == "Grooming"):
            ptype = "grooming"
        elif path and path[1] == "cat-litter-tray" or re.search(KW[0][0], lowinv) and not path:
            ptype = "accessories"
        elif not path and cat_csv == "Cat litter":
            ptype = "litter"
        else:
            ptype = "accessories"
        ov = names.get(art, {})
        if ov.get("ptype"):
            ptype = ov["ptype"]
        if re.search(r"hiding place for tablets", (page or {}).get("name", ""), re.I):
            ptype = "treats"
        if cat_csv == "Vitamins & supplements" and ptype in ("grooming", "accessories"):
            ptype = "supplements" if re.search(r"vitamin|supplement|paste|tablet|drops|oil|malt|calcium|հավելում|վիտամին|մալթ|պաստա", (page or {}).get("name", "") + " " + lowinv, re.I) else ptype

        # category leaf
        if ptype == "toys":
            tt = TOY_TYPE.get(seg) or TOY_TYPE.get(path[1] if len(path) > 1 else "")
            ev = f"breadcrumb '{seg}'" if tt else ""
            if tt == "Mouse & Animal" and re.search(r"\bball", (page or {}).get("name", ""), re.I):
                tt = "Ball"
            if ov.get("toy_type"):
                tt, ev = ov["toy_type"], f"override: invoice '{inv[:40]}'"
            if not tt:
                for rx, t, mat in TOY_KW:
                    if re.search(rx, lowinv):
                        tt, ev = t, f"invoice name '{inv[:40]}'"; break
            if tt == "Catnip" and sp == "dog":
                tt = "Plush"
            leaf = TOY_LEAF.get(sp, {}).get(tt)
            if not leaf:
                needs_cat.append({**r, "Note": f"toy type undetermined (page {'yes' if page else 'no'}, seg '{seg}')"}); continue
            cat_ids, toy_type = [leaf], (tt, ev)
        elif ptype == "treats":
            chew = seg == "chewing-items" or re.search(r"ծամ|ոսկոր|chew|bone|antler|ear|rawhide", lowinv + " " + (page or {}).get("name", "").lower())
            cat_ids = pair(7 if chew else 6, 14)
        elif ptype == "grooming":
            key = seg
            if not key:
                for rx, k in KW:
                    if re.search(rx, lowinv):
                        key = {"shampoo": "shampoos", "brush": "brushes-combs", "tool": "trimmers", "paw": "claws-paws",
                               "ear": "ear", "teeth": "teeth", "eye": "eye", "litter-acc": "litter-acc"}.get(k, k); break
            nm = ((page or {}).get("name", "") + " " + lowinv).lower()
            if key == "teeth-ears-eyes" or key in ("ear", "teeth", "eye"):
                if re.search(r"\bear|ականջ", nm): cat_ids = pair(32, 39)
                elif re.search(r"eye|աչք", nm): cat_ids = pair(33, 40); flagged.append({"code": code, "what": "eye care filed under Skin Care (no Eye Care leaf)"})
                else: cat_ids = pair(30, 37); flagged.append({"code": code, "what": "dental care filed under Grooming Tools (no Dental Care leaf)"})
            elif key in ("dog-health", "cat-health"):
                if re.search(r"tick|flea|տիզ|լու", nm): cat_ids = pair(42, 51); ptype = "supplements"
                elif re.search(r"sock|pant|diaper|nappy|pad|bait|protection|boot|shoe|belly band|muzzle|collar|lint|roller|glove|blanket|mat\b", nm):
                    b = acc_bucket((page or {}).get("name", ""), seg, lowinv, species); cat_ids = [ACC_CAT[b]] if b else [13]; ptype = "accessories"
                elif re.search(r"tablet|pill|medic|դեղ|հաբ", nm) and not re.search(r"hiding", nm): cat_ids = pair(47, 55); ptype = "supplements"
                elif re.search(r"vitamin|supplement|paste|drops|oil|malt|calcium|powder|tabs|վիտամին|մալթ", nm): cat_ids = pair(43, 52); ptype = "supplements"
                else:
                    b = acc_bucket((page or {}).get("name", ""), seg, lowinv, species); cat_ids = [ACC_CAT[b]] if b else [13]; ptype = "accessories"
                    if not b: flagged.append({"code": code, "what": "dog/cat-health item filed under Accessories — check leaf"})
            elif key == "textile-cleaning" or key == "litter-acc":
                cat_ids = [78] if key == "textile-cleaning" else [67]; ptype = "accessories"
            elif key in GROOM_LEAF and GROOM_LEAF[key]:
                cat_ids = pair(*GROOM_LEAF[key])
            else:
                needs_cat.append({**r, "Note": f"grooming leaf undetermined ('{key}')"}); continue
        elif ptype == "supplements":
            nm = ((page or {}).get("name", "") + " " + lowinv).lower()
            if seg == "claws-paws": cat_ids = pair(31, 38); ptype = "grooming"
            elif seg == "catnip-attractants": cat_ids = [25]
            elif re.search(r"tick|flea|տիզ|լու", nm): cat_ids = pair(42, 51)
            elif re.search(r"digest|probiotic|մարս", nm): cat_ids = pair(44, 53)
            elif re.search(r"calm|relax|հանգստ", nm): cat_ids = pair(48, 56)
            elif re.search(r"\bear|ականջ", nm): cat_ids = pair(32, 39); ptype = "grooming"
            elif re.search(r"tooth|dental|teeth|ատամ", nm): cat_ids = pair(30, 37); ptype = "grooming"; flagged.append({"code": code, "what": "dental care filed under Grooming Tools (no Dental Care leaf)"})
            else: cat_ids = pair(43, 52)
        elif ptype == "litter":
            cat_ids = [65 if re.search(r"սիլիկ|silic|գրանուլ", lowinv) else 60]
        else:  # accessories
            if path and path[1] == "cat-litter-tray" or re.search(KW[0][0], lowinv):
                cat_ids = [67]
            elif seg == "supplementary-feed":
                cat_ids = pair(43, 52); ptype = "supplements"
            else:
                b = acc_bucket((page or {}).get("name", ""), seg, lowinv, species)
                cat_ids = [ACC_CAT[b]] if b else [13]
        if ov.get("cat_ids"):
            cat_ids = ov["cat_ids"]
        if ptype not in types:
            continue

        # --- name / label / texts
        if art in names and names[art].get("force"):
            name = names[art]["name"]; src = names[art].get("src") or (page["url"] if page else "fallback: hafo/invoice")
        elif page:
            name = clean_name(page["name"]); src = page["url"]
        elif art in names:
            name = names[art]["name"]; src = names[art].get("src") or "fallback: hafo/invoice"
        else:
            if not price:
                unpriced.append({"Article Code": code, "Brand": "Trixie", "Official Site": "not on trixie.de (no product page)", "Proposed Product Name": inv,
                                 "Proposed Variant": "", "Buy Price (AMD)": cost, "Sale Price (AMD)": "", "Qty": stock_of(r["Qty Received"]), "Species": species,
                                 "Invoice Name (as printed)": inv, "Why no price": why + (f" — {hafo_note}" if hafo_note else ""), "Status": "NOT imported — needs a sale price from you"})
                continue
            needs_name.append({**r, "hafo_title": h.get("title_hy"), "meta_keywords": h.get("meta_keywords"), "ptype": ptype, "cat_ids": cat_ids}); continue
        label = (names.get(art, {}).get("label") if (not page or names.get(art, {}).get("force")) else None) or label_from(spec, inv)
        bullets = list((page or {}).get("bullets", []))
        prose = (page or {}).get("prose", [])
        heading = (page or {}).get("info_heading", "")
        comp = (page or {}).get("composition", [])
        analytical = (page or {}).get("analytical", {})
        additives = (page or {}).get("additives", {})
        feeding = (page or {}).get("feeding", "")

        # --- attributes
        attrs, ev = {}, {}
        text_all = " ".join([heading] + bullets + prose).lower()
        family = None
        if ptype == "toys":
            family = 5
            tt, tev = toy_type
            attrs["toy-type"] = vid("toy-type", tt); ev["toy-type"] = tev
            for b in bullets:
                nb = b.lower().strip()
                for token, lab in MATERIAL:
                    if (nb.startswith(token) or nb == token) and vid("material", lab):
                        attrs["material"] = vid("material", lab); ev["material"] = b; break
                if "material" in attrs: break
            if ov.get("material") and vid("material", ov["material"]):
                attrs["material"] = vid("material", ov["material"]); ev["material"] = f"override: invoice '{inv[:40]}'"
            if "material" not in attrs and not page:
                for rx, t, mat in TOY_KW:
                    if re.search(rx, lowinv) and mat and vid("material", mat):
                        attrs["material"] = vid("material", mat); ev["material"] = f"invoice '{inv[:40]}'"; break
            lab, q = first_match(text_all, FEATURE, "toy-feature")
            if lab: attrs["toy-feature"] = vid("toy-feature", lab); ev["toy-feature"] = q
            sz = size_cm(inv) or (re.search(r"(\d+[.,]?\d*)\s*cm", spec.get("Measurements", "")) or [None, None])[1]
            if sz:
                sz = sz.replace(",", ".").rstrip("0").rstrip(".") if "." in sz else sz
                if vid("toy-size", f"{sz} cm"):
                    attrs["toy-size"] = vid("toy-size", f"{sz} cm"); ev["toy-size"] = f"size {sz} cm"
                else:
                    wanted[("toy-size", f"{sz} cm")] += 1; wanted_ev[("toy-size", f"{sz} cm")] = inv[:60]
            cf = colour_family(spec.get("Colour"))
            if cf: attrs["color-family"] = vid("color-family", cf); ev["color-family"] = f"Colour: {spec.get('Colour')}"
            if re.search(r"\bpuppy|junior", text_all + " " + name.lower()) and vid("lifestage", "Puppy"):
                attrs["lifestage"] = vid("lifestage", "Puppy"); ev["lifestage"] = "puppy"
            if re.search(r"\bkitten", text_all + " " + name.lower()) and vid("lifestage", "Kitten"):
                attrs["lifestage"] = vid("lifestage", "Kitten"); ev["lifestage"] = "kitten"
        elif ptype == "treats":
            family = 3
            wl = weight_label(spec, inv)
            if wl:
                if vid("product-weight", wl): attrs["product-weight"] = vid("product-weight", wl); ev["product-weight"] = wl
                else: wanted[("product-weight", wl)] += 1; wanted_ev[("product-weight", wl)] = name
            nm = name.lower()
            for w in FLAVOR_WORDS:
                if re.search(rf"\b{w}", nm):
                    lab = FLAVOR_MAP.get(w, w.title())
                    if vid("flavor", lab): attrs["flavor"] = vid("flavor", lab); ev["flavor"] = f"name '{name}'"
                    else: wanted[("flavor", lab)] += 1; wanted_ev[("flavor", lab)] = name
                    break
            ing, q = ingredient_of(comp)
            if ing: attrs["ingredient"] = vid("ingredient", ing); ev["ingredient"] = q
            lab, q = first_match(text_all + " " + nm, HEALTH, "health-feature")
            if lab: attrs["health-feature"] = vid("health-feature", lab); ev["health-feature"] = q
            lab, q = first_match(text_all, DIET, "special-diet")
            if lab: attrs["special-diet"] = vid("special-diet", lab); ev["special-diet"] = q
            if re.search(r"\bpuppy|junior", nm + " " + text_all) and vid("lifestage", "Puppy"): attrs["lifestage"] = vid("lifestage", "Puppy"); ev["lifestage"] = "puppy/junior"
            if re.search(r"\bkitten", nm + " " + text_all) and vid("lifestage", "Kitten"): attrs["lifestage"] = vid("lifestage", "Kitten"); ev["lifestage"] = "kitten"
            if re.search(r"\bsenior", nm) and vid("lifestage", "Senior"): attrs["lifestage"] = vid("lifestage", "Senior"); ev["lifestage"] = "senior (no age stated)"
            m = re.search(r"for (small|medium|large) dogs", text_all)
            if m and vid("breed-size", f"{m.group(1).title()} Breeds"): attrs["breed-size"] = vid("breed-size", f"{m.group(1).title()} Breeds"); ev["breed-size"] = m.group(0)
        elif ptype == "supplements":
            family = 4
            lab, q = first_match(name.lower() + " " + text_all, FORM, "product-form")
            if lab: attrs["product-form"] = vid("product-form", lab); ev["product-form"] = q
            lab, q = first_match(text_all + " " + name.lower(), HEALTH, "health-feature")
            if lab: attrs["health-feature"] = vid("health-feature", lab); ev["health-feature"] = q
            wl = weight_label(spec, inv)
            if wl and vid("product-weight", wl): attrs["product-weight"] = vid("product-weight", wl); ev["product-weight"] = wl
            elif wl: wanted[("product-weight", wl)] += 1; wanted_ev[("product-weight", wl)] = name
        elif ptype == "litter":
            wl = weight_label(spec, inv)
            if wl and vid("product-weight", wl): attrs["product-weight"] = vid("product-weight", wl); ev["product-weight"] = wl
        if ptype in ("accessories", "grooming"):
            # accessory variant axes (rule 9a): size 28 + color-family 15
            sz = acc_size(label)
            if sz:
                if vid("size", sz): attrs["size"] = vid("size", sz); ev["size"] = f"label '{label}'"
                else: wanted[("size", sz)] += 1; wanted_ev[("size", sz)] = f"{name} — {label}"
            cf = acc_colour(spec.get("Colour"), label)
            if cf:
                if vid("color-family", cf): attrs["color-family"] = vid("color-family", cf); ev["color-family"] = f"Colour: {spec.get('Colour') or label}"
                else: wanted[("color-family", cf)] += 1; wanted_ev[("color-family", cf)] = f"{name} — {label}"
        attrs = {k: v for k, v in attrs.items() if v}

        # --- texts
        keep = [b for b in bullets if not (ptype == "toys" and any(b.lower().startswith(t) for t, _ in MATERIAL))]
        about = ""
        if keep: about += "<ul>" + "".join(f"<li>{b}</li>" for b in keep) + "</ul>"
        about += "".join(f"<p>{p}</p>" for p in prose)
        ingr = ""
        if comp: ingr += "<p><strong>Composition:</strong> " + " ".join(comp) + "</p>"
        if analytical: ingr += "<p><strong>Analytical constituents:</strong> " + ", ".join(f"{k} {v}" for k, v in analytical.items()) + "</p>"
        if additives: ingr += "<p><strong>Additives:</strong> " + ", ".join(f"{k} {v}" for k, v in additives.items()) + "</p>"
        feed = f"<p>{feeding}</p>" if feeding else ""

        images = gallery.get(art, [])
        variant = {"sku": art, "code": code, "name": label or "", "pricing_type": "fixed", "price": price,
                   "cost_price": cost, "stock": stock_of(r["Qty Received"]), "images": images,
                   "attribute_value_ids": attrs, "about_this_item": about, "ingredient_information": ingr,
                   "feeding_instructions": feed, "_ev": ev, "_inv": inv, "_why": why, "_hafo": hafo_note, "_species": species}
        # grouping key: page for families with variant axes, else the row itself
        gkey = (art2page.get(art) if page else (f"name:{names[art]['name']}" if art in names else f"row:{art}"))
        if art in names and names[art].get("existing"):
            variant["_existing"] = int(names[art]["existing"])
        groups.setdefault(gkey, {"name": name, "ptype": ptype, "cat_ids": cat_ids, "family": family, "src": src, "rows": []})
        groups[gkey]["rows"].append(variant)

    # ---- sibling price fallback + split collisions + build products
    products, sibling = [], []
    slugs_used = collections.Counter()
    for gkey, g in groups.items():
        rows_ = g["rows"]
        priced = [v for v in rows_ if v["price"]]
        for v in rows_:
            if v["price"]:
                continue
            sibs = [s for s in priced if s["cost_price"] == v["cost_price"] and s["sku"] != v["sku"]]
            prices = sorted({s["price"] for s in sibs})
            if len(prices) == 1:
                v["price"] = prices[0]; v["_sibling"] = sibs[0]["sku"]
                sibling.append({"Article Code": v["code"], "Brand": "Trixie", "Product": g["name"], "Variant": v["name"],
                                "Buy Price (AMD)": v["cost_price"], "Sale Price (AMD)": v["price"], "Priced from (sibling code)": sibs[0]["code"],
                                "Sibling hafo price": sibs[0]["price"], "Why hafo had no price": v["_why"], "Date": "2026-09-10"})
            elif len(prices) > 1:
                v["_why"] = "sibling prices differ"; v["_hafo"] = "candidates " + ", ".join(f"{s['code']}={s['price']}" for s in sibs)
        keep = []
        for v in rows_:
            if v["price"]:
                keep.append(v)
            else:
                unpriced.append({"Article Code": v["code"], "Brand": "Trixie", "Official Site": g["src"], "Proposed Product Name": g["name"],
                                 "Proposed Variant": v["name"], "Buy Price (AMD)": v["cost_price"], "Sale Price (AMD)": "",
                                 "Qty": v["stock"], "Species": v["_species"], "Invoice Name (as printed)": v["_inv"],
                                 "Why no price": v["_why"] + (f" — {v['_hafo']}" if v["_hafo"] else ""), "Status": "NOT imported — needs a sale price from you"})
        if not keep:
            continue
        # split variants whose attribute combination collides (or single-variant types)
        buckets = []
        if g["family"] and len(keep) > 1:
            seen = {}
            need_pw = g["ptype"] in ("treats", "supplements") and any("product-weight" in v["attribute_value_ids"] for v in keep)
            for v in keep:
                k = json.dumps(v["attribute_value_ids"], sort_keys=True)
                if k in seen or not v["attribute_value_ids"] or (need_pw and "product-weight" not in v["attribute_value_ids"]):
                    buckets.append([v]); flagged.append({"code": v["code"], "what": f"split from '{g['name']}': attribute combination not distinct ({k})"})
                else:
                    seen[k] = v
            main = [v for v in keep if not any(v is b[0] for b in buckets)]
            buckets = ([main] if main else []) + buckets
        elif len(keep) > 1 and not g["family"]:
            # accessories: one product per page, variants told apart by size/colour
            seen = {}
            for v in keep:
                k = json.dumps(v["attribute_value_ids"], sort_keys=True)
                if k in seen or not v["attribute_value_ids"]:
                    buckets.append([v]); flagged.append({"code": v["code"], "what": f"split from '{g['name']}': attribute combination not distinct ({k})"})
                else:
                    seen[k] = v
            main = [v for v in keep if not any(v is b[0] for b in buckets)]
            buckets = ([main] if main else []) + buckets
        else:
            buckets = [keep]
        for bi, bucket in enumerate(buckets):
            name = g["name"]
            if bi > 0:
                lab = bucket[0]["name"]
                if lab and lab.lower() not in name.lower():
                    name = f"{name}, {lab}"
            base = "trixie-" + slugify(name)
            slug = base
            if slug in live_by_slug or slugs_used[base]:
                slug = f"{base}-{bucket[0]['sku']}"
            slugs_used[base] += 1
            existing = live_by_page.get((gkey or "").split("?")[0]) if not gkey.startswith(("row:", "name:")) else None
            if not existing:
                existing = next((v["_existing"] for v in bucket if v.get("_existing")), None)
            if not existing:
                existing = live_by_slug.get(base, (None,))[0] if base in live_by_slug and live_by_slug[base][1]["name"] == name else None
            variants = []
            for i, v in enumerate(sorted(bucket, key=lambda x: (x["name"] or ""))):
                variants.append({k: v[k] for k in ("sku", "name", "pricing_type", "price", "cost_price", "stock", "images",
                                                    "attribute_value_ids", "about_this_item", "ingredient_information", "feeding_instructions")}
                                | {"is_default": i == 0, "sort_order": i, "_ev": v["_ev"], "_inv": v["_inv"], "_code": v["code"], "_sibling": v.get("_sibling")})
            products.append({"slug": slug, "name": name, "category_ids": g["cat_ids"], "brand_id": BRAND,
                             "attribute_family_id": g["family"], "variants": variants, "source": g["src"], "ptype": g["ptype"],
                             **({"existing_id": int(existing)} if existing else {})})

    # single-variant products sharing a Name (sizes/colours of one line without a family): the label goes into the Name
    cnt = collections.Counter(p["name"] for p in products)
    live_names = {p["name"] for p in live.values()}
    used = collections.Counter()
    for p in products:
        if len(p["variants"]) == 1 and (cnt[p["name"]] > 1 or p["name"] in live_names) and not p.get("existing_id"):
            lab = p["variants"][0]["name"]
            if lab and lab.lower() not in p["name"].lower():
                p["name"] = f"{p['name']}, {lab}"
        base = "trixie-" + slugify(p["name"])
        used[base] += 1
        p["slug"] = base if used[base] == 1 and base not in live_by_slug else f"{base}-{p['variants'][0]['sku']}"
    dup = [n for n, c in collections.Counter(p["name"] for p in products).items() if c > 1]
    for n in dup:
        flagged.append({"code": ",".join(v["_code"] for p in products if p["name"] == n for v in p["variants"]), "what": f"duplicate product name '{n}' (differs only by article)"})
    # 13 Accessories is not a product category (absent from /categories?forProducts) — rows that only fit there are blocked
    blocked = [p for p in products if p["category_ids"] == [13]]
    products = [p for p in products if p["category_ids"] != [13]]
    out = {"products": products, "blocked_no_category": blocked, "unpriced": unpriced, "notfound": notfound, "flagged": flagged,
           "wanted": [{"attribute": k[0], "label": k[1], "count": n, "evidence": wanted_ev[k]} for k, n in wanted.most_common()],
           "needs_name": needs_name, "needs_category": needs_cat, "sibling": sibling}
    json.dump(out, open(a.out, "w"), ensure_ascii=False, indent=1)
    c = collections.Counter(p["ptype"] for p in products)
    print(f"products {len(products)} ({dict(c)}), variants {sum(len(p['variants']) for p in products)}, "
          f"unpriced {len(unpriced)}, notfound {len(notfound)}, needs_name {len(needs_name)}, needs_category {len(needs_cat)}, "
          f"sibling-priced {len(sibling)}, flagged {len(flagged)}, wanted {len(wanted)}", file=sys.stderr)


if __name__ == "__main__":
    main()
