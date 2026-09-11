#!/usr/bin/env python3
"""Build the Simba (Monge) wet-food payloads + ru/hy translation files.

Source of every English sentence: the official spec sheets linked from
monge.it product pages (`.siruk-cache/simba-pdf/*.pdf`, read 2026-09-10).
Prices: hafo rows in `.siruk-cache/simba-hafo.json`; cost: the CSV.
Stock: CSV qty, with the placeholder rule qty 1 -> 10 (user, 2026-09-10).

Writes .siruk-cache/simba-<key>.json (payload) and simba-<key>-{ru,hy}.json
(translations; the SKU->text map is keyed by SKU so it works before the id
is known -- set-translation.py only needs SKUs).
"""
import json, html

C = ".siruk-cache"
hafo = {r["code"]: r for r in json.load(open(f"{C}/simba-hafo.json"))}
media = dict(l.split() for l in open(f"{C}/simba-img/media-ids.txt").read().split("\n") if l.strip())
media = {k: int(v) for k, v in media.items()}
menu = json.load(open("reference/attribute-values.json"))

def v(attr, label):
    i = menu[attr]["values"][label]
    assert i, (attr, label)
    return i

def price(code):
    r = hafo[code]
    assert r["confirmed"] and r["src"] == "variant" and r["wholesale"] == r["cost"], code
    assert r["price"] > r["cost"], code
    return r["price"], r["cost"]

def stock(qty):
    return 10 if qty == 1 else qty

P = lambda s: f"<p>{s}</p>"
LI = lambda items: "<ul>" + "".join(f"<li>{x}</li>" for x in items) + "</ul>"
def TABLE(head, rows):
    h = "<tr>" + "".join(f"<th>{c}</th>" for c in head) + "</tr>"
    b = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows)
    return f"<table>{h}{b}</table>"

# ---------------------------------------------------------------- texts (EN)
DOG_TABLE = TABLE(["Weight of adult dog (kg)", "5-9", "9-15", "15-25", ">25"],
                  [["Daily feed (grams/day)", "400-620", "620-900", "900-1350", ">1350"]])
CAT_TABLE = TABLE(["Weight of adult cat (kg)", "4", "5", "6"],
                  [["Daily feed (grams/day)", "200", "220", "250"]])
PATE_TABLE = TABLE(["Weight of adult dog (kg)", "5-9", "9-15"],
                   [["Daily feed (grams/day)", "350-550 g", "550-810 g"]])

DOG_FEED = P("<strong>Instructions for use:</strong> To be served at room temperature. Leave always available to the animal fresh and clean water. Refrigerate unused portion and consume within 2 days. Recommended daily feeding intakes (see table) may be split into 2 daily meals. Do not open the can, if it is dented or swollen. Animal food, not suitable for human consumption.") + P("<strong>Recommended daily feeding intakes (grams/day):</strong>") + DOG_TABLE
CAT_FEED = P("<strong>Instructions for use:</strong> To be served at room temperature. Fresh and clean water should be available at all times. Storage conditions: once opened, keep refrigerated and consume within 2 days. Feeding instructions: for a medium size cat (4 kg), 200 grams of product daily, shared in 2 meals. Do not open the can, if it is dented or swollen. Animal food, not suitable for human consumption.") + P("<strong>Recommended daily feeding intakes (grams/day):</strong>") + CAT_TABLE
PATE_FEED = P("<strong>Instructions for use:</strong> To be served at room temperature. Leave always available to the animal fresh and clean water. Keep in cool and dry place. Refrigerate unused portion and consume within 2 days. Recommended daily feeding intakes: for an adult medium size dog (10 kg) with normal activity, give 600 grams of product, split into 2 daily meals. Do not open the alutray, if it is dented or swollen. Animal food, not suitable for human consumption.") + P("<strong>Recommended daily feeding intakes (grams/day):</strong>") + PATE_TABLE

DOG_ADD = "Vitamin A (Retinyl Acetate) 2000 IU, Vitamin D3 200 IU, Vitamin E (all-rac-alpha-tocopheryl acetate 3a700i) 5 mg."
CAT_ADD = "Vitamin A (Retinyl Acetate) 2000 IU, Vitamin D3 160 IU, Vitamin E (all rac-alpha-tocopheryl-acetate 3a700i) 5 mg."
PATE_ADD = "Vitamin A (Retinyl Acetate) 2500 IU, Vitamin D3 200 IU, Vitamin E (all-rac-alpha-tocopheryl acetate 3a700i) 5 mg."
DOG_AN = "crude protein 8.0%, crude fibre 1.21%, crude fat 6.0%, crude ash 3%, moisture 80.0%."
CAT_AN = "crude protein 8.0%, crude fibre 0.8%, crude fat 6.0%, crude ash 2.5%, moisture 80%."
PATE_AN = "crude protein 9%, crude fibre 0.4%, crude fat 7.5%, crude ash 2.1%, moisture 81%."

def ingredients(comp, an, add):
    return P(f"<strong>Composition:</strong> {comp}") + P(f"<strong>Analytical constituents:</strong> {an}") + P(f"<strong>Additives (nutritional additives/kg):</strong> {add}")

