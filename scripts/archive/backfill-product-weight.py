#!/usr/bin/env python3
"""Put the pack weight on every variant whose pack prints one.

Reverses the 2026-08-12 "skip `product-weight` on `per_kg` variants" rule
(user decision 2026-09-14): the numeric `weight` field prices the bag, the
attribute is what the storefront facets and the pack-size selector read, and
they are not the same job. Symptom that produced the decision: the dog dry-food
sidebar offered exactly one pack size (800 g) because 36 of 37 dry-food
variants carried no attribute at all -- and that one was a hand-fix leak, not a
deliberate exception.

Evidence only -- the weight is READ, never derived (rule 8):

  1. the variant's numeric `weight` field (kg), which is the pack weight the
     `per_kg` pricing already uses;
  2. else the weight/volume printed in the variant label;
  3. else the one printed in the product name.

and these are NOT pack weights, so they are skipped and reported:

  * a dose band -- `1-4 kg`, `up to 4 kg`, `over 16 kg` -- which is the PET's
    weight and belongs on `pet-weight-range` (27);
  * a length -- `75 cm` collar, `23 cm` Matatabi lolly -- and a bowl's
    capacity written as a measurement string (`0.4 l / o 17 cm`), which is
    `size` (28);
  * a bare count -- `10 tablets`, `19455` (an sku used as a label).

Multipack forms follow the pack: `12 pcs./120 g` is a 120 g pack, `2 x 60 g`
is 120 g of bones. Evidence for the second reading: product 527 already
carries 140 g and 200 g on its sibling variants, so the axis is the pack, not
the piece. (A wet-food CASE -- `12X85G`, twelve separately-sized cans -- keeps
the unit-weight rule in the wet-food skill; no row in this batch is one.)

Two guards, both from rule 9a / the product-874 bug: a variant missing the
value drops out of the storefront's pack-size dropdown, so a product ends up
with the attribute on EVERY variant or on none -- a product with even one
unreadable variant is skipped whole and reported. And an existing value is
never overwritten, only filled in where it is absent.

    scripts/backfill-product-weight.py                  # audit, print the plan
    scripts/backfill-product-weight.py --create-values  # add the missing menu values (+ ru/hy)
    scripts/backfill-product-weight.py --apply          # write the attribute onto the variants
    scripts/backfill-product-weight.py --families all   # widen past the edible families

After --create-values run scripts/translate-attributes.py (rule 13), and after
--apply run scripts/refresh-attributes.sh.
"""
import argparse, json, os, re, subprocess, sys, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, ".siruk-cache", "pwfill")
TRANS = os.path.join(ROOT, "reference", "translations-attributes.json")
KEEP = ("name", "slug", "category_ids", "brand_id", "attribute_family_id",
        "is_best_seller", "is_on_sale", "is_discontinued", "variants")
EDIBLE = ("Dry Food", "Wet Food", "Treats", "Supplements")
CODE = "product-weight"

# The menu spells 85 g the old way; never create a second value for it.
ALIAS = {"85 g": "85 gr"}
RU = {"g": "г", "kg": "кг", "ml": "мл", "l": "л"}
HY = {"g": "գ", "kg": "կգ", "ml": "մլ", "l": "լ"}

UNIT = r"(?:kg|gr|g|ml|l)"
# A dose band on antiparasitics: the PET's weight, not the pack's.
DOSE = re.compile(r"(?:up to|under|over|from)\s*\d+(?:[.,]\d+)?\s*kg"
                  r"|\d+(?:[.,]\d+)?\s*[-–—]\s*\d+(?:[.,]\d+)?\s*kg", re.I)
# A dimension: collar length, toy length, bowl diameter.
DIM = re.compile(r"[ø⌀]?\s*\d+(?:[.,]\d+)?\s*(?:cm|mm)\b", re.I)
PACK_OF = re.compile(r"(\d+)\s*(?:pcs\.?|pieces|pc\.?)?\s*/\s*(\d+(?:[.,]\d+)?)\s*(" + UNIT + r")\b", re.I)
TIMES = re.compile(r"(\d+)\s*[x×]\s*(\d+(?:[.,]\d+)?)\s*(" + UNIT + r")\b", re.I)
PLAIN = re.compile(r"(?<![\w.])(\d+(?:,\d{3})*(?:\.\d+)?)\s*(" + UNIT + r")\b", re.I)


