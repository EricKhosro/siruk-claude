#!/usr/bin/env python3
"""Store a Russian or Armenian translation of a product (name, meta, variant texts).

Verified 2026-09-10 on the demo API:
  * a product's `name`, `meta`, and each variant's `about_this_item` /
    `ingredient_information` / `feeding_instructions` are stored PER LOCALE —
    PUT the body with "locale": "ru" | "hy" and `en` is untouched;
  * a variant's `name` (the label), `slug`, sku, prices, stock, images and
    attribute ids are SINGLE-LANGUAGE — whatever the last PUT sent wins for
    every locale. So this script always copies them from the `en` record and
    refuses a translation file that tries to change them.

translation.json:
  {"name": "…",
   "variants": {"<sku>": {"about_this_item": "<html>", "ingredient_information": "…", "feeding_instructions": "…"}}}
(`meta` is accepted but the products API has no SEO meta field — it is ignored.)
Missing keys keep the English text (the API returns the locale's own value or
falls back), so translate what you can and leave the rest out.

    scripts/set-translation.py <product-id> <ru|hy> <translation.json> [--dry-run]
"""
import json, os, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, ".siruk-cache")
KEEP = ("slug", "category_ids", "brand_id", "attribute_family_id", "is_best_seller", "is_on_sale", "is_discontinued")
VKEEP = ("id", "name", "pricing_type", "sku", "price", "price_per_kg", "min_allowed_price", "cost_price",
         "compare_at_price", "weight", "is_default", "stock", "vendor_stock", "sort_order", "images", "attribute_value_ids")
VTEXT = ("about_this_item", "ingredient_information", "feeding_instructions")


def api(method, path, payload=None, lang=None):
    env = dict(os.environ, SIRUK_NO_PACE=os.environ.get("SIRUK_NO_PACE", ""))
    if lang:
        env["SIRUK_LANG"] = lang
    args = [os.path.join(ROOT, "scripts/api.sh"), method, path]
    if payload is not None:
        p = os.path.join(CACHE, f"_tr-{lang or 'w'}.json")
        json.dump(payload, open(p, "w"), ensure_ascii=False)
        args.append(p)
    r = subprocess.run(args, capture_output=True, text=True, cwd=ROOT, timeout=180, env=env)
    i = r.stdout.find("{")
    if i < 0:
        sys.exit(f"api {method} {path} failed: {r.stderr.strip()[-300:]}")
    return json.loads(r.stdout[i:])


def main():
    if len(sys.argv) < 4:
        sys.exit(__doc__)
    pid, lang, tfile = sys.argv[1], sys.argv[2], sys.argv[3]
    dry = "--dry-run" in sys.argv
    if lang not in ("ru", "hy"):
        sys.exit("lang must be ru or hy (en is the source language)")
    tr = json.load(open(tfile))
    for bad in ("slug", "sku", "price", "variants_list"):
        if bad in tr:
            sys.exit(f"translation file must not carry '{bad}' — single-language fields come from en")

    en = api("GET", f"/products/{pid}", lang="en")["data"]
    skus = {v["sku"]: v for v in en["variants"]}
    unknown = set((tr.get("variants") or {})) - set(skus)
    if unknown:
        sys.exit(f"translation names SKUs not on product {pid}: {sorted(unknown)}")
    for sku, t in (tr.get("variants") or {}).items():
        extra = set(t) - set(VTEXT)
        if extra:
            sys.exit(f"variant {sku}: only {VTEXT} are translatable, got {sorted(extra)}")

    body = {k: en.get(k) for k in KEEP}
    body["name"] = tr.get("name") or en["name"]
    body["meta"] = tr.get("meta") if tr.get("meta") is not None else en.get("meta")
    body["locale"] = lang
    body["variants"] = []
    for v in en["variants"]:
        nv = {k: v.get(k) for k in VKEEP if k in v}
        nv["images"] = nv.get("images") or []
        nv["attribute_value_ids"] = nv.get("attribute_value_ids") or {}
        t = (tr.get("variants") or {}).get(v["sku"], {})
        for f in VTEXT:
            nv[f] = t.get(f) if t.get(f) is not None else (v.get(f) or "")
        body["variants"].append(nv)

    if dry:
        print(json.dumps(body, ensure_ascii=False, indent=1)); return
    before_en = {"name": en["name"], "vnames": [v["name"] for v in en["variants"]],
                 "texts": [[v.get(f) or "" for f in VTEXT] for v in en["variants"]]}
    api("PUT", f"/products/{pid}", body, lang=lang)
    got = api("GET", f"/products/{pid}", lang=lang)["data"]
    en2 = api("GET", f"/products/{pid}", lang="en")["data"]
    problems = []
    if got["name"] != body["name"]:
        problems.append(f"{lang} name not stored: {got['name']!r}")
    if en2["name"] != before_en["name"]:
        problems.append(f"EN NAME OVERWRITTEN: {en2['name']!r}")
    if [v["name"] for v in en2["variants"]] != before_en["vnames"]:
        problems.append("EN VARIANT LABELS CHANGED")
    if [[v.get(f) or "" for f in VTEXT] for v in en2["variants"]] != before_en["texts"]:
        problems.append("EN VARIANT TEXTS OVERWRITTEN")
    for v in got["variants"]:
        t = (tr.get("variants") or {}).get(v["sku"], {})
        for f in VTEXT:
            if t.get(f) is not None and (v.get(f) or "") != t[f]:
                problems.append(f"{lang} {v['sku']}.{f} not stored")
    print(f"product {pid} [{lang}]: name={got['name']!r}  variants={len(got['variants'])}  "
          + ("OK" if not problems else "PROBLEMS: " + "; ".join(problems)))
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