def about_dog(flav, src, pack):
    return P(f"SIMBA DOG CHUNKS WITH {flav.upper()} is a complete pet food for adult dogs of all sizes. Chunks in gravy formulated with quality ingredients such as {src}, are oven-baked to enhance their natural taste and stimulate your pet's daily appetite. The formulation has been developed with a specific combination of vitamins A-D3-E to meet the nutritional requirements of your pet's daily needs. No added colours or preservatives.") + \
        LI(["Complete pet food for adult dogs of all sizes", "Chunks in gravy, oven cooked", "No added colours or preservatives", "No cruelty test", "Made in Italy", f"Pack size: {pack}"])

def about_cat(flav, src, pack):
    return P(f"SIMBA CAT CHUNKIES WITH {flav.upper()} is a complete pet food for adult cat. Chunks in gravy formulated with quality ingredients such as {src}, are oven-baked to enhance their natural taste and stimulate your pet's daily appetite. The formulation has been developed with a specific combination of vitamins A-D3-E to meet the nutritional requirements of your pet's daily needs. No added colours or preservatives.") + \
        LI(["Complete pet food for adult cats", "Chunks in gravy, oven cooked", "No added colours or preservatives", "No cruelty test", "Made in Italy", f"Pack size: {pack}"])

def about_pate(flav, src, pack):
    return P(f"SIMBA DOG PATÉ WITH {flav.upper()} is a complete pet food for adult dogs of all sizes. Paté formulated with quality ingredients such as {src}, steam cooked to enhance their natural taste and stimulate your pet's daily appetite. The formulation has been developed with a specific combination of vitamins A-D3-E to meet the nutritional requirements of your pet's daily needs. No added colours or preservatives.") + \
        LI(["Complete pet food for adult dogs of all sizes", "Paté, steam cooked", "No added colours or preservatives", "No cruelty test", "Made in Italy", f"Pack size: {pack}"])

# ---------------------------------------------------------------- texts (RU / HY)
RU_DOG_TABLE = TABLE(["Вес взрослой собаки (кг)", "5-9", "9-15", "15-25", ">25"], [["Суточная норма (г/день)", "400-620", "620-900", "900-1350", ">1350"]])
HY_DOG_TABLE = TABLE(["Չափահաս շան քաշը (կգ)", "5-9", "9-15", "15-25", ">25"], [["Օրական չափաբաժին (գ/օր)", "400-620", "620-900", "900-1350", ">1350"]])
RU_CAT_TABLE = TABLE(["Вес взрослой кошки (кг)", "4", "5", "6"], [["Суточная норма (г/день)", "200", "220", "250"]])
HY_CAT_TABLE = TABLE(["Չափահաս կատվի քաշը (կգ)", "4", "5", "6"], [["Օրական չափաբաժին (գ/օր)", "200", "220", "250"]])
RU_PATE_TABLE = TABLE(["Вес взрослой собаки (кг)", "5-9", "9-15"], [["Суточная норма (г/день)", "350-550 г", "550-810 г"]])
HY_PATE_TABLE = TABLE(["Չափահաս շան քաշը (կգ)", "5-9", "9-15"], [["Օրական չափաբաժին (գ/օր)", "350-550 գ", "550-810 գ"]])

