#!/usr/bin/env python3
"""Assign the new Supplies / Cleaning & Potty / Scratcher leaves to the 201
Trixie products parked in trixie-plan.json's `blocked_no_category`, and move
them into `products` so scripts/import-plan.py picks them up.

Classification uses the trixie.de productworld path from the row's Source
(the brand's own shelf), with name overrides where Trixie's shelf and Chewy's
differ (muzzles, socks, cooling mats, car seat covers, place mats).

    scripts/_recat-blocked-2026-09-11.py [--apply]
"""
import csv, json, os, re, sys, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLAN = os.path.join(ROOT, ".siruk-cache", "trixie-plan.json")
CSV = os.path.join(ROOT, "runs", "2026-09-11", "blocked-no-category.csv")

CAT = {
    "dog-collars": 69, "dog-bowls": 70, "dog-beds": 71, "dog-clothing": 72,
    "dog-travel": 73, "dog-training": 74, "dog-pads": 76, "dog-poop": 77,
    "dog-cleaners": 78, "cat-collars": 79, "cat-scratchers": 81,
    "dog-grooming-tools": 30,
}

TRIXIE_SHELF = {
    "dog-collars": "dog-collars", "dog-leashes": "dog-collars",
    "dog-harnesses": "dog-collars", "luminous-items-safety": "dog-collars",
    "jogging-accessories": "dog-collars",
    "dog-bowls-accessories": "dog-bowls",
    "travel-bowls-drinking-bottles": "dog-bowls",
    "dog-poop-bags-dispensers": "dog-poop",
    "textile-cleaning": "dog-cleaners",
    "cat-harnesses-collars": "cat-collars",
    "scratching-cardboards": "cat-scratchers",
    "scratching-furniture-for-wall-mounting": "cat-scratchers",
}


def bucket(name, source):
    n = name.lower()
    # name overrides — Trixie files these under "dog health"/"care", Chewy does not
    if "poisoned bait protection" in n:            return "dog-training"   # muzzle
    if "dog socks" in n:                           return "dog-clothing"
    if "cooling mat" in n:                         return "dog-beds"
    if "car seat cover" in n:                      return "dog-travel"
    if "towel with pockets" in n:                  return "dog-grooming-tools"
    if "poop scoop" in n or "poop bag" in n:       return "dog-poop"
    if "place mat" in n or "silicone tray" in n:   return "dog-bowls"
    if re.search(r"\b(nappy|diaper|protective pants|pads for protective)", n):
        return "dog-pads"
    if "lint" in n or "upholstery" in n or "textile brush" in n:
        return "dog-cleaners"
    if "scratching" in n:                          return "cat-scratchers"

    m = re.match(r"https://www\.trixie\.de/en/productworld/([^?]+)", source or "")
    if m:
        shelf = TRIXIE_SHELF.get(m.group(1).split("/")[2] if len(m.group(1).split("/")) > 2 else "")
        if shelf:
            return shelf

    # fallback rows (no brand-site URL): decide on the name
    if re.search(r"\b(collar|harness|lead|leash|bandana|choke|chain)\b", n):
        return "cat-collars" if re.search(r"\b(cat|kitten)\b", n) else "dog-collars"
    if "bowl" in n or "bottle" in n:               return "dog-bowls"
    return None


def main():
    apply = "--apply" in sys.argv
    plan = json.load(open(PLAN))
    blocked = plan["blocked_no_category"]

    # article code -> Source url, from the blocked CSV
    src = {r["Article Code"]: r["Source"] for r in csv.DictReader(open(CSV))}

    counts, unresolved, moved = collections.Counter(), [], []
    for p in blocked:
        codes = [v.get("_code") for v in p["variants"]]
        buckets = {bucket(p["name"], src.get(c, p.get("source", ""))) for c in codes}
        buckets.discard(None)
        if len(buckets) != 1:
            unresolved.append((p["slug"], p["name"], sorted(b or "?" for b in buckets)))
            continue
        b = buckets.pop()
        p["category_ids"] = [CAT[b]]
        counts[b] += 1
        moved.append(p)

    for b, n in counts.most_common():
        print(f"{n:5d}  {b:<20} -> category {CAT[b]}")
    print(f"{sum(counts.values())} classified, {len(unresolved)} unresolved")
    for u in unresolved:
        print("  ??", u)

    if not apply:
        print("\n(dry run — pass --apply to move them into plan['products'])")
        return
    if unresolved:
        sys.exit("refusing to apply with unresolved rows")
    plan["products"].extend(moved)
    plan["blocked_no_category"] = []
    json.dump(plan, open(PLAN, "w"), ensure_ascii=False, indent=1)
    print(f"\nmoved {len(moved)} products into plan['products'] "
          f"({len(plan['products'])} total)")


if __name__ == "__main__":
    main()
