#!/usr/bin/env python3
"""Plan the small-brand rows of the 2026-09-11 import (Comfy, Club 4 Paws,
Iv San Bernard, Beaphar, Rolf Club, Inspector, Gelmintal, Insectal, Cliny,
Mr. Fresh, Ok-Lock) -> .siruk-cache/small-plan.json for scripts/import-plan.py.

Hand-written mapping row -> official page (exact: Comfy/Neoterica image file
names carry the article code; Club 4 Paws / ISB / Beaphar: the brand's own
page for that exact product). Prices only from hafo; CSV price = cost.
Rows without an official page (Мяу, Kormell, Moor, Justin, Интеко, Dogman,
Pchelodar «Отидез форте», ISB perfumes) are reported, not planned.
"""
import json, os, re, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, ".siruk-cache")
MENU = json.load(open(os.path.join(ROOT, "reference/attribute-values.json")))
VAL = {code: {k.lower(): v for k, v in d["values"].items()} for code, d in MENU.items()}
ALIAS = {"product-weight": {"85 g": "85 gr"}}


def vid(code, label):
    label = ALIAS.get(code, {}).get(label, label)
    return VAL.get(code, {}).get((label or "").lower())


def A(**labels):
    out = {}
    for code, lab in labels.items():
        code = code.replace("_", "-")
        v = vid(code, lab)
        if v:
            out[code] = v
        else:
            WANTED[(code, lab)] += 1
    return out


WANTED = collections.Counter()
hafo = json.load(open(os.path.join(CACHE, "hafo-all.json")))
todo = {r["Article Code"].strip(): r for r in json.load(open(os.path.join(CACHE, "todo-rows.json")))}
neo = json.load(open(os.path.join(CACHE, "neoterica/pages.json")))
c4p = json.load(open(os.path.join(CACHE, "brands/club4paws-pages.json")))
isb = json.load(open(os.path.join(CACHE, "brands/isb-pages.json")))
comfy = json.load(open(os.path.join(CACHE, "brands/comfy-pages.json")))
NEO = "https://neoterica.ru/products/"
C4P = "https://club4paws.com/product/cats/"
ISB = "https://isbusa.com/product/"
products, unpriced, notfound, flagged, blocked = [], [], [], [], []
TR = {}          # english string -> [ru, hy] for the dictionary


def price_of(code):
    r = todo[code]; cost = int(float(r["Buy Price (AMD)"])); h = hafo.get(code) or {}
    p, w = h.get("price_amd"), h.get("wholesale_price_amd")
    if h.get("confirmed") and h.get("price_source") == "variant" and w == cost and p and p > cost:
        return int(p), cost, None
    why = "not on hafo" if not h.get("hafo_id") else ("on hafo, size missing" if h.get("price_source") != "variant" else f"wrong row (price {p}, wholesale {w} vs cost {cost})")
    return None, cost, why


def stock_of(code):
    q = int(float(todo[code]["Qty Received"] or 0) or 0)
    return 10 if q <= 1 else q


def neo_desc(u):
    p = neo.get(u, {}); t = p.get("text", ""); n = p.get("name", "")
    i = t.rfind(n)
    seg = t[i + len(n):] if i >= 0 else t
    for stop in ("ИМЕЮТСЯ ПРОТИВОПОКАЗАНИЯ", "Купить у Партнеров", "Задать вопрос"):
        j = seg.find(stop)
        if j > 0:
            seg = seg[:j]
    return seg.strip()[:700]


def add(code, brand_id, slug_prefix, name, label, cat_ids, family, attrs, images, about_en, about_ru, about_hy, src, ingr="", feed="", ptype="", extra_note=None):
    price, cost, why = price_of(code)
    r = todo[code]
    if not price:
        unpriced.append({"Article Code": code, "Brand": r["Brand"], "Official Site": src, "Proposed Product Name": name, "Proposed Variant": label,
                         "Buy Price (AMD)": cost, "Sale Price (AMD)": "", "Qty": stock_of(code), "Species": r["Species"], "Invoice Name (as printed)": r["Product Name (as printed)"],
                         "Why no price": why, "Status": "NOT imported — needs a sale price from you"})
        return
    if extra_note:
        flagged.append({"code": code, "what": extra_note})
    if about_en:
        TR[about_en] = [about_ru, about_hy]
    variant = {"sku": code, "name": label, "pricing_type": "fixed", "price": price, "cost_price": cost, "stock": stock_of(code), "images": images,
               "attribute_value_ids": attrs, "about_this_item": f"<p>{about_en}</p>" if about_en else "", "ingredient_information": ingr, "feeding_instructions": feed,
               "is_default": True, "sort_order": 0, "_code": code, "_inv": r["Product Name (as printed)"], "_ev": {}}
    products.append({"slug": slug_prefix + "-" + re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", name.lower())).strip("-"), "name": name, "category_ids": cat_ids,
                     "brand_id": brand_id, "attribute_family_id": family, "variants": [variant], "source": src, "ptype": ptype or "small"})


# ---------------------------------------------------------------- Comfy (28) — dog toys, family 5
for code, cf_code, name, label, leaf, tt, feat, colour, size in (
        ("19245AQ", "113303", "Mint Dental Rugby", "8 × 6.5 cm, pink", 21, "Chew & Dental", "Dental", "Pink", "8 cm"),
        ("19256AQ", "113314", "Snacky Strawberry", "7.5 × 6.5 cm, red", 22, "Activity & Intelligence", None, "Red", "7.5 cm"),
        ("19284AQ", "113373", "Snacky Ball", "ø 8.5 cm, green", 22, "Activity & Intelligence", None, "Green", "8.5 cm"),
        ("19449AQ", "113554", "Mint Dental Bone", "16.5 cm, green", 21, "Chew & Dental", "Dental", "Green", "16.5 cm"),
        ("30681AQ", "114329", "Strong Dog Hammer", "13.5 cm, red", 21, "Chew & Dental", "Tough Chewer", "Red", "13.5 cm")):
    e = comfy[cf_code]
    attrs = A(toy_type=tt, color_family=colour, toy_size=size)
    if feat:
        attrs.update(A(toy_feature=feat))
    about = {"113303": "Mint-scented dental rugby ball from the Comfy Snacky family: the textured surface cleans teeth while the dog chews and it can be filled with treats.",
             "113314": "Strawberry-shaped treat toy from the Comfy Snacky family: fill it with snacks and let the dog work them out.",
             "113373": "Textured ball from the Comfy Snacky family: can be filled with treats to keep the dog busy.",
             "113554": "Mint-scented dental bone from Comfy: the nubs massage the gums and help clean the teeth while chewing.",
             "114329": "Hammer-shaped toy from the Comfy Strong Dog line, made for active dogs with strong jaws."}[cf_code]
    about_ru = {"113303": "Мятный дентальный мяч для регби из семейства Comfy Snacky: рельефная поверхность чистит зубы во время жевания, игрушку можно наполнять лакомствами.",
                "113314": "Игрушка-клубника для лакомств из семейства Comfy Snacky: наполните её снеками и дайте собаке их добыть.",
                "113373": "Рельефный мяч из семейства Comfy Snacky: можно наполнять лакомствами, чтобы занять собаку.",
                "113554": "Мятная дентальная косточка Comfy: шипы массируют дёсны и помогают чистить зубы при жевании.",
                "114329": "Игрушка-молоток из линейки Comfy Strong Dog, созданной для активных собак с сильными челюстями."}[cf_code]
    about_hy = {"113303": "Անանուխի բույրով դենտալ ռեգբիի գնդակ Comfy Snacky ընտանիքից. ռելիեֆային մակերեսը մաքրում է ատամները ծամելիս, խաղալիքը կարելի է լցնել հյուրասիրություններով։",
                "113314": "Ելակի ձևով խաղալիք հյուրասիրությունների համար Comfy Snacky ընտանիքից. լցրեք այն նախուտեստներով և թողեք շանը դրանք հանել։",
                "113373": "Ռելիեֆային գնդակ Comfy Snacky ընտանիքից. կարելի է լցնել հյուրասիրություններով՝ շանը զբաղեցնելու համար։",
                "113554": "Անանուխի բույրով դենտալ ոսկոր Comfy-ից. ելուստները մերսում են լնդերը և օգնում մաքրել ատամները ծամելիս։",
                "114329": "Մուրճի ձևով խաղալիք Comfy Strong Dog շարքից, որը ստեղծված է ուժեղ ծնոտներով ակտիվ շների համար։"}[cf_code]
    add(code, 28, "comfy", name, label, [leaf], 5, attrs, e["images"], about, about_ru, about_hy, e["page"], ptype="toys")

