#!/usr/bin/env python3
"""Put every non-food product under EVERY species it is sold for (2026-11-12).

Beds, carriers, bowls, brushes and the like were filed under one species only,
because our stored text rarely says "for dogs and cats" -- Trixie's own copy
just describes the bed. The brand's catalogue does say it: every article on
trixie.shop (Trixie's own Shopify store, cached by scripts/trixie-shop-index.py)
carries species tags `01_hund` / `01_katze` / `01_kleintier`. Harvey Bed 37318,
Boho Bed 38213, Junior Cave 38254 and the Capri / Relax transport boxes are
tagged dog AND cat, but sat in Dog > Beds / Carriers only.

Evidence, per product (any one is enough):
  trixie-tag   a trixie.shop variant whose sku is our sku (or our sku minus the
               trailing check digit) carries the species tag
  text         our stored about/name says "for dogs and cats" (the DUAL regex of
               scripts/multi-category.py: a plural suitability claim, never brand
               boilerplate like "your dog and cat")

For each species the evidence names but the product is not shelved under, the
MIRROR leaf of one of its current leaves is added. No mirror -> reported as a
gap (creating a category needs an explicit ask, CLAUDE.md rule 8). Food,
treats and toys are left out: their leaves are not one-to-one across species.

Never removes a category, never adds a parent. Reads the live catalogue
(`siruk export`), writes through the payload builder (put_body) with a fresh
GET per product, paced by scripts/api.sh.

    scripts/species-categories.py                  # audit -> runs/<date>/species-plan.csv
    scripts/species-categories.py --apply          # write the plan
    scripts/species-categories.py --export <json>  # reuse a saved export
"""
import csv, datetime, glob, json, os, re, subprocess, sys, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from siruk_payload import PayloadError, put_body  # noqa: E402

import importlib.util
_spec = importlib.util.spec_from_file_location("multicat", os.path.join(ROOT, "scripts/multi-category.py"))
_mc = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(_mc)
DUAL = _mc.DUAL

SHOP = os.path.join(ROOT, ".siruk-cache", "trixie-shop-catalogue.json")
TAG = {"01_hund": "dog", "01_katze": "cat", "01_kleintier": "small"}

# leaf -> {species: mirror leaf}. Only real one-to-one shelves.
PAIRS = [  # (dog, cat)
    (28, 35), (29, 36), (30, 37), (31, 38), (32, 39), (33, 40),   # grooming
    (42, 51), (43, 52), (44, 53), (45, 54), (47, 55), (48, 56), (49, 58),
    (69, 79),    # collars, leashes, ID tags
    (70, 109),   # bowls & feeders
    (71, 107),   # beds
    (73, 108),   # carriers & travel
    (78, 112),   # cleaners, stain removers, lint rollers (cat leaf created 2026-11-12)
]
MIRROR = collections.defaultdict(dict)
for d, c in PAIRS:
    MIRROR[d]["cat"] = c
    MIRROR[c]["dog"] = d
# Dog behaviour / odour sprays -> cat 67 (user call 2026-09-11). One way only:
# 67 also holds scoops and litter trays, whose dog shelf is 77, not 74.
MIRROR[74]["cat"] = 67
for g in (28, 29, 30, 31, 32, 33, 35, 36, 37, 38, 39, 40):
    MIRROR[g]["small"] = 104      # Small Animal > Grooming
for s in (70, 71, 73, 107, 108, 109):
    MIRROR[s]["small"] = 105      # Small Animal > Supplies
SKIP_TYPES = {"Dry Food", "Wet Food", "Treats", "Toys"}


def api(method, path, payload=None):
    args = [os.path.join(ROOT, "scripts/api.sh"), method, path]
    tmp = None
    if payload is not None:
        tmp = os.path.join(ROOT, ".siruk-cache", "_species_put.json")
        json.dump(payload, open(tmp, "w"), ensure_ascii=False)
        args.append(tmp)
    r = subprocess.run(args, capture_output=True, text=True, cwd=ROOT, timeout=180)
    i = r.stdout.find("{")
    return json.loads(r.stdout[i:]) if i >= 0 else {"_err": r.stderr}


def species_tree():
    out = api("GET", "/categories?forProducts=true")["data"]
    sp, nm = {}, {}
    def walk(nodes, top):
        for n in nodes:
            sp[n["id"]] = top; nm[n["id"]] = n["name"]
            walk(n.get("children") or [], top)
    for t in out:
        walk([t], {"Dog": "dog", "Cat": "cat", "Small Animal": "small", "Bird": "bird"}.get(t["name"], t["name"]))
    return sp, nm


