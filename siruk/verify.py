"""ru/hy coverage audit — the port of scripts/verify-translations.py (CLAUDE.md 13:
translation status is reported from this, never from what was sent).

A locale counts as missing when its value is empty or identical to the English
one (a fallback, not a translation), unless reference/translations.json maps the
text to itself (proper nouns, materials). Brand names are Latin by policy, so
only an empty brand name or an untranslated brand meta.description counts.
Attribute names, value labels, product-type names and variant labels are not
translatable on this backend.
"""
import html, json, os, re

from siruk import client as _client
from siruk.config import ROOT

LANG = {"ru": 0, "hy": 1}
VTEXT = ("about_this_item", "ingredient_information", "feeding_instructions")
_dict = None


def dictionary():
    global _dict
    if _dict is None:
        with open(os.path.join(ROOT, "reference", "translations.json"), encoding="utf-8") as f:
            _dict = json.load(f)
    return _dict


def ws(s):
    return re.sub(r"\s+", " ", html.unescape(s or "")).strip()


def expected_text(text, lang):
    """What the dictionary says the translation of one text node is (None if unknown)."""
    T, key = dictionary(), ws(text)
    if key in T["strings"]:
        return T["strings"][key][LANG[lang]]
    for opener, v in T["paragraphs"].items():
        if key.startswith(ws(opener)):
            return v[LANG[lang]]
    return None


def identity_ok(en_value, stored, lang, kind):
    """A stored value identical to English is fine when the dictionary maps it to itself."""
    if kind == "name":
        t = dictionary()["names"].get(en_value)
        return bool(t) and t[LANG[lang]] == stored
    nodes = re.findall(r"<(?:li|p)>(.*?)</(?:li|p)>", en_value or "", flags=re.S)
    return bool(nodes) and all(expected_text(n, lang) == ws(n) for n in nodes)


def _get(path, lang):
    try:
        return _client.default().get(path, lang=lang) or {}
    except _client.ApiError:
        return {}


def _flatten(nodes, out):
    for n in nodes:
        out.append(n)
        _flatten(n.get("children") or [], out)
    return out


def product_gaps(pid):
    """[(pid, lang, field, en name)] for one product."""
    out = []
    recs = {l: (_get(f"/products/{pid}", l).get("data") or {}) for l in ("en", "ru", "hy")}
    en = recs["en"]
    for l in ("ru", "hy"):
        r = recs[l]
        if not r.get("name") or (r["name"] == en.get("name") and not identity_ok(en.get("name"), r["name"], l, "name")):
            out.append((pid, l, "name", en.get("name")))
        for ve, vl in zip(en.get("variants", []), r.get("variants", [])):
            for f in VTEXT:
                if (ve.get(f) or "").strip() and (vl.get(f) or "") == ve.get(f) \
                        and not identity_ok(ve.get(f), vl.get(f), l, "text"):
                    out.append((pid, l, f"{ve['sku']}.{f}", en.get("name")))
    return out


def all_product_ids():
    return sorted({p["id"] for p in _client.default().paginate("/products", lang="en", max_pages=1000)})


def translations(only=None, catalogue=True, progress=None):
    """→ {"counts": {...}, "missing": {"product": [...], "category": [...], "brand": [...]}}.
    only: product ids to check (None = every product). catalogue: also check categories
    and brands (the script always did)."""
    missing = {"product": [], "category": [], "brand": []}
    ids = sorted(set(only)) if only else all_product_ids()
    for i, pid in enumerate(ids, 1):
        missing["product"] += product_gaps(pid)
        if progress:
            progress(i, len(ids))
    counts = {"products": len(ids)}
    if catalogue:
        cats = _flatten(_get("/categories?forProducts=true", "en").get("data", []), [])
        for c in cats:
            for l in ("ru", "hy"):
                r = _get(f"/categories/{c['id']}", l).get("data") or {}
                if not r.get("name") or r["name"] == c["name"]:
                    missing["category"].append((c["id"], l, "name", c["name"]))
        brands = _get("/brands?forProducts=true", "en").get("data", [])
        for b in brands:
            en = _get(f"/brands/{b['id']}", "en").get("data") or {}
            for l in ("ru", "hy"):
                r = _get(f"/brands/{b['id']}", l).get("data") or {}
                if not r.get("name"):
                    missing["brand"].append((b["id"], l, "name", en.get("name")))
                if (r.get("meta") or {}).get("description") in (None, "", (en.get("meta") or {}).get("description")):
                    missing["brand"].append((b["id"], l, "meta.description", en.get("name")))
        counts.update(categories=len(cats), brands=len(brands))
    return {"counts": counts, "missing": missing,
            "complete": not any(missing.values()),
            "note": "attribute names / value labels / family names / variant labels: NOT translatable on this backend"}


def print_report(res, out_path=None):
    """The script's printout, line for line."""
    c = res["counts"]
    print(f"products: {c['products']}  categories: {c.get('categories', '-')}  brands: {c.get('brands', '-')}")
    if out_path:
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(res["missing"], f, ensure_ascii=False, indent=1)
    for k, v in res["missing"].items():
        print(f"{k}: {len(v)} missing translation(s)")
        for t in v[:40]:
            print("   ", t)
    print(res["note"] + " (see reference/admin-api.md)")
