#!/usr/bin/env python3
"""Turn a hand-curated sibling-groups file into a merge plan for
scripts/merge-products.py.

Why a second planner: scripts/plan-product-merge.py groups Trixie
*accessories* from official-page signals and strips a trailing variant label
off the product name. Food, treats and pharmacy rows fail both tests — the
flavour / dose band sits INSIDE the product name ("Barbecue Ribs with Duck",
"Quadro Drops for Dogs 10–25 kg") and the brand gives every flavour its own
page, so the official signal would keep them apart although flavour, pack
weight, texture and dose band are variant axes (reference/data-tables.md §2,
the type skills). Those groups are decided by hand, with evidence, in
runs/<date>/variant-groups.json:

    {"groups": [{"ids": [535, 536], "name": "Barbecue Ribs",
                 "name_ru": "…", "name_hy": "…", "slug": "<optional>",
                 "why": "<evidence>",
                 "variants": {"31466": {"label": "Duck, 2 pcs./110 g",
                                        "axes": {"flavor": "Duck",
                                                 "flavor": "Chicken"}}, …}}]}

Per group this script picks the surviving product (most variants, then the
lowest id), unions the categories, keeps every variant's own sku / prices /
images / texts (merge-products.py reads them live) and adds the attribute
labels in `axes` on top of the attributes the variant already carries. It
refuses a group where two variants would end up with the same attribute
combination — the storefront could not render a selector for them — and lists
every attribute label the closed menu still lacks.

    scripts/plan-variant-merge.py --run runs/<date>          # -> merge-plan.json + merge-plan.md
"""
import argparse, collections, json, os, pathlib, re, sys

ROOT = pathlib.Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SNAP = ROOT / ".siruk-cache" / "catalogue-snapshot.json"
MENU = ROOT / "reference" / "attribute-values.json"

# brand id -> slug prefix (scripts/ids.sh is the truth; this only builds slugs)
BRAND_SLUG = {1: "acana", 2: "belcando", 3: "brit", 4: "canvit", 5: "monge", 6: "orijen",
              7: "royal-canin", 8: "trixie", 9: "farmina", 10: "schesir", 11: "leonardo",
              12: "stuzzy", 13: "bewi-dog", 14: "bewi-cat", 15: "dogland", 16: "ok-lock",
              17: "club-4-paws", 18: "gemon", 19: "simba", 20: "lechat", 21: "special-dog",
              22: "rolf-club", 23: "inspector", 24: "gelmintal", 25: "insectal", 26: "cliny",
              27: "mr-fresh", 28: "comfy", 29: "iv-san-bernard", 30: "beaphar", 31: "8in1",
              32: "mooor", 33: "kormell", 34: "justin", 35: "myau"}


