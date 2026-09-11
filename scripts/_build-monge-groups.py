#!/usr/bin/env python3
"""Hand-written grouping of the Monge-group CSV rows (2026-09-10 import) ->
.siruk-cache/monge-groups.json for scripts/plan-monge.py.

Shelf test (reference/product-rules.md): line + species + lifestage + breed
size + special diet + health claim = product; flavour / texture / pack = variant.
Identity per row comes from hafo (article code) + the monge.shop EAN join;
names are the brand's English wording without the brand.
"""
import json, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MONGE, GEMON, LECHAT, SPECIAL = 5, 18, 20, 21
G = {}


def add(code, product, label, brand=MONGE, family=2, cats=(11,), ptype="wet", **kw):
    G[code] = {"product": product, "label": label, "brand_id": brand, "family": family, "cat_ids": list(cats), "ptype": ptype, **kw}


CW, DW, CD, DD, DT, CT = (11,), (4,), (10,), (3,), (6,), (14,)
DV, CV = (4, 5), (11,)          # veterinary: dog also in 5 Health Condition

# ---- Monge cat wet: BWild Grain Free pouches 85 g (chunks in sauce)
add("012767", "BWild Grain Free Adult Cat", "Cod with Prawns & Vegetables 85 g")
add("012777", "BWild Grain Free Adult Cat", "Anchovies with Vegetables 85 g")
add("012757", "BWild Grain Free Adult Cat", "Buffalo with Vegetables 85 g", attr_labels={"lifestage": "Adult"})
add("012787", "BWild Grain Free Sterilised Cat", "Salmon with Prawns & Vegetables 85 g", attr_labels={"special-diet": "Sterilised"})
add("012797", "BWild Grain Free Sterilised Cat", "Tuna with Prawns & Vegetables 85 g", attr_labels={"special-diet": "Sterilised"})
add("012807", "BWild Grain Free Sterilised Cat", "Wild Boar with Vegetables 85 g", attr_labels={"special-diet": "Sterilised"})
# BWild Grain Free cat paté 100 g
add("012857", "BWild Grain Free Large Breed Cat Paté", "Buffalo 100 g", attr_labels={"lifestage": "Adult"})
add("012867", "BWild Grain Free Adult Cat Paté", "Cod 100 g")
add("012877", "BWild Grain Free Adult Cat Paté", "Anchovies 100 g")
add("012887", "BWild Grain Free Adult Cat Paté", "Salmon 100 g")
add("012897", "BWild Grain Free Sterilised Cat Paté", "Tuna 100 g", attr_labels={"special-diet": "Sterilised"})
add("012907", "BWild Grain Free Sterilised Cat Paté", "Wild Boar 100 g", attr_labels={"special-diet": "Sterilised"})
# Grill cat pouches 85 g (chunks in jelly)
add("013607", "Grill Kitten", "Salmon 85 g")
add("013617", "Grill Adult Cat", "Rabbit 85 g")
add("013627", "Grill Adult Cat", "Lamb 85 g")
add("013637", "Grill Sterilised Cat", "Chicken 85 g", attr_labels={"special-diet": "Sterilised"})
add("013647", "Grill Sterilised Cat", "Veal 85 g", flavor="Veal", attr_labels={"special-diet": "Sterilised"})
add("013657", "Grill Sterilised Cat", "Trout 85 g", flavor="Trout", attr_labels={"special-diet": "Sterilised"})
# Fresh cat pouches 85 g
add("301067", "Fresh Adult Cat", "Chicken with Vegetables 85 g")
add("301087", "Fresh Sterilised Cat", "Beef 85 g", attr_labels={"special-diet": "Sterilised"})
add("301097", "Fresh Sterilised Cat", "Herring 85 g", attr_labels={"special-diet": "Sterilised"})
# VetSolution cat wet 100 g
add("014627", "VetSolution Urinary Struvite Cat", "100 g", cats=CV, attr_labels={"special-diet": "Veterinary Diet", "health-feature": "Urinary Tract Health"})
add("014647", "VetSolution Renal & Oxalate Cat", "100 g", cats=CV, attr_labels={"special-diet": "Veterinary Diet", "health-feature": "Kidney Care"})
add("014657", "VetSolution Recovery Cat", "100 g", cats=CV, attr_labels={"special-diet": "Veterinary Diet", "health-feature": "Recovery"})
# VetSolution cat dry 1.5 kg
for c, n, hf in (("081517", "Gastrointestinal", "Digestive Health"), ("081657", "Renal", "Kidney Care"), ("081687", "Hepatic", "Liver Care"), ("081757", "Diabetic", "Diabetic Support")):
    add(c, f"VetSolution {n} Cat", "1.5 kg", family=1, cats=CD, ptype="dry", attr_labels={"special-diet": "Veterinary Diet", "health-feature": hf})
