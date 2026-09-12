#!/usr/bin/env python3
"""Assign every treat product to its Chewy-style leaf under Dog/Cat > Treat.

Written 2026-09-12, when the user asked for treat subcategories (dog had one
leaf, cat none). The 13 new leaves are 82-94; leaf 7 was renamed
"Bones, Bully Sticks & Naturals".

The decision is made from the variant's own stored text -- the brand-site
composition and bullet list written at import -- never from the name alone
where text exists. Rules, in order (first match wins):

  naturals   single-ingredient / named dried animal part (skin, ear, scalp,
             leg, tail) with no hide substrate            -> 7   (dog only)
  chew       composition contains rawhide / collagen / hide -> 85  (dog only)
  freeze     "freeze-dried" in the composition            -> 87 dog / 89 cat
  lickable   "liquid snack" / pate / paste / malt, or moisture >= 50 % on a
             spreadable format                            -> 88 dog / 90 cat
  dental     the product's own line or claim is dental
             (Denta Fun, Dentros, Monge Gift Dental)      -> 83 dog / 92 cat
  biscuit    baked cereal cookie, no moisture declared    -> 84 dog / 89 cat
  jerky      the pack's form word is a flat sliced-meat
             format: filet, stripe/strip, coin, carpaccio,
             tender                                       -> 86  (dog only)
  crunchy    an explicit crunchy layer / crunchy format    -> 89  (cat only)
  catnip     catnip / matatabi attractant                 -> 93  (cat only)
  grass      seed-substrate grass to grow                 -> 94  (cat only)
  soft       everything else: semi-moist meaty or cereal
             morsels, the default treat shelf             -> 82 dog / 91 cat

Cat has no Naturals / Long-Lasting Chews / Jerky / Biscuits / Freeze-Dried
leaf (the Chewy cat menu the user supplied has six entries), so a cat
freeze-dried or baked-cookie row lands on Crunchy Treats -- flagged in the
report as a question rather than silently widened.

    scripts/classify-treats.py            # print the plan
    scripts/classify-treats.py --apply    # write category_ids
"""
import json, os, re, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, ".siruk-cache", "treats")
KEEP = ("name", "slug", "category_ids", "brand_id", "attribute_family_id",
        "is_best_seller", "is_on_sale", "variants")

LEAF = {                       # (dog id, cat id)
    "naturals": (7,  None), "chew":    (85, None), "jerky":   (86, None),
    "biscuit":  (84, 89),   "freeze":  (87, 89),   "crunchy": (None, 89),
    "lickable": (88, 90),   "soft":    (82, 91),   "dental":  (83, 92),
    "catnip":   (None, 93), "grass":   (None, 94),
}
# Where a cat row lands when its bucket has no cat leaf.
CAT_FALLBACK = {"naturals": 91, "chew": 91, "jerky": 91}

NAME = {7: "Bones, Bully Sticks & Naturals", 82: "Soft & Chewy Treats",
        83: "Dental Treats", 84: "Biscuits & Cookies", 85: "Long-Lasting Chews",
        86: "Jerky Treats", 87: "Freeze-Dried & Dehydrated", 88: "Lickable Treats",
        89: "Crunchy Treats", 90: "Lickable Treats", 91: "Soft & Chewy Treats",
        92: "Dental Treats", 93: "Catnip", 94: "Cat Grass"}

# Species is taken from the Trixie shelf path / article range, not from the
# category the row currently sits in -- 546 was filed under Dog with a cat
# article number and a cat shelf.
CAT_ART = re.compile(r"^4\d{4}$")          # Trixie 4xxxx = cat
SPECIES_OVERRIDE = {546: "cat"}            # verified: shelf cat/, sku 42681