RU_DOG_FEED = P("<strong>Инструкция по применению:</strong> Подавать при комнатной температуре. У животного всегда должна быть свежая и чистая вода. Неиспользованную порцию хранить в холодильнике и употребить в течение 2 дней. Рекомендуемую суточную норму (см. таблицу) можно разделить на 2 кормления. Не открывайте банку, если она помята или вздута. Корм для животных, не предназначен для употребления человеком.") + P("<strong>Рекомендуемая суточная норма (г/день):</strong>") + RU_DOG_TABLE
HY_DOG_FEED = P("<strong>Օգտագործման ցուցումներ.</strong> Մատուցել սենյակային ջերմաստիճանում։ Կենդանու համար միշտ հասանելի պահեք թարմ և մաքուր ջուր։ Չօգտագործված մասը պահեք սառնարանում և օգտագործեք 2 օրվա ընթացքում։ Առաջարկվող օրական չափաբաժինը (տես աղյուսակը) կարելի է բաժանել 2 կերակրման։ Մի բացեք պահածոն, եթե այն ճմռթված կամ ուռած է։ Կենդանիների կեր, մարդու սպառման համար պիտանի չէ։") + P("<strong>Առաջարկվող օրական չափաբաժին (գ/օր).</strong>") + HY_DOG_TABLE
RU_CAT_FEED = P("<strong>Инструкция по применению:</strong> Подавать при комнатной температуре. Свежая и чистая вода должна быть доступна постоянно. Условия хранения: после вскрытия хранить в холодильнике и употребить в течение 2 дней. Рекомендации по кормлению: кошке среднего размера (4 кг) — 200 г продукта в день, разделённые на 2 кормления. Не открывайте банку, если она помята или вздута. Корм для животных, не предназначен для употребления человеком.") + P("<strong>Рекомендуемая суточная норма (г/день):</strong>") + RU_CAT_TABLE
HY_CAT_FEED = P("<strong>Օգտագործման ցուցումներ.</strong> Մատուցել սենյակային ջերմաստիճանում։ Թարմ և մաքուր ջուրը միշտ պետք է հասանելի լինի։ Պահպանման պայմաններ. բացելուց հետո պահեք սառնարանում և օգտագործեք 2 օրվա ընթացքում։ Կերակրման ցուցումներ. միջին չափի կատվի համար (4 կգ)՝ օրական 200 գ, բաժանված 2 կերակրման։ Մի բացեք պահածոն, եթե այն ճմռթված կամ ուռած է։ Կենդանիների կեր, մարդու սպառման համար պիտանի չէ։") + P("<strong>Առաջարկվող օրական չափաբաժին (գ/օր).</strong>") + HY_CAT_TABLE
RU_PATE_FEED = P("<strong>Инструкция по применению:</strong> Подавать при комнатной температуре. У животного всегда должна быть свежая и чистая вода. Хранить в сухом прохладном месте. Неиспользованную порцию хранить в холодильнике и употребить в течение 2 дней. Рекомендуемая суточная норма: взрослой собаке среднего размера (10 кг) с нормальной активностью — 600 г продукта в день, разделённые на 2 кормления. Не открывайте ламистер, если он помят или вздут. Корм для животных, не предназначен для употребления человеком.") + P("<strong>Рекомендуемая суточная норма (г/день):</strong>") + RU_PATE_TABLE
HY_PATE_FEED = P("<strong>Օգտագործման ցուցումներ.</strong> Մատուցել սենյակային ջերմաստիճանում։ Կենդանու համար միշտ հասանելի պահեք թարմ և մաքուր ջուր։ Պահել չոր և զով տեղում։ Չօգտագործված մասը պահեք սառնարանում և օգտագործեք 2 օրվա ընթացքում։ Առաջարկվող օրական չափաբաժին. միջին չափի չափահաս շան համար (10 կգ) սովորական ակտիվությամբ՝ օրական 600 գ, բաժանված 2 կերակրման։ Մի բացեք սկուտեղը, եթե այն ճմռթված կամ ուռած է։ Կենդանիների կեր, մարդու սպառման համար պիտանի չէ։") + P("<strong>Առաջարկվող օրական չափաբաժին (գ/օր).</strong>") + HY_PATE_TABLE

RU_DOG_AN = "сырой протеин 8,0%, сырая клетчатка 1,21%, сырой жир 6,0%, сырая зола 3%, влага 80,0%."
HY_DOG_AN = "հում սպիտակուց 8,0%, հում բջջանյութ 1,21%, հում ճարպ 6,0%, հում մոխիր 3%, խոնավություն 80,0%։"
RU_CAT_AN = "сырой протеин 8,0%, сырая клетчатка 0,8%, сырой жир 6,0%, сырая зола 2,5%, влага 80%."
HY_CAT_AN = "հում սպիտակուց 8,0%, հում բջջանյութ 0,8%, հում ճարպ 6,0%, հում մոխիր 2,5%, խոնավություն 80%։"
RU_PATE_AN = "сырой протеин 9%, сырая клетчатка 0,4%, сырой жир 7,5%, сырая зола 2,1%, влага 81%."
HY_PATE_AN = "հում սպիտակուց 9%, հում բջջանյութ 0,4%, հում ճարպ 7,5%, հում մոխիր 2,1%, խոնավություն 81%։"
RU_DOG_ADD = "витамин A (ретинилацетат) 2000 МЕ, витамин D3 200 МЕ, витамин E (all-rac-альфа-токоферилацетат 3a700i) 5 мг."
HY_DOG_ADD = "վիտամին A (ռետինիլ ացետատ) 2000 ՄՄ, վիտամին D3 200 ՄՄ, վիտամին E (all-rac-ալֆա-տոկոֆերիլ ացետատ 3a700i) 5 մգ։"
RU_CAT_ADD = "витамин A (ретинилацетат) 2000 МЕ, витамин D3 160 МЕ, витамин E (all-rac-альфа-токоферилацетат 3a700i) 5 мг."
HY_CAT_ADD = "վիտամին A (ռետինիլ ացետատ) 2000 ՄՄ, վիտամին D3 160 ՄՄ, վիտամին E (all-rac-ալֆա-տոկոֆերիլ ացետատ 3a700i) 5 մգ։"
RU_PATE_ADD = "витамин A (ретинилацетат) 2500 МЕ, витамин D3 200 МЕ, витамин E (all-rac-альфа-токоферилацетат 3a700i) 5 мг."
HY_PATE_ADD = "վիտամին A (ռետինիլ ացետատ) 2500 ՄՄ, վիտամին D3 200 ՄՄ, վիտամին E (all-rac-ալֆա-տոկոֆերիլ ացետատ 3a700i) 5 մգ։"

def ru_ing(comp, an, add):
    return P(f"<strong>Состав:</strong> {comp}") + P(f"<strong>Гарантированный анализ:</strong> {an}") + P(f"<strong>Добавки (пищевые добавки/кг):</strong> {add}")