# Monge cat dry
add("005517", "Monoprotein Adult Cat", "Salmon 1.5 kg", family=1, cats=CD, ptype="dry", attr_labels={"special-diet": "Monoprotein"})
add("005527", "Monoprotein Sterilised Cat", "Beef 1.5 kg", family=1, cats=CD, ptype="dry", attr_labels={"special-diet": "Sterilised"})
add("011937", "Sterilised Cat", "Chicken 1.5 kg", family=1, cats=CD, ptype="dry", attr_labels={"special-diet": "Sterilised"})
add("012007", "BWild Adult Cat", "Hare 1.5 kg", family=1, cats=CD, ptype="dry", flavor="Hare")
add("012067", "BWild Grain Free Large Breed Cat", "Buffalo 1.5 kg", family=1, cats=CD, ptype="dry")
add("012087", "BWild Grain Free Sterilised Cat", "Tuna with Peas 1.5 kg", family=1, cats=CD, ptype="dry", attr_labels={"special-diet": "Sterilised"})
# Monge dog dry
add("004097", "Mini Adult", "Chicken & Rice 800 g", family=1, cats=DD, ptype="dry", breed_size="Small Breeds")  # invoice + hafo row + monge.shop EAN 8009470004091 all say 800 g (2026-09-11)
add("011257", "All Breeds Puppy & Junior", "Lamb & Rice 800 g", family=1, cats=DD, ptype="dry", breed_size="All Breeds", attr_labels={"lifestage": "Puppy", "flavor": "Lamb"})
add("011407", "Extra Small Puppy & Junior", "Chicken 800 g", family=1, cats=DD, ptype="dry", breed_size="Extra Small Breeds", attr_labels={"lifestage": "Puppy", "flavor": "Chicken"})
add("011477", "Extra Small Adult", "Lamb & Rice 800 g", family=1, cats=DD, ptype="dry", breed_size="Extra Small Breeds", attr_labels={"lifestage": "Adult", "flavor": "Lamb"})
# Monge dog wet: Grill pouches 100 g
add("013117", "Grill Adult Dog", "Chicken & Turkey 100 g", cats=DW)
add("013127", "Grill Adult Dog", "Salmon 100 g", cats=DW)
add("013167", "Grill Adult Dog", "Lamb with Vegetables 100 g", cats=DW)
add("013177", "Grill Puppy", "Chicken & Turkey 100 g", cats=DW)
# Fruit paté
for c, l in (("013217", "Chicken with Raspberries 100 g"), ("013237", "Duck with Orange 100 g"), ("013247", "Salmon with Pear 100 g"), ("013257", "Pork with Pineapple 100 g"), ("014337", "Turkey with Citrus Fruits 400 g")):
    add(c, "Fruit Adult Dog Paté", l, cats=DW, attr_labels={"lifestage": "Adult"})
# Fresh paté pouches 100 g
for c, l in (("013017", "Tuna 100 g"), ("013037", "Chicken with Vegetables 100 g"), ("013067", "Chicken 100 g"), ("013097", "Pork 100 g"), ("013107", "Cod 100 g")):
    add(c, "Fresh Adult Dog Paté", l, cats=DW)
# Fresh cans 400 g
add("014447", "Fresh Puppy", "Veal with Vegetables 400 g", cats=DW)
add("014487", "Fresh Senior Dog", "Turkey with Vegetables 400 g", cats=DW)
for c, l in (("014457", "Veal 400 g"), ("014467", "Pork 400 g"), ("014477", "Chicken 400 g"), ("014497", "Trout 400 g"), ("014567", "Duck 400 g"), ("014577", "Lamb 400 g")):
    add(c, "Fresh Adult Dog", l, cats=DW, **({"flavor": "Veal"} if "Veal" in l else {"flavor": "Trout"} if "Trout" in l else {}))
