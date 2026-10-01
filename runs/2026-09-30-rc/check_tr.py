#!/usr/bin/env python3
"""Check tr/<key>-{ru,hy}.json against plan.json: every sku present, <p>/<li>/<ul>/<strong>
counts match the English per field, numbers preserved, no brand in the name, no leftover English.
    python3 runs/2026-09-30-rc/check_tr.py [key ...]"""
import json, os, re, sys
from collections import Counter
D = os.path.dirname(os.path.abspath(__file__))
plan = json.load(open(os.path.join(D, "plan.json")))["products"]
only = set(sys.argv[1:])
FIELDS = ("about_this_item", "ingredient_information")
TAGS = ("<p>", "</p>", "<li>", "</li>", "<ul>", "</ul>", "<strong>", "</strong>")
num = lambda s: Counter(re.findall(r"\d+(?:\.\d+)?", re.sub(r"<[^>]+>|&#x?[0-9a-f]+;|на 1 кг|1 կգ-ում", " ", s)))
errs = warns = 0; files = 0
for pr in plan:
    if only and pr["key"] not in only:
        continue
    for lang in ("ru", "hy"):
        f = os.path.join(D, "tr", f"{pr['key']}-{lang}.json")
        if not os.path.exists(f):
            print(f"MISSING {f}"); errs += 1; continue
        files += 1
        try:
            t = json.load(open(f))
        except Exception as e:
            print(f"BADJSON {f}: {e}"); errs += 1; continue
        def err(m):
            global errs; errs += 1; print(f"ERR {pr['key']}-{lang}: {m}")
        def warn(m):
            global warns; warns += 1; print(f"warn {pr['key']}-{lang}: {m}")
        if set(t) - {"name", "variants"}: err(f"extra keys {set(t)-{'name','variants'}}")
        if not t.get("name"): err("no name")
        elif re.search(r"royal\s*canin", t["name"], re.I): err("brand in name")
        skus = {v["sku"] for v in pr["variants"]}
        got = set(t.get("variants", {}))
        if skus - got: err(f"missing skus {skus-got}")
        if got - skus: err(f"unknown skus {got-skus}")
        for v in pr["variants"]:
            tv = t.get("variants", {}).get(v["sku"], {})
            if set(tv) - set(FIELDS): err(f"{v['sku']} extra fields {set(tv)-set(FIELDS)}")
            for fld in FIELDS:
                en, tr = v[fld] or "", tv.get(fld, "")
                if en and not tr: err(f"{v['sku']} {fld} empty"); continue
                for tag in TAGS:
                    if en.count(tag) != tr.count(tag):
                        err(f"{v['sku']} {fld} {tag} {en.count(tag)} vs {tr.count(tag)}")
                if num(en) != num(tr):
                    a, b = num(en), num(tr)
                    warn(f"{v['sku']} {fld} numbers differ: missing {dict(a-b)} extra {dict(b-a)}")
                plain = re.sub(r"<[^>]+>", " ", tr)
                script = r"[А-Яа-яЁё]" if lang == "ru" else r"[Ա-֏]"
                if not re.search(script, plain): err(f"{v['sku']} {fld} not in {lang} script")
print(f"{files} files checked, {errs} errors, {warns} warnings")
sys.exit(1 if errs else 0)