# ---------------------------------------------------------------- Club 4 Paws (17) — cat wet, family 2
C4 = {"142495": ("z-indichkoiu-v-zhele-povnoratsionnii-konservovanii-korm-dlia-doroslikh-kotiv-2", "Turkey in Jelly 85 g", "Turkey", "Chunks in Jelly", "85 g", "Premium Adult Cat"),
      "142505": ("z-kachkoiu-v-sousi-povnoratsionnii-konservovanii-korm-dlia-doroslikh-kotiv-1", "Duck in Gravy 85 g", "Duck", "Chunks in Gravy", "85 g", "Premium Adult Cat"),
      "142515": ("club-4-paws-premium-with-rabbit-in-jelly-somplete-canned-pet-food-for-adult-cats", "Rabbit in Jelly 85 g", "Rabbit", "Chunks in Jelly", "85 g", "Premium Adult Cat"),
      "142525": ("club-4-paws-premium-with-chicken-in-gravy-somplete-canned-pet-food-for-adult-cats", "Chicken in Gravy 85 g", "Chicken", "Chunks in Gravy", "85 g", "Premium Adult Cat"),
      "142565": ("z-ialovichinoiu-v-zhele-povnoratsionnii-konservovanii-korm-dlia-doroslikh-koti-1", "Beef in Jelly 85 g", "Beef", "Chunks in Jelly", "85 g", "Premium Adult Cat"),
      "143015": ("club-4-paws-premium-with-veal-in-gravy-somplete-canned-pet-food-for-adult-cats", "Veal in Gravy 85 g", "Veal", "Chunks in Gravy", "85 g", "Premium Adult Cat"),
      "908935": ("club-4-paws-premium-sterilised-somplete-canned-pet-food-for-adult-sterilised-cats", "Chicken in Jelly 80 g", "Chicken", "Chunks in Jelly", "80 g", "Premium Sterilised Cat")}
groups = collections.OrderedDict()
for code, (slug, label, fl, tx, w, prod) in C4.items():
    u = C4P + ("club-4-paws-premium-" + slug if not slug.startswith("club-4-paws") else slug)
    pg = c4p.get(u) or {}
    price, cost, why = price_of(code)
    if not price:
        unpriced.append({"Article Code": code, "Brand": "Club 4 Paws", "Official Site": u, "Proposed Product Name": prod, "Proposed Variant": label, "Buy Price (AMD)": cost, "Sale Price (AMD)": "",
                         "Qty": stock_of(code), "Species": "Cat", "Invoice Name (as printed)": todo[code]["Product Name (as printed)"], "Why no price": why, "Status": "NOT imported — needs a sale price from you"})
        continue
    attrs = A(product_weight=w, lifestage="Adult", flavor=fl, texture=tx, packaging="Pouch")
    if prod.endswith("Sterilised Cat"):
        attrs.update(A(special_diet="Sterilised"))
    ing = re.search(r"\b(turkey|duck|rabbit|chicken|beef|veal)\b", pg.get("composition", ""), re.I)
    if ing:
        attrs.update(A(ingredient=ing.group(1).title()))
    ingr = (f"<p><strong>Composition:</strong> {pg['composition']}</p>" if pg.get("composition") else "") + (f"<p><strong>Analytical constituents:</strong> {pg['analytical']}</p>" if pg.get("analytical") else "")
    about = "Complete canned food for adult cats with chunks of meat in " + ("jelly" if "Jelly" in tx else "gravy") + f", rich in {fl.lower()}." if not prod.endswith("Sterilised Cat") else "Complete canned food for adult sterilised cats with chunks of chicken in jelly."
    TR[about] = [("Полнорационный консервированный корм для взрослых кошек с кусочками мяса в " + ("желе" if "Jelly" in tx else "соусе") + f", с {{'Turkey':'индейкой','Duck':'уткой','Rabbit':'кроликом','Chicken':'курицей','Beef':'говядиной','Veal':'телятиной'}}[fl]." if not prod.endswith("Sterilised Cat") else "Полнорационный консервированный корм для взрослых стерилизованных кошек с кусочками курицы в желе."),
                 ("Ամբողջական պահածոյացված կեր հասուն կատուների համար՝ մսի կտորներով " + ("ժելեում" if "Jelly" in tx else "սոուսում") + f", {{'Turkey':'հնդկահավով','Duck':'բադով','Rabbit':'ճագարով','Chicken':'հավով','Beef':'տավարով','Veal':'հորթի մսով'}}[fl]։" if not prod.endswith("Sterilised Cat") else "Ամբողջական պահածոյացված կեր հասուն ստերիլիզացված կատուների համար՝ հավի կտորներով ժելեում։")]
    TR[about] = [TR[about][0].replace("{'Turkey':'индейкой','Duck':'уткой','Rabbit':'кроликом','Chicken':'курицей','Beef':'говядиной','Veal':'телятиной'}[fl]", {'Turkey':'индейкой','Duck':'уткой','Rabbit':'кроликом','Chicken':'курицей','Beef':'говядиной','Veal':'телятиной'}[fl]),
                 TR[about][1].replace("{'Turkey':'հնդկահավով','Duck':'բադով','Rabbit':'ճագարով','Chicken':'հավով','Beef':'տավարով','Veal':'հորթի մսով'}[fl]", {'Turkey':'հնդկահավով','Duck':'բադով','Rabbit':'ճագարով','Chicken':'հավով','Beef':'տավարով','Veal':'հորթի մսով'}[fl])]
    v = {"sku": code, "name": label, "pricing_type": "fixed", "price": price, "cost_price": cost, "stock": stock_of(code), "images": pg.get("images", []),
         "attribute_value_ids": attrs, "about_this_item": f"<p>{about}</p>", "ingredient_information": ingr, "feeding_instructions": "", "_code": code, "_inv": todo[code]["Product Name (as printed)"], "_ev": {}}
    groups.setdefault(prod, []).append((v, u))
