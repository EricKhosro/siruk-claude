#!/usr/bin/env python3
"""Write ru + hy for a batch of products from one slug-keyed translation file.

The file maps a product slug to {"skus": [...], "ru": [name, about_html],
"hy": [name, about_html]} — the same about text is written to every SKU listed,
which is right for a product whose variants differ only by flavour or size.
Product ids come from the import-plan state file, so a slug never has to be
resolved by name search.

    scripts/apply-translations.py <translations.json> <plan.state.json>
"""
import json, os, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, ".siruk-cache")


def main():
    tr = json.load(open(sys.argv[1]))
    state = json.load(open(sys.argv[2]))
    ids = {slug: rec["id"] for slug, rec in state["done"].items()}
    missing = [s for s in tr if s not in ids]
    if missing:
        print("not in state (skipped):", missing, file=sys.stderr)
    for slug, t in tr.items():
        pid = ids.get(slug)
        if not pid:
            continue
        for loc in ("ru", "hy"):
            name, about = t[loc]
            body = {"name": name,
                    "variants": {sku: {"about_this_item": about} for sku in t["skus"]}}
            p = os.path.join(CACHE, f"tr-{pid}-{loc}.json")
            json.dump(body, open(p, "w"), ensure_ascii=False, indent=1)
            r = subprocess.run([os.path.join(ROOT, "scripts/set-translation.py"),
                                str(pid), loc, p], capture_output=True, text=True,
                               cwd=ROOT, timeout=300)
            line = (r.stdout.strip().splitlines() or [r.stderr.strip()[-200:]])[-1]
            print(f"{slug} [{loc}] {line}")


main()