def hy_ing(comp, an, add):
    return P(f"<strong>Բաղադրություն.</strong> {comp}") + P(f"<strong>Վերլուծական բաղադրիչներ.</strong> {an}") + P(f"<strong>Հավելումներ (սննդային հավելումներ/կգ).</strong> {add}")

def ru_about_dog(flav_ru, src_ru, pack_ru):
    return P(f"SIMBA DOG КУСОЧКИ С {flav_ru.upper()} — полнорационный корм для взрослых собак всех размеров. Кусочки в соусе, приготовленные из качественных ингредиентов, таких как {src_ru}, запечены в духовке, чтобы подчеркнуть их натуральный вкус и стимулировать ежедневный аппетит вашего питомца. Рецептура разработана со специальной комбинацией витаминов A-D3-E для удовлетворения ежедневных потребностей животного в питательных веществах. Без добавления красителей и консервантов.") + \
        LI(["Полнорационный корм для взрослых собак всех размеров", "Кусочки в соусе, запечённые в духовке", "Без добавления красителей и консервантов", "Не тестируется на животных", "Сделано в Италии", f"Упаковка: {pack_ru}"])
def hy_about_dog(flav_hy, src_hy, pack_hy):
    return P(f"SIMBA DOG {flav_hy.upper()} ԿՏՈՐՆԵՐ՝ լիարժեք կեր բոլոր չափերի չափահաս շների համար։ Սոուսով կտորները, պատրաստված որակյալ բաղադրիչներից, ինչպիսին է {src_hy}, թխված են ջեռոցում՝ ընդգծելու դրանց բնական համը և խթանելու ձեր ընտանի կենդանու ամենօրյա ախորժակը։ Բաղադրատոմսը մշակվել է A-D3-E վիտամինների հատուկ համակցությամբ՝ կենդանու ամենօրյա սննդային պահանջները բավարարելու համար։ Առանց ավելացված ներկանյութերի և պահածոյացնող նյութերի։") + \
        LI(["Լիարժեք կեր բոլոր չափերի չափահաս շների համար", "Սոուսով կտորներ, թխված ջեռոցում", "Առանց ավելացված ներկանյութերի և պահածոյացնող նյութերի", "Չի փորձարկվում կենդանիների վրա", "Արտադրված է Իտալիայում", f"Փաթեթավորում՝ {pack_hy}"])
def ru_about_cat(flav_ru, src_ru, pack_ru):
    return P(f"SIMBA CAT КУСОЧКИ С {flav_ru.upper()} — полнорационный корм для взрослых кошек. Кусочки в соусе, приготовленные из качественных ингредиентов, таких как {src_ru}, запечены в духовке, чтобы подчеркнуть их натуральный вкус и стимулировать ежедневный аппетит вашего питомца. Рецептура разработана со специальной комбинацией витаминов A-D3-E для удовлетворения ежедневных потребностей животного в питательных веществах. Без добавления красителей и консервантов.") + \
        LI(["Полнорационный корм для взрослых кошек", "Кусочки в соусе, запечённые в духовке", "Без добавления красителей и консервантов", "Не тестируется на животных", "Сделано в Италии", f"Упаковка: {pack_ru}"])
def hy_about_cat(flav_hy, src_hy, pack_hy):
    return P(f"SIMBA CAT {flav_hy.upper()} ԿՏՈՐՆԵՐ՝ լիարժեք կեր չափահաս կատուների համար։ Սոուսով կտորները, պատրաստված որակյալ բաղադրիչներից, ինչպիսին է {src_hy}, թխված են ջեռոցում՝ ընդգծելու դրանց բնական համը և խթանելու ձեր ընտանի կենդանու ամենօրյա ախորժակը։ Բաղադրատոմսը մշակվել է A-D3-E վիտամինների հատուկ համակցությամբ՝ կենդանու ամենօրյա սննդային պահանջները բավարարելու համար։ Առանց ավելացված ներկանյութերի և պահածոյացնող նյութերի։") + \
        LI(["Լիարժեք կեր չափահաս կատուների համար", "Սոուսով կտորներ, թխված ջեռոցում", "Առանց ավելացված ներկանյութերի և պահածոյացնող նյութերի", "Չի փորձարկվում կենդանիների վրա", "Արտադրված է Իտալիայում", f"Փաթեթավորում՝ {pack_hy}"])
def ru_about_pate(flav_ru, src_ru, pack_ru):
    return P(f"SIMBA DOG ПАШТЕТ С {flav_ru.upper()} — полнорационный корм для взрослых собак всех размеров. Паштет, приготовленный из качественных ингредиентов, таких как {src_ru}, приготовлен на пару, чтобы подчеркнуть натуральный вкус и стимулировать ежедневный аппетит вашего питомца. Рецептура разработана со специальной комбинацией витаминов A-D3-E для удовлетворения ежедневных потребностей животного в питательных веществах. Без добавления красителей и консервантов.") + \
        LI(["Полнорационный корм для взрослых собак всех размеров", "Паштет, приготовленный на пару", "Без добавления красителей и консервантов", "Не тестируется на животных", "Сделано в Италии", f"Упаковка: {pack_ru}"])
