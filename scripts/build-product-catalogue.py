#!/usr/bin/env python3
"""Turn the raw invoice-line ledger into a deduplicated product catalogue.

One row per article code (the supplier's SKU), carrying the brand, a cleaned
name, species and category. Rows whose brand cannot be established go to the
needs-review file instead.
"""
import csv, re, sys, collections

SRC = "csv/invoices/2026-09-lines-raw.csv"
OUT = "csv/invoices/2026-09-products.csv"
REVIEW = "csv/invoices/2026-09-products-needs-review.csv"

# Brand markers found in the description, most specific first.
BRAND_PATTERNS = [
    (r"MONGE GIFT", "Monge"), (r"BWILD|Bwild", "Monge"), (r"GRAN BONTA", "Monge"),
    (r"MONGE LEO'?S", "Monge"), (r"MONGE|Monge", "Monge"),
    (r"Gemon|GEMON", "Gemon"), (r"SIMBA|Simba", "Simba"),
    (r"Lechat|LECHAT", "Lechat"), (r"SPECIAL DOG", "Special Dog"),
    (r"LACTOL", "Lactol"),
    (r"Rolf Club", "Rolf Club"), (r"Inspector", "Inspector"),
    (r"Գելմենտալ|Ճիճվամուղ.*E\d|/E\d{3}", "Gelmintal"),
    (r"Ինսեկտալ|ինսեկտալ|/N\d{3}", "Insectal"),
    (r"Cliny|Ag\+", "Cliny"), (r"Mr\.Fresh", "Mr. Fresh"),
    (r"TRADITIONAL PLUS|ATAMI LINE|DO IT YOURSELF|DERMOBRUSH", "Iv San Bernard"),
    (r"Denta ?Fun|DENTAFUN|DENTAL,|PREMIO|TASTIES|BE NORDIC|CityStyle|Silver Reflect|"
     r"Simple'?n'?Clean|Happy Hearts|Happy Rolls|Mini Bones|Bony Mix|Be Eco|"
     r"SUSHI ROLLS|Vegan|DOG ACTIVITY|Aqua Toy|Y-harness|Premium Trekking|"
     r"Active Comfort|Snack-Snake|SnackHantel|Stop It Indoor|NO STRESS", "Trixie"),
    (r"4 ?ԹԱԹ", "4 Թաթ"), (r"ՄՅԱՈՒ", "Մյաու"),
    (r"Moor", "Moor"), (r"Kormell", "Kormell"), (r"Justin", "Justin"),
    (r"SMART", "SMART"), (r"Comfy", "Comfy"), (r"DOGMAN", "Dogman"),
    (r"Интеко", "Интеко"), (r"Отидез|Дезацид", "Api-San"),
]
# Article-code suffix → brand, used only when the text gives nothing.
SUFFIX_BRAND = [("MG", "Monge"), ("IVS", "Iv San Bernard"), ("Tx", "Trixie"),
                ("TXN", "Trixie"), ("PCHL", "Api-San"), ("AQ", "Comfy")]

def brand_of(desc, code):
    for pat, name in BRAND_PATTERNS:
        if re.search(pat, desc):
            return name, "description"
    for suf, name in SUFFIX_BRAND:
        if code.endswith(suf):
            return name, f"article-code suffix '{suf}'"
    return "", ""

def species_of(d):
    dog = re.search(r"\bշն\b|շների|շն\.|շան|շնիկ|Շան", d)
    cat = re.search(r"կատու|կատվ|կատ\.|Կատու|կատ\b", d)
    if dog and cat: return "Dog & Cat"
    if dog: return "Dog"
    if cat: return "Cat"
    return ""

CATEGORY_RULES = [
    (r"Լցանյութ|Ավազ", "Cat litter"),
    (r"Պահածո|Պաուչ|Պաշտետ|ժելե|ռագու|MOUSSE|Կեր .*\d+\s*գ\b", "Wet food"),
    (r"Կեր .*\d+([.,]\d+)?\s*կգ", "Dry food"),
    (r"Հյուրասիրություն|Ձողիկներ|Ոսկոր|Բարձիկներ|Մսային|Չորիկներ|Թխվածք|"
     r"Պեչենի|Ֆիլե|Խորտիկներ|Չլե|Գնդիկներ|Մածուկ|Չուպաչուպս", "Treats"),
    (r"Խաղալիք|Փափուկ խաղալիք", "Toys"),
    (r"Կաթիլներ|Հաբեր|Ցողարկիչ|Վիտամին|Կերային հավելում|Ճիճվամուղ|Օշարակ|"
     r"Լոսիոն|Հեղուկ|գել|Փոշի կաթ|դեղատուփ|Բալզամ աչքերի", "Vitamins & supplements"),
    (r"Շամպուն|Սանր|Մկրատ|Խոզանակ|Մասաժոր|Լիպկի|Օծանելիք|անձեռոցիկ|Ատամի", "Grooming"),
    (r"Վզնոց|Զգեստիկ|Շլեյկա|Դնչկալ|Մեղալիոն|Գուլպա|Կիսավարտիք|Տակդիր|Շերեփ|"
     r"Կերաման|Ջրաման|Տուալետ|Սկուտեղ|Գորգ|Ներքնակ|Տուփ|Աղբի տոպրակ|Սրբիչ|"
     r"Լոգանքի|ճանկելու|Կատվախոտ|անանուխ|Խոտի սերմեր|Հակասթրես", "Accessories"),
]
def category_of(d):
    for pat, name in CATEGORY_RULES:
        if re.search(pat, d):
            return name
    return ""

rows = list(csv.DictReader(open(SRC)))
by_code = collections.OrderedDict()
for r in rows:
    code = r["Article Code"].strip()
    d = r["Description (as printed)"]
    e = by_code.setdefault(code, {"desc": d, "price": r["Unit Price (AMD)"],
                                  "qty": 0.0, "srcs": set(), "dates": set()})
    # keep the longest description seen (duplicate copies sometimes truncate)
    if len(d) > len(e["desc"]): e["desc"] = d
    try: e["qty"] += float(r["Qty"] or 0)
    except ValueError: pass
    e["srcs"].add(r["Source PDF"]); e["dates"].add(r["Date"])

prod, review = [], []
for code, e in by_code.items():
    d = e["desc"]
    brand, how = brand_of(d, code)
    row = {"Article Code": code, "Brand": brand,
           "Product Name (as printed)": d,
           "Species": species_of(d), "Category": category_of(d),
           "Buy Price (AMD)": e["price"], "Qty Received": int(e["qty"]) if e["qty"]==int(e["qty"]) else e["qty"],
           "Sale Price (AMD)": "", "Invoice Date": sorted(e["dates"])[0],
           "Source": sorted(e["srcs"])[0], "Brand Source": how}
    (prod if brand else review).append(row)

FIELDS = list(prod[0].keys())
for path, data in ((OUT, prod), (REVIEW, review)):
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS); w.writeheader(); w.writerows(data)

print(f"{len(by_code)} unique article codes from {len(rows)} invoice lines")
print(f"  {len(prod):>4} with an identified brand  -> {OUT}")
print(f"  {len(review):>4} needing review           -> {REVIEW}")
print("\nBy brand:")
for b, n in collections.Counter(r["Brand"] for r in prod).most_common():
    print(f"  {b:<18} {n:>4}")
