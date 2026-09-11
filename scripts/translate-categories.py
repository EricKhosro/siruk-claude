#!/usr/bin/env python3
"""Write Russian (ru) and Armenian (hy) names for every admin category.

Categories are translatable per locale (verified 2026-09-10): PUT the same
body with `"locale": "ru"` / `"hy"`, and each locale keeps its own `name`.
The slug is owned by `en` and is sent unchanged. Names come from the table
below, keyed by the English name so the id tree can change without edits.

    scripts/translate-categories.py [--dry-run]
"""
import json, os, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, ".siruk-cache")

# English name -> (ru, hy). Parent context in the comment where a name repeats.
NAMES = {
    "Dog": ("Собаки", "Շներ"),
    "Cat": ("Кошки", "Կատուներ"),
    "Food": ("Корм", "Կեր"),
    "Dry Food": ("Сухой корм", "Չոր կեր"),
    "Wet Food": ("Влажный корм", "Թաց կեր"),
    "Health Condition": ("Лечебный корм", "Բուժական կեր"),
    "Treat": ("Лакомства", "Հյուրասիրություններ"),
    "Dog Bones, Bully Sticks & Chews": ("Кости и жевательные лакомства", "Ոսկորներ և ծամելու հյուրասիրություններ"),
    "Vitamins & Supplements": ("Витамины и добавки", "Վիտամիններ և հավելումներ"),
    "Accessories": ("Аксессуары", "Աքսեսուարներ"),
    "Toys": ("Игрушки", "Խաղալիքներ"),
    "Plush": ("Плюшевые игрушки", "Փափուկ խաղալիքներ"),
    "Latex & Rubber": ("Латекс и резина", "Լատեքս և ռետին"),
    "Rope & Tug": ("Канаты и перетягивание", "Պարաններ և քաշքշուկ"),
    "Fetch & Retrieve": ("Игрушки для апортировки", "Ապորտի խաղալիքներ"),
    "Chew & Dental": ("Жевательные и для зубов", "Ծամելու և ատամների խնամքի"),
    "Activity & Intelligence": ("Развивающие игрушки", "Զարգացնող խաղալիքներ"),
    "Mice & Animals": ("Мышки и зверушки", "Մկնիկներ և կենդանիներ"),
    "Balls": ("Мячики", "Գնդակներ"),
    "Catnip": ("Кошачья мята", "Կատվախոտ"),
    "Grooming": ("Уход и груминг", "Խնամք"),
    "Brushes & Combs": ("Щётки и расчёски", "Խոզանակներ և սանրեր"),
    "Shampoos & Conditioners": ("Шампуни и кондиционеры", "Շամպուններ և կոնդիցիոներներ"),
    "Grooming Tools": ("Инструменты для груминга", "Խնամքի գործիքներ"),
    "Paw & Nail Care": ("Уход за лапами и когтями", "Թաթերի և ճանկերի խնամք"),
    "Ear Care": ("Уход за ушами", "Ականջների խնամք"),
    "Skin Care": ("Уход за кожей", "Մաշկի խնամք"),
    # Health & Pharmacy (Chewy menu, 2026-09-10)
    "Health & Pharmacy": ("Здоровье и аптека", "Առողջություն և դեղատուն"),
    "Flea & Tick": ("От блох и клещей", "Լվերի և տզերի դեմ"),
    "Probiotics & Digestive Health": ("Пробиотики и пищеварение", "Պրոբիոտիկներ և մարսողություն"),
    "Allergy & Itch Relief": ("От аллергии и зуда", "Ալերգիայի և քորի դեմ"),
    "Heartworm & Dewormers": ("Антигельминтики", "Հակաճիճվային միջոցներ"),
    "Pharmacy & Prescriptions": ("Аптека и рецептурные препараты", "Դեղատուն և դեղատոմսով դեղեր"),
    "Anxiety & Calming Care": ("Успокоительные средства", "Հանգստացնող միջոցներ"),
    "Urinary Tract & Kidneys": ("Мочевыводящие пути и почки", "Միզուղիներ և երիկամներ"),
    "Test Kits": ("Тесты", "Թեստեր"),
    # Cat litter
    "Litter": ("Наполнители", "Լցանյութեր"),
    "Clumping": ("Комкующиеся", "Կծկվող"),
    "Scented": ("Ароматизированные", "Բուրավետ"),
    "Unscented": ("Без запаха", "Առանց հոտի"),
    "Natural": ("Натуральные", "Բնական"),
    "Lightweight": ("Лёгкие", "Թեթև"),
    "Crystal": ("Силикагелевые", "Սիլիկագելային"),
    # Supplies
    "Supplies": ("Товары и аксессуары", "Պարագաներ"),  # both Dog 68 and Cat 66
    "Litter Boxes & Accessories": ("Лотки и аксессуары", "Արկղեր և պարագաներ"),
    # Supplies / Cleaning & Potty / Scratchers (Chewy menu, 2026-09-11)
    "Collars, Leashes & Harnesses": ("Ошейники, поводки и шлейки", "Վզնոցներ, զգեստիկներ և շլեյկաներ"),
    "Bowls & Feeders": ("Миски и кормушки", "Կերամաններ և կերակրիչներ"),
    "Beds": ("Лежаки и коврики", "Պառկելատեղեր և գորգեր"),
    "Clothing & Accessories": ("Одежда и аксессуары", "Հագուստ և աքսեսուարներ"),
    "Carriers & Travel": ("Переноски и путешествия", "Տեղափոխիչներ և ճանապարհորդություն"),
    "Training & Behavior": ("Дрессировка и коррекция поведения", "Վարժեցում և վարքի ուղղում"),
    "Cleaning & Potty": ("Уборка и туалет", "Մաքրություն և զուգարան"),
    "Pee Pads & Diapers": ("Пелёнки и подгузники", "Խանձարուրներ և տակդիրներ"),
    "Poop Bags & Scoopers": ("Пакеты и совки для уборки", "Տոպրակներ և թիակներ"),
    "Cleaners & Stain Removers": ("Средства от запаха и пятен", "Հոտի և բծերի դեմ միջոցներ"),
    "Trees, Condos & Scratchers": ("Домики и когтеточки", "Տնակներ և ճանկասրիչներ"),
    "Scratchers & Scratching Posts": ("Когтеточки", "Ճանկասրիչներ"),
}