for prod, vs in groups.items():
    # veal has no flavor value -> split it off so the selector stays consistent
    main = [x for x in vs if "flavor" in x[0]["attribute_value_ids"]]; rest = [x for x in vs if "flavor" not in x[0]["attribute_value_ids"]]
    for bucket, suffix in (([main], ""), ([[x] for x in rest], " split")):
        for b in bucket:
            if not b:
                continue
            name = prod if b is main else f"{prod} {b[0][0]['name']}"
            if b is not main:
                flagged.append({"code": b[0][0]["sku"], "what": f"split from '{prod}': flavour value missing in the menu"})
            variants = []
            for i, (v, u) in enumerate(sorted(b, key=lambda x: x[0]["name"])):
                variants.append(dict(v, is_default=(i == 0), sort_order=i))
            products.append({"slug": "club-4-paws-" + re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-"), "name": name, "category_ids": [11], "brand_id": 17, "attribute_family_id": 2,
                             "variants": variants, "source": b[0][1], "ptype": "wet"})

# ---------------------------------------------------------------- Iv San Bernard (29) — grooming, no family
for code, slug, name, label, cats, en, ru, hy in (
        ("03168IVS", "lemon-limone-shampoo", "Traditional Line Lemon Shampoo for Short Coats, 300 ml", "300 ml", [29, 36],
         "Lemon shampoo from the Traditional Line, designed for genetically short-coated dogs and cats; use diluted 3:1.",
         "Шампунь Lemon из линии Traditional Line, разработанный для собак и кошек с генетически короткой шерстью; используется в разведении 3:1.",
         "Lemon շամպուն Traditional Line շարքից՝ նախատեսված գենետիկորեն կարճամազ շների և կատուների համար. օգտագործել 3:1 նոսրացմամբ։"),
        ("03174IVS", "green-apple-mela-verde-shampoo", "Traditional Line Green Apple Shampoo for Long Coats, 300 ml", "300 ml", [29, 36],
         "Green Apple shampoo from the Traditional Line, designed for long-coated dogs and cats; use diluted 3:1.",
         "Шампунь Green Apple из линии Traditional Line, разработанный для длинношёрстных собак и кошек; используется в разведении 3:1.",
         "Green Apple շամպուն Traditional Line շարքից՝ նախատեսված երկարամազ շների և կատուների համար. օգտագործել 3:1 նոսրացմամբ։"),
        ("03177IVS", "lemon-limone-conditioner-mask", "Traditional Line Lemon Conditioner for Short Coats, 300 ml", "300 ml", [29, 36],
         "Lemon conditioner mask from the Traditional Line, the pair of the Lemon shampoo for short-coated dogs and cats.",
         "Кондиционер-маска Lemon из линии Traditional Line — пара к шампуню Lemon для короткошёрстных собак и кошек.",
         "Lemon կոնդիցիոներ-դիմակ Traditional Line շարքից՝ Lemon շամպունի զույգը կարճամազ շների և կատուների համար։"),
        ("03183IVS", "green-apple-mela-verde-conditioner-mask", "Traditional Line Green Apple Conditioner for Long Coats, 300 ml", "300 ml", [29, 36],
         "Green Apple conditioner mask from the Traditional Line, the pair of the Green Apple shampoo for long-coated dogs and cats.",
         "Кондиционер-маска Green Apple из линии Traditional Line — пара к шампуню Green Apple для длинношёрстных собак и кошек.",
         "Green Apple կոնդիցիոներ-դիմակ Traditional Line շարքից՝ Green Apple շամպունի զույգը երկարամազ շների և կատուների համար։"),
        ("03681IVS", "protective-shield-shampoo", "Protective Shield Shampoo, 300 ml", "300 ml", [29, 36],
         "Protective Shield shampoo with eucalyptus and mint for any coat type, formulated to help keep parasites away.",
         "Шампунь Protective Shield с эвкалиптом и мятой для любого типа шерсти, помогающий отпугивать паразитов.",
         "Protective Shield շամպուն էվկալիպտով և անանուխով ցանկացած տեսակի մազածածկի համար, որն օգնում է հեռու պահել մակաբույծներին։"),
        ("03684IVS", "protective-conditioner-mask", "Protective Shield Conditioner, 300 ml", "300 ml", [29, 36],
         "Protective Shield conditioner mask with eucalyptus and mint for any coat type, the pair of the Protective Shield shampoo.",
         "Кондиционер-маска Protective Shield с эвкалиптом и мятой для любого типа шерсти — пара к шампуню Protective Shield.",
         "Protective Shield կոնդիցիոներ-դիմակ էվկալիպտով և անանուխով ցանկացած տեսակի մազածածկի համար՝ Protective Shield շամպունի զույգը։"),
        ("04115IVS", "h270-2-phase-equalizer-300-ml", "Atami H270 Two-Phase Detangling Spray Conditioner, 300 ml", "300 ml", [29, 36],
         "Two-phase leave-in spray conditioner from the Atami line: a brushing, scissoring and finishing spray that eases detangling.",
         "Двухфазный несмываемый спрей-кондиционер линии Atami: спрей для расчёсывания, стрижки и финиша, облегчающий распутывание.",
         "Երկփուլային չլվացվող սփրեյ-կոնդիցիոներ Atami շարքից՝ սանրման, խուզման և ավարտական մշակման սփրեյ, որը հեշտացնում է թնջուկների քանդումը։")):
    pg = isb.get(ISB + slug + "/", {})
    add(code, 29, "iv-san-bernard", name, label, cats, None, {}, pg.get("images", []), en, ru, hy, ISB + slug + "/", ptype="grooming",
        extra_note="feature image is the brand's group shot of the product's sizes — isbusa.com publishes no single-bottle packshot (needs-packshot)")
for code in ("05565IVS", "05566IVS"):
    r = todo[code]
    notfound.append({"Article Code": code, "Brand": "Iv San Bernard", "Invoice Name (as printed)": r["Product Name (as printed)"], "Buy Price (AMD)": r["Buy Price (AMD)"], "Qty": r["Qty Received"], "Species": r["Species"],
                     "Note": "hafo-priced, but the DIY 125 ml perfume line has no page on the brand's reachable site (isbusa.com lists other perfume lines; ivsanbernard.it is behind a CAPTCHA) — no official name/image"})


