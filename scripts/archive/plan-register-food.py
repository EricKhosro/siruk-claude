#!/usr/bin/env python3
"""Plan the food rows of the 2026-09-16 register import (Monge, Gemon, Simba,
Club 4 Paws, Myau) -> runs/<date>/plan-food.json for scripts/import-plan.py.

Inputs: runs/<date>/register-todo-rows.json (cost, `Վաճառքի գին`, `Kg`, qty)
and the brand-site research JSONs (research-monge.json, research-kormotech.json:
official page, English name, images packshot-first, composition, feeding).

Decisions are hand-written in ROWS below, one entry per article: the LINE
product it belongs to (never the flavour-named row product — rule 9), the
variant label, the closed-menu attribute labels with the evidence being the
research row, and, for a line that is already live, the product to attach to
and the name it should carry once it has siblings (`rename_to`, applied by
scripts/fix-outgrown-names.py after the import).

Prices: `Վաճառքի գին` is the sale price (rule 2c); dry bags are `fixed` at the
pack price with `weight` = pack kg, and a row with a `Kg` rate also gets the
per-kilo twin (`<sku>-KG`, per_kg, weight 1, product-weight 1 kg — the
convention of product 964 / make-perkg-twin.py).

    scripts/plan-register-food.py --run runs/2026-09-16-register
"""
import argparse, collections, json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MENU = json.load(open(os.path.join(ROOT, "reference/attribute-values.json")))
VAL = {code: {k.lower(): v for k, v in d["values"].items()} for code, d in MENU.items()}
ALIAS = {"product-weight": {"85 g": "85 gr"}}
BRAND_SLUG = {5: "monge", 18: "gemon", 19: "simba", 17: "club-4-paws", 35: "myau"}
WANTED = collections.Counter()


def vid(code, label):
    label = ALIAS.get(code, {}).get(label, label)
    v = VAL.get(code, {}).get((label or "").lower())
    if not v:
        WANTED[(code, label)] += 1
    return v


def A(**labels):
    out = {}
    for code, lab in labels.items():
        code = code.replace("_", "-")
        if lab:
            v = vid(code, lab)
            if v:
                out[code] = v
    return out


def slugify(s):
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", s.lower())).strip("-")


# ---------------------------------------------------------------- the map ----
# key -> product; rows -> (code, label, attrs, extra)
MONGE_DOG = dict(brand=5, family=1, cats=[3], species="dog")
MONGE_CAT = dict(brand=5, family=1, cats=[10], species="cat")
GEMON_DOG = dict(brand=18, family=1, cats=[3]); GEMON_CAT = dict(brand=18, family=1, cats=[10])
SIMBA_DOG = dict(brand=19, family=1, cats=[3])
C4P_DOG = dict(brand=17, family=1, cats=[3]); C4P_CAT = dict(brand=17, family=1, cats=[10])
GEMON_WET = dict(brand=18, family=2, cats=[4]); C4P_WET = dict(brand=17, family=2, cats=[11]); MYAU_WET = dict(brand=35, family=2, cats=[11]); MYAU_DRY = dict(brand=35, family=1, cats=[10])

