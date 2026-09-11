#!/usr/bin/env python3
"""Import a plan of products into the Siruk admin, resumable.

Plan file: {"products": [ {slug, name, category_ids, brand_id, attribute_family_id,
  "variants": [ {sku, name, pricing_type, price | price_per_kg+weight, cost_price, stock,
                 is_default, sort_order, images: [url...], attribute_value_ids: {},
                 about_this_item, ingredient_information, feeding_instructions} ],
  "existing_id": <optional: add the variants to this product instead of creating> } ]}

Per product: upload every image url (scripts/upload-media.sh, cached, verified),
exact-slug check against the live catalogue, then scripts/create-product.sh
(FORCE=1: the planner already guarantees one product per line) or, for
existing_id / a slug that already exists, scripts/add-variant.sh per missing SKU.
State in <plan>.state.json — a re-run continues where it stopped.

    scripts/import-plan.py plan.json [--limit N] [--dry-run] [--only slug,slug]
"""
import argparse, json, os, re, subprocess, sys, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, ".siruk-cache")


def sh(args, env=None, timeout=600):
    r = subprocess.run(args, capture_output=True, text=True, timeout=timeout, cwd=ROOT,
                       env=dict(os.environ, **(env or {})))
    return r.returncode, r.stdout.strip(), r.stderr.strip()


def load(path, default):
    if os.path.exists(path):
        try:
            return json.load(open(path))
        except ValueError:
            pass
    return default


def save(path, obj):
    tmp = path + ".tmp"
    json.dump(obj, open(tmp, "w"), ensure_ascii=False, indent=1)
    os.replace(tmp, path)


def api_get(path):
    code, out, err = sh([os.path.join(ROOT, "scripts/api.sh"), "GET", path])
    i = out.find("{")
    return json.loads(out[i:]) if i >= 0 else None


def find_by_slug(slug, name):
    """Exact slug match through the name search (the only search the API has)."""
    for q in (name, slug.replace("-", " ")):
        d = api_get("/products?search=" + q.replace(" ", "%20").replace("&", "%26"))
        for p in (d or {}).get("data", []):
            if p.get("slug") == slug:
                return p.get("id")
    return None


def upload(url, media):
    if url in media:
        return media[url]
    code, out, err = sh([os.path.join(ROOT, "scripts/upload-media.sh"), url], timeout=900)
    mid = None
    for line in reversed(out.splitlines()):
        if line.strip().isdigit():
            mid = int(line.strip()); break
    if mid:
        media[url] = mid
    else:
        media[url] = None
        print(f"      image FAILED {url[-70:]}: {(err or out)[-160:]}", file=sys.stderr)
    return mid


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("plan")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--only", default="")
    a = ap.parse_args()

    plan = json.load(open(a.plan))["products"]
    state_path = a.plan.rsplit(".json", 1)[0] + ".state.json"
    state = load(state_path, {"done": {}, "failed": {}, "media": {}})
    only = set(a.only.split(",")) if a.only else None

    todo = [p for p in plan if p["slug"] not in state["done"] and (not only or p["slug"] in only)]
    if a.limit:
        todo = todo[: a.limit]
    print(f"{len(state['done'])} done, {len(state['failed'])} failed before, {len(todo)} to do", file=sys.stderr)

    for n, p in enumerate(todo, 1):
        tag = f"[{n}/{len(todo)}] {p['name'][:40]:<42}"
        variants, no_image = [], []
        for v in p["variants"]:
            ids = []
            for url in v.get("images") or []:
                if a.dry_run:
                    ids.append(0); continue
                mid = upload(url, state["media"])
                save(state_path, state)
                if mid and mid not in ids:
                    ids.append(mid)
            if not ids:
                no_image.append(v["sku"])
            nv = {k: v[k] for k in v if k != "images" and not k.startswith("_")}
            nv["images"] = ids
            nv.setdefault("vendor_stock", False)
            nv.setdefault("about_this_item", ""); nv.setdefault("ingredient_information", ""); nv.setdefault("feeding_instructions", "")
            variants.append(nv)

        payload = {"name": p["name"], "slug": p["slug"], "category_ids": p["category_ids"],
                   "brand_id": p["brand_id"], "attribute_family_id": p.get("attribute_family_id"),
                   "is_best_seller": False, "is_on_sale": False, "variants": variants}
        ppath = os.path.join(CACHE, f"plan-payload-{p['slug'][:60]}.json")
        save(ppath, payload)

        if a.dry_run:
            print(f"{tag} DRY variants={len(variants)} images={[len(v['images']) for v in variants]} no_image={no_image}", file=sys.stderr)
            continue

        existing = p.get("existing_id") or find_by_slug(p["slug"], p["name"])
        if existing:
            live = api_get(f"/products/{existing}")["data"]
            have = {str(v["sku"]) for v in live["variants"]}
            added, errs = [], []
            for v in variants:
                if str(v["sku"]) in have:
                    continue
                v = dict(v); v.pop("is_default", None); v.pop("sort_order", None)
                vpath = os.path.join(CACHE, f"plan-variant-{v['sku']}.json")
                save(vpath, v)
                code, out, err = sh([os.path.join(ROOT, "scripts/add-variant.sh"), str(existing), vpath])
                if code == 0:
                    added.append(v["sku"])
                else:
                    errs.append(f"{v['sku']}: {(err or out)[-200:]}")
            if errs:
                state["failed"][p["slug"]] = {"id": existing, "errors": errs}
                print(f"{tag} PARTIAL id={existing} added={added} errors={errs}", file=sys.stderr)
            else:
                state["done"][p["slug"]] = {"id": existing, "added": added, "no_image": no_image, "note": "existing product"}
                print(f"{tag} EXISTS id={existing} added={added}", file=sys.stderr)
            save(state_path, state)
            continue

        code, out, err = sh([os.path.join(ROOT, "scripts/create-product.sh"), ppath], env={"FORCE": "1"})
        m = re.search(r"created product (\d+)", out + err)
        if m:
            state["done"][p["slug"]] = {"id": int(m.group(1)), "no_image": no_image}
            state["failed"].pop(p["slug"], None)
            print(f"{tag} OK id={m.group(1)} variants={len(variants)}" + (f" NO IMAGE {no_image}" if no_image else ""), file=sys.stderr)
        else:
            state["failed"][p["slug"]] = (out + " | " + err)[-600:]
            print(f"{tag} FAILED {(err or out)[-220:]}", file=sys.stderr)
        save(state_path, state)
        sh([os.path.join(ROOT, "scripts/pace.sh"), "product"])

    save(state_path, state)
    print(f"\ndone={len(state['done'])} failed={len(state['failed'])}", file=sys.stderr)
    for s, e in list(state["failed"].items())[:20]:
        print(f"  FAIL {s}: {str(e)[:200]}", file=sys.stderr)


if __name__ == "__main__":
    main()