# Monge Gift: no text was stored at import, so the line is resolved from the
# brand page (monge.it/en/product/monge-gift-*), quoted in EVIDENCE below.
MONGE_LINE = [
    (re.compile(r"Gift Filled & Crunchy Dental", re.I), "dental",
     "monge.it: 'crunchy layer with sodium tripolyphosphate to support dental "
     "hygiene and a soft peppermint filling for fresh breath'"),
    (re.compile(r"Gift Meat Minis Dental", re.I), "dental",
     "monge.it: 'sodium tripolyphosphate to support oral hygiene ... apple, a "
     "source of minerals for dental health'"),
    (re.compile(r"Gift Filled & Crunchy", re.I), "crunchy",
     "monge.it: 'an external crunchy layer ... and a soft cheese filling'"),
    (re.compile(r"Gift Soft Sticks", re.I), "soft", "monge.it line name: 'Soft Sticks'"),
    (re.compile(r"Gift Meat Minis", re.I), "soft",
     "monge.it: 'with fresh meat, a precious source of highly digestible ... "
     "proteins' (no crunchy or dental claim)"),
    (re.compile(r"Gift Sticks", re.I), "soft",
     "monge.it: fresh-meat sticks, no crunchy or dental claim"),
]

# Rows the brand site no longer carries (discontinued articles, no page text).
# Each takes the bucket of the live sibling article of the same Trixie line.
SIBLING = {
    382: ("soft", "31667 discontinued; same line as 31701 Balls with Chicken "
                  "and Rice (chicken 77 %, rice 15 %, moisture 15.5 %)"),
    398: ("soft", "31803 discontinued; the 300 g pack of line 31747 "
                  "'Sticks with chicken breast & fish' (mirrors 394)"),
}

NATURAL_PART = re.compile(
    r"100 ?% ?(dried )?(buffalo headskin|salmon skin|white ?fish skin|shrimps|"
    r"chicken hearts)|buffalo headskin|rabbit ears \(|rabbit legs with fur|"
    r"whitefish skin \(9\d|100 % (white ?fish|salmon) skin", re.I)
HIDE = re.compile(r"\brawhide\b|\bcollagen\b|buffalo skin|beef skin", re.I)
FREEZE = re.compile(r"freeze[- ]dried", re.I)
LICK = re.compile(r"liquid snack|p[aâ]t[eé]|paste|\bmalt\b", re.I)
DENTAL = re.compile(r"support dental hygiene|dental hygiene|oral hygiene|"
                    r"fresh breath", re.I)
JERKY_FORM = re.compile(r"\b(filets?|stripes?|strips?|coins?|carpaccio|tenders?)\b", re.I)
MOIST = re.compile(r"Moisture content ([\d.]+)", re.I)
BAKED_NAME = re.compile(r"\b(cookies?|biscuits?|farmies|loops|choco drops)\b", re.I)
CEREAL_LED = re.compile(r"Composition:?\s*\|?\s*(cereals|wheat flour|rice flour|flour)", re.I)


def strip(h):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", h or "")).strip()


def species(d):
    if d["id"] in SPECIES_OVERRIDE:
        return SPECIES_OVERRIDE[d["id"]]
    if any(CAT_ART.match(str(v.get("sku") or "")) for v in d["variants"]):
        return "cat"
    if re.search(r"\bcats?\b|\bkitten\b", d["name"], re.I):
        return "cat"
    return "cat" if d["category_ids"] == [14] else "dog"


def classify(d):
    """-> (bucket, evidence). Evidence is a quote from the product's own text."""
    name, v = d["name"], d["variants"][0]
    about, ingr = strip(v.get("about_this_item")), strip(v.get("ingredient_information"))
    text = f"{about} {ingr}"

    for rx, bucket, ev in MONGE_LINE:
        if rx.search(name):
            return bucket, ev
    if d["id"] in SIBLING:
        return SIBLING[d["id"]]

    if re.search(r"matatabi|catnip (ball|heart|mouse)", about, re.I):
        return "catnip", f"about: '{about[:90]}'"
    if re.search(r"seed-substrate|ryegrass|grass", name + " " + about, re.I) \
       and "grass" in name.lower():
        return "grass", f"about: '{about[:90]}'"

    m = FREEZE.search(text)
    if m:
        return "freeze", f"composition: '{m.group(0)}'"
    m = NATURAL_PART.search(ingr)
    if m and not HIDE.search(ingr):
        return "naturals", f"composition: '{m.group(0)}'"
    m = HIDE.search(text)
    if m:
        return "chew", f"composition/bullets: '{m.group(0)}'"
    m = LICK.search(f"{name} {about}")
    if m:
        return "lickable", f"'{m.group(0)}' in name/bullets"
    m = DENTAL.search(text) or (re.search(r"denta ?fun|dentros", name, re.I))
    if m:
        return "dental", f"'{m.group(0)}'"
    mo = MOIST.search(ingr)
    if BAKED_NAME.search(name) and (CEREAL_LED.search(ingr) or not mo):
        return "biscuit", ("cereal/flour-led composition" if CEREAL_LED.search(ingr)
                           else "baked, no moisture declared")
    if JERKY_FORM.search(name):
        return "jerky", f"pack form word '{JERKY_FORM.search(name).group(0)}'"
    if re.search(r"crunch", text, re.I):
        return "crunchy", "crunchy format stated"
    return "soft", (f"moisture {mo.group(1)} %" if mo else "semi-moist meaty morsel")


