#!/usr/bin/env python3
"""Audit ru/hy coverage of everything on the server that stores per-locale text:
products (name + variant texts), categories (name), brands (name + meta).
A locale counts as missing when its value is empty or identical to the English
one (a fallback, not a translation) — except brand names, which are Latin by policy.

    scripts/verify-translations.py [--only id,id] [--fix-products]
"""
import html, json, os, re, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T = json.load(open(os.path.join(ROOT, "reference/translations.json")))
LANG = {"ru": 0, "hy": 1}


def ws(s):
    return re.sub(r"\s+", " ", html.unescape(s or "")).strip()


def expected_text(text, lang):
    """What the dictionary says the translation of one text node is (None if unknown)."""
    key = ws(text)
    if key in T["strings"]:
        return T["strings"][key][LANG[lang]]
    for opener, v in T["paragraphs"].items():
        if key.startswith(ws(opener)):
            return v[LANG[lang]]
    return None


def identity_ok(en_value, stored, lang, kind):
    """A stored value identical to English is fine when the dictionary itself maps it
    to the same text (proper nouns like 'Turbinio', materials like 'TPE')."""
    if kind == "name":
        t = T["names"].get(en_value)
        return bool(t) and t[LANG[lang]] == stored
    nodes = re.findall(r"<(?:li|p)>(.*?)</(?:li|p)>", en_value or "", flags=re.S)
    return bool(nodes) and all(expected_text(n, lang) == ws(n) for n in nodes)


def api(path, lang):
    env = dict(os.environ, SIRUK_NO_PACE="1", SIRUK_LANG=lang)
    r = subprocess.run([os.path.join(ROOT, "scripts/api.sh"), "GET", path], capture_output=True, text=True, cwd=ROOT, env=env, timeout=120)
    i = r.stdout.find("{")
    return json.loads(r.stdout[i:]) if i >= 0 else {}


def flatten(nodes, out):
    for n in nodes:
        out.append(n); flatten(n.get("children") or [], out)
    return out


def main():
    missing = {"product": [], "category": [], "brand": []}
    # products (--only id,id restricts the product sweep; categories and brands are always checked)
    only = {int(x) for x in sys.argv[sys.argv.index("--only") + 1].split(",")} if "--only" in sys.argv else None
    ids, page = [], 1
    while True:
        d = api(f"/products?page={page}", "en")
        ids += [p["id"] for p in d.get("data", [])]
        if page >= (d.get("meta") or {}).get("last_page", 1):
            break
        page += 1
    if only:
        ids = [i for i in ids if i in only]
    for pid in sorted(set(ids)):
        recs = {l: (api(f"/products/{pid}", l).get("data") or {}) for l in ("en", "ru", "hy")}
        en = recs["en"]
        for l in ("ru", "hy"):
            r = recs[l]
            if not r.get("name") or (r["name"] == en.get("name") and not identity_ok(en.get("name"), r["name"], l, "name")):
                missing["product"].append((pid, l, "name", en.get("name")))
            for ve, vl in zip(en.get("variants", []), r.get("variants", [])):
                for f in ("about_this_item", "ingredient_information", "feeding_instructions"):
                    if (ve.get(f) or "").strip() and (vl.get(f) or "") == ve.get(f) and not identity_ok(ve.get(f), vl.get(f), l, "text"):
                        missing["product"].append((pid, l, f"{ve['sku']}.{f}", en.get("name")))
    # categories
    cats = flatten(api("/categories?forProducts=true", "en").get("data", []), [])
    for c in cats:
        for l in ("ru", "hy"):
            r = api(f"/categories/{c['id']}", l).get("data") or {}
            if not r.get("name") or r["name"] == c["name"]:
                missing["category"].append((c["id"], l, "name", c["name"]))
    # brands
    for b in api("/brands?forProducts=true", "en").get("data", []):
        en = api(f"/brands/{b['id']}", "en").get("data") or {}
        for l in ("ru", "hy"):
            r = api(f"/brands/{b['id']}", l).get("data") or {}
            if not r.get("name"):
                missing["brand"].append((b["id"], l, "name", en.get("name")))
            if (r.get("meta") or {}).get("description") in (None, "", (en.get("meta") or {}).get("description")):
                missing["brand"].append((b["id"], l, "meta.description", en.get("name")))
    print(f"products: {len(set(ids))}  categories: {len(cats)}  brands: {len(api('/brands?forProducts=true','en').get('data', []))}")
    for k, v in missing.items():
        print(f"{k}: {len(v)} missing translation(s)")
        for t in v[:40]:
            print("   ", t)
    print("attribute names / value labels / family names / variant labels: NOT translatable on this backend (see reference/admin-api.md)")
    sys.exit(1 if any(missing.values()) else 0)


if __name__ == "__main__":
    main()