def hy_about_pate(flav_hy, src_hy, pack_hy):
    return P(f"SIMBA DOG {flav_hy.upper()} ՊԱՇՏԵՏ՝ լիարժեք կեր բոլոր չափերի չափահաս շների համար։ Պաշտետը, պատրաստված որակյալ բաղադրիչներից, ինչպիսին է {src_hy}, եփված է գոլորշով՝ ընդգծելու բնական համը և խթանելու ձեր ընտանի կենդանու ամենօրյա ախորժակը։ Բաղադրատոմսը մշակվել է A-D3-E վիտամինների հատուկ համակցությամբ՝ կենդանու ամենօրյա սննդային պահանջները բավարարելու համար։ Առանց ավելացված ներկանյութերի և պահածոյացնող նյութերի։") + \
        LI(["Լիարժեք կեր բոլոր չափերի չափահաս շների համար", "Պաշտետ, եփված գոլորշով", "Առանց ավելացված ներկանյութերի և պահածոյացնող նյութերի", "Չի փորձարկվում կենդանիների վրա", "Արտադրված է Իտալիայում", f"Փաթեթավորում՝ {pack_hy}"])

# ---------------------------------------------------------------- flavour tables
# key: flavor label, en source phrase, composition, media key, ingredient value,
#      ru flavour (instrumental), ru source, ru composition, hy flavour, hy source, hy composition
DOG = {
 "beef": dict(flavor="Beef", src="beef, source of protein and minerals",
     comp="meat and animal derivatives (beef 6%), cereals, eggs and egg derivatives, minerals.", img="dog-beef", ing="Beef",
     ru_f="говядиной", ru_src="говядина, источник белка и минералов", ru_comp="мясо и продукты животного происхождения (говядина 6%), злаки, яйца и яичные продукты, минеральные вещества.",
     hy_f="տավարի մսով", hy_src="տավարի միսը՝ սպիտակուցի և հանքանյութերի աղբյուր", hy_comp="միս և կենդանական ծագման մթերքներ (տավարի միս 6%), հացահատիկ, ձու և ձվի մթերքներ, հանքային նյութեր։"),
 "chicken-turkey": dict(flavor="Chicken & Turkey", src="chicken and turkey, source of protein and minerals",
     comp="meat and animal derivatives (chicken 10%, turkey 10%), cereals, eggs and egg derivatives, minerals.", img="dog-chicken-turkey", ing="Chicken",
     ru_f="курицей и индейкой", ru_src="курица и индейка, источник белка и минералов", ru_comp="мясо и продукты животного происхождения (курица 10%, индейка 10%), злаки, яйца и яичные продукты, минеральные вещества.",
     hy_f="հավով և հնդկահավով", hy_src="հավն ու հնդկահավը՝ սպիտակուցի և հանքանյութերի աղբյուր", hy_comp="միս և կենդանական ծագման մթերքներ (հավ 10%, հնդկահավ 10%), հացահատիկ, ձու և ձվի մթերքներ, հանքային նյութեր։"),
 "lamb": dict(flavor="Lamb", src="lamb, source of protein and minerals",
     comp="meat and animal derivatives (lamb 5%), cereals, eggs and egg derivatives, minerals.", img="dog-lamb", ing="Lamb",
     ru_f="ягнёнком", ru_src="ягнёнок, источник белка и минералов", ru_comp="мясо и продукты животного происхождения (ягнёнок 5%), злаки, яйца и яичные продукты, минеральные вещества.",
     hy_f="գառան մսով", hy_src="գառան միսը՝ սպիտակուցի և հանքանյութերի աղբյուր", hy_comp="միս և կենդանական ծագման մթերքներ (գառան միս 5%), հացահատիկ, ձու և ձվի մթերքներ, հանքային նյութեր։"),
 "wild-game": dict(flavor="Wild Game", src="wild game, source of protein and minerals",
     comp="meat and animal derivatives (wild game 6%), cereals, eggs and egg derivatives, minerals.", img="dog-wild-game", ing=None,
     ru_f="дичью", ru_src="дичь, источник белка и минералов", ru_comp="мясо и продукты животного происхождения (дичь 6%), злаки, яйца и яичные продукты, минеральные вещества.",
     hy_f="որսամսով", hy_src="որսամիսը՝ սպիտակուցի և հանքանյութերի աղբյուր", hy_comp="միս և կենդանական ծագման մթերքներ (որսամիս 6%), հացահատիկ, ձու և ձվի մթերքներ, հանքային նյութեր։"),
 "beef-veg": dict(flavor="Beef & Vegetables", src="beef and vegetables, source of protein and fibres",
     comp="meat and animal derivatives (beef 8%), vegetables (4.2%), cereals, eggs and egg derivatives, minerals.", img="dog-beef-veg", ing="Beef",
     ru_f="говядиной и овощами", ru_src="говядина и овощи, источник белка и клетчатки", ru_comp="мясо и продукты животного происхождения (говядина 8%), овощи (4,2%), злаки, яйца и яичные продукты, минеральные вещества.",
     hy_f="տավարի մսով և բանջարեղենով", hy_src="տավարի միսն ու բանջարեղենը՝ սպիտակուցի և բջջանյութի աղբյուր", hy_comp="միս և կենդանական ծագման մթերքներ (տավարի միս 8%), բանջարեղեն (4,2%), հացահատիկ, ձու և ձվի մթերքներ, հանքային նյութեր։"),
}
CAT = {
 "chicken": dict(flavor="Chicken", src="chicken, source of protein and minerals",
     comp="meat and animal derivatives (chicken 12%), cereals, eggs and egg derivatives, minerals.", img="cat-chicken", ing="Chicken",
     ru_f="курицей", ru_src="курица, источник белка и минералов", ru_comp="мясо и продукты животного происхождения (курица 12%), злаки, яйца и яичные продукты, минеральные вещества.",
     hy_f="հավով", hy_src="հավը՝ սպիտակուցի և հանքանյութերի աղբյուր", hy_comp="միս և կենդանական ծագման մթերքներ (հավ 12%), հացահատիկ, ձու և ձվի մթերքներ, հանքային նյութեր։"),
 "tuna": dict(flavor="Tuna", src="tuna, source of protein and minerals",
     comp="meat and animal derivatives, fish and fish derivatives (tuna 6%), cereals, eggs and egg derivatives, minerals.", img="cat-tuna", ing=None,
     ru_f="тунцом", ru_src="тунец, источник белка и минералов", ru_comp="мясо и продукты животного происхождения, рыба и рыбные продукты (тунец 6%), злаки, яйца и яичные продукты, минеральные вещества.",
     hy_f="թունայով", hy_src="թունան՝ սպիտակուցի և հանքանյութերի աղբյուր", hy_comp="միս և կենդանական ծագման մթերքներ, ձուկ և ձկան մթերքներ (թունա 6%), հացահատիկ, ձու և ձվի մթերքներ, հանքային նյութեր։"),
 "guinea-duck": dict(flavor="Guinea Fowl & Duck", src="guinea fowl and duck, source of protein and minerals",
     comp="meat and animal derivatives (guinea fowl 5%, duck 5%), cereals, eggs and egg derivatives, minerals.", img="cat-guinea-duck", ing=None,
     ru_f="цесаркой и уткой", ru_src="цесарка и утка, источник белка и минералов", ru_comp="мясо и продукты животного происхождения (цесарка 5%, утка 5%), злаки, яйца и яичные продукты, минеральные вещества.",
     hy_f="խայտահավով և բադով", hy_src="խայտահավն ու բադը՝ սպիտակուցի և հանքանյութերի աղբյուր", hy_comp="միս և կենդանական ծագման մթերքներ (խայտահավ 5%, բադ 5%), հացահատիկ, ձու և ձվի մթերքներ, հանքային նյութեր։"),
 "lamb": dict(flavor="Lamb", src="lamb, source of protein and minerals",
     comp="meat and animal derivatives (lamb 6%), cereals, eggs and egg derivatives, minerals.", img="cat-lamb", ing="Lamb",
     ru_f="ягнёнком", ru_src="ягнёнок, источник белка и минералов", ru_comp="мясо и продукты животного происхождения (ягнёнок 6%), злаки, яйца и яичные продукты, минеральные вещества.",
     hy_f="գառան մսով", hy_src="գառան միսը՝ սպիտակուցի և հանքանյութերի աղբյուր", hy_comp="միս և կենդանական ծագման մթերքներ (գառան միս 6%), հացահատիկ, ձու և ձվի մթերքներ, հանքային նյութեր։"),
}
PATE = dict(flavor="Beef & Peas", src="beef and peas, source of proteins and fibres",
     comp="meat and animal derivatives (beef 7.5%), vegetables (peas 4.5%), minerals.", img="dog-pate-beef-peas", ing="Beef",
     ru_f="говядиной и горошком", ru_src="говядина и горошек, источник белка и клетчатки", ru_comp="мясо и продукты животного происхождения (говядина 7,5%), овощи (горошек 4,5%), минеральные вещества.",
     hy_f="տավարի մսով և ոլոռով", hy_src="տավարի միսն ու ոլոռը՝ սպիտակուցի և բջջանյութի աղբյուր", hy_comp="միս և կենդանական ծագման մթերքներ (տավարի միս 7,5%), բանջարեղեն (ոլոռ 4,5%), հանքային նյութեր։")