def shop_index():
    if not os.path.exists(SHOP):
        print("no trixie.shop cache -- run scripts/trixie-shop-index.py first", file=sys.stderr)
        return {}
    c = json.load(open(SHOP))
    idx = {}
    for p in (c if isinstance(c, list) else c.get("products", [])):
        sp = {TAG[t] for t in p.get("tags", []) if t in TAG}
        if not sp:
            continue
        for v in p.get("variants", []):
            if v.get("sku"):
                idx.setdefault(v["sku"].strip(), set()).update(sp)
    return idx


def load_export(path):
    if not path:
        path = os.path.join(ROOT, "runs", datetime.date.today().isoformat(), "species-export.json")
        subprocess.run(["uv", "run", "--no-sync", "siruk", "export", "-q", "--format", "json",
                        "-o", path], cwd=ROOT, check=True)
    by = collections.defaultdict(list)
    for r in json.load(open(path)):
        by[r["product_id"]].append(r)
    return by


def main():
    apply = "--apply" in sys.argv
    exp = sys.argv[sys.argv.index("--export") + 1] if "--export" in sys.argv else None
    SP, NM = species_tree()
    idx = shop_index()
    rows, gaps = [], []
    for pid, rs in sorted(load_export(exp).items()):
        r = rs[0]
        if r["product_type"] in SKIP_TYPES:
            continue
        cur = set(r["category_ids"])
        want, why = set(), []
        if r["brand"] == "Trixie":
            for x in rs:
                s = (x["sku"] or "").strip()
                hit = idx.get(s) or idx.get(s[:-1]) or set()
                if hit:
                    want |= hit; why.append(f"trixie.shop {s}: {'+'.join(sorted(hit))}")
                    break
        text = re.sub(r"<[^>]+>", " ", (r.get("about_this_item") or "")) + " " + r["product_name"]
        m = DUAL.search(text)
        if m:
            want |= {"dog", "cat"}; why.append(f"text: '{m.group(0)[:50]}'")
        have = {SP.get(c) for c in cur}
        add = set()
        for s in sorted(want - have):
            mir = [MIRROR[c][s] for c in sorted(cur) if s in MIRROR.get(c, {})]
            if mir:
                add.add(mir[0])
            else:
                gaps.append({"id": pid, "name": r["product_name"], "cats": sorted(cur),
                             "species": s, "why": "; ".join(why)})
        if add:
            rows.append({"id": pid, "name": r["product_name"], "from": sorted(cur),
                         "add": sorted(add), "to": sorted(cur | add),
                         "add_names": ", ".join(f"{a} {NM.get(a)}" for a in sorted(add)),
                         "why": "; ".join(why)})

    day = os.path.join(ROOT, "runs", datetime.date.today().isoformat())
    os.makedirs(day, exist_ok=True)
    with open(os.path.join(day, "species-plan.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["id", "name", "from", "add", "add_names", "to", "why"])
        w.writeheader(); w.writerows(rows)
    with open(os.path.join(day, "species-gaps.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["id", "name", "cats", "species", "why"])
        w.writeheader(); w.writerows(gaps)
    for x in rows:
        print(f"{x['id']:>5} {x['name'][:40]:<42} {x['from']} + {x['add']}  ({x['why'][:60]})")
    print(f"\n{len(rows)} products gain a leaf, {len(gaps)} gaps (no mirror leaf) -> {day}/species-*.csv")
    if not apply:
        print("(audit only -- pass --apply to write)")
        return
    ok = fail = 0
    for x in rows:
        cur = api("GET", f"/products/{x['id']}").get("data")
        if not cur:
            print(f"  GET failed {x['id']}"); fail += 1; continue
        want = sorted(set(cur["category_ids"]) | set(x["add"]))
        try:
            body = put_body(cur)
        except PayloadError as e:
            print(f"  REFUSING {x['id']}: {e}"); fail += 1; continue
        body["category_ids"] = want
        res = api("PUT", f"/products/{x['id']}", body).get("data") or {}
        good = (sorted(res.get("category_ids") or []) == want
                and len(res.get("variants", [])) == len(cur["variants"]))
        ok += good; fail += not good
        print(f"  {x['id']:<5} {'ok' if good else 'FAILED'} -> {res.get('category_ids')}")
    print(f"\nupdated={ok} failed={fail}")


if __name__ == "__main__":
    main()
