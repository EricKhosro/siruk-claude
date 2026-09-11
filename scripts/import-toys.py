#!/usr/bin/env python3
"""Import the planned toys into the Siruk admin.

Reads .siruk-cache/toy-plan.json (from plan-toys.py) and, per product:
  1. resolves an official image per variant  (scripts/trixie-image.sh <article>)
  2. uploads it                              (scripts/upload-media.sh <url>)
  3. checks the catalogue for an existing product with the same slug
  4. POSTs the product and verifies it by reading it back

Resumable: a state file records which slugs are done, so a re-run continues.
Images are resolved through a cache because trixie-image.sh probes 12 CDN urls
per article and trixie.de throttles bursts.

Usage:
    import-toys.py [--limit N] [--dry-run]
"""
import argparse, json, os, re, subprocess, sys, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, ".siruk-cache")
PLAN = os.path.join(CACHE, "toy-plan.json")
STATE = os.path.join(CACHE, "toy-import-state.json")
IMGMAP = os.path.join(CACHE, "toy-images.json")


MATERIAL_ONLY = re.compile(
    r"^(plush|fabric|latex|natural rubber|rubber|thermoplastic rubber|tpr|"
    r"cotton|polyester|plastic|vinyl|wood|paper cord|foam|felt)"
    r"[\w\s/()\-.]*$", re.I)


def sh(args, timeout=180):
    r = subprocess.run(args, capture_output=True, text=True, timeout=timeout, cwd=ROOT)
    return r.returncode, r.stdout.strip(), r.stderr.strip()


def load(path, default):
    if os.path.exists(path):
        try:
            return json.load(open(path))
        except ValueError:
            pass
    return default


def save(path, obj):
    json.dump(obj, open(path, "w"), ensure_ascii=False, indent=1)


def image_for(article, imgmap):
    if article in imgmap:
        return imgmap[article]
    code, out, _ = sh([os.path.join(ROOT, "scripts/trixie-image.sh"), article])
    url = out.splitlines()[0].strip() if out else ""
    imgmap[article] = url
    save(IMGMAP, imgmap)
    time.sleep(0.8)                     # trixie.de throttles bursts
    return url


def slug_exists(slug, name):
    """Exact-slug check -- the real uniqueness key.

    create-product.sh's own guard is a *fuzzy name* match, which is right for
    hand-driven imports but false-positives here: "Playing Rope" and "Playing
    Rope with Woven-in Ball" are different Trixie products on different pages.
    The planner already guarantees one product per Trixie product page with a
    unique slug, so we do the precise check ourselves and then set FORCE=1 to
    skip the fuzzy one.
    """
    code, out, _ = sh([os.path.join(ROOT, "scripts/api.sh"), "GET",
                       "/products?search=" + name.replace(" ", "%20")])
    try:
        data = json.loads(out[out.index("{"):])["data"]
    except Exception:
        return None
    for p in data:
        if p.get("slug") == slug:
            return p.get("id")
    return None


def upload(url, mediamap):
    if url in mediamap:
        return mediamap[url]
    code, out, err = sh([os.path.join(ROOT, "scripts/upload-media.sh"), url], timeout=300)
    mid = None
    for line in reversed(out.splitlines()):
        if line.strip().isdigit():
            mid = int(line.strip()); break
    if mid:
        mediamap[url] = mid
    return mid


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    plan = json.load(open(PLAN))["planned"]
    state = load(STATE, {"done": {}, "failed": {}, "media": {}})
    imgmap = load(IMGMAP, {})

    todo = [p for p in plan if p["slug"] not in state["done"]]
    if a.limit:
        todo = todo[: a.limit]
    print(f"{len(state['done'])} already imported, {len(todo)} to do", file=sys.stderr)

    for n, p in enumerate(todo, 1):
        variants, no_image = [], []
        for v in p["variants"]:
            url = image_for(v["sku"], imgmap)
            mid = upload(url, state["media"]) if url else None
            if not mid:
                no_image.append(v["sku"])
            # A bullet that only restates the Material attribute is not content:
            # 72 of these pages publish nothing but "cotton/polyester", which
            # would render as an "About this item" saying one word already shown
            # as an attribute. Drop those; leave the field empty if none remain.
            keep = [b for b in p["bullets"] if not MATERIAL_ONLY.match(b.strip())]
            body = "".join(f"<li>{b}</li>" for b in keep)
            variants.append({
                "name": v["label"],
                "about_this_item": (f"<ul>{body}</ul>" if body else "")
                                   + (f"<p>{p['description']}</p>" if p["description"] else ""),
                "ingredient_information": "", "feeding_instructions": "",
                "pricing_type": "fixed",
                "sku": v["sku"], "price": v["price"], "cost_price": v["cost_price"],
                "stock": v["stock"], "vendor_stock": False,
                "sort_order": v["sort_order"], "is_default": v["is_default"],
                "images": [mid] if mid else [],
                "attribute_value_ids": v["attribute_value_ids"],
            })

        payload = {
            "name": p["name"], "slug": p["slug"],
            "category_ids": [p["category_id"]],
            "brand_id": 8, "attribute_family_id": p["attribute_family_id"],
            "is_best_seller": False, "is_on_sale": False,
            "variants": variants,
        }
        path = os.path.join(CACHE, "toy-payload.json")
        save(path, payload)

        tag = f"[{n}/{len(todo)}] {p['name'][:36]:<38}"
        if a.dry_run:
            print(f"{tag} DRY  variants={len(variants)} no_image={no_image}", file=sys.stderr)
            continue

        existing = slug_exists(p["slug"], p["name"])
        if existing:
            state["done"][p["slug"]] = {"id": existing, "no_image": no_image,
                                        "note": "already existed"}
            print(f"{tag} SKIP already exists id={existing}", file=sys.stderr)
            save(STATE, state)
            continue

        env = dict(os.environ, FORCE="1")
        r = subprocess.run([os.path.join(ROOT, "scripts/create-product.sh"), path],
                           capture_output=True, text=True, timeout=300, cwd=ROOT, env=env)
        out, err = r.stdout.strip(), r.stderr.strip()
        m = re.search(r"created product (\d+)", out + err)
        if m:
            state["done"][p["slug"]] = {"id": int(m.group(1)), "no_image": no_image}
            print(f"{tag} OK id={m.group(1)} variants={len(variants)}"
                  + (f" NO IMAGE {no_image}" if no_image else ""), file=sys.stderr)
        else:
            state["failed"][p["slug"]] = (out + " | " + err)[-400:]
            print(f"{tag} FAILED {(err or out)[-160:]}", file=sys.stderr)
        save(STATE, state)

    save(STATE, state)
    print(f"\ndone={len(state['done'])} failed={len(state['failed'])}", file=sys.stderr)
    if state["failed"]:
        for s, e in list(state["failed"].items())[:10]:
            print(f"  FAIL {s}: {e[:150]}", file=sys.stderr)


if __name__ == "__main__":
    main()