# CSV rows -> (flavour key, pack)
DOG_ROWS = [("009017", "beef", "415 g"), ("009127", "beef", "1230 g"),
            ("009027", "chicken-turkey", "415 g"), ("009137", "chicken-turkey", "1230 g"),
            ("009167", "lamb", "415 g"), ("009147", "lamb", "1230 g"),
            ("009177", "wild-game", "415 g"), ("009157", "wild-game", "1230 g"),
            ("009187", "beef-veg", "1230 g")]
CAT_ROWS = [("009077", "chicken", "415 g"), ("009097", "tuna", "415 g"),
            ("009517", "guinea-duck", "415 g"), ("009547", "lamb", "415 g")]
PATE_ROWS = [("009257", "pate", "150 g")]
QTY = {"009257": 12, "009267": 12}  # everything else is 1 in the CSV

def ru_pack(p): return p.replace(" g", " г")
def hy_pack(p): return p.replace(" g", " գ")

def variant(code, spec, pack, kind, first):
    pr, cost = price(code)
    attrs = {"lifestage": v("lifestage", "Adult"), "flavor": v("flavor", spec["flavor"]),
             "product-weight": v("product-weight", pack),
             "special-diet": v("special-diet", "No Artificial Colorants")}
    if kind == "pate":
        attrs["texture"] = v("texture", "Pate"); attrs["packaging"] = v("packaging", "Tray")
    else:
        attrs["texture"] = v("texture", "Chunks in Gravy"); attrs["packaging"] = v("packaging", "Can")
    if spec["ing"]:
        attrs["ingredient"] = v("ingredient", spec["ing"])
    if kind == "dog":
        about, ing, feed = about_dog(spec["flavor"], spec["src"], pack), ingredients(spec["comp"], DOG_AN, DOG_ADD), DOG_FEED
        ru = dict(about_this_item=ru_about_dog(spec["ru_f"], spec["ru_src"], ru_pack(pack)), ingredient_information=ru_ing(spec["ru_comp"], RU_DOG_AN, RU_DOG_ADD), feeding_instructions=RU_DOG_FEED)
        hy = dict(about_this_item=hy_about_dog(spec["hy_f"], spec["hy_src"], hy_pack(pack)), ingredient_information=hy_ing(spec["hy_comp"], HY_DOG_AN, HY_DOG_ADD), feeding_instructions=HY_DOG_FEED)
    elif kind == "cat":
        about, ing, feed = about_cat(spec["flavor"], spec["src"], pack), ingredients(spec["comp"], CAT_AN, CAT_ADD), CAT_FEED
        ru = dict(about_this_item=ru_about_cat(spec["ru_f"], spec["ru_src"], ru_pack(pack)), ingredient_information=ru_ing(spec["ru_comp"], RU_CAT_AN, RU_CAT_ADD), feeding_instructions=RU_CAT_FEED)
        hy = dict(about_this_item=hy_about_cat(spec["hy_f"], spec["hy_src"], hy_pack(pack)), ingredient_information=hy_ing(spec["hy_comp"], HY_CAT_AN, HY_CAT_ADD), feeding_instructions=HY_CAT_FEED)
    else:
        about, ing, feed = about_pate(spec["flavor"], spec["src"], pack), ingredients(spec["comp"], PATE_AN, PATE_ADD), PATE_FEED
        ru = dict(about_this_item=ru_about_pate(spec["ru_f"], spec["ru_src"], ru_pack(pack)), ingredient_information=ru_ing(spec["ru_comp"], RU_PATE_AN, RU_PATE_ADD), feeding_instructions=RU_PATE_FEED)
        hy = dict(about_this_item=hy_about_pate(spec["hy_f"], spec["hy_src"], hy_pack(pack)), ingredient_information=hy_ing(spec["hy_comp"], HY_PATE_AN, HY_PATE_ADD), feeding_instructions=HY_PATE_FEED)
    vobj = {"name": f"{spec['flavor']} {pack}", "pricing_type": "fixed", "sku": code,
            "price": pr, "cost_price": cost, "stock": stock(QTY.get(code, 1)),
            "is_default": first, "sort_order": 0, "images": [media[spec["img"]]],
            "attribute_value_ids": attrs,
            "about_this_item": about, "ingredient_information": ing, "feeding_instructions": feed}
    return vobj, ru, hy