PRODUCTS = {
 "monge-all-breeds-adult": dict(MONGE_DOG, name="All Breeds Adult", rows=[
    ("011137", "Duck & Rice 12 kg", dict(lifestage="Adult", breed_size="All Breeds", flavor="Duck", special_diet="Monoprotein")),
    ("011347", "Beef & Rice 12 kg", dict(lifestage="Adult", breed_size="All Breeds", flavor="Beef", special_diet="Monoprotein")),
    ("011327", "Lamb & Rice 12 kg", dict(lifestage="Adult", breed_size="All Breeds", flavor="Lamb", special_diet="Monoprotein")),
    ("011307", "Salmon & Rice 12 kg", dict(lifestage="Adult", breed_size="All Breeds", flavor="Salmon", special_diet="Monoprotein")),
    ("011157", "Rabbit & Rice 12 kg", dict(lifestage="Adult", breed_size="All Breeds", flavor="Rabbit", special_diet="Monoprotein")),
    ("011397", "Turkey & Rice 12 kg", dict(lifestage="Adult", breed_size="All Breeds", flavor="Turkey", special_diet="Monoprotein"))]),
 "monge-all-breeds-puppy-junior-lamb-rice-800-g": dict(MONGE_DOG, name="All Breeds Puppy & Junior", existing=639, rename_to="All Breeds Puppy & Junior", rows=[
    ("011217", "Salmon & Rice 12 kg", dict(lifestage="Puppy", breed_size="All Breeds", flavor="Salmon", special_diet="Monoprotein")),
    ("006487", "Beef & Rice 15 kg", dict(lifestage="Puppy", breed_size="All Breeds", flavor="Beef", special_diet="Monoprotein"))]),
 "monge-mini-adult-chicken-rice-800-g": dict(MONGE_DOG, name="Mini Adult", existing=636, rename_to="Mini Adult", rows=[
    ("MG006117", "Chicken 15 kg", dict(lifestage="Adult", breed_size="Small Breeds", flavor="Chicken")),
    ("MG006067", "Lamb & Rice 15 kg", dict(lifestage="Adult", breed_size="Small Breeds", flavor="Lamb", special_diet="Monoprotein")),
    ("MG006077", "Salmon & Rice 15 kg", dict(lifestage="Adult", breed_size="Small Breeds", flavor="Salmon", special_diet="Monoprotein"))]),
 "monge-mini-puppy-junior": dict(MONGE_DOG, name="Mini Puppy & Junior", rows=[
    ("MG006107", "Chicken 15 kg", dict(lifestage="Puppy", breed_size="Small Breeds", flavor="Chicken")),
    ("005947", "Lamb & Rice 15 kg", dict(lifestage="Puppy", breed_size="Small Breeds", flavor="Lamb", special_diet="Monoprotein")),
    ("005937", "Salmon & Rice 15 kg", dict(lifestage="Puppy", breed_size="Small Breeds", flavor="Salmon", special_diet="Monoprotein"))]),
 "monge-mini-starter": dict(MONGE_DOG, name="Mini Starter", rows=[
    ("MG006087", "Chicken 15 kg", dict(lifestage="Puppy", breed_size="Small Breeds", flavor="Chicken"))]),
 "monge-medium-puppy-junior": dict(MONGE_DOG, name="Medium Puppy & Junior", rows=[
    ("MG006347", "Chicken 15 kg", dict(lifestage="Puppy", breed_size="Medium Breeds", flavor="Chicken"))]),
 "monge-maxi-puppy-junior": dict(MONGE_DOG, name="Maxi Puppy & Junior", rows=[
    ("MG006027", "Chicken 15 kg", dict(lifestage="Puppy", breed_size="Large Breeds", flavor="Chicken"))]),
 "monge-maxi-adult": dict(MONGE_DOG, name="Maxi Adult", rows=[
    ("004417", "Chicken 12 kg", dict(lifestage="Adult", breed_size="Large Breeds", flavor="Chicken"))]),
 "monge-bwild-low-grain-all-breeds-adult": dict(MONGE_DOG, name="BWild Low Grain All Breeds Adult", rows=[
    ("011757", "Wild Boar 12 kg", dict(lifestage="Adult", breed_size="All Breeds", flavor="Boar")),
    ("011797", "Deer 12 kg", dict(lifestage="Adult", breed_size="All Breeds", flavor="Venison"))]),
 "monge-bwild-low-grain-all-breeds-puppy-junior": dict(MONGE_DOG, name="BWild Low Grain All Breeds Puppy & Junior", rows=[
    ("011897", "Deer 12 kg", dict(lifestage="Puppy", breed_size="All Breeds", flavor="Venison"))]),
 "monge-bwild-grain-free-all-breeds-adult": dict(MONGE_DOG, name="BWild Grain Free All Breeds Adult", rows=[
    ("011737", "Lamb, Potatoes & Peas 12 kg", dict(lifestage="Adult", breed_size="All Breeds", flavor="Lamb", special_diet="Grain-Free"))]),
 "monge-hairball-cat": dict(MONGE_CAT, name="Hairball Cat", placeholder_note="10 kg breeder bag has no Monge photo — monge.it line packshot, hafo last", rows=[
    ("MG 004797", "Chicken 10 kg", dict(lifestage="Adult", flavor="Chicken", health_feature="Hairball Control"))]),
 "monge-indoor-cat": dict(MONGE_CAT, name="Indoor Cat", rows=[
    ("MG 004827", "Chicken 10 kg", dict(lifestage="Adult", flavor="Chicken", special_diet="Indoor"))]),
 "monge-kitten-cat": dict(MONGE_CAT, name="Kitten Cat", rows=[
    ("MG 004817", "Chicken 10 kg", dict(lifestage="Kitten", flavor="Chicken"))]),
 "monge-sensitive-cat": dict(MONGE_CAT, name="Sensitive Cat", rows=[
    ("MG 004837", "Chicken 10 kg", dict(lifestage="Adult", flavor="Chicken", health_feature="Sensitive Digestion"))]),
 "monge-adult-cat": dict(MONGE_CAT, name="Adult Cat", rows=[
    ("MG 004807", "Chicken 10 kg", dict(lifestage="Adult", flavor="Chicken"))]),
 "gemon-kitten-cat": dict(GEMON_CAT, name="Kitten Cat", rows=[
    ("297257", "Chicken & Rice 7 kg", dict(lifestage="Kitten", flavor="Chicken"))]),
 "gemon-adult-cat": dict(GEMON_CAT, name="Adult Cat", rows=[
    ("297267", "Chicken & Turkey 7 kg", dict(lifestage="Adult", flavor="Chicken & Turkey"))]),
 "gemon-mini-adult-dog": dict(GEMON_DOG, name="Mini Adult Dog", rows=[
    ("MM005677", "Chicken & Rice 20 kg", dict(lifestage="Adult", breed_size="Small Breeds", flavor="Chicken"))]),
 "gemon-regular-adult-dog": dict(GEMON_DOG, name="Regular All Breeds Adult Dog", rows=[
    ("MM006177", "Chicken & Rice 20 kg", dict(lifestage="Adult", breed_size="All Breeds", flavor="Chicken"))]),
 "gemon-adult-dog-pate-150-g": dict(GEMON_WET, name="Adult Dog Paté, 150 g", rows=[
    ("300417", "Beef 150 g", dict(lifestage="Adult", breed_size="All Breeds", flavor="Beef", texture="Pate", packaging="Tray", product_weight="150 g")),
    ("300447", "Lamb 150 g", dict(lifestage="Adult", breed_size="All Breeds", flavor="Lamb", texture="Pate", packaging="Tray", product_weight="150 g")),
    ("300457", "Tuna 150 g", dict(lifestage="Adult", breed_size="All Breeds", flavor="Tuna", texture="Pate", packaging="Tray", product_weight="150 g"))]),
 "gemon-mature-dog-pate-light": dict(GEMON_WET, name="Mature Dog Paté Light", rows=[
    ("300437", "Turkey 150 g", dict(lifestage="Senior", breed_size="All Breeds", flavor="Turkey", texture="Pate", packaging="Tray", product_weight="150 g", special_diet="Low Fat"))]),
 "gemon-sterilised-dog-pouch": dict(GEMON_WET, name="Sterilised Dog Pouch", rows=[
    ("300657", "Chicken & Turkey 100 g", dict(lifestage="Adult", breed_size="All Breeds", flavor="Chicken & Turkey", special_diet="Sterilised", texture="Chunks in Gravy", packaging="Pouch", product_weight="100 g"))]),
 "simba-adult-dog-kibbles": dict(SIMBA_DOG, name="Adult Dog Kibbles", rows=[
    ("009977", "Tuna 20 kg", dict(lifestage="Adult", breed_size="All Breeds", flavor="Tuna")),
    ("009957", "Lamb 20 kg", dict(lifestage="Adult", breed_size="All Breeds", flavor="Lamb"))]),
 "club-4-paws-premium-sterilised-dry-cat-food": dict(C4P_CAT, name="Premium Sterilised Dry Cat Food", rows=[
    ("909665", "Chicken 14 kg", dict(lifestage="Adult", flavor="Chicken", special_diet="Sterilised"))]),
 "club-4-paws-premium-hairball-control-dry-cat-food": dict(C4P_CAT, name="Premium Hairball Control Dry Cat Food", rows=[
    ("909335", "Chicken 14 kg", dict(lifestage="Adult", flavor="Chicken", health_feature="Hairball Control"))]),
 "club-4-paws-premium-active-dry-dog-food": dict(C4P_DOG, name="Premium Active Dry Dog Food", rows=[
    ("909555", "Chicken 14 kg", dict(lifestage="Adult", breed_size="All Breeds", flavor="Chicken", health_feature="High-Energy"))]),
 "club-4-paws-premium-large-breeds-adult-dry-dog-food": dict(C4P_DOG, name="Premium Large Breeds Adult Dry Dog Food", rows=[
    ("909645", "Chicken 14 kg", dict(lifestage="Adult", breed_size="Large Breeds", flavor="Chicken"))]),
 "club-4-paws-premium-medium-breeds-adult-dry-dog-food": dict(C4P_DOG, name="Premium Medium Breeds Adult Dry Dog Food", rows=[
    ("909715", "Chicken 14 kg", dict(lifestage="Adult", breed_size="Medium Breeds", flavor="Chicken"))]),
 "club-4-paws-premium-small-breeds-adult-dry-dog-food": dict(C4P_DOG, name="Premium Small Breeds Adult Dry Dog Food", rows=[
    ("909545", "Chicken 14 kg", dict(lifestage="Adult", breed_size="Small Breeds", flavor="Chicken"))]),
 "club-4-paws-premium-puppies-dry-dog-food": dict(C4P_DOG, name="Premium Puppies Dry Dog Food", rows=[
    ("909695", "Chicken 14 kg", dict(lifestage="Puppy", breed_size="All Breeds", flavor="Chicken"))]),
 "club-4-paws-premium-adult-cat": dict(C4P_WET, name="Premium Adult Cat", existing=727, rows=[
    ("142535", "Salmon in Jelly 85 g", dict(lifestage="Adult", flavor="Salmon", texture="Chunks in Jelly", packaging="Pouch", product_weight="85 g")),
    ("142545", "Mackerel in Gravy 85 g", dict(lifestage="Adult", flavor="Mackerel", texture="Chunks in Gravy", packaging="Pouch", product_weight="85 g"))]),
 "club-4-paws-premium-sterilised-cat": dict(C4P_WET, name="Premium Sterilised Cat", existing=729, rows=[
    ("367575", "Rabbit in Jelly 80 g", dict(lifestage="Adult", flavor="Rabbit", special_diet="Sterilised", texture="Chunks in Jelly", packaging="Pouch", product_weight="80 g"))]),
 "club-4-paws-premium-adult-cat-7": dict(C4P_WET, name="Premium Adult Cat 7+", rows=[
    ("144975", "Chicken in Gravy 85 g", dict(lifestage="Senior", flavor="Chicken", texture="Chunks in Gravy", packaging="Pouch", product_weight="85 g"))]),
 "myau-adult-cat-pouch": dict(MYAU_WET, name="Adult Cat Pouch, 85 g", existing=1050, rows=[
    ("142645", "Liver in Gravy", dict(lifestage="Adult", flavor="Liver", texture="Chunks in Gravy", packaging="Pouch", product_weight="85 g"))]),
 "myau-kitten-dry-food": dict(MYAU_DRY, name="Kitten Dry Food", hafo_only=True, rows=[
    ("902135", "11 kg", dict(lifestage="Kitten"))]),
}
# ---- Beaphar (brand 30): research-beaphar.json (beaphar.cz / beaphar.ru pages print our SKU)
BEA = dict(brand=30)
BEAPHAR = {
 "beaphar-vitamin-b-complex": dict(BEA, family=4, cats=[43, 52], name="Vitamin B Complex", rows=[
    ("12523", "50 ml", dict(product_form="Liquid", health_feature="Vitamins & Minerals", product_weight="50 ml"))],
    en="Vitamin B complex drops for dogs, cats, small animals and birds: a supplementary feed supporting vitality, appetite and a healthy coat."),
 "beaphar-kittys-protein": dict(BEA, family=4, cats=[52], name="Kitty's Protein", rows=[
    ("BP12510", "75 tablets", dict(product_form="Tablet", health_feature="Vitamins & Minerals"))],
    en="Heart-shaped protein-rich supplementary treats for cats and kittens from 6 weeks, with the minerals needed for a cat's vitality."),
 "beaphar-play-spray": dict(BEA, family=4, cats=[25], name="Play Spray", rows=[
    ("BP12526", "150 ml", dict(product_form="Spray", product_weight="150 ml"))]),
 "beaphar-puppy-trainer": dict(BEA, family=4, cats=[74], name="Puppy Trainer", rows=[
    ("12562", "50 ml", dict(product_form="Liquid", product_weight="50 ml"))]),
 "beaphar-flea-tick-collar-for-cats": dict(BEA, family=4, cats=[51], name="Flea & Tick Collar for Cats", rows=[
    ("10203", "35 cm, orange", dict(product_form="Collar", health_feature="Anti-Parasitic", size="35 cm", color_family="Orange")),
    ("10202", "35 cm, purple", dict(product_form="Collar", health_feature="Anti-Parasitic", size="35 cm", color_family="Purple"))],
    en="Flea and tick collar for cats from 6 months: kills parasites and protects against re-infestation with fleas and ticks for 6 months."),
 "beaphar-catty-home": dict(BEA, family=4, cats=[67], name="Catty Home", rows=[
    ("12566", "10 ml", dict(product_form="Liquid", product_weight="10 ml"))],
    en="Catty Home is a natural attractant with extra pulling power for cats — ideal for training a kitten to use its litter tray, scratching post or basket."),
 "beaphar-malt-paste": dict(BEA, family=4, cats=[53], name="Malt Paste", rows=[
    ("13689", "100 g", dict(product_form="Paste", health_feature="Hairball Control", product_weight="100 g"))]),
 "beaphar-paw-balm": dict(BEA, family=None, cats=[31, 38], name="Paw Balm", rows=[
    ("10270", "40 ml", dict())],
    en="Paw balm protects the pads of dogs' and cats' paws, especially in winter (road salt) and summer (hot surfaces); softens the skin of the pads and works against cracking and irritation."),
 "beaphar-cat-a-dent-bits": dict(BEA, family=3, cats=[92], name="Cat-a-dent Bits", rows=[
    ("11406", "35 g", dict(product_weight="35 g", health_feature="Dental & Breath Care"))],
    en="Crunchy pillow-shaped treats for cats' dental care: strengthen the tooth enamel, remove plaque mechanically and polish the teeth; chlorophyll absorbs mouth odour for fresh breath."),
 "beaphar-malt-bits": dict(BEA, family=3, cats=[91], name="Malt Bits", rows=[
    ("12622", "Original 35 g", dict(product_weight="35 g", health_feature="Hairball Control")),
    ("12621", "Salmon 35 g", dict(product_weight="35 g", health_feature="Hairball Control", flavor="Salmon"))]),
 "beaphar-bio-cosmetic-shampoo-puppy": dict(BEA, family=None, cats=[29], name="BIO Cosmetic Shampoo Puppy", rows=[("12281", "200 ml", dict())]),
 "beaphar-bio-cosmetic-shampoo-shiny-coat": dict(BEA, family=None, cats=[29], name="BIO Cosmetic Shampoo Shiny Coat", rows=[("12282", "200 ml", dict())]),
 "beaphar-bio-cosmetic-shampoo-sensitive": dict(BEA, family=None, cats=[29], name="BIO Cosmetic Shampoo Sensitive", rows=[("12287", "200 ml", dict())]),
 "beaphar-white-coat-shampoo-dog": dict(BEA, family=None, cats=[29], name="White Coat Shampoo for Dogs", rows=[("19983", "250 ml", dict())]),
 "beaphar-universal-shampoo-dog": dict(BEA, family=None, cats=[29], name="Universal Shampoo for Dogs", rows=[("19967", "250 ml", dict())]),
 "beaphar-cat-shampoo": dict(BEA, family=None, cats=[36], name="Cat Shampoo", rows=[("19963", "250 ml", dict())]),
 "beaphar-puppy-shampoo": dict(BEA, family=None, cats=[29], name="Puppy Shampoo", rows=[("19905", "250 ml", dict())]),
 "beaphar-long-coat-shampoo-dog": dict(BEA, family=None, cats=[29], name="Long Coat Shampoo for Dogs", rows=[("13843", "250 ml", dict())]),
 "beaphar-brown-coat-shampoo-dog": dict(BEA, family=None, cats=[29], name="Brown Coat Shampoo for Dogs", rows=[("14206", "250 ml", dict())]),
}
PRODUCTS.update(BEAPHAR)