BEAPHAR_INGR = {
    "15185": "<p><strong>Composition:</strong> milk and milk derivatives, oils and fats, minerals.</p>"
             "<p><strong>Additives:</strong> vit. A 25000 IU, vit. B1 5 mg, vit. B2 3 mg, vit. B6 3 mg, vit. B12 60 µg, vit. C 100 mg, I (3b201) 0.25 mg, vit. D3 2000 IU, vit. E 130 IU, vit. K3 2.9 mg, biotin 50 µg, calcium D-pantothenate 10 mg, nicotinic acid 20 mg, DL-methionine 3000 mg, Fe (ferrous sulphate monohydrate) 80 mg, Mn (manganous sulphate monohydrate) 30 mg, Se (sodium selenite) 0.2 mg, Zn (3b605) 50 mg, antioxidants.</p>"
             "<p><strong>Analytical constituents:</strong> crude protein 24 %, crude fibre 0 %, crude fat 24 %, crude ash 7 %, moisture 3.5 %, calcium 0.8 %, phosphorus 0.7 %, sodium 0.5 %, magnesium 0.16 %, potassium 1.5 %, docosahexaenoic acid (DHA) 0.1 %.</p>",
    "15186": "<p><strong>Composition:</strong> milk and milk derivatives, oils and fats, minerals, algae.</p>"
             "<p><strong>Additives:</strong> antioxidants, vit. A 25000 IU, vit. B1 5 mg, vit. B2 3 mg, vit. B6 3 mg, vit. B12 60 µg, vit. C 620 mg, vit. D3 2000 IU, vit. E 210 IU, biotin 50 µg, vit. K3 3 mg, taurine 3000 mg, calcium D-pantothenate 10 mg, nicotinic acid 20 mg.</p>"
             "<p><strong>Analytical constituents:</strong> crude protein 32 %, crude fat 24 %, crude ash 7 %, moisture 3.5 %, calcium 0.8 %, phosphorus 0.7 %, sodium 0.5 %, magnesium 0.16 %, potassium 1.5 %, DHA 0.1 %.</p>"}
BEAPHAR_FEED = {
    "15185": ["Always fully read the product label before use.",
              "Using the scoop provided, add Beaphar Lactol Puppy Milk to warm water (allow boiled water to cool before use) and stir until completely dissolved. Allow to cool until lukewarm (38 °C or blood temperature).",
              "The use of proper feeding equipment is highly recommended, such as the Beaphar Feeding Set or Beaphar Feeding Syringes. These should always be clean and sterile.",
              "Beaphar Lactol can also be mixed with cold water for older dogs. Prepared Beaphar Lactol can be refrigerated for 24 hours but should be reheated to 38 °C or blood temperature before feeding to young animals.",
              "Complete diet for un-weaned puppies: it is important to weigh young puppies on a daily basis so that you can compare their daily growth increase with the growth tables from your breeder or vet.",
              "Recommended dilution: add 7 level scoops to 100 ml warm water. 1 litre of prepared Beaphar Lactol Puppy Milk contains approximately 1250 kcal. The volume per day must be split across the recommended number of feeds per day.",
              "Feeding guide: 250 g puppy (2–14 days) 100 ml per day in 6–8 feeds; 500 g (15–21 days) 160 ml in 6 feeds; 1 kg (22–28 days) 250 ml in 6 feeds; 2 kg (29–35 days) 400 ml in 4–6 feeds; 5 kg (36–42 days) 900 ml in 2–6 feeds.",
              "After the 28th day, slowly change to a more solid diet, i.e. puppy food. Mix prepared Beaphar Lactol with a small amount of puppy food, gradually decreasing the volume of milk and increasing the amount of solid food each day.",
              "Complementary feeding (in addition to their normal food): puppies below 8 weeks up to 40 ml per kg in addition to their mother's milk; weaned puppies over 8 weeks, adult dogs during pregnancy or lactation, sick or convalescent: 11 ml per kg."],
    "15186": ["Always fully read the product label before use.",
              "Using the scoop provided, add Beaphar Lactol Kitten Milk to warm water (allow boiled water to cool before use) and stir until completely dissolved. Allow to cool until lukewarm (38 °C or blood temperature).",
              "The use of proper feeding equipment is highly recommended, such as the Beaphar Feeding Set or Beaphar Feeding Syringes. These should always be clean and sterile.",
              "Beaphar Lactol can also be mixed with cold water for older cats. Prepared Beaphar Lactol Kitten Milk can be refrigerated for 24 hours but should be reheated to 38 °C or blood temperature before feeding to young animals.",
              "Complete diet for un-weaned kittens: it is important to weigh young kittens on a daily basis so that you can compare their daily growth increase with the growth tables from your breeder or vet.",
              "Recommended dilution: add 7 level scoops to 100 ml warm water. 1 litre of prepared Beaphar Lactol Kitten Milk contains approximately 1250 kcal. The volume per day must be split across the recommended number of feeds per day.",
              "Feeding guide: 100 g kitten (2–7 days) 50 ml per day in 6–12 feeds; 200 g (8–21 days) 80 ml in 8 feeds; 400 g (22–28 days) 135 ml in 6–8 feeds; 600 g (29–35 days) 180 ml in 4–6 feeds; 1 kg (36–42 days) 250 ml in 3 feeds.",
              "After the 36th day, slowly change to a more solid diet, i.e. kitten food. Mix prepared Beaphar Lactol Kitten Milk with a small amount of kitten food, gradually decreasing the volume of milk and increasing the amount of solid food each day.",
              "Complementary feeding (in addition to their normal food): kittens below 6 weeks up to 40 ml per kg in addition to their mother's milk; weaned or weaning kittens over 6 weeks, adult cats during pregnancy or lactation, sick or convalescent: 13 ml per kg."]}
