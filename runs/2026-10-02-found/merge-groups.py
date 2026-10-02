#!/usr/bin/env python3
"""Fold the queued bulk items of one product into a single item (rule 9: variants, not
siblings). card-import --queue writes one product per card; these cards are flavours /
colours of the same product, so their variants go onto the first card's item.

    merge-groups.py            # dry run
    merge-groups.py --write    # rewrites bulk/<leader>.json, moves the others to bulk-merged/
"""
import json, os, shutil, sys

HERE = os.path.dirname(os.path.abspath(__file__))
B, M = os.path.join(HERE, "bulk"), os.path.join(HERE, "bulk-merged")
GROUPS = [
    ["CP909145", "CP909205", "909155", "REG00030"],   # Club 4 Paws Premium Adult Dry Cat Food
    ["PG901425", "PG900025"],                         # Gav! Adult Dry Dog Food
    ["PM902085", "PM902075", "PM902105"],             # Myau Adult Dry Cat Food
    ["IN10247", "IN10882"],                           # 8in1 Delights Bones L
    ["BP12512", "BP10196", "BP10199"],                # Beaphar Flea & Tick Collar for Dogs
    ["20632", "20629", "20630"],                      # Beaphar Soft Flea Collar for Cats
]
WRITE = "--write" in sys.argv
for g in GROUPS:
    items = [json.load(open(os.path.join(B, f"{c}.json"))) for c in g]
    lead = items[0]
    names = {i["name"] for i in items}
    assert len(names) == 1, f"{g}: names differ {names}"
    assert len({i["brand_id"] for i in items}) == 1 and len({i["attribute_family_id"] for i in items}) == 1, g
    cats = []
    for i in items:
        cats += [c for c in i["category_ids"] if c not in cats]
    variants = []
    for i in items:
        for v in i["variants"]:
            v = dict(v); v["is_default"] = not variants
            variants.append(v)
    tr = {}
    for lang in ("ru", "hy"):
        t = {"name": lead["translations"][lang]["name"], "variants": {}}
        for i in items:
            t["variants"].update(i["translations"][lang].get("variants") or {})
        tr[lang] = t
    merged = dict(lead, category_ids=cats, variants=variants, translations=tr)
    print(f"{g[0]} '{lead['name']}' ({lead['slug']}): {len(variants)} variants "
          f"{[v['sku'] for v in variants]} cats {cats}")
    if WRITE:
        os.makedirs(M, exist_ok=True)
        for c in g[1:]:
            shutil.move(os.path.join(B, f"{c}.json"), os.path.join(M, f"{c}.json"))
        shutil.copy(os.path.join(B, f"{g[0]}.json"), os.path.join(M, f"{g[0]}.before-merge.json"))
        json.dump(merged, open(os.path.join(B, f"{g[0]}.json"), "w"), ensure_ascii=False, indent=1)
