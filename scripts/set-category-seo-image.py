#!/usr/bin/env python3
"""Fill every category's SEO image (meta_image) that is still empty.

    scripts/set-category-seo-image.py            # dry run: what each category would get
    scripts/set-category-seo-image.py --apply    # PUT, then read each one back

Source, in order (user 2026-10-23): the category's own `image`, else the first image of the
product that leads the category's storefront listing (public /api/categories/<path>/products,
default Relevance order, subcategory products included). A category with neither is skipped.

The category PUT body is {name, slug, parent_id, list_as_products, meta_image}, copied from a
fresh GET (see set-complements.py for why list_as_products must be sent). HasSeo syncs SEO when
meta_image is in the request; with no `meta` key it fills nothing, so title/description stay.
"""
import json, os, sys, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from siruk_payload import api  # noqa: E402

PUBLIC = "https://api.siruk.am/api"


def top_product_image(path):
    req = urllib.request.Request(f"{PUBLIC}/categories/{path}/products", headers={"User-Agent": "curl/8"})
    with urllib.request.urlopen(req, timeout=60) as r:
        items = json.load(r).get("items") or []
    for it in items:
        if it.get("images"):
            return it["images"][0]["id"], f"product {it['productId']} {it['displayName']}"
    return None, None


def main():
    apply = "--apply" in sys.argv
    cats = api("GET", "/categories?search=&sortBy=id")["data"]
    done = skipped = kept = 0
    for c in sorted(cats, key=lambda c: c["id"]):
        if c.get("meta_image"):
            kept += 1
            continue
        if c.get("image"):
            mid, why = c["image"], "own image"
        else:
            mid, why = top_product_image(c["path"])
        if not mid:
            print(f"SKIP {c['id']:>4} {c['path']}: no image, no products with images")
            skipped += 1
            continue
        print(f"{'SET ' if apply else 'would'} {c['id']:>4} {c['path']}: meta_image {mid} ({why})")
        if not apply:
            continue
        cur = api("GET", f"/categories/{c['id']}")["data"]
        body = {"name": cur["name"], "slug": cur["slug"], "parent_id": cur.get("parent_id"),
                "list_as_products": bool(cur.get("list_as_products")), "meta_image": mid}
        api("PUT", f"/categories/{c['id']}", body)
        back = api("GET", f"/categories/{c['id']}")["data"]
        if back.get("meta_image") != mid or back.get("meta") != cur.get("meta") \
                or back.get("image") != cur.get("image") \
                or back.get("complement_category_ids") != cur.get("complement_category_ids"):
            sys.exit(f"read-back mismatch on category {c['id']}: {json.dumps(back)[:400]}")
        done += 1
    print(f"\n{'set' if apply else 'would set'} {done if apply else '-'}; already had one {kept}; skipped {skipped}")


if __name__ == "__main__":
    main()
