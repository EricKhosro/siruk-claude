#!/usr/bin/env python3
"""Related-search chips on category leaves, en/ru/hy, from reference/related-searches.json.

    scripts/set-related-searches.py                 # dry run: what would be written
    scripts/set-related-searches.py --apply         # write the empty ones, read each back
    scripts/set-related-searches.py --apply --ids 5 7
    scripts/set-related-searches.py --apply --force # also overwrite chips already set

One PUT per locale (Content-Language picks the translation): {name (that locale's), slug,
parent_id, list_as_products, related_searches}. The update fills only the keys it is sent, except
`list_as_products`, which an absent key resets to false — so the current value is always sent.
`meta` is not sent (HasSeo would re-sync meta_image), and image, featured_image, description,
quick_links, complements and pins stay as they are (checked on the read-back). A locale that
already has chips is left alone unless --force. The storefront turns each line into a chip that
opens the search page for it (SearchService::curatedRelatedSearches).
"""
import json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from siruk_payload import api  # noqa: E402

LANGS = ("en", "ru", "hy")
KEEP = ("slug", "parent_id", "image", "featured_image", "description", "quick_links",
        "list_as_products", "complement_category_ids", "meta", "meta_image")


def main():
    apply, force = "--apply" in sys.argv, "--force" in sys.argv
    only = {int(a) for a in sys.argv[sys.argv.index("--ids") + 1:] if a.isdigit()} if "--ids" in sys.argv else None
    want = {int(k): v for k, v in json.load(open(os.path.join(ROOT, "reference/related-searches.json"),
                                                 encoding="utf-8")).items() if not k.startswith("_")}
    plan = []
    for cid, spec in sorted(want.items()):
        if only and cid not in only:
            continue
        for l in LANGS:
            text = "\n".join(p.strip() for p in spec[l] if p.strip())
            assert len(text) <= 2000, (cid, l)
            plan.append((cid, spec["path"], l, text))
    writes = 0
    for cid, path, l, text in plan:
        cur = api("GET", f"/categories/{cid}", lang=l)["data"]
        if cur.get("path") != path:
            sys.exit(f"category {cid} is {cur.get('path')!r} live, the file says {path!r}: fix the file first")
        have = (cur.get("related_searches") or "").strip()
        if l != "en" and have and have == "\n".join(want[cid]["en"]):
            have = ""                        # an untranslated field falls back to the English text
        if have == text:
            print(f"same {cid:>4} [{l}] {path}"); continue
        if have and not force:
            print(f"kept {cid:>4} [{l}] {path}: already has {have.count(chr(10)) + 1} chips (--force to overwrite)"); continue
        if not apply:
            print(f"plan {cid:>4} [{l}] {path}: {text.replace(chr(10), ' | ')}"); writes += 1; continue
        body = {"name": cur["name"], "slug": cur["slug"], "parent_id": cur.get("parent_id"),
                "list_as_products": bool(cur.get("list_as_products")), "related_searches": text}
        api("PUT", f"/categories/{cid}", body, lang=l)
        back = api("GET", f"/categories/{cid}", lang=l)["data"]
        bad = [k for k in KEEP if back.get(k) != cur.get(k)]
        if back.get("name") != cur["name"]:
            bad.append("name")
        if (back.get("related_searches") or "").strip() != text:
            bad.append("related_searches")
        if bad:
            sys.exit(f"category {cid} [{l}] read-back mismatch on {bad}")
        writes += 1
        print(f"ok   {cid:>4} [{l}] {path}: {text.replace(chr(10), ' | ')}")
    print(f"{'written' if apply else 'planned'}: {writes} locale writes")


if __name__ == "__main__":
    main()