# ---------------------------------------------------------------- Beaphar (30) — milk replacers, family 4
for code, art, name, label, cats, ls, en, ru, hy in (
        ("15247", "15185", "Lactol Puppy Milk, 250 g", "250 g", [43], "Puppy",
         "Beaphar Lactol Puppy Milk is a milk replacer formulated to mimic maternal milk, enriched with DHA and vitamins A, B6, B12 and D, for hand-rearing and supplementing puppies.",
         "Beaphar Lactol Puppy Milk — заменитель молока, максимально приближенный к материнскому, обогащённый DHA и витаминами A, B6, B12 и D, для выкармливания и докармливания щенков.",
         "Beaphar Lactol Puppy Milk-ը կաթի փոխարինիչ է՝ մշակված մայրական կաթին առավելագույնս նմանվելու համար, հարստացված DHA-ով և A, B6, B12 և D վիտամիններով՝ շան ձագերին կերակրելու և լրացուցիչ սնուցելու համար։"),
        ("15248", "15186", "Lactol Kitten Milk, 250 g", "250 g", [52], "Kitten",
         "Beaphar Lactol Kitten Milk is a milk replacer formulated to mimic maternal milk, enriched with DHA, taurine and vitamins A, B6, B12 and D, for hand-rearing and supplementing kittens.",
         "Beaphar Lactol Kitten Milk — заменитель молока, максимально приближенный к материнскому, обогащённый DHA, таурином и витаминами A, B6, B12 и D, для выкармливания и докармливания котят.",
         "Beaphar Lactol Kitten Milk-ը կաթի փոխարինիչ է՝ մշակված մայրական կաթին առավելագույնս նմանվելու համար, հարստացված DHA-ով, տաուրինով և A, B6, B12 և D վիտամիններով՝ կատվի ձագերին կերակրելու և լրացուցիչ սնուցելու համար։")):
    h = open(os.path.join(CACHE, "brands", f"beaphar-{art}.html"), encoding="utf-8", errors="ignore").read()
    og = re.search(r'property="og:image"\s+content="([^"]+)"', h)
    attrs = A(product_form="Powder", health_feature="Milk Replacer", product_weight="250 g", lifestage=ls)
    # beaphar.com "Composition" tab (Ingredients / Additives / Analysis) — copied from the page, "Read more" UI text dropped
    ingr = BEAPHAR_INGR[art]
    feed = "".join(f"<p>{x}</p>" for x in BEAPHAR_FEED[art])
    add(code, 30, "beaphar", name, label, cats, 4, attrs, [og.group(1)] if og else [], en, ru, hy, f"https://www.beaphar.com/product/{art}-lactol-{'puppy' if ls == 'Puppy' else 'kitty'}-milk",
        ingr=ingr, feed=feed, ptype="supplements",
        extra_note="filed under Vitamins & Supplements — no Milk Replacer / Puppy Milk leaf in the tree")

# ---------------------------------------------------------------- Neoterica brands — family 4, Russian page text as the ru description
def neo_add(code, brand_id, prefix, slug, name, label, cats, attrs, en, hy, note=None):
    u = NEO + slug; p = neo.get(u)
    if not p:
        flagged.append({"code": code, "what": f"neoterica page {slug} not fetched"}); return
    ru = neo_desc(u)
    en = f"{name}. {en}"; hy = f"{name}. {hy}"          # unique per product: the dictionary is keyed by the English text
    add(code, brand_id, prefix, name, label, cats, 4, attrs, p.get("images", []), en, ru or en, hy, u, ptype="supplements", extra_note=note)


RC, INS, GEL, INSE, CLI = 22, 23, 24, 25, 26
AP = "Anti-Parasitic"
# Rolf Club 3D
for code, slug, name, label, cats, form in (
        ("071582", "rolfclub-3d-oshejnik-dlya-srednih-sobak-65-sm", "3D Flea & Tick Collar for Medium Dogs, 65 cm", "65 cm", [42], "Collar"),
        ("071622", "rolfclub-3d-oshejnik-dlya-shhenkov-i-melk-sobak-40-sm", "3D Flea & Tick Collar for Puppies and Small Dogs, 40 cm", "40 cm", [42], "Collar"),
        ("072092", "rolfclub-3d-oshejnik-dlya-krupnyh-sobak-75-sm", "3D Flea & Tick Collar for Large Dogs, 75 cm", "75 cm", [42], "Collar"),
        ("071832", "rolfclub-3d-kapli-dlya-sobak-4-10-kg-0-8-ml", "3D Flea & Tick Drops for Dogs 4–10 kg", "4–10 kg, 0.8 ml", [42], "Liquid"),
        ("071842", "rolfclub-3d-kapli-dlya-sobak-10-20-kg-1-5-ml", "3D Flea & Tick Drops for Dogs 10–20 kg", "10–20 kg, 1.5 ml", [42], "Liquid"),
        ("072582", "rolfclub-3d-kapli-dlya-sobak-40-60-kg-4-ml", "3D Flea & Tick Drops for Dogs 40–60 kg", "40–60 kg, 4 ml", [42], "Liquid"),
        ("071862", "rolfclub-3d-kapli-dlya-koshek-do-4-kg-0-5-ml", "3D Flea & Tick Drops for Cats up to 4 kg", "up to 4 kg, 0.5 ml", [51], "Liquid"),
        ("075302", "rolfclub-3d-kapli-dlya-koshek-bolee-8-15-kg-1-5-ml", "3D Flea & Tick Drops for Cats 8–15 kg", "8–15 kg, 1.5 ml", [51], "Liquid"),
        ("072012", "rolfclub-3d-sprej-dlya-sobak-200-ml", "3D Flea & Tick Spray for Dogs, 200 ml", "200 ml", [42], "Spray"),
        ("072022", "rolfclub-3d-sprej-dlya-koshek-200-ml", "3D Flea & Tick Spray for Cats, 200 ml", "200 ml", [51], "Spray")):
    kind = {"Collar": "collar", "Liquid": "spot-on drops", "Spray": "spray"}[form]
    en = f"Rolf Club 3D {kind} against ticks, fleas and other insects: triple protection that kills existing parasites and repels new ones."
    hy = f"Rolf Club 3D {{'collar':'վզկապ','spot-on drops':'կաթիլներ','spray':'սփրեյ'}}[kind] տզերի, լվերի և այլ միջատների դեմ. եռակի պաշտպանություն, որը ոչնչացնում է առկա մակաբույծներին և վանում նորերին։".replace("{'collar':'վզկապ','spot-on drops':'կաթիլներ','spray':'սփրեյ'}[kind]", {'collar': 'վզկապ', 'spot-on drops': 'կաթիլներ', 'spray': 'սփրեյ'}[kind])
    neo_add(code, RC, "rolf-club", slug, name, label, cats, A(product_form=form, health_feature=AP), en, hy)
for code, slug, name, label, cats in (
        ("070932", "sekskontrol-tabletki-dlya-koshek-10sht", "SexControl Tablets for Female Cats, 10 tablets", "10 tablets", [55]),
        ("070952", "sekskontrol-tabletki-dlya-kotov-10sht", "SexControl Tablets for Male Cats, 10 tablets", "10 tablets", [55]),
        ("071502", "sekskontrol-kapli-dlya-koshek-3-ml", "SexControl Drops for Female Cats, 3 ml", "3 ml", [55]),
        ("071522", "sekskontrol-kapli-dlya-kotov-3-ml", "SexControl Drops for Male Cats, 3 ml", "3 ml", [55]),
        ("075742", "sekskontrol-tabletki-dlya-suk-i-kobelej-10-tab", "SexControl Tablets for Dogs, 10 tablets", "10 tablets", [47])):
    form = "Tablet" if "Tablets" in name else "Liquid"
    en = "SexControl hormonal preparation for regulating sexual heat and related behaviour; veterinary product, follow the instructions."
    hy = "SexControl հորմոնային պատրաստուկ սեռական հոսքի և հարակից վարքի կարգավորման համար. անասնաբուժական արտադրանք, հետևեք հրահանգներին։"
    neo_add(code, RC, "rolf-club", slug, name, label, cats, A(product_form=form, health_feature="Hormone Support"), en, hy,
            note="invoice and hafo name it 'Rolf Club'; neoterica.ru lists SexControl as its own line — filed under brand Rolf Club as invoiced")