def num(s):
    return float(s.replace(",", ""))


def label_for(qty, unit):
    unit = "g" if unit.lower() == "gr" else unit.lower()
    n = round(qty, 3)
    txt = str(int(n)) if n == int(n) else f"{n:g}"
    lab = f"{txt} {unit}"
    return ALIAS.get(lab, lab)


def from_text(text):
    """The weight/volume a pack prints, once dose bands and dimensions are out."""
    cleaned = DIM.sub(" ", DOSE.sub(" ", text))
    m = PACK_OF.search(cleaned)
    if m:
        return label_for(num(m.group(2)), m.group(3)), f"pack of {m.group(1)}, {m.group(2)} {m.group(3)}"
    m = TIMES.search(cleaned)
    if m:
        return label_for(int(m.group(1)) * num(m.group(2)), m.group(3)), f"{m.group(1)} x {m.group(2)} {m.group(3)}"
    m = PLAIN.search(cleaned)
    if m:
        return label_for(num(m.group(1)), m.group(2)), None
    return None, None


def read_weight(v, product_name):
    """-> (label, evidence, warning) or (None, why-not, None)."""
    w = v.get("weight")
    if isinstance(w, (int, float)) and w > 0:
        # The field is in kg, but the MENU and the pack say grams below a kilo
        # (800 g, not 0.8 kg) -- so a bare unit swap here would fork the value.
        lab = label_for(w * 1000, "g") if w < 1 else label_for(w, "kg")
        printed, _ = from_text(v.get("name") or "")
        warn = (f"weight field {w} kg but the label prints {printed}"
                if printed and printed != lab else None)
        return lab, f"variant weight field {w} kg", warn
    for src, text in (("label", v.get("name") or ""), ("product name", product_name or "")):
        lab, how = from_text(text)
        if lab:
            return lab, f"{src} '{text}'" + (f" -> {how}" if how else ""), None
    why = "no weight printed"
    if DOSE.search(v.get("name") or ""):
        why = "dose band (pet weight, -> pet-weight-range 27)"
    elif DIM.search(v.get("name") or ""):
        why = "a dimension, not a pack weight (-> size 28)"
    elif re.search(r"\btablets?\b|\bpcs\b", v.get("name") or "", re.I):
        why = "a count, no weight printed"
    return None, why, None


def api(method, path, payload=None, tag="_put"):
    args = [os.path.join(ROOT, "scripts/api.sh"), method, path]
    if payload is not None:
        p = os.path.join(CACHE, f"{tag}.json")
        json.dump(payload, open(p, "w"), ensure_ascii=False)
        args.append(p)
    r = subprocess.run(args, capture_output=True, text=True, cwd=ROOT, timeout=300)
    i = r.stdout.find("{")
    return json.loads(r.stdout[i:]) if i >= 0 else {"_err": r.stderr[-400:], "_out": r.stdout[:400]}