def api(method, path, payload=None):
    args = [os.path.join(ROOT, "scripts/api.sh"), method, path]
    if payload is not None:
        p = os.path.join(CACHE, "_put.json")
        json.dump(payload, open(p, "w"), ensure_ascii=False)
        args.append(p)
    r = subprocess.run(args, capture_output=True, text=True, cwd=ROOT, timeout=180)
    i = r.stdout.find("{")
    return json.loads(r.stdout[i:]) if i >= 0 else {"_err": r.stderr, "_out": r.stdout}


def main():
    apply = "--apply" in sys.argv
    det = [json.loads(l) for l in open(os.path.join(CACHE, "detail.ndjson"))]
    plan = []
    for d in sorted(det, key=lambda x: x["id"]):
        sp = species(d)
        bucket, ev = classify(d)
        dog_id, cat_id = LEAF[bucket]
        want = cat_id if sp == "cat" else dog_id
        fallback = ""
        if want is None:                      # bucket has no leaf for that species
            want = CAT_FALLBACK[bucket] if sp == "cat" else LEAF["soft"][0]
            fallback = f"(no {bucket} leaf for {sp} -> {NAME[want]})"
        plan.append({"id": d["id"], "name": d["name"], "species": sp,
                     "bucket": bucket, "from": d["category_ids"], "to": want,
                     "evidence": ev, "fallback": fallback})
    json.dump(plan, open(os.path.join(CACHE, "plan.json"), "w"),
              ensure_ascii=False, indent=1)

    for p in plan:
        moved = "" if p["from"] == [p["to"]] else "*"
        print(f"{p['id']:>4} {moved:1} {p['species']:<3} {p['name'][:46]:<48} "
              f"{p['from']} -> {p['to']:>2} {NAME[p['to']]:<30} {p['fallback']}")
    print()
    from collections import Counter
    for (sp, to), n in sorted(Counter((p["species"], p["to"]) for p in plan).items()):
        print(f"  {n:>4}  {sp:<3} {to:>2} {NAME[to]}")
    print(f"\n{sum(1 for p in plan if p['from'] != [p['to']])} of {len(plan)} move")

    if not apply:
        print("(dry run -- pass --apply to write)")
        return
    ok = skip = fail = 0
    for p in plan:
        if p["from"] == [p["to"]]:
            skip += 1; continue
        cur = api("GET", f"/products/{p['id']}").get("data")
        if not cur:
            print(f"  GET failed {p['id']}"); fail += 1; continue
        body = {k: cur[k] for k in KEEP if k in cur}
        body["category_ids"] = [p["to"]]
        res = api("PUT", f"/products/{p['id']}", body).get("data", {})
        if res.get("category_ids") == [p["to"]] and len(res.get("variants", [])) == len(cur["variants"]):
            ok += 1
            print(f"  {p['id']:<4} -> {p['to']:>2} {NAME[p['to']]:<30} "
                  f"({len(res['variants'])} variants kept)")
        else:
            fail += 1
            print(f"  {p['id']:<4} FAILED cats={res.get('category_ids')} "
                  f"variants={len(res.get('variants', []))} was {len(cur['variants'])}")
    print(f"\nmoved={ok} already-correct={skip} failed={fail}")


if __name__ == "__main__":
    main()