def build(key, name, slug, cats, rows, table, kind, ru_name, hy_name):
    variants, ru, hy = [], {}, {}
    for i, (code, fk, pack) in enumerate(rows):
        spec = PATE if kind == "pate" else table[fk]
        vo, r, h = variant(code, spec, pack, kind, i == 0)
        vo["sort_order"] = i
        variants.append(vo); ru[code] = r; hy[code] = h
    payload = {"name": name, "slug": slug, "category_ids": cats, "brand_id": 19, "attribute_family_id": 2,
               "is_best_seller": False, "is_on_sale": False, "variants": variants}
    json.dump(payload, open(f"{C}/simba-{key}.json", "w"), ensure_ascii=False, indent=1)
    json.dump({"name": ru_name, "variants": ru}, open(f"{C}/simba-{key}-ru.json", "w"), ensure_ascii=False, indent=1)
    json.dump({"name": hy_name, "variants": hy}, open(f"{C}/simba-{key}-hy.json", "w"), ensure_ascii=False, indent=1)
    print(key, name, "->", len(variants), "variants;", [(x["sku"], x["name"], x["price"], x["cost_price"], x["stock"], x["attribute_value_ids"]) for x in variants])

import sys
if "--pate2" not in sys.argv:
    build("dog-chunks", "Chunks Adult", "simba-chunks-adult", [4], DOG_ROWS, DOG, "dog",
          "Кусочки в соусе Adult", "Կտորներ սոուսով Adult")
    build("cat-chunkies", "Chunkies Adult", "simba-chunkies-adult", [11], CAT_ROWS, CAT, "cat",
          "Кусочки в соусе Adult", "Կտորներ սոուսով Adult")
    build("dog-pate", "Paté Adult Beef & Peas 150 g", "simba-pate-adult-beef-and-peas-150g", [4], PATE_ROWS, None, "pate",
          "Паштет Adult Говядина и горошек 150 г", "Պաշտետ Adult տավարի միս և ոլոռ 150 գ")