# ---- small brands (research-small.json): brands 36–42 created 2026-09-17
SMALL = {
 "pchelodar-dezacid-forte": dict(brand=42, family=4, cats=[47, 55], name="Dezacid Forte Eye & Nasal Drops", rows=[
    ("63911PCHL", "10 ml", dict(product_form="Liquid", product_weight="10 ml"))]),
 "pchelodar-otidez-forte": dict(brand=42, family=4, cats=[32, 39], name="Otidez Forte Ear Drops", rows=[
    ("63833PCHL", "15 ml", dict(product_form="Liquid", health_feature="Ear Care"))]),
 "versele-laga-extreme-compact": dict(brand=36, family=9, cats=[60], name="eXtreme Compact Clumping Litter", rows=[
    ("423079V", "7.5 l", dict())]),
 "versele-laga-senegal": dict(brand=36, family=9, cats=[62], name="Senegal Clay Litter", rows=[
    ("423074V", "12 l", dict())]),
 "versele-laga-silica": dict(brand=36, family=9, cats=[65], name="Silica Litter", rows=[
    ("423080V", "5 l", dict())]),
 "eco-premium-clumping-wood-litter-peach": dict(brand=40, family=9, cats=[60, 61], name="Clumping Wood Litter, Peach", rows=[
    ("48905E", "5 l", dict())]),
 "eco-premium-clumping-wood-litter-green-tea": dict(brand=40, family=9, cats=[60, 61], name="Clumping Wood Litter, Green Tea", rows=[
    ("48893E", "5 l", dict())]),
 "mnyams-crunchy-pillows-kitten": dict(brand=37, family=3, cats=[89], name="Crunchy Pillows for Kittens", rows=[
    ("548833", "Chicken & Egg with Taurine 60 g", dict(lifestage="Kitten", flavor="Chicken", product_weight="60 g"))]),
 "mnyams-crunchy-pillows-healthy-teeth": dict(brand=37, family=3, cats=[89, 92], name="Crunchy Pillows Healthy Teeth", rows=[
    ("548803", "Chicken with Vitamins 60 g", dict(lifestage="Adult", flavor="Chicken", product_weight="60 g", health_feature="Dental & Breath Care"))]),
 "mnyams-crunchy-pillows-hairball": dict(brand=37, family=3, cats=[89], name="Crunchy Pillows Hairball Control", rows=[
    ("548773", "Chicken with Vitamin Complex 60 g", dict(lifestage="Adult", flavor="Chicken", product_weight="60 g", health_feature="Hairball Control"))]),
 "mnyams-crunchy-pillows-healthy-skin-coat": dict(brand=37, family=3, cats=[89], name="Crunchy Pillows Healthy Skin & Coat", rows=[
    ("548783", "Poultry with Zinc 60 g", dict(lifestage="Adult", flavor="Poultry", product_weight="60 g", health_feature="Skin & Coat Health"))]),
 "mnyams-crunchy-pillows-sterilised": dict(brand=37, family=3, cats=[89], name="Crunchy Pillows for Sterilised Cats", rows=[
    ("548843", "Chicken & Cranberry with L-Carnitine 60 g", dict(lifestage="Adult", flavor="Chicken", product_weight="60 g", special_diet="Sterilised"))]),
 "mnyams-cream-treat": dict(brand=37, family=3, cats=[90], name="Cream Treat Purée", rows=[
    ("703803", "Katsuo Tuna, 4 × 15 g", dict(lifestage="Adult", flavor="Tuna", product_weight="60 g")),
    ("703813", "Katsuo & Maguro Tuna, 4 × 15 g", dict(lifestage="Adult", flavor="Seafood & Fish", product_weight="60 g")),
    ("540693", "Katsuo Tuna & Shrimp, 4 × 15 g", dict(lifestage="Adult", flavor="Shrimp", product_weight="60 g")),
    ("703833", "Chicken, 4 × 15 g", dict(lifestage="Adult", flavor="Chicken", product_weight="60 g")),
    ("540713", "Duck & Katsuo Tuna, 4 × 15 g", dict(lifestage="Adult", flavor="Duck", product_weight="60 g"))]),
 "derevenskie-lakomstva-goose-strips-mini": dict(brand=38, family=3, cats=[86], name="Goose Meat Strips for Mini Breeds", rows=[
    ("208986", "55 g", dict(flavor="Duck", breed_size="Small Breeds", product_weight="55 g"))]),
 "derevenskie-lakomstva-venison-strips": dict(brand=38, family=3, cats=[86], name="Venison Meat Strips", rows=[
    ("208946", "90 g", dict(flavor="Venison", product_weight="90 g"))]),
 "derevenskie-lakomstva-ostrich-medallions": dict(brand=38, family=3, cats=[86], name="Ostrich Meat Medallions", rows=[
    ("208976", "90 g", dict(flavor="Ostrich", product_weight="90 g"))]),
 "derevenskie-lakomstva-chicken-duck-medallions": dict(brand=38, family=3, cats=[86], name="Chicken & Duck Meat Medallions", rows=[
    ("214926", "90 g", dict(flavor="Chicken", product_weight="90 g"))]),
 "derevenskie-lakomstva-meat-braids": dict(brand=38, family=3, cats=[85], name="Meat Braids with Chicken, Duck & Cod", rows=[
    ("214936", "90 g", dict(flavor="Chicken", product_weight="90 g"))]),
 "derevenskie-lakomstva-veal-sesame-training-treats": dict(brand=38, family=3, cats=[82], name="Veal & Sesame Training Treats", rows=[
    ("212836", "90 g", dict(flavor="Veal", product_weight="90 g"))]),
 "derevenskie-lakomstva-duck-fillet-slices-mini": dict(brand=38, family=3, cats=[86], name="Duck Fillet Slices for Mini Breeds", rows=[
    ("711536", "55 g", dict(flavor="Duck", breed_size="Small Breeds", product_weight="55 g"))]),
 "iv-san-bernard-dermobrush": dict(brand=29, family=None, cats=[28, 35], name="Dermobrush", placeholder_note="only a group render of the pattern range on the brand site — needs a packshot", rows=[
    ("06018IVS", "Fantasia", dict())]),
 "iv-san-bernard-traditional-plus-banana-shampoo": dict(brand=29, family=None, cats=[29, 36], name="Traditional Plus Banana Shampoo for Medium Coats, 300 ml", rows=[
    ("03171IVS", "300 ml", dict())]),
 "8in1-pro-fillets-skin-coat": dict(brand=31, family=3, cats=[86], name="PRO Fillets Skin & Coat", rows=[
    ("11241S", "80 g", dict(flavor="Chicken", product_weight="80 g", health_feature="Skin & Coat Health"))]),
 "8in1-pro-fillets-active": dict(brand=31, family=3, cats=[86], name="PRO Fillets Active", rows=[
    ("11238", "80 g", dict(flavor="Chicken", product_weight="80 g", health_feature="Hip & Joint Support"))]),
 "8in1-meaty-treats-freeze-dried-duck": dict(brand=31, family=3, cats=[87], name="Meaty Treats Freeze Dried Duck Breast", rows=[
    ("14604S", "50 g", dict(flavor="Duck", product_weight="50 g"))]),
 "kaskad-classic-leather-collar-padded": dict(brand=41, family=None, cats=[69], name="Classic Leather Collar, padded", rows=[
    ("00244K", "35 mm, 50–59 cm", dict())]),
 "kaskad-classic-leather-collar-braid": dict(brand=41, family=None, cats=[69], name="Classic Leather Collar with Braid", rows=[
    ("00247K", "35 mm, 50–59 cm", dict())]),
 "flexi-new-neon-tape-lead-5-m": dict(brand=39, family=None, cats=[69], name="New Neon Tape Lead, 5 m", rows=[
    ("032008", "S, 5 m, orange", dict(size="S", color_family="Orange")),
    ("032038", "S, 5 m, blue", dict(size="S", color_family="Blue")),
    ("032108", "M, 5 m, pink", dict(size="M", color_family="Pink")),
    ("031908", "M, 5 m, green", dict(size="M", color_family="Green"))]),
 "mr-fresh-expert-scratching-post-training-spray": dict(brand=27, family=None, cats=[81], name="Expert Scratching Post Training Spray for Cats", rows=[
    ("076532", "200 ml", dict())]),
}
PRODUCTS.update(SMALL)