# BWild Grain Free dog cans 400 g
add("012607", "BWild Grain Free Puppy", "Duck 400 g", cats=DW)
add("012617", "BWild Grain Free Adult Dog", "Lamb 400 g", cats=DW)
add("012627", "BWild Grain Free Adult Dog", "Salmon 400 g", cats=DW)
add("012647", "BWild Grain Free Adult Dog", "Turkey 400 g", cats=DW)
add("012637", "BWild Grain Free Mini Adult Dog", "Duck 400 g", cats=DW)
# Solo monoprotein dog paté 150 g + 400 g
for c, l in (("014137", "Chicken 150 g"), ("014147", "Turkey 150 g"), ("014177", "Venison 150 g"), ("014187", "Duck 150 g"), ("014407", "Beef 150 g"), ("014417", "Pork 150 g"),
             ("014217", "Chicken 400 g"), ("014227", "Turkey 400 g"), ("014237", "Lamb 400 g"), ("014247", "Tuna 400 g"), ("014437", "Duck 400 g")):
    add(c, "Solo Monoprotein Adult Dog Paté", l, cats=DW, attr_labels={"special-diet": "Monoprotein"})
# VetSolution dog wet
add("082017", "VetSolution Diabetic & Obesity Dog", "400 g", cats=DV, attr_labels={"special-diet": "Veterinary Diet", "health-feature": "Diabetic Support"})
for c, l in (("082037", "Tuna 400 g"), ("082047", "Duck 400 g"), ("082057", "Lamb 400 g")):
    add(c, "VetSolution Hypo Monoprotein Dog", l, cats=DV, attr_labels={"special-diet": "Veterinary Diet", "health-feature": "Allergy Relief"})
for c, n, hf in (("014507", "Dermatosis", "Skin & Coat Health"), ("014517", "Gastrointestinal", "Digestive Health"), ("014527", "Renal", "Kidney Care"), ("014537", "Recovery", "Recovery")):
    add(c, f"VetSolution {n} Dog", "150 g", cats=DV, attr_labels={"special-diet": "Veterinary Diet", "health-feature": hf})
# Gran Bonta (no brand page found yet; names from hafo, pack from hafo/cost)
add("041537", "Gran Bonta Adult Dog", "Meat 400 g", cats=DW, attr_labels={"lifestage": "Adult"})
add("041567", "Gran Bonta Adult Dog", "Meat 1230 g", cats=DW, attr_labels={"lifestage": "Adult"})
add("041577", "Gran Bonta Adult Dog", "Chicken & Turkey 1230 g", cats=DW, attr_labels={"lifestage": "Adult"})
add("041587", "Gran Bonta Adult Dog", "Chicken & Turkey 400 g", cats=DW, attr_labels={"lifestage": "Adult"})
add("041787", "Gran Bonta Chef Adult Dog", "Meat, Egg & Cheese 415 g", cats=DW, attr_labels={"lifestage": "Adult"})
add("041887", "Gran Bonta Chef Adult Dog", "Beef 1230 g", cats=DW, attr_labels={"lifestage": "Adult"})
# Leo's
add("390797", "Leo's Puppy Chunks", "Chicken & Turkey 415 g", cats=DW, attr_labels={"lifestage": "Puppy"},
    images=["https://www.monge.it/wp-content/uploads/2020/06/monge_cane_umido_leos_bocconi_con_pollo_e_tacchino_puppy.jpg"])
add("390807", "Leo's Adult Chunks", "Poultry 415 g", cats=DW, attr_labels={"lifestage": "Adult"})
# Special Dog Excellence
add("060347", "Excellence Medium Adult", "Lamb 1275 g", brand=SPECIAL, cats=DW, breed_size="Medium Breeds", attr_labels={"lifestage": "Adult"})
add("060357", "Excellence Maxi Adult", "Beef 1275 g", brand=SPECIAL, cats=DW, breed_size="Large Breeds", attr_labels={"lifestage": "Adult"})
# Lechat
add("061787", "Excellence Adult Cat", "Beef 100 g", brand=LECHAT, attr_labels={"lifestage": "Adult"})
for c, l in (("008607", "Beef 100 g"), ("008617", "Chicken with Vegetables 100 g"), ("008627", "Duck 100 g"), ("008637", "Salmon 100 g")):
    add(c, "Fresh Adult Cat Paté", l, brand=LECHAT, attr_labels={"lifestage": "Adult"})
