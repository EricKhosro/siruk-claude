#!/usr/bin/env python3
"""Give every product all the categories it belongs to.

`category_ids` is a list and the admin's Categories field is a multi-select
tree, but the big bulk imports (Trixie, Monge, toys, treats, Acana/Orijen)
each wrote a single id. Only 29 products -- the Inspector / Gelmintal /
Insectal / Cliny / Iv San Bernard / Monge VetSolution rows, whose type skill
already carried the rule -- were filed correctly. This audits the rest and
adds the missing leaves.

What it does NOT do:
  * add a parent category. Parents roll their children up on their own
    (checked 2026-09-12: /dog/treat/ lists 48 cards from leaves 7 and 82-88
    with nothing assigned to 6), so a parent adds no listing and breaks the
    leaf rule.
  * remove anything. The new id list is always a SUPERSET of the current one;
    the script aborts on any product whose categories would shrink.
  * invent a category. Where a species has no mirror leaf (cat has no Bowls,
    Beds, Cleaning or Health Condition node) the row is reported, not guessed.

Rules, each needing evidence from the product's own stored text:

  dual-species  the pack/brand text says it is for dogs AND cats
                -> add the MIRROR leaf in the other species' tree
  (a dual-species dewormer therefore becomes 46 + 55: Cat has no dewormer
   leaf, so 46 mirrors to 55 Pharmacy & Prescriptions -- which is exactly how
   Inspector Quadro Tabs 763-765 and Gelmintal 779-780 are already filed.)
  vet-diet      a stated clinical indication on a food
                -> add 5 Health Condition (dog; cat has no such leaf)

    scripts/multi-category.py              # audit, print the plan
    scripts/multi-category.py --apply      # write it
"""
import json, os, re, subprocess, sys, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, ".siruk-cache", "multicat")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
# The PUT body is rebuilt by the one payload builder (catalog model 2026-09-29).
from siruk_payload import PayloadError, put_body  # noqa: E402

# Leaf <-> leaf across the two species trees. Only real mirrors; a leaf with no
# counterpart maps to None and is reported instead of guessed.
MIRROR = {
    3: 10, 10: 3,          # Dry Food
    4: 11, 11: 4,          # Wet Food
    28: 35, 35: 28,        # Brushes & Combs
    29: 36, 36: 29,        # Shampoos & Conditioners
    30: 37, 37: 30,        # Grooming Tools
    31: 38, 38: 31,        # Paw & Nail Care
    32: 39, 39: 32,        # Ear Care
    33: 40, 40: 33,        # Skin Care
    42: 51, 51: 42,        # Flea & Tick
    43: 52, 52: 43,        # Vitamins & Supplements
    44: 53, 53: 44,        # Probiotics & Digestive Health
    45: 54, 54: 45,        # Allergy & Itch Relief
    47: 55, 55: 47,        # Pharmacy & Prescriptions
    48: 56, 56: 48,        # Anxiety & Calming Care
    49: 58, 58: 49,        # Test Kits
    69: 79, 79: 69,        # Collars, Leashes & Harnesses
    22: 26, 26: 22,        # Toys > Activity & Intelligence
    # Treats: dog has 8 leaves, cat 6 -- collapse to the nearest cat shelf.
    82: 91, 91: 82,        # Soft & Chewy
    83: 92, 92: 83,        # Dental
    88: 90, 90: 88,        # Lickable
    84: 89, 87: 89,        # Biscuits / Freeze-Dried -> cat Crunchy
    89: 84,
    7: 91, 85: 91, 86: 91, # Naturals / Chews / Jerky -> cat Soft & Chewy
    # Cat behaviour and odour sprays live in 67 (user call, 2026-09-11).
    74: 67, 67: 74,
    # No counterpart on the other side:
    46: 55,                # dog dewormers -> cat Pharmacy
    57: None, 59: None, 60: None, 61: None, 62: None, 63: None, 64: None,
    65: None, 5: None, 70: None, 71: None, 72: None, 73: None, 76: None,
    77: None, 78: None, 81: None, 17: None, 18: None, 19: None, 20: None,
    21: None, 23: None, 24: None, 25: None, 93: None, 94: None,
}
# The dual-species claim must be a SUITABILITY claim about this product, not
# brand boilerplate. Every real hit in the catalogue reads "for dogs and cats",
# "for dogs, cats and other small animals", "designed for ... dogs and cats" or
# "cleaning of the ears of dogs and cats" -- anchored by for/of/on/with, and
# always PLURAL. Acana's range blurb "help your dog and cat live a full and
# healthy life" is the shape to reject, so "your" is excluded and the singular
# is not accepted (found on 988/993/1000, 2026-09-12).
SPECIES = r"(?:dogs|puppies)\s*(?:,|and|&|/|\+)\s*(?:cats|kittens)" \
          r"|(?:cats|kittens)\s*(?:,|and|&|/|\+)\s*(?:dogs|puppies)"
