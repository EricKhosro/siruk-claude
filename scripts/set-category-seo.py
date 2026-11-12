#!/usr/bin/env python3
"""Category SEO: meta title + description in en/ru/hy and the SEO image (user + SEO specialist, 2026-11-10).

    scripts/set-category-seo.py                 # dry run: preview CSV + length check, no writes
    scripts/set-category-seo.py --apply         # write every category that differs, read each back
    scripts/set-category-seo.py --apply --ids 3 10

Text: siruk/seo.py category_meta() with the phrase from reference/category-seo-phrases.json
("Buy Dry Dog Food Online" / "Buy dry dog food online at Siruk. Choose from trusted brands and get
delivery in Yerevan."), title <= 60 and description <= 160 characters in every locale.
SEO image (meta_image) = the category's own `image` (not featured_image); no image -> left empty.

One PUT per locale (Content-Language picks the seo row's locale): {name (that locale's), slug,
parent_id, list_as_products, meta, meta_image}. HasSeo re-syncs meta_image on every PUT that carries
`meta`, so meta_image is always sent with it or the image would be cleared. image, featured_image,
description, quick_links, related_searches, complements and pins are not sent and stay as they are
(checked on the read-back).
"""
import csv, json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from siruk_payload import api  # noqa: E402
from siruk.seo import category_meta, TITLE_MAX, DESC_MAX  # noqa: E402

LANGS = ("en", "ru", "hy")
KEEP = ("slug", "parent_id", "image", "featured_image", "complement_category_ids", "list_as_products")


def main():
    apply = "--apply" in sys.argv
    only = {int(a) for a in sys.argv[sys.argv.index("--ids") + 1:]} if "--ids" in sys.argv else None
    phrases = {int(k): v for k, v in json.load(open(os.path.join(ROOT, "reference/category-seo-phrases.json"))).items()
               if not k.startswith("_")}
    cats = {l: {c["id"]: c for c in api("GET", "/categories?search=&sortBy=id", lang=l)["data"]} for l in LANGS}
    missing = sorted(set(cats["en"]) - set(phrases))
    if missing:
        sys.exit(f"no phrase in reference/category-seo-phrases.json for categories {missing}")

    rows, plan = [], []
    for cid in sorted(cats["en"]):
        if only and cid not in only:
            continue
        en = cats["en"][cid]
        img = en.get("image")
        for i, l in enumerate(LANGS):
            want = category_meta(l, phrases[cid][i])
            cur = cats[l][cid]
            same = (cur.get("meta") or {}) == want and cur.get("meta_image") == img
            rows.append({"id": cid, "path": en["path"], "lang": l, "title": want["title"], "title_len": len(want["title"]),
                         "description": want["description"], "desc_len": len(want["description"]),
                         "seo_image": img or "", "old_title": (cur.get("meta") or {}).get("title"),
                         "status": "same" if same else "write"})
            assert len(want["title"]) <= TITLE_MAX and len(want["description"]) <= DESC_MAX
            if not same:
                plan.append((cid, l, want, img))

    out = os.path.join(ROOT, "runs/2026-11-10/category-seo-preview.csv")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader(); w.writerows(rows)
    print(f"preview: {out}")
    print(f"longest title {max(r['title_len'] for r in rows)}/{TITLE_MAX}, "
          f"longest description {max(r['desc_len'] for r in rows)}/{DESC_MAX}")
    noimg = sorted({r["id"] for r in rows if not r["seo_image"]})
    print(f"{len(plan)} locale writes planned; no category image (SEO image left empty): {noimg}")
    if not apply:
        return

    for cid, l, want, img in plan:
        cur = api("GET", f"/categories/{cid}", lang=l)["data"]
        body = {"name": cur["name"], "slug": cur["slug"], "parent_id": cur.get("parent_id"),
                "list_as_products": bool(cur.get("list_as_products")), "meta": want, "meta_image": img}
        api("PUT", f"/categories/{cid}", body, lang=l)
        back = api("GET", f"/categories/{cid}", lang=l)["data"]
        bad = [k for k in KEEP if back.get(k) != cur.get(k)]
        if back.get("name") != cur["name"]:
            bad.append("name")
        if (back.get("meta") or {}) != want:
            bad.append("meta")
        if back.get("meta_image") != img:
            bad.append("meta_image")
        if bad:
            sys.exit(f"category {cid} [{l}] read-back mismatch on {bad}: {json.dumps(back, ensure_ascii=False)[:500]}")
        print(f"ok {cid:>4} [{l}] {want['title']}")
    print(f"done: {len(plan)} locale writes")


if __name__ == "__main__":
    main()