# Inspector
for code, slug, name, label, cats, form, en, hy in (
        ("073242", "inspector-oshejnik-dlya-srednih-sobak-65-sm", "Flea & Tick Collar for Medium Dogs, 65 cm", "65 cm", [42], "Collar",
         "Inspector collar protecting dogs against ticks, fleas and helminths.", "Inspector վզկապ, որը պաշտպանում է շներին տզերից, լվերից և ճիճուներից։"),
        ("075772", "inspector-oshejnik-dlya-melkih-sobak-40-sm", "Flea & Tick Collar for Small Dogs, 40 cm", "40 cm", [42], "Collar",
         "Inspector collar protecting small dogs against ticks, fleas and helminths.", "Inspector վզկապ, որը պաշտպանում է փոքր շներին տզերից, լվերից և ճիճուներից։"),
        ("075112", "inspector-mini-kapli-dlya-koshek-i-sobak-0-5-2-kg", "Mini Drops for Cats and Dogs 0.5–2 kg", "0.5–2 kg", [42, 51], "Liquid",
         "Inspector Mini spot-on drops for cats and dogs of 0.5–2 kg: protection against 20 kinds of external and internal parasites.", "Inspector Mini կաթիլներ 0,5–2 կգ կատուների և շների համար. պաշտպանություն 20 տեսակի արտաքին և ներքին մակաբույծներից։"),
        ("077562", "-kaplidyoshenctr14g", "Quadro Drops for Cats 1–4 kg", "1–4 kg", [51], "Liquid",
         "Inspector Quadro spot-on drops for cats of 1–4 kg: insectoacaricide and anthelmintic against 20 kinds of parasites.", "Inspector Quadro կաթիլներ 1–4 կգ կատուների համար. ինսեկտոակարիցիդ և հակաճիճվային միջոց 20 տեսակի մակաբույծների դեմ։"),
        ("077572", "-kaplidyoshenctr48g", "Quadro Drops for Cats 4–8 kg", "4–8 kg", [51], "Liquid",
         "Inspector Quadro spot-on drops for cats of 4–8 kg: insectoacaricide and anthelmintic against 20 kinds of parasites.", "Inspector Quadro կաթիլներ 4–8 կգ կատուների համար. ինսեկտոակարիցիդ և հակաճիճվային միջոց 20 տեսակի մակաբույծների դեմ։"),
        ("077592", "-kaplidysobnectr14g", "Quadro Drops for Dogs 1–4 kg", "1–4 kg", [42], "Liquid",
         "Inspector Quadro spot-on drops for dogs of 1–4 kg: insectoacaricide and anthelmintic against 20 kinds of parasites.", "Inspector Quadro կաթիլներ 1–4 կգ շների համար. ինսեկտոակարիցիդ և հակաճիճվային միջոց 20 տեսակի մակաբույծների դեմ։"),
        ("077602", "-kaplidysobnectr410g", "Quadro Drops for Dogs 4–10 kg", "4–10 kg", [42], "Liquid",
         "Inspector Quadro spot-on drops for dogs of 4–10 kg: insectoacaricide and anthelmintic against 20 kinds of parasites.", "Inspector Quadro կաթիլներ 4–10 կգ շների համար. ինսեկտոակարիցիդ և հակաճիճվային միջոց 20 տեսակի մակաբույծների դեմ։"),
        ("077612", "inspector-kapli-dlya-sobak-10-25-kg-2-5-ml", "Quadro Drops for Dogs 10–25 kg", "10–25 kg, 2.5 ml", [42], "Liquid",
         "Inspector Quadro spot-on drops for dogs of 10–25 kg: insectoacaricide and anthelmintic against 20 kinds of parasites.", "Inspector Quadro կաթիլներ 10–25 կգ շների համար. ինսեկտոակարիցիդ և հակաճիճվային միջոց 20 տեսակի մակաբույծների դեմ։"),
        ("077632", "inspector-kapli-dlya-sobak-40-60-kg-6-ml", "Quadro Drops for Dogs 40–60 kg", "40–60 kg, 6 ml", [42], "Liquid",
         "Inspector Quadro spot-on drops for dogs of 40–60 kg: insectoacaricide and anthelmintic against 20 kinds of parasites.", "Inspector Quadro կաթիլներ 40–60 կգ շների համար. ինսեկտոակարիցիդ և հակաճիճվային միջոց 20 տեսակի մակաբույծների դեմ։"),
        ("077922", "ushnie-kaplctor", "Ear Drops for Dogs and Cats, 10 ml", "10 ml", [32, 39], "Liquid",
         "Inspector insecticidal ear drops for dogs and cats against ear mites.", "Inspector ինսեկտիցիդային ականջի կաթիլներ շների և կատուների համար՝ ականջի տզերի դեմ։"),
        ("077982", "tableki-dyosh052l", "Quadro Tabs for Cats and Dogs 0.5–2 kg", "0.5–2 kg", [46, 55], "Tablet",
         "Inspector Quadro tablets for cats and dogs of 0.5–2 kg against external and internal parasites.", "Inspector Quadro հաբեր 0,5–2 կգ կատուների և շների համար՝ արտաքին և ներքին մակաբույծների դեմ։"),
        ("077992", "tableki-dyosh28g", "Quadro Tabs for Cats and Dogs 2–8 kg", "2–8 kg", [46, 55], "Tablet",
         "Inspector Quadro tablets for cats and dogs of 2–8 kg against external and internal parasites.", "Inspector Quadro հաբեր 2–8 կգ կատուների և շների համար՝ արտաքին և ներքին մակաբույծների դեմ։"),
        ("078002", "tableki-dyosh816g", "Quadro Tabs for Cats and Dogs 8–16 kg", "8–16 kg", [46, 55], "Tablet",
         "Inspector Quadro tablets for cats and dogs of 8–16 kg against external and internal parasites.", "Inspector Quadro հաբեր 8–16 կգ կատուների և շների համար՝ արտաքին և ներքին մակաբույծների դեմ։"),
        ("078012", "tableki-so16g", "Quadro Tabs for Dogs over 16 kg", "over 16 kg", [46], "Tablet",
         "Inspector Quadro tablets for dogs over 16 kg against external and internal parasites.", "Inspector Quadro հաբեր 16 կգ-ից բարձր շների համար՝ արտաքին և ներքին մակաբույծների դեմ։")):
    hf = "Ear Mite Treatment" if "Ear" in name else AP
    neo_add(code, INS, "inspector", slug, name, label, cats, A(product_form=form, health_feature=hf), en, hy,
            note="cat dewormers filed under Pharmacy & Prescriptions — the cat tree has no Dewormers leaf" if 55 in cats else None)