DUAL = re.compile(
    r"\b(?:for|of|on|with|suits?|suitable for)\s+"
    r"(?!your\b)(?:(?!your\b)[a-z][a-z-]*\s+){0,4}"
    r"(?:both\s+)?(?:" + SPECIES + r")\b"
    r"|\bշների և կատուների\b|\bշն\s*/\s*կատ\b|\bշն/կատ\b",
    re.I)
# A dog-only or cat-only statement that would contradict a loose DUAL hit.
VET = re.compile(r"vetsolution|veterinary diet|dietetic|clinical|"
                 r"prescription diet", re.I)


def load_tree():
    """{leaf id -> 'Dog'|'Cat'} and {id -> name}, read from the live tree."""
    out = subprocess.run([os.path.join(ROOT, "scripts/api.sh"), "GET",
                          "/categories?forProducts=true"],
                         capture_output=True, text=True, cwd=ROOT, timeout=180).stdout
    data = json.loads(out[out.index("{"):])["data"]
    sp, nm = {}, {}
    def walk(nodes, top):
        for n in nodes:
            sp[n["id"]] = top; nm[n["id"]] = n["name"]
            walk(n.get("children") or [], top)
    for t in data:
        walk([t], t["name"])
    return sp, nm


SPECIES_OF, LEAF_NAME = {}, {}


def api(method, path, payload=None):
    args = [os.path.join(ROOT, "scripts/api.sh"), method, path]
    if payload is not None:
        p = os.path.join(CACHE, "_put.json")
        json.dump(payload, open(p, "w"), ensure_ascii=False)
        args.append(p)
    r = subprocess.run(args, capture_output=True, text=True, cwd=ROOT, timeout=180)
    i = r.stdout.find("{")
    return json.loads(r.stdout[i:]) if i >= 0 else {"_err": r.stderr, "_out": r.stdout}


def text_of(d):
    v = d.get("v0") or {}
    raw = " ".join(str(v.get(k) or "") for k in ("about", "ingr", "feed"))
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", raw)) + " " + d["name"]


def plan_for(d, inv):
    """-> (add:set, reasons:list, gaps:list)"""
    cur = set(d["category_ids"])
    add, reasons, gaps = set(), [], []
    t = text_of(d)
    arm = inv.get(d["id"], "")

    m = DUAL.search(t) or DUAL.search(arm)
    if m:
        # Which species trees is it already shelved in? A product already on
        # both sides needs nothing -- Inspector Quadro Tabs are 46 (dog
        # dewormer) + 55 (cat pharmacy) and must NOT also collect 47.
        have = {SPECIES_OF.get(c) for c in cur} - {None}
        for c in sorted(cur):
            mir = MIRROR.get(c, "unknown")
            if mir is None:
                gaps.append(f"leaf {c} ({LEAF_NAME.get(c,'?')}) has no counterpart in the other tree")
            elif mir == "unknown":
                gaps.append(f"leaf {c} not in the mirror map")
            elif SPECIES_OF.get(mir) in have:
                pass                       # that species is already covered
            elif mir not in cur:
                add.add(mir)
                reasons.append(f"dual-species ({c} {LEAF_NAME.get(c,'?')} -> "
                               f"{mir} {LEAF_NAME.get(mir,'?')}): '{m.group(0).strip()[:52]}'")

    # NOTE: there is deliberately no "dewormer also goes in 47" rule. Checked
    # 2026-09-12: 46 holds 12 dewormers, 55 holds the cat ones (Cat has no
    # dewormer leaf) and 47 holds only the First Aid Kit and SexControl. The
    # dual-species dewormers are 46+55, which the mirror rule above already
    # produces -- 46+47 was never a convention here.

    mv = VET.search(t)
    if mv and cur & {3, 4} and 5 not in cur:
        add.add(5); reasons.append(f"veterinary diet -> also 5 Health Condition: '{mv.group(0)}'")
    if mv and cur & {10, 11}:
        gaps.append("cat veterinary diet, but Cat has no Health Condition leaf")

    add -= cur
    return add, reasons, gaps