# Gemon dog pouches 100 g
add("300607", "Adult Dog Pouch", "Beef & Ham 100 g", brand=GEMON, cats=DW, flavor="Beef", attr_labels={"lifestage": "Adult"})
add("300617", "Adult Dog Pouch", "Salmon 100 g", brand=GEMON, cats=DW, attr_labels={"lifestage": "Adult"})
add("300627", "Adult Dog Pouch", "Game 100 g", brand=GEMON, cats=DW, flavor="Wild Game", attr_labels={"lifestage": "Adult"})
add("300637", "Puppy & Junior Dog Pouch", "Chicken 100 g", brand=GEMON, cats=DW, attr_labels={"lifestage": "Puppy"})
add("300657", "Sterilised Dog Pouch", "Chicken & Turkey 100 g", brand=GEMON, cats=DW, attr_labels={"special-diet": "Sterilised", "lifestage": "Adult"},
    page="https://www.monge.it/en/product/gemon-all-breeds-sterilised-chunkies-with-chicken-and-turkey/")
for c, l in (("300417", "100 g"), ("300437", "100 g"), ("300447", "100 g"), ("300457", "100 g")):
    add(c, "Dog Pouch", l, brand=GEMON, cats=DW)
# Gemon cat
add("300687", "Adult Cat Pouch", "Pork 100 g", brand=GEMON, attr_labels={"lifestage": "Adult"})
add("300907", "Sterilised Cat Pouch", "Tuna 100 g", brand=GEMON, flavor="Tuna", attr_labels={"special-diet": "Sterilised", "lifestage": "Adult"})
add("300737", "Adult Cat Chunks", "Salmon & Shrimp 415 g", brand=GEMON, flavor="Salmon", attr_labels={"lifestage": "Adult"})
add("300747", "Sterilised Cat Chunks", "Tuna & White Fish 415 g", brand=GEMON, flavor="Tuna", attr_labels={"lifestage": "Adult", "special-diet": "Sterilised"})
add("299957", "Sterilised Cat Paté", "Turkey 400 g", brand=GEMON, attr_labels={"special-diet": "Sterilised", "lifestage": "Adult"})
add("299967", "Adult Cat Paté", "Beef 400 g", brand=GEMON, flavor="Beef", attr_labels={"lifestage": "Adult"})
add("301017M", "Adult Cat Mousse", "Chicken & Salmon 85 g", brand=GEMON, texture="Mousse", attr_labels={"lifestage": "Adult"})
add("301027M", "Adult Cat Mousse", "Chicken & Pork 85 g", brand=GEMON, texture="Mousse", attr_labels={"lifestage": "Adult"})
add("301037M", "Sterilised Cat Mousse", "Chicken & Liver 85 g", brand=GEMON, texture="Mousse", attr_labels={"special-diet": "Sterilised", "lifestage": "Adult"})
add("301047M", "Sterilised Cat Mousse", "Tuna & Pork 85 g", brand=GEMON, texture="Mousse", attr_labels={"special-diet": "Sterilised", "lifestage": "Adult"})
# Gemon dog cans / patés
add("387807", "Adult Dog Paté", "Beef & Tripe 400 g", brand=GEMON, cats=DW, flavor="Beef", attr_labels={"lifestage": "Adult"})
add("387817", "Adult Dog Paté", "Lamb 400 g", brand=GEMON, cats=DW, attr_labels={"lifestage": "Adult"})
add("387857", "Medium Adult Dog Chunks", "Veal & Liver 415 g", brand=GEMON, cats=DW, breed_size="Medium Breeds", flavor="Veal", attr_labels={"lifestage": "Adult"})
add("387867", "Puppy & Junior Dog Chunks", "Chicken & Turkey 415 g", brand=GEMON, cats=DW, attr_labels={"lifestage": "Puppy"})
add("387877", "Mini Adult Dog Chunks", "Chicken & Rice 415 g", brand=GEMON, cats=DW, breed_size="Small Breeds", attr_labels={"lifestage": "Adult"})
add("387907", "Maxi Adult Dog Paté", "Beef & Rice 1250 g", brand=GEMON, cats=DW, breed_size="Large Breeds", attr_labels={"lifestage": "Adult"})
add("387917", "Medium Adult Dog Paté", "Lamb & Rice 1250 g", brand=GEMON, cats=DW, breed_size="Medium Breeds", attr_labels={"lifestage": "Adult"})
add("387927", "Medium Adult Dog Paté", "Chicken & Turkey 1250 g", brand=GEMON, cats=DW, breed_size="Medium Breeds", attr_labels={"lifestage": "Adult"})
# Gemon dry (unpriced on hafo: size missing) — planned so they land in the unpriced CSV with a proper name
add("387947", "Maxi Adult", "Chicken 20 kg", brand=GEMON, family=1, cats=DD, ptype="dry", breed_size="Large Breeds")
add("387957", "All Breeds Puppy & Junior", "Chicken & Rice 15 kg", brand=GEMON, family=1, cats=DD, ptype="dry", breed_size="All Breeds", attr_labels={"lifestage": "Puppy"})
add("387967", "All Breeds Puppy & Junior", "Chicken & Rice 15 kg (2)", brand=GEMON, family=1, cats=DD, ptype="dry", breed_size="All Breeds", attr_labels={"lifestage": "Puppy"})
# Monge Gift treats (one product per row: each carries its own claim)
for c, n, cats, hf in (
        ("08523MG", "Gift Soft Sticks Adult Cat Rabbit with Sage", CT, "Heart Care"),
        ("08524MG", "Gift Soft Sticks Kitten Trout with Chamomile", CT, None),
        ("08525MG", "Gift Soft Sticks Adult Cat Pork with Rosehips & Cheese", CT, None),
        ("08526MG", "Gift Soft Sticks Hairball Cat Salmon with Artichoke", CT, "Hairball Control"),
        ("08527MG", "Gift Soft Sticks Skin Support Cat Cod", CT, "Skin & Coat Health"),
        ("08528MG", "Gift Soft Sticks Sterilised Cat Duck with Lemon Balm & Cranberries", CT, None),
        ("08539MG", "Gift Sticks Adult Dog Rabbit with Betaglucans", DT, "Immune Support"),
        ("08540MG", "Gift Sticks Adult Dog Trout with Turmeric", DT, "Weight Management"),
        ("08541MG", "Gift Sticks Puppy & Junior Pork with Milk", DT, "Dental & Breath Care"),
        ("08542MG", "Gift Sticks Adult Dog Lamb with Chestnuts", DT, None),
        ("08543MG", "Gift Sticks Adult Dog Salmon with Aloe Vera", DT, "Skin & Coat Health"),
        ("08544MG", "Gift Sticks Adult Dog Duck with Spirulina", DT, "High-Energy"),
        ("08500MG", "Gift Filled & Crunchy Dental Cat Rabbit with Peppermint", CT, "Dental & Breath Care"),
        ("08501MG", "Gift Filled & Crunchy Kitten Trout with Milk", CT, None),
        ("08502MG", "Gift Filled & Crunchy Adult Cat Pork with Cheese", CT, "Appetite Stimulation"),
        ("08503MG", "Gift Filled & Crunchy Hairball Cat Salmon with Catnip", CT, "Hairball Control"),
        ("08504MG", "Gift Filled & Crunchy Skin Support Cat Cod with Aloe Vera", CT, "Skin & Coat Health"),
        ("08505MG", "Gift Filled & Crunchy Sterilised Cat Duck with Cranberries", CT, "Heart Care"),
        ("08513MG", "Gift Meat Minis Hairball Cat Salmon with Plum", CT, "Hairball Control"),
        ("08514MG", "Gift Meat Minis Dental Cat Rabbit with Apple", CT, "Dental & Breath Care"),
        ("08515MG", "Gift Meat Minis Kitten Trout with Blueberries", CT, None),
        ("08516MG", "Gift Meat Minis Adult Cat Pork with Pineapple & Cheese", CT, "Heart Care"),
        ("08518MG", "Gift Meat Minis Sterilised Cat Duck with Pomegranate & Cranberries", CT, None)):
    al = {"health-feature": hf, "special-diet": "Grain-Free"}
    if "Sterilised" in n:
        al["special-diet"] = "Sterilised"
    if "Kitten" in n:
        al["lifestage"] = "Kitten"
    elif "Puppy" in n:
        al["lifestage"] = "Puppy"
    else:
        al["lifestage"] = "Adult"
    add(c, n, "", family=3, cats=cats, ptype="treats", attr_labels=al, flavor=("Trout" if "Trout" in n else None))

json.dump(G, open(os.path.join(ROOT, ".siruk-cache/monge-groups.json"), "w"), ensure_ascii=False, indent=1)
print(len(G), "rows grouped")
