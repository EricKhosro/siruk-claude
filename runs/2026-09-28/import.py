#!/usr/bin/env python3
"""Import the sirook.pdf plan (runs/2026-09-28/plan.py), one product at a time.

Per product: exists-check → upload every gallery image into
products/<brand-slug>/<type> → create-product.sh → set-translation.py ru + hy
→ record in state.json. Resumable: finished keys are skipped.

    runs/2026-09-28/import.py [--only key,key] [--dry-run]
"""
import json, os, re, runpy, subprocess, sys, urllib.parse

RUN = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(RUN))
CACHE = os.path.join(ROOT, ".siruk-cache")
STATE = os.path.join(RUN, "state.json")
PLAN = runpy.run_path(os.path.join(RUN, "plan.py"))["PRODUCTS"]
BRAND_SLUG = {36: "versele-laga", 8: "trixie"}
STOCK = 10  # every invoice row is Qty 1 → placeholder stock 10 (user rule)


def sh(*args, env=None, check=True):
    r = subprocess.run(args, capture_output=True, text=True, cwd=ROOT,
                       env=dict(os.environ, **(env or {})))
    if check and r.returncode:
        raise SystemExit(f"FAILED {' '.join(args)}\n{r.stdout[-1500:]}\n{r.stderr[-1500:]}")
    return r


def unit_qty(label):
    """'800 g' → ('g', 800); '1 kg' → ('kg', 1); '2 × 54 g' → ('g', 108)."""
    m = re.search(r"(?:(\d+)\s*×\s*)?(\d+(?:\.\d+)?)\s*(kg|g)\b", label)
    n = float(m.group(2)) * (int(m.group(1)) if m.group(1) else 1)
    return m.group(3), (int(n) if n == int(n) else n)


def load_state():
    return json.load(open(STATE)) if os.path.exists(STATE) else {"done": {}}


def main():
    only = next((a.split("=", 1)[1].split(",") for a in sys.argv if a.startswith("--only=")), None)
    dry = "--dry-run" in sys.argv
    state = load_state()
    for p in PLAN:
        k = p["key"]
        if only and k not in only:
            continue
        if k in state["done"]:
            print(f"skip {k} (done: {state['done'][k]['id']})")
            continue
        slug = f"{BRAND_SLUG[p['brand']]}-{k}"
        folder = f"products/{BRAND_SLUG[p['brand']]}/{p['media']}"

        # exists? exact slug, then name search (create-product.sh also refuses)
        q = urllib.parse.quote(p["name"]["en"])
        raw = sh("scripts/api.sh", "GET", f"/products?search={q}").stdout
        found = json.loads(raw[raw.find("{"):] or "{}")
        ours = {d["id"] for d in state["done"].values()}
        hits = [(x["id"], x["name"]) for x in found.get("data", []) if x["id"] not in ours]
        if hits:
            print(f"!! {k}: similar live products {hits} — stopping for a look")
            return

        variants = []
        for i, v in enumerate(p["variants"]):
            imgs = list(v["images"]) + ([v["hafo_img"]] if v.get("hafo_img") else [])
            ids = []
            for u in imgs:
                if dry:
                    ids.append(0); continue
                out = sh("scripts/upload-media.sh", u, folder, check=False)
                mid = out.stdout.strip().splitlines()[-1] if out.returncode == 0 and out.stdout.strip() else ""
                if not mid.isdigit():
                    print(f"   image FAILED {u}\n{out.stderr[-400:]}")
                    continue
                ids.append(int(mid))
            unit, qty = unit_qty(v["label"])
            attrs = {c: i_ for c, i_ in v["attrs"].items() if c != "product-weight"}  # server derives it
            variants.append({
                "name": v["label"], "sku": v.get("sku", v["code"]),
                "sale_mode": "pack", "pricing_type": "fixed", "unit": unit, "net_quantity": qty,
                "price": v["price"], "cost_price": v["cost"], "stock": STOCK, "vendor_stock": False,
                "is_default": i == 0, "sort_order": i, "images": ids,
                "attribute_value_ids": attrs,
                "about_this_item": (v.get("about") or {}).get("en", ""),
                "ingredient_information": (v.get("ingr") or {}).get("en", ""),
                "feeding_instructions": (v.get("feed") or {}).get("en", ""),
            })
        payload = {"name": p["name"]["en"], "slug": slug, "category_ids": p["cats"],
                   "brand_id": p["brand"], "attribute_family_id": p["family"],
                   "is_best_seller": False, "is_on_sale": False, "variants": variants}
        path = os.path.join(CACHE, f"sirook-{k}.json")
        json.dump(payload, open(path, "w"), ensure_ascii=False, indent=1)
        if dry:
            print(f"DRY {k}: {len(variants)} variant(s) → {path}")
            continue
        if not all(v["images"] for v in variants):
            print(f"!! {k}: a variant has no image — not writing"); return

        out = sh("scripts/create-product.sh", path, env={"FORCE": "1"})  # checked above; only this run's own products may match
        m = re.search(r"created product (\d+)", out.stdout + out.stderr)
        pid = int(m.group(1))
        print(f"created {pid} {p['name']['en']}")

        tr_ok = {}
        for lang in ("ru", "hy"):
            tr = {"name": p["name"][lang], "variants": {}}
            for v, pv in zip(p["variants"], variants):
                tr["variants"][pv["sku"]] = {f: (v.get(src) or {}).get(lang, "")
                                             for f, src in (("about_this_item", "about"),
                                                            ("ingredient_information", "ingr"),
                                                            ("feeding_instructions", "feed"))}
            tp = os.path.join(CACHE, f"tr-{pid}-{lang}.json")
            json.dump(tr, open(tp, "w"), ensure_ascii=False, indent=1)
            r = sh("scripts/set-translation.py", str(pid), lang, tp, check=False)
            tr_ok[lang] = r.returncode == 0
            print(f"   {lang}: {'OK' if tr_ok[lang] else 'FAILED ' + (r.stdout + r.stderr)[-300:]}")

        state["done"][k] = {"id": pid, "slug": slug, "skus": [v["sku"] for v in variants],
                            "images": {v["sku"]: v["images"] for v in variants}, "translations": tr_ok}
        json.dump(state, open(STATE, "w"), indent=1)
        sh("scripts/pace.sh", "product", check=False)


if __name__ == "__main__":
    main()