# Gelmintal
for code, slug, name, label, cats, form in (
        ("073452", "gelmintal-spot-on-dlya-koshek-do-4-kg-0-4-ml", "Spot-on for Cats up to 4 kg", "up to 4 kg, 0.4 ml", [55], "Liquid"),
        ("073722", "gelmintal-spot-on-dlya-koshek-4-10-kg-1-ml", "Spot-on for Cats 4–10 kg", "4–10 kg, 1 ml", [55], "Liquid"),
        ("074302", "gelmintal-spot-on-dlya-shhenkov-i-sobak-do-10-kg-2-pipetki-po-0-5-ml", "Spot-on for Puppies and Dogs up to 10 kg", "up to 10 kg, 2 × 0.5 ml", [46], "Liquid"),
        ("074312", "gelmintal-spot-on-dlya-sobak-bolee-10-kg-2-pipetki-po-2-5-ml", "Spot-on for Dogs over 10 kg", "over 10 kg, 2 × 2.5 ml", [46], "Liquid"),
        ("074022", "gelmintal-sirop-dlya-kotyat-i-koshek-menee-4-kg-5-ml", "Syrup for Kittens and Cats under 4 kg, 5 ml", "5 ml", [55], "Liquid"),
        ("074052", "gelmintal-sirop-dlya-koshek-bolee-4-kg-5-ml", "Syrup for Cats over 4 kg, 5 ml", "5 ml", [55], "Liquid"),
        ("074042", "gelmintal-sirop-dlya-shhenkov-i-sobak-menee-10-kg-10-ml", "Syrup for Puppies and Dogs under 10 kg, 10 ml", "10 ml", [46], "Liquid"),
        ("074032", "gelmintal-sirop-dlya-sobak-bolee-10-kg-10-ml", "Syrup for Dogs over 10 kg, 10 ml", "10 ml", [46], "Liquid"),
        ("074072", "tableki-gmn", "Tablets for Kittens and Cats up to 4 kg, 2 tablets", "2 tablets", [55], "Tablet"),
        ("074082", "tableki-gmndyosh4", "Tablets for Cats over 4 kg, 2 tablets", "2 tablets", [55], "Tablet"),
        ("074092", "tableki-gmndyschov102", "Tablets for Puppies and Dogs under 10 kg, 2 tablets", "2 tablets", [46], "Tablet"),
        ("074102", "tableki-gmndyso102h", "Tablets for Dogs over 10 kg, 2 tablets", "2 tablets", [46], "Tablet"),
        ("078362", "gel-mintasropdychkv10", "Mini Syrup for Puppies and Kittens, 10 ml", "10 ml", [46, 55], "Liquid"),
        ("792732", "gel-mintabs", "Mini Tabs for Puppies, Kittens and Small Breeds, 10 tablets", "10 tablets", [46, 55], "Tablet")):
    en = "Gelmintal broad-spectrum dewormer (moxidectin + praziquantel) against round and tape worms; veterinary product, follow the dosage on the pack."
    hy = "Gelmintal լայն սպեկտրի հակաճիճվային միջոց (մոքսիդեկտին + պրազիկվանտել) կլոր և ժապավենաձև որդերի դեմ. անասնաբուժական արտադրանք, հետևեք փաթեթի չափաբաժնին։"
    neo_add(code, GEL, "gelmintal", slug, name, label, cats, A(product_form=form, health_feature=AP), en, hy,
            note="cat dewormer filed under Pharmacy & Prescriptions — the cat tree has no Dewormers leaf" if 55 in cats else None)
# Insectal
for code, slug, name, label, cats in (
        ("073652", "insektal-kapli-dlya-koshek-i-sobak-ot-2-do4-kg-0-5-ml", "Flea & Tick Drops for Cats and Dogs 2–4 kg", "2–4 kg, 0.5 ml", [42, 51]),
        ("073662", "insektal-kapli-dlya-sobak-ot-4-do-10-kg-0-8-ml", "Flea & Tick Drops for Cats and Dogs 4–10 kg", "4–10 kg, 0.8 ml", [42, 51]),
        ("073672", "insektal-kapli-dlya-sobak-10-20-kg-1-5-ml", "Flea & Tick Drops for Dogs 10–20 kg", "10–20 kg, 1.5 ml", [42]),
        ("073692", "insektal-kapli-dlya-sobak-40-60-kg-4-3-ml", "Flea & Tick Drops for Dogs 40–60 kg", "40–60 kg, 4.3 ml", [42]),
        ("791832", "insektal-kombo-kapli-dlya-koshek-1-4kg", "Combo Drops for Cats 1–4 kg", "1–4 kg", [51]),
        ("791842", "-insektalombpdyh410g", "Combo Drops for Cats 4–8 kg", "4–8 kg", [51]),
        ("791852", "-insektalombpdy14g", "Combo Drops for Dogs 1–4 kg", "1–4 kg", [42]),
        ("791862", "kapli-dysobnetm4g", "Combo Drops for Dogs 4–10 kg", "4–10 kg", [42]),
        ("791872", "kapli-dysobnetm14g", "Combo Drops for Dogs 10–25 kg", "10–25 kg", [42])):
    combo = "Combo" in name
    en = ("Insectal Combo spot-on drops: protection against ticks, fleas and helminths in one pipette." if combo else "Insectal spot-on drops against ticks, fleas and lice: an affordable insectoacaricide for regular protection.")
    hy = ("Insectal Combo կաթիլներ. պաշտպանություն տզերից, լվերից և ճիճուներից մեկ պիպետով։" if combo else "Insectal կաթիլներ տզերի, լվերի և ոջիլների դեմ. մատչելի ինսեկտոակարիցիդ կանոնավոր պաշտպանության համար։")
    neo_add(code, INSE, "insectal", slug, name, label, cats, A(product_form="Liquid", health_feature=AP), en, hy)