# ---------------------------------------------------------------- 009267 via the sibling-price fallback (CLAUDE.md rule 2a, 2026-09-10)
# hafo has no listing for 009267; 009257 (same product 326, same cost 355) is
# priced 480 on hafo -> 009267 takes 480. Writes the ONE-variant file for
# scripts/add-variant.sh and re-writes the ru/hy files for 326 with BOTH SKUs
# and the renamed product ("Paté Adult 150 g": flavour now varies).
PATE2 = dict(flavor="Chicken", src="chicken and liver, source of proteins and minerals",
     comp="meat and animal derivatives (chicken 12%, liver 6%), minerals.", img="dog-pate-chicken-liver", ing="Chicken",
     ru_f="курицей и печенью", ru_src="курица и печень, источник белка и минералов", ru_comp="мясо и продукты животного происхождения (курица 12%, печень 6%), минеральные вещества.",
     hy_f="հավով և լյարդով", hy_src="հավն ու լյարդը՝ սպիտակուցի և հանքանյութերի աղբյուր", hy_comp="միս և կենդանական ծագման մթերքներ (հավ 12%, լյարդ 6%), հանքային նյութեր։")
SIBLING = {"009267": ("009257", 480)}   # code -> (priced sibling, its hafo price)

def build_pate2():
    code, (sib, sale) = "009267", SIBLING["009267"]
    cost = 355
    assert hafo[sib]["price"] == sale and hafo[sib]["cost"] == cost, "sibling changed"
    assert sale > cost
    ru_p, hy_p = ru_about_pate(PATE2["ru_f"], PATE2["ru_src"], ru_pack("150 g")), hy_about_pate(PATE2["hy_f"], PATE2["hy_src"], hy_pack("150 g"))
    vo = {"name": "Chicken & Liver 150 g", "pricing_type": "fixed", "sku": code,
          "price": sale, "cost_price": cost, "stock": stock(QTY.get(code, 1)),
          "images": [media[PATE2["img"]]],
          "attribute_value_ids": {"lifestage": v("lifestage", "Adult"), "flavor": v("flavor", PATE2["flavor"]),
                                  "product-weight": v("product-weight", "150 g"), "special-diet": v("special-diet", "No Artificial Colorants"),
                                  "texture": v("texture", "Pate"), "packaging": v("packaging", "Tray"), "ingredient": v("ingredient", PATE2["ing"])},
          "about_this_item": P("SIMBA DOG PATÉ WITH CHICKEN AND LIVER is a complete pet food for adult dogs of all sizes. Paté formulated with quality ingredients such as chicken and liver, source of proteins and minerals, steam cooked to enhance their natural taste and stimulate your pet's daily appetite. The formulation has been developed with a specific combination of vitamins A-D3-E to meet the nutritional requirements of your pet's daily needs. No added colours or preservatives.") +
                             LI(["Complete pet food for adult dogs of all sizes", "Paté, steam cooked", "No added colours or preservatives", "No cruelty test", "Made in Italy", "Pack size: 150 g"]),
          "ingredient_information": ingredients(PATE2["comp"], PATE_AN, PATE_ADD), "feeding_instructions": PATE_FEED}
    json.dump(vo, open(f"{C}/simba-dog-pate-v2.json", "w"), ensure_ascii=False, indent=1)
    ru = json.load(open(f"{C}/simba-dog-pate-ru.json")); hy = json.load(open(f"{C}/simba-dog-pate-hy.json"))
    ru["name"], hy["name"] = "Паштет Adult 150 г", "Պաշտետ Adult 150 գ"
    ru["variants"][code] = dict(about_this_item=ru_p, ingredient_information=ru_ing(PATE2["ru_comp"], RU_PATE_AN, RU_PATE_ADD), feeding_instructions=RU_PATE_FEED)
    hy["variants"][code] = dict(about_this_item=hy_p, ingredient_information=hy_ing(PATE2["hy_comp"], HY_PATE_AN, HY_PATE_ADD), feeding_instructions=HY_PATE_FEED)
    json.dump(ru, open(f"{C}/simba-dog-pate-ru.json", "w"), ensure_ascii=False, indent=1)
    json.dump(hy, open(f"{C}/simba-dog-pate-hy.json", "w"), ensure_ascii=False, indent=1)
    print("pate v2:", vo["sku"], vo["name"], vo["price"], vo["cost_price"], vo["stock"], vo["attribute_value_ids"], "ru/hy SKUs:", sorted(ru["variants"]))

import sys
if "--pate2" in sys.argv:
    build_pate2()