def api(method, path, payload=None, lang=None):
    env = dict(os.environ, SIRUK_NO_PACE="1")
    if lang:
        env["SIRUK_LANG"] = lang
    args = [os.path.join(ROOT, "scripts/api.sh"), method, path]
    if payload is not None:
        p = os.path.join(CACHE, "_trcat.json")
        json.dump(payload, open(p, "w"), ensure_ascii=False)
        args.append(p)
    r = subprocess.run(args, capture_output=True, text=True, cwd=ROOT, timeout=120, env=env)
    i = r.stdout.find("{")
    return json.loads(r.stdout[i:]) if i >= 0 else {"_err": r.stderr}


def flatten(nodes, out):
    for n in nodes:
        out.append(n)
        flatten(n.get("children") or [], out)
    return out


def main():
    dry = "--dry-run" in sys.argv
    cats = flatten(api("GET", "/categories?forProducts=true").get("data", []), [])
    missing = sorted({c["name"] for c in cats if c["name"] not in NAMES})
    if missing:
        print("no translation for:", missing); sys.exit(1)
    bad = []
    for c in cats:
        full = api("GET", f"/categories/{c['id']}", lang="en").get("data") or {}
        for i, lang in enumerate(("ru", "hy")):
            body = {"parent_id": full.get("parent_id"), "name": NAMES[c["name"]][i], "slug": full["slug"],
                    "description": full.get("description") or "", "quick_links": full.get("quick_links") or [],
                    "meta": full.get("meta") or {}, "locale": lang}
            if dry:
                print(f"{c['id']:>3} {c['name']:<32} {lang}: {body['name']}"); continue
            api("PUT", f"/categories/{c['id']}", body)
            got = (api("GET", f"/categories/{c['id']}", lang=lang).get("data") or {}).get("name")
            if got != body["name"]:
                bad.append((c["id"], lang, got))
        en = (api("GET", f"/categories/{c['id']}", lang="en").get("data") or {}).get("name")
        if not dry and en != c["name"]:
            bad.append((c["id"], "en-overwritten!", en))
        if not dry:
            print(f"{c['id']:>3} {c['name']:<32} ru/hy ok")
    print("problems:", bad if bad else "none")


if __name__ == "__main__":
    main()
