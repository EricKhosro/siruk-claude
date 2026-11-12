#!/usr/bin/env python3
"""Brand SEO: meta title + description in en/ru/hy (user + SEO specialist, 2026-11-10).

    scripts/set-brand-seo.py                    # dry run: preview CSV + length check, no writes
    scripts/set-brand-seo.py --apply            # write every brand that differs, read each back
    scripts/set-brand-seo.py --apply --logo     # also set the SEO image (meta_image) to the brand logo
    scripts/set-brand-seo.py --apply --ids 1 3

Text: siruk/seo.py brand_meta() — "{Brand} – Buy Online in Yerevan" / "Buy {Brand} online at Siruk.
Browse the full range, delivered in Yerevan.", title <= 60 and description <= 160 in every locale.

One PUT per locale (Content-Language picks the seo row's locale): {name (that locale's), slug, meta,
meta_image}. HasSeo re-syncs meta_image on every PUT that carries `meta`, so the current meta_image
(or the logo with --logo) is always sent, or it would be cleared. `image` (the logo) is not sent and
stays as it is (checked on the read-back).
"""
import csv, json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from siruk_payload import api  # noqa: E402
from siruk.seo import brand_meta, TITLE_MAX, DESC_MAX  # noqa: E402

LANGS = ("en", "ru", "hy")


def main():
    apply, logo = "--apply" in sys.argv, "--logo" in sys.argv
    only = {int(a) for a in sys.argv[sys.argv.index("--ids") + 1:]} if "--ids" in sys.argv else None
    brands = {l: {b["id"]: b for b in api("GET", "/brands", lang=l)["data"]} for l in LANGS}

    rows, plan = [], []
    for bid in sorted(brands["en"]):
        if only and bid not in only:
            continue
        en = brands["en"][bid]
        img = en.get("image") if logo else en.get("meta_image")
        for l in LANGS:
            cur = brands[l][bid]
            want = brand_meta(l, cur["name"].strip())
            assert len(want["title"]) <= TITLE_MAX and len(want["description"]) <= DESC_MAX
            same = (cur.get("meta") or {}) == want and cur.get("meta_image") == img
            rows.append({"id": bid, "brand": cur["name"], "lang": l, "title": want["title"],
                         "title_len": len(want["title"]), "description": want["description"],
                         "desc_len": len(want["description"]), "seo_image": img or "",
                         "old_title": (cur.get("meta") or {}).get("title"),
                         "old_description": (cur.get("meta") or {}).get("description"),
                         "status": "same" if same else "write"})
            if not same:
                plan.append((bid, l, want, img))

    out = os.path.join(ROOT, "runs/2026-11-10/brand-seo-preview.csv")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader(); w.writerows(rows)
    print(f"preview: {out}")
    print(f"longest title {max(r['title_len'] for r in rows)}/{TITLE_MAX}, "
          f"longest description {max(r['desc_len'] for r in rows)}/{DESC_MAX}")
    print(f"{len(plan)} locale writes planned; no SEO image: {sorted({r['id'] for r in rows if not r['seo_image']})}")
    if not apply:
        return

    for bid, l, want, img in plan:
        cur = api("GET", f"/brands/{bid}", lang=l)["data"]
        api("PUT", f"/brands/{bid}", {"name": cur["name"], "slug": cur["slug"], "meta": want, "meta_image": img}, lang=l)
        back = api("GET", f"/brands/{bid}", lang=l)["data"]
        bad = [k for k in ("name", "slug", "image") if back.get(k) != cur.get(k)]
        if (back.get("meta") or {}) != want:
            bad.append("meta")
        if back.get("meta_image") != img:
            bad.append("meta_image")
        if bad:
            sys.exit(f"brand {bid} [{l}] read-back mismatch on {bad}: {json.dumps(back, ensure_ascii=False)[:500]}")
        print(f"ok {bid:>4} [{l}] {want['title']}")
    print(f"done: {len(plan)} locale writes")


if __name__ == "__main__":
    main()
