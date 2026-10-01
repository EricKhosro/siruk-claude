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
Missing keys keep whatever that locale already holds (read back before the PUT),
falling back to the English text only where the locale has nothing — so a file
that translates one new variant does not wipe the other variants' translations
(it used to: 2026-09-23, product 1150 lost four ru/hy descriptions that way).

    scripts/set-translation.py <product-id> <ru|hy> <translation.json> [--dry-run]
"""
import json, os, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, ".siruk-cache")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
# Variants are re-sent through the one payload builder (catalog model 2026-09-29):
# the API refuses the old fields and anything server-only such as item_content.
from siruk_payload import product_body, product_type, to_variant_payload  # noqa: E402
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

    cur = api("GET", f"/products/{pid}", lang=lang)["data"]
    cur_v = {v["sku"]: v for v in cur.get("variants") or []}

    def kept(sku, f, en_val):
        """The locale's own current text when it differs from en; else en."""
        c = (cur_v.get(sku) or {}).get(f)
        return c if c and c != en_val else (en_val or "")

    body = product_body(en)
    body["name"] = tr.get("name") or (cur.get("name") if cur.get("name") and cur.get("name") != en["name"] else en["name"])
    body["meta"] = tr.get("meta") if tr.get("meta") is not None else en.get("meta")
    body["locale"] = lang
    body["variants"] = []
    allowed = {a["id"] for a in product_type(en["attribute_family_id"]).get("attributes") or []}
    for v in en["variants"]:
        nv = to_variant_payload(v, allowed)
        t = (tr.get("variants") or {}).get(v["sku"], {})
        for f in VTEXT:
            nv[f] = t.get(f) if t.get(f) is not None else kept(v["sku"], f, v.get(f))
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