# Cliny
for code, slug, name, label, cats, fam_attrs, en, hy, note in (
        ("073502", "cliny-zubnoj-gel-75-ml", "Dental Gel with Silver Ions, 75 ml", "75 ml", [30, 37], A(product_form="Gel", health_feature="Dental & Breath Care"),
         "Cliny dental gel with silver ions for dogs and cats: cleans teeth, freshens breath and helps prevent plaque.", "Cliny ատամի գել արծաթի իոններով շների և կատուների համար. մաքրում է ատամները, թարմացնում շնչառությունը և օգնում կանխել փառը։", "dental care filed under Grooming Tools (no Dental Care leaf)"),
        ("073532", "cliny-zhidkost-dlya-polosti-rta-300-ml", "Oral Care Liquid with Silver Ions, 300 ml", "300 ml", [30, 37], A(product_form="Liquid", health_feature="Dental & Breath Care"),
         "Cliny oral care liquid with silver ions, added to drinking water to freshen breath and support oral hygiene.", "Cliny բերանի խոռոչի հեղուկ արծաթի իոններով, ավելացվում է խմելու ջրին՝ շնչառությունը թարմացնելու և բերանի հիգիենային աջակցելու համար։", "dental care filed under Grooming Tools (no Dental Care leaf)"),
        ("074282", "cliny-sprej-dlya-polosti-rta-100-ml", "Oral Care Spray with Silver Ions, 100 ml", "100 ml", [30, 37], A(product_form="Spray", health_feature="Dental & Breath Care"),
         "Cliny oral care spray with silver ions: sprayed on the teeth and gums to freshen breath and help prevent plaque.", "Cliny բերանի խոռոչի սփրեյ արծաթի իոններով. ցողվում է ատամների և լնդերի վրա՝ շնչառությունը թարմացնելու և փառը կանխելու համար։", "dental care filed under Grooming Tools (no Dental Care leaf)"),
        ("073542", "cliny-loson-dlya-glaz-50-ml", "Eye Cleansing Lotion with Silver Ions, 50 ml", "50 ml", [33, 40], A(product_form="Liquid", health_feature="Eye Care"),
         "Cliny eye lotion with silver ions for gentle cleaning of the eye area of dogs and cats.", "Cliny աչքի լոսյոն արծաթի իոններով՝ շների և կատուների աչքերի հատվածի նուրբ մաքրման համար։", "eye care filed under Skin Care (no Eye Care leaf)"),
        ("073552", "cliny-loson-dlya-ushej-50-ml", "Ear Cleansing Lotion with Silver Ions, 50 ml", "50 ml", [32, 39], A(product_form="Liquid", health_feature="Ear Care"),
         "Cliny ear lotion with silver ions for regular hygienic cleaning of the ears of dogs and cats.", "Cliny ականջի լոսյոն արծաթի իոններով՝ շների և կատուների ականջների կանոնավոր հիգիենիկ մաքրման համար։", None),
        ("073512", "cliny-pasta-dlya-vyvoda-shersti-75-ml", "Hairball Malt Paste, 75 ml", "75 ml", [53], A(product_form="Paste", health_feature="Hairball Control"),
         "Cliny malt paste for cats: helps swallowed hair pass through the digestive tract and prevents hairballs.", "Cliny ածիկի մածուկ կատուների համար. օգնում է կուլ տված մազերին անցնել մարսողական համակարգով և կանխում մազագնդիկները։", None)):
    neo_add(code, CLI, "cliny", slug, name, label, cats, fam_attrs, en, hy, note)
# Mr. Fresh — cleaning / behaviour sprays: no product category in the tree
for code in ("075732", "075762", "076412", "076472", "076482", "076492", "076502"):
    r = todo[code]; price, cost, why = price_of(code)
    blocked.append({"Article Code": code, "Brand": "Mr. Fresh", "Proposed Product Name": r["Product Name (as printed)"], "Buy Price (AMD)": cost, "Sale Price (AMD)": price or "",
                    "Why": "odour/stain removers and behaviour-correction sprays: no product category in the tree (13 Accessories cannot hold products) — needs a Cleaning & Odour Control leaf"})

# ---------------------------------------------------------------- Ok-Lock (16) — litter, no official product page/image
for code, name, label, w in (("1101413", "SMART Clumping Plant-Based Cat Litter, 5 l", "5 l", "5 l"), ("1101213", "SMART Clumping Plant-Based Cat Litter, 11 l", "11 l", "11 l")):
    en = "SMART plant-based clumping cat litter by OK-LOCK: forms firm clumps and locks odours."
    hy = "SMART բուսական հիմքով գնդվող լցանյութ կատուների համար OK-LOCK-ից. կազմում է ամուր գնդիկներ և փակում հոտերը։"
    add(code, 16, "ok-lock", name, label, [60], None, A(product_weight=w), [], en, "SMART растительный комкующийся наполнитель для кошачьего туалета от OK-LOCK: образует плотные комки и запирает запахи.", hy,
        "https://ok-lock.pet (landing page; no product page or article-keyed image)", ptype="litter", extra_note="no official image: ok-lock.pet is a landing page whose pictures are not keyed to the article")

# ---------------------------------------------------------------- rows with no official source
for code, brand, note in (("142595", "Мяу", ""), ("142605", "Мяу", ""), ("142615", "Мяу", ""), ("142625", "Мяу", ""), ("142635", "Мяу", ""), ("142655", "Мяու", ""), ("143005", "Мяу", ""),
                          ("142645", "Мяу", "also unpriced"), ("147245", "Мяу", "also unpriced"),
                          ("83041J", "Kormell", ""), ("83042J", "Kormell", ""), ("83047J", "Kormell", ""), ("83010J", "Moor", ""), ("83014J", "Moor", ""), ("83077J", "Justin", ""),
                          ("03623K", "Интеко", ""), ("61001K", "Dogman", "also unpriced"), ("63833PCHL", "Api-San", "brand is Pchelodar (PCHL suffix, hafo brand «Пчелодар»), not Api-San"), ("63911PCHL", "Api-San", "also unpriced; brand is Pchelodar")):
    if code not in todo:
        continue
    r = todo[code]
    notfound.append({"Article Code": code, "Brand": r["Brand"], "Invoice Name (as printed)": r["Product Name (as printed)"], "Buy Price (AMD)": r["Buy Price (AMD)"], "Qty": r["Qty Received"], "Species": r["Species"],
                     "Note": ("brand has no official site reachable (Мяу is a Kormotech budget brand with no brand site; Kormell/Moor/Justin/Интеко/Dogman have none found; Pchelodar's site does not resolve) — no verified logo, name or image; " + note).strip("; ")})
# Iv San Bernard 06018IVS / 03171IVS, Rolf Club 072022, Inspector 073252, Mr. Fresh 076532, Club 4 Paws unpriced rows -> the unpriced CSV
for code in ("06018IVS", "03171IVS", "073252", "076532", "142535", "142545", "144975", "367575"):
    if code in todo:
        r = todo[code]; price, cost, why = price_of(code)
        if not price:
            unpriced.append({"Article Code": code, "Brand": r["Brand"], "Official Site": "", "Proposed Product Name": r["Product Name (as printed)"], "Proposed Variant": "", "Buy Price (AMD)": cost, "Sale Price (AMD)": "",
                             "Qty": stock_of(code), "Species": r["Species"], "Invoice Name (as printed)": r["Product Name (as printed)"], "Why no price": why, "Status": "NOT imported — needs a sale price from you"})

out = {"products": products, "unpriced": unpriced, "notfound": notfound, "flagged": flagged, "blocked_no_category": [], "blocked_rows": blocked,
       "wanted": [{"attribute": k[0], "label": k[1], "count": n} for k, n in WANTED.most_common()], "translations": TR}
json.dump(out, open(os.path.join(CACHE, "small-plan.json"), "w"), ensure_ascii=False, indent=1)
print(f"products {len(products)} unpriced {len(unpriced)} notfound {len(notfound)} blocked {len(blocked)} flagged {len(flagged)} wanted {dict(WANTED)}")