HELD = {"61001K": "Dogman litter tray: the maker has no website — no source for name, image or text (rule 7)",
        "03623K": "Интеко litter tray: the maker has no website (and skipped on the user's call on 2026-09-15)",
        "703823": "Mnyams tuna & shrimp purée: article 703829 is not on mnyams.ru (likely the older article of 540693, unproven)",
        "11244S": "8in1 Fillets Pro Digest: delisted from 8in1.eu (404) — no brand image",
        "042718": "flexi New Comfort XS cord: model replaced by Comfort Plus, page 404 — no brand image",
        "12625": "Beaphar Vit Bits 35 g: no Beaphar page prints article 12625 (beaphar.ru's Vit Bits is article 11611; UK is 11416) — name-match only, rule 6",
        "147245": "Myau sterilised turkey pouch: no brand page, no hafo row keyed to the code — nothing to picture it with (rule 7)"}

DRY_FAMILY = 1


def pack_kg(label):
    m = re.search(r"(\d+(?:[.,]\d+)?)\s*kg", label)
    return float(m.group(1).replace(",", ".")) if m else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True)
    a = ap.parse_args()
    run = a.run
    rows = {r["Article Code"].replace("\xa0", " ").strip(): r for r in json.load(open(os.path.join(run, "register-todo-rows.json")))}
    research = {}
    for g in ("monge", "kormotech", "beaphar", "small"):
        p = os.path.join(run, f"research-{g}.json")
        if os.path.exists(p):
            for r in json.load(open(p))["rows"]:
                research[str(r.get("code")).strip()] = r
    snap = json.load(open(os.path.join(ROOT, ".siruk-cache/catalogue-snapshot.json")))
    live_skus = {str(v["sku"]) for p in snap.values() for v in p["variants"]}

    products, held, needs_image, notes = [], [], [], []
    for slug, P in PRODUCTS.items():
        variants = []
        for i, (code, label, attrs) in enumerate(P["rows"]):
            r = rows.get(code)
            if not r:
                notes.append(f"{code}: not in register-todo-rows (already live?)"); continue
            if code in live_skus or code.replace(" ", "") in live_skus:
                notes.append(f"{code}: already a live SKU — skipped"); continue
            res = research.get(code) or {}
            cost = int(float(r["Buy Price (AMD)"])); sale = float(r["_sale"] or 0); kg_rate = float(r["_kg"] or 0)
            if not sale or sale <= cost:
                held.append({"code": code, "why": f"register price {sale} does not beat cost {cost}", "product": P["name"]}); continue
            if sale >= 5 * cost:
                held.append({"code": code, "why": f"SUSPECT register price {sale} is {sale/cost:.1f}x cost {cost} — looks like a typo, confirm", "product": P["name"]}); continue
            dry = P["family"] == DRY_FAMILY
            kg = pack_kg(label)
            av = A(**attrs)
            if dry:
                av.update(A(packaging="Bag", product_weight=f"{kg:g} kg" if kg else None))
            imgs = list(res.get("images") or [])
            hafo_img = res.get("hafo_image") or res.get("hafo_placeholder") or None
            if hafo_img and hafo_img not in imgs:
                imgs.append(hafo_img)
            if not imgs and P.get("hafo_only"):
                h = r.get("_hafo_url")
                notes.append(f"{code}: hafo-only — image to be taken from {h}")
            if not imgs or P.get("placeholder_note"):
                needs_image.append({"code": code, "product": P["name"], "why": P.get("placeholder_note") or "no brand photo found", "hafo": r.get("_hafo_url")})
            sib = res.get("english_sibling") if isinstance(res.get("english_sibling"), dict) else {}
            desc = res.get("description") or sib.get("description") or P.get("en") or ""
            about = f"<p>{desc}</p>" if desc else ""
            ingr = ""
            comp = res.get("composition") or sib.get("composition")
            if comp: ingr += f"<p><strong>Composition:</strong> {comp}</p>"
            if res.get("analytical_constituents"): ingr += f"<p><strong>Analytical constituents:</strong> {res['analytical_constituents']}</p>"
            if res.get("additives"): ingr += f"<p><strong>Additives:</strong> {res['additives']}</p>"
            feedtxt = res.get("feeding") or res.get("feeding_or_directions") or sib.get("directions") or sib.get("feeding_or_directions") or ""
            feed = f"<p>{feedtxt}</p>" if feedtxt else ""
            q = int(float(r["Qty Received"] or 1)); stock = 10 if q <= 1 else q
            v = {"sku": code, "name": label, "pricing_type": "fixed", "price": int(sale), "cost_price": cost, "stock": stock,
                 "images": imgs, "attribute_value_ids": av, "about_this_item": about, "ingredient_information": ingr,
                 "feeding_instructions": feed, "is_default": i == 0 and not P.get("existing"), "sort_order": i,
                 "_inv": r["Product Name (as printed)"], "_code": code, "_src": res.get("page_url") or r.get("_hafo_url"),
                 "_price_source": "register", "_reg_no": r["_reg_no"]}
            if dry and kg:
                v["weight"] = kg
            variants.append(v)
            if dry and kg_rate and kg:
                if kg_rate <= cost / kg:
                    held.append({"code": code + "-KG", "why": f"register Kg rate {kg_rate} does not beat cost/kg {cost/kg:.0f}", "product": P["name"]})
                else:
                    tw = dict(v, sku=f"{code}-KG", name="By weight, 1 kg", pricing_type="per_kg", price=0, price_per_kg=int(kg_rate), weight=1,
                              cost_price=int(round(cost / kg)),
                              is_default=False, sort_order=i + 100, attribute_value_ids=dict(av, **A(product_weight="1 kg")),
                              _price_source="register Kg")
                    variants.append(tw)
        if not variants:
            continue
        prod = {"slug": slug, "name": P["name"], "category_ids": P["cats"], "brand_id": P["brand"], "attribute_family_id": P["family"],
                "variants": variants, "source": "register 2026-09-16 + brand research", "ptype": "dry" if P["family"] == 1 else "wet"}
        if P.get("existing"):
            prod["existing_id"] = P["existing"]
            if P.get("rename_to"):
                prod["rename_to"] = P["rename_to"]
        products.append(prod)

    for code, why in HELD.items():
        held.append({"code": code, "why": why, "product": ""})
    out = {"products": products, "held": held, "needs_image": needs_image, "notes": notes,
           "wanted": [{"attribute": k[0], "label": k[1], "count": n} for k, n in WANTED.most_common()]}
    json.dump(out, open(os.path.join(run, "plan-food.json"), "w"), ensure_ascii=False, indent=1)
    print(f"products {len(products)} variants {sum(len(p['variants']) for p in products)} held {len(held)} needs_image {len(needs_image)} wanted {len(WANTED)}", file=sys.stderr)
    for n in notes: print("  note:", n, file=sys.stderr)
    for k, n in WANTED.most_common(): print("  wanted:", k, n, file=sys.stderr)


if __name__ == "__main__":
    main()
