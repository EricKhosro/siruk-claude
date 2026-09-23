#!/usr/bin/env python3
"""Write the ru/hy labels of a FEW attribute values, by id.

`translate-attributes.py` rewrites every value on the server (~1,700 PUTs);
this one is for the handful a run just created with `add-attribute-values.py`.
Labels come from reference/translations-attributes.json, keyed by the English
label the value carries live (rule 13).

    scripts/translate-attribute-values.py 830 831 842
"""
import json, os, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, ".siruk-cache")
T = json.load(open(os.path.join(ROOT, "reference/translations-attributes.json")))
MENU = json.load(open(os.path.join(ROOT, "reference/attribute-values.json")))
ATTR_CODE = {d["attribute_id"]: code for code, d in MENU.items()}


def api(method, path, payload=None, lang=None):
    env = dict(os.environ)
    if lang:
        env["SIRUK_LANG"] = lang
    args = [os.path.join(ROOT, "scripts/api.sh"), method, path]
    if payload is not None:
        p = os.path.join(CACHE, "_trval.json")
        json.dump(payload, open(p, "w"), ensure_ascii=False)
        args.append(p)
    r = subprocess.run(args, capture_output=True, text=True, cwd=ROOT, timeout=120, env=env)
    i = r.stdout.find("{")
    return json.loads(r.stdout[i:]) if i >= 0 else {"_err": r.stderr[-200:]}


def main():
    ids = [int(x) for x in sys.argv[1:]]
    if not ids:
        raise SystemExit(__doc__)
    bad = 0
    for vid in ids:
        en = (api("GET", f"/attribute-values/{vid}", lang="en").get("data") or {})
        code = en.get("attributeCode") or ATTR_CODE.get(en.get("attributeId"))
        tr = T["values"].get(code, {}).get(en.get("label"))
        if not tr:
            print(f"{vid}: no translation for {code} = {en.get('label')!r}"); bad += 1; continue
        for i, lang in enumerate(("ru", "hy")):
            api("PUT", f"/attribute-values/{vid}",
                {"locale": lang, "attribute_id": en["attributeId"], "value": en["value"],
                 "label": tr[i], "sort_order": en.get("sort_order", 0)})
        got = [(api("GET", f"/attribute-values/{vid}", lang=l).get("data") or {}).get("label") for l in ("en", "ru", "hy")]
        ok = got == [en["label"], tr[0], tr[1]]
        print(f"{vid} {code} {en['label']!r}: en/ru/hy read back {got} {'OK' if ok else 'MISMATCH'}")
        bad += 0 if ok else 1
    sys.exit(1 if bad else 0)


main()