def fetch(refresh):
    """Every product, in full. Cached -- the catalogue is 700 GETs."""
    os.makedirs(CACHE, exist_ok=True)
    path = os.path.join(CACHE, "detail.ndjson")
    if os.path.exists(path) and not refresh:
        return [json.loads(l) for l in open(path)]
    ids, page, last = [], 1, 1
    while page <= last:
        d = api("GET", f"/products?page={page}")
        ids += [p["id"] for p in d.get("data", [])]
        last = (d.get("meta") or {}).get("last_page", 1)
        page += 1
    out = []
    with open(path, "w") as fh:
        for n, pid in enumerate(ids, 1):
            d = api("GET", f"/products/{pid}").get("data")
            if d:
                out.append(d)
                fh.write(json.dumps(d, ensure_ascii=False) + "\n")
            if n % 50 == 0:
                print(f"  fetched {n}/{len(ids)}", file=sys.stderr)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="write the attribute onto the variants")
    ap.add_argument("--create-values", action="store_true", help="create the menu values the plan needs")
    ap.add_argument("--refresh", action="store_true", help="re-fetch the catalogue instead of using the cache")
    ap.add_argument("--families", default="edible", help="'edible' (default) or 'all'")
    ap.add_argument("--sort-values", action="store_true",
                    help="renumber sort_order so the facet reads in weight order (mass, then volume)")
    a = ap.parse_args()
    os.makedirs(CACHE, exist_ok=True)

    attr = api("GET", "/attributes/1").get("data") or {}
    if attr.get("code") != CODE:
        sys.exit("attribute 1 is not product-weight -- check scripts/ids.sh")
    menu = {v["label"]: v["id"] for v in attr.get("values", [])}
    print(f"menu: {len(menu)} product-weight values, isFilterable={attr.get('isFilterable')}")

    products = fetch(a.refresh)
    want_all = a.families == "all"

    plan, skipped, warnings, untouched = [], [], [], 0
    for p in sorted(products, key=lambda x: x["id"]):
        fam = p.get("attribute_family_name")
        if not want_all and fam not in EDIBLE:
            continue
        rows, blocked = [], []
        for v in p["variants"]:
            avi = v.get("attribute_value_ids")
            avi = avi if isinstance(avi, dict) else {}
            if avi.get(CODE):
                untouched += 1
                continue
            lab, why, warn = read_weight(v, p["name"])
            row = {"sku": v["sku"], "variant": v["name"], "label": lab, "why": why}
            if warn:
                row["warn"] = warn
                warnings.append({"id": p["id"], "name": p["name"], **row})
            (rows if lab else blocked).append(row)
        if not rows and not blocked:
            continue
        if blocked:
            # All-or-none per product: a half-filled axis hides variants.
            skipped.append({"id": p["id"], "name": p["name"], "family": fam,
                            "would_fill": rows, "blocked": blocked})
            continue
        plan.append({"id": p["id"], "name": p["name"], "family": fam, "fill": rows})

    need = sorted({r["label"] for pr in plan for r in pr["fill"]} - set(menu))
    json.dump({"plan": plan, "skipped": skipped, "warnings": warnings, "new_values": need},
              open(os.path.join(CACHE, "plan.json"), "w"), ensure_ascii=False, indent=1)

    for pr in plan:
        print(f"{pr['id']:>4} {pr['name'][:44]:<46} [{pr['family'] or '-'}]")
        for r in pr["fill"]:
            print(f"       {r['sku']:<12} {r['label']:<10} <- {r['why']}"
                  + (f"   !! {r['warn']}" if r.get("warn") else ""))
    nfill = sum(len(pr["fill"]) for pr in plan)
    print(f"\n{nfill} variants in {len(plan)} products would gain {CODE}; "
          f"{untouched} already have it")
    print("by family:", dict(collections.Counter(
        pr["family"] for pr in plan for _ in pr["fill"])))

    if skipped:
        print(f"\n{len(skipped)} products SKIPPED whole (a variant prints no pack weight -- "
              "filling the rest would hide it from the pack-size dropdown):")
        for s in skipped:
            print(f"  {s['id']:>4} {s['name'][:42]:<44} [{s['family'] or '-'}]")
            for b in s["blocked"]:
                print(f"        - {b['sku']:<12} {b['variant'][:34]:<36} {b['why']}")
            for r in s["would_fill"]:
                print(f"        . {r['sku']:<12} {r['variant'][:34]:<36} would be {r['label']}")
    if warnings:
        print(f"\n{len(warnings)} variants where the weight field and the printed label DISAGREE "
              "-- check which one the pack says before trusting either:")
        for w in warnings:
            print(f"  {w['id']:>4} {w['name'][:38]:<40} {w['sku']:<12} {w['warn']}")
    if need:
        print(f"\n{len(need)} menu values missing: {need}")
    grams_over_kilo = sorted(
        (float(l.rsplit(" ", 1)[0].replace(",", "")), l)
        for l in set(menu) | set(need)
        if l.endswith((" g", " gr")) and float(l.rsplit(" ", 1)[0].replace(",", "")) >= 1000)
    if grams_over_kilo:
        print("\nheads-up -- each pack is taken as printed, so above a kilo the menu mixes units: "
              + ", ".join(l for _, l in grams_over_kilo)
              + " sit next to the kg values. Normalising them is a separate call -- say the word.")

    if a.create_values:
        if not need:
            print("\nno values to create")
        tr = json.load(open(TRANS))
        for lab in need:
            r = api("POST", "/attribute-values",
                    {"attribute_id": attr["id"], "value": lab.replace(" ", "-").replace(".", "-"),
                     "label": lab}, tag="_val")
            vid = (r.get("data") or {}).get("id")
            if not vid:
                print(f"  ! {lab} FAILED {str(r)[:160]}")
                continue
            menu[lab] = vid
            print(f"  + {lab} -> {vid}")
            n, u = lab.rsplit(" ", 1)
            tr["values"][CODE][lab] = [f"{n} {RU[u]}", f"{n} {HY[u]}"]
        json.dump(tr, open(TRANS, "w"), ensure_ascii=False, indent=1)
        print(f"  wrote ru/hy into {os.path.relpath(TRANS, ROOT)} -- "
              "run scripts/translate-attributes.py")

    if a.sort_values:
        # attribute-redesign.md: "value lists sorted logically (... product-weight
        # by weight), not alphabetically -- sort_order supports this". New values
        # are appended by the API, so the facet ends up in creation order.
        MASS = {"g": 1, "gr": 1, "kg": 1000}
        VOL = {"ml": 1, "l": 1000}
        ranked = []
        for v in attr.get("values", []):
            try:
                n, u = v["label"].rsplit(" ", 1)
                q = float(n.replace(",", ""))
            except ValueError:
                print(f"  ? {v['label']}: not '<number> <unit>', left where it is"); continue
            if u in MASS:
                ranked.append((0, q * MASS[u], v))
            elif u in VOL:
                ranked.append((1, q * VOL[u], v))
            else:
                print(f"  ? {v['label']}: unit '{u}' is neither mass nor volume, left where it is")
        ranked.sort(key=lambda r: (r[0], r[1]))
        moved = 0
        for i, (_, _, v) in enumerate(ranked):
            if v.get("sort_order") == i:
                continue
            # sort_order is single-language (admin-api.md), so one write is enough;
            # the en label is resent unchanged so the locale rows are not disturbed.
            r = api("PUT", f"/attribute-values/{v['id']}",
                    {"locale": "en", "attribute_id": attr["id"], "value": v["value"],
                     "label": v["label"], "sort_order": i}, tag="_sort")
            if (r.get("data") or {}).get("id"):
                moved += 1
            else:
                print(f"  ! {v['label']} sort failed {str(r)[:120]}")
        print(f"\nsorted {len(ranked)} values by weight ({moved} moved): "
              + ", ".join(v["label"] for _, _, v in ranked))

    if not a.apply:
        print("\n(audit only -- pass --apply to write)")
        return

    missing = sorted({r["label"] for pr in plan for r in pr["fill"]} - set(menu))
    if missing:
        sys.exit(f"refusing to write: menu still lacks {missing} -- run --create-values first")

    ok = fail = 0
    for pr in plan:
        cur = api("GET", f"/products/{pr['id']}").get("data")
        if not cur:
            print(f"  GET failed {pr['id']}"); fail += 1; continue
        want = {r["sku"]: menu[r["label"]] for r in pr["fill"]}
        body = {k: cur[k] for k in KEEP if k in cur}
        for v in body["variants"]:
            avi = v.get("attribute_value_ids")
            v["attribute_value_ids"] = avi = avi if isinstance(avi, dict) else {}
            if v["sku"] in want and not avi.get(CODE):
                avi[CODE] = want[v["sku"]]
        have = [bool((v.get("attribute_value_ids") or {}).get(CODE)) for v in body["variants"]]
        if not all(have):
            print(f"  REFUSING {pr['id']}: would leave a variant without {CODE}"); fail += 1; continue
        res = api("PUT", f"/products/{pr['id']}", body).get("data", {})
        rv = res.get("variants", [])
        good = (len(rv) == len(cur["variants"])
                and all((v.get("attribute_value_ids") or {}).get(CODE) for v in rv))
        if good:
            ok += 1
            print(f"  {pr['id']:<4} {pr['name'][:38]:<40} {len(rv)} variants, all carry {CODE}")
        else:
            fail += 1
            print(f"  {pr['id']:<4} FAILED variants={len(rv)} was {len(cur['variants'])} "
                  f"{[(v.get('sku'), (v.get('attribute_value_ids') or {}).get(CODE)) for v in rv]}")
    print(f"\nupdated={ok} failed={fail}")


if __name__ == "__main__":
    main()