def slugify(s):
    s = s.lower().replace("’", "").replace("'", "").replace("â", "a")
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return re.sub(r"-+", "-", s).strip("-")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True, help="run folder holding variant-groups.json")
    ap.add_argument("--groups", default=None)
    a = ap.parse_args()
    run = pathlib.Path(a.run)
    groups = json.load(open(a.groups or run / "variant-groups.json"))["groups"]
    snap = {int(k): v for k, v in json.load(open(SNAP)).items()}
    menu = json.load(open(MENU))
    taken = {p["slug"]: pid for pid, p in snap.items()}

    plan, problems, missing = [], [], collections.defaultdict(set)
    for g in groups:
        ids = g["ids"]
        absent = [i for i in ids if i not in snap]
        if absent:
            problems.append(f"{g['name']}: products {absent} are not in the snapshot")
            continue
        members = sorted(ids, key=lambda i: (-len(snap[i]["variants"]), i))
        target = members[0]
        cats = sorted({c for i in ids for c in snap[i]["category_ids"]})
        brands = {snap[i]["brand_id"] for i in ids}
        if len(brands) != 1:
            problems.append(f"{g['name']}: brands differ {brands}")
            continue
        fams = [snap[i]["attribute_family_id"] for i in ids if snap[i].get("attribute_family_id")]
        if len(set(fams)) > 1:
            problems.append(f"{g['name']}: attribute families differ {set(fams)}")
            continue

        vs, want = [], dict(g["variants"])
        for i in ids:
            for v in sorted(snap[i]["variants"], key=lambda v: (v.get("sort_order") or 0, v["id"])):
                spec = want.pop(v["sku"], None)
                if spec is None:
                    problems.append(f"{g['name']}: sku {v['sku']} of product {i} has no entry in the groups file")
                    continue
                attrs = dict(v.get("attrs") or {})
                for code, label in spec.get("axes", {}).items():
                    if label not in menu.get(code, {}).get("values", {}):
                        missing[code].add(label)
                    attrs[code] = label
                vs.append({"from_product": i, "old_variant_id": v["id"], "sku": v["sku"],
                           "old_label": v.get("label"), "label": spec["label"],
                           "axes": dict(spec.get("axes", {})), "_attrs": attrs,
                           "sale_mode": v.get("sale_mode"), "price": v.get("price"),
                           "size": (v.get("measure_type"), v.get("content"), v.get("pack_count")),
                           "cost_price": v.get("cost_price")})
        if want:
            problems.append(f"{g['name']}: skus {sorted(want)} in the groups file are not on products {ids}")
        # options + net content tell variants apart (option signature, catalog model 2026-09-29)
        key = lambda v: (tuple(sorted(v["_attrs"].items())), v["size"])
        combos = collections.Counter(key(v) for v in vs)
        for combo, n in combos.items():
            if n > 1:
                dup = [v["sku"] for v in vs if key(v) == combo]
                problems.append(f"{g['name']}: variants {dup} share attribute combination {dict(combo)}")
        for v in vs:
            if not v["_attrs"] and not v["size"][0]:
                problems.append(f"{g['name']}: {v['sku']} would carry no attribute at all")
        axes = sorted({c for v in vs for c in v["axes"]} |
                      {c for c in ("flavor", "pet-weight-range", "size", "color-family")
                       if len({v["_attrs"].get(c) for v in vs}) > 1})

        slug = g.get("slug") or slugify(f"{BRAND_SLUG.get(snap[target]['brand_id'], 'b' + str(snap[target]['brand_id']))} {g['name']}")
        if taken.get(slug) not in (None, target):
            slug = f"{slug}-{target}"
        plan.append({
            "group": sorted(ids), "target": target, "absorb": sorted(set(ids) - {target}),
            "name": g["name"], "name_ru": g.get("name_ru"), "name_hy": g.get("name_hy"),
            "slug": slug, "old_slug": snap[target]["slug"],
            "brand_id": snap[target]["brand_id"], "brand": snap[target].get("brand"),
            "category_ids": cats,
            "attribute_family_id": fams[0] if fams else None,
            "axis": axes, "why_name": g.get("why"),
            "variants": [{k: v[k] for k in ("from_product", "old_variant_id", "sku", "label", "axes")} for v in vs],
            "_review": [{"sku": v["sku"], "from": v["from_product"], "was": v["old_label"],
                         "attrs": v["_attrs"], "price": v["price"], "cost": v["cost_price"]} for v in vs],
        })

    run.mkdir(parents=True, exist_ok=True)
    json.dump({"plan": plan, "missing_values": {k: sorted(v) for k, v in missing.items()},
               "problems": problems},
              open(run / "merge-plan.json", "w"), ensure_ascii=False, indent=1)

    with open(run / "merge-plan.md", "w") as f:
        f.write(f"# Variant merge plan — {len(plan)} products from "
                f"{sum(len(p['group']) for p in plan)} ({sum(len(p['absorb']) for p in plan)} folded away)\n\n")
        for p in plan:
            f.write(f"## {p['name']}  (keep {p['target']}, delete {p['absorb']}) — slug `{p['slug']}`\n")
            f.write(f"categories {p['category_ids']} · family {p['attribute_family_id']} · axis {p['axis']}\n\n")
            f.write(f"_{p['why_name']}_\n\n| sku | from | old label | new label | attributes | price / cost |\n|---|---|---|---|---|---|\n")
            for r in p["_review"]:
                f.write(f"| {r['sku']} | {r['from']} | {r['was']} | "
                        f"{next(v['label'] for v in p['variants'] if v['sku']==r['sku'])} | "
                        f"{', '.join(f'{k}={v}' for k, v in sorted(r['attrs'].items()))} | {r['price']} / {r['cost']} |\n")
            f.write("\n")
        if missing:
            f.write("## Attribute values the menu lacks\n\n")
            for k, v in missing.items():
                f.write(f"- `{k}`: {', '.join(sorted(v))}\n")
        if problems:
            f.write("\n## Problems\n\n" + "\n".join(f"- {x}" for x in problems) + "\n")

    print(f"{len(plan)} merged products, {sum(len(p['absorb']) for p in plan)} folded away", file=sys.stderr)
    for k, v in missing.items():
        print(f"  missing {k}: {sorted(v)}", file=sys.stderr)
    for x in problems:
        print(f"  PROBLEM {x}", file=sys.stderr)
    print(f"wrote {run/'merge-plan.json'} and merge-plan.md", file=sys.stderr)
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