def main():
    apply = "--apply" in sys.argv
    global SPECIES_OF, LEAF_NAME
    SPECIES_OF, LEAF_NAME = load_tree()
    det = [json.loads(l) for l in open(os.path.join(CACHE, "detail.ndjson"))]
    inv = {}
    tp = os.path.join(ROOT, ".siruk-cache", "trixie-plan.json")
    if os.path.exists(tp):
        for p in json.load(open(tp))["products"]:
            for v in p["variants"]:
                inv[p["slug"]] = v.get("_inv") or ""
        inv = {d["id"]: inv.get(d["slug"], "") for d in det}

    rows, gap_rows = [], []
    for d in sorted(det, key=lambda x: x["id"]):
        add, reasons, gaps = plan_for(d, inv)
        if add:
            rows.append({"id": d["id"], "name": d["name"],
                         "from": sorted(d["category_ids"]),
                         "to": sorted(set(d["category_ids"]) | add),
                         "add": sorted(add), "why": reasons})
        for g in gaps:
            gap_rows.append({"id": d["id"], "name": d["name"],
                             "cats": sorted(d["category_ids"]), "gap": g})

    json.dump(rows, open(os.path.join(CACHE, "plan.json"), "w"), ensure_ascii=False, indent=1)
    json.dump(gap_rows, open(os.path.join(CACHE, "gaps.json"), "w"), ensure_ascii=False, indent=1)

    for r in rows:
        print(f"{r['id']:>4} {r['name'][:42]:<44} {r['from']} + {r['add']}")
        for w in r["why"]:
            print(f"       · {w}")
    print(f"\n{len(rows)} products gain a category, {len(gap_rows)} gaps reported")
    print(collections.Counter(c for r in rows for c in r["add"]).most_common())

    if not apply:
        print("\n(audit only -- pass --apply to write)")
        return

    ok = fail = 0
    for r in rows:
        cur = api("GET", f"/products/{r['id']}").get("data")
        if not cur:
            print(f"  GET failed {r['id']}"); fail += 1; continue
        want = sorted(set(cur["category_ids"]) | set(r["add"]))
        if not set(want) >= set(cur["category_ids"]):
            print(f"  REFUSING {r['id']}: would shrink"); fail += 1; continue
        try:
            body = put_body(cur)
        except PayloadError as e:
            print(f"  REFUSING {r['id']}: {e}"); fail += 1; continue
        body["category_ids"] = want
        res = api("PUT", f"/products/{r['id']}", body).get("data", {})
        good = (sorted(res.get("category_ids") or []) == want
                and len(res.get("variants", [])) == len(cur["variants"]))
        if good:
            ok += 1
            print(f"  {r['id']:<4} {r['name'][:38]:<40} -> {want} ({len(res['variants'])} variants kept)")
        else:
            fail += 1
            print(f"  {r['id']:<4} FAILED cats={res.get('category_ids')} "
                  f"variants={len(res.get('variants', []))} was {len(cur['variants'])}")
    print(f"\nupdated={ok} failed={fail}")


if __name__ == "__main__":
    main()
