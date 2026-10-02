#!/usr/bin/env python3
"""Production fix 2026-10-01: no pack size in a product name (user rule).

The storefront's displayName is "Brand Name, <size label>", so a size inside the
name prints twice ("Classics Wild Coast, 9.7 kg, 9.7 kg"). Strips a trailing net
content (kg / g / ml and the ru / hy spellings) from the en, ru and hy names of
every product whose variants carry a size label. Slugs are left alone (URLs stay).
Physical dimensions of accessories (cm, l/ø) are not net content and stay.

    names.py [--write] [--ids …]
"""
import json, os, re, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
os.environ.update(SIRUK_API="https://api.siruk.am/api/admin",
                  SIRUK_TOKEN_FILE=os.path.join(ROOT, ".siruk-token-prod"))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from siruk_payload import api, product_type, product_body, to_variant_payload  # noqa: E402

WRITE = "--write" in sys.argv
IDS = [int(a) for a in sys.argv[sys.argv.index("--ids") + 1:]] if "--ids" in sys.argv else None
NET = re.compile(r"[,\s]*(?<![–\-\d.,])\b\d+(?:[.,]\d+)?\s*(?:kg|g|ml|кг|г|мл|կգ|գ|մլ)\.?\s*$", re.I)
STATE = os.path.join(HERE, "names-state.json")
state = json.load(open(STATE)) if os.path.exists(STATE) else {"done": {}}


# Stripping the size made these pairs identical; they are cat vs dog recipes (categories
# 10 vs 3, 37 vs 30), not mis-split sizes — the species goes in the en name instead.
OVERRIDE = {971: "Highest Protein Wild Prairie Cat", 1006: "Highest Protein Wild Prairie Dog",
            974: "Highest Protein Grasslands Cat", 1033: "Highest Protein Grasslands Dog",
            978: "Highest Protein Pacifica Cat", 1035: "Highest Protein Pacifica Dog",
            505: "Dental Hygiene Set for Dogs", 506: "Dental Hygiene Set for Cats"}

LOC_OVERRIDE = {(505, "ru"): "Набор для гигиены зубов для собак", (505, "hy"): "Ատամների հիգիենայի հավաքածու շների համար",
                (506, "ru"): "Набор для гигиены зубов для кошек", (506, "hy"): "Ատամների հիգիենայի հավաքածու կատուների համար"}


def strip(n):
    return NET.sub("", n or "").strip(" ,") if n else n


if IDS is None:
    IDS = json.load(open(os.path.join(HERE, "names-ids.json")))
plan = []
for pid in IDS:
    en = api("GET", f"/products/{pid}")["data"]
    if all(v["size_label"] in (None, "") for v in en["variants"]) and pid not in OVERRIDE:
        continue
    row = {"id": pid, "slug": en["slug"]}
    for lang in ("en", "ru", "hy"):
        n = en["name"] if lang == "en" else api("GET", f"/products/{pid}", lang=lang)["data"]["name"]
        row[lang] = (n, OVERRIDE[pid] if lang == "en" and pid in OVERRIDE
                     else LOC_OVERRIDE.get((pid, lang)) or strip(n))
    if any(a != b for a, b in (row[l] for l in ("en", "ru", "hy"))):
        plan.append(row)
        print(pid, " | ".join(f"{l}: {row[l][0]!r} → {row[l][1]!r}" for l in ("en", "ru", "hy") if row[l][0] != row[l][1]))
json.dump(plan, open(os.path.join(HERE, "names-plan.json"), "w"), ensure_ascii=False, indent=1)
print(len(plan), "products to rename")
if not WRITE:
    sys.exit()
for row in plan:
    pid = row["id"]
    if str(pid) in state["done"]:
        continue
    if row["en"][0] != row["en"][1]:
        p = api("GET", f"/products/{pid}")["data"]
        allowed = {a["id"] for a in product_type(p["attribute_family_id"]).get("attributes") or []}
        body = product_body(p)
        body["name"] = row["en"][1]
        body["variants"] = [to_variant_payload(v, allowed) for v in p["variants"]]
        r = api("PUT", f"/products/{pid}", body)
        if (r.get("data") or {}).get("name") != row["en"][1]:
            sys.exit(f"{pid}: en rename failed {json.dumps(r)[:400]}")
    for lang in ("ru", "hy"):
        if row[lang][0] == row[lang][1]:
            continue
        f = os.path.join(HERE, "tr", f"n-{pid}-{lang}.json")
        os.makedirs(os.path.dirname(f), exist_ok=True)
        json.dump({"name": row[lang][1]}, open(f, "w"), ensure_ascii=False)
        r = subprocess.run([os.path.join(ROOT, "scripts/set-translation.py"), str(pid), lang, f],
                           capture_output=True, text=True, cwd=ROOT)
        if r.returncode:
            sys.exit(f"{pid} {lang}: {r.stderr[-300:]}")
    state["done"][str(pid)] = row
    json.dump(state, open(STATE, "w"), ensure_ascii=False, indent=1)
    print("renamed", pid, row["en"][1])
    subprocess.run([os.path.join(ROOT, "scripts/pace.sh"), "product"])
