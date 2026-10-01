#!/usr/bin/env python3
"""Fold each duplicate group from the merge plan into ONE product.

    scripts/plan-product-merge.py            # writes runs/<date>/merge-plan.json
    scripts/merge-products.py --dry-run
    scripts/merge-products.py                # writes to the API

Per group, in this order — the order matters:

  1. GET every product in the group fresh and save it under
     runs/<date>/merge-backup/, so a half-finished group can be rebuilt.
  2. Build the target's new body and check it in full BEFORE anything is
     deleted: every sku present, every variant priced above cost, exactly one
     default, and scripts/siruk_payload.py's check_variants against the
     target's product type (options valid for the type, one value per option,
     no two variants with the same options + size).
  3. DELETE the absorbed products.  This must happen before the PUT: SKUs are
     unique catalogue-wide, so the target cannot claim a sku that another
     product still holds (422 "SKU already in use").
  4. PUT the target, read it back, and record old variant id -> new variant id.
  5. Write the ru and hy product names and the per-sku translated texts.

The target keeps its own id and its own variants keep their variant ids, so
its /dp/<id> links survive; the absorbed products' variants are re-created and
get new ids, which is what runs/<date>/variant-id-map.csv is for.

Catalog model 2026-09-29: every variant goes through siruk_payload's
to_variant_payload (the target's product type decides which attributes are
kept); axis attributes are written as attribute_values keyed by attribute id.
`price` is the pack price for every variant (no per_kg branch). A plan axis on
`product-weight` is skipped — pack size is measure_type/content on the variant,
carried over as it is. Stock is a ledger: an absorbed variant is re-created
with `initial_stock` = the available quantity it had before the DELETE.

Resumable: --state remembers the groups that finished.
"""
import argparse, csv, datetime, json, os, pathlib, re, subprocess, sys, time

ROOT = pathlib.Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CACHE = ROOT / ".siruk-cache"

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from siruk_payload import (VTEXT, attributes, check_variants, product_body,  # noqa: E402
                           product_type, to_variant_payload)


class NotFound(Exception):
    pass


def api(method, path, payload=None, lang=None):
    args = [str(ROOT / "scripts/api.sh"), method, path]
    env = dict(os.environ)
    if lang:
        env["SIRUK_LANG"] = lang
    if payload is not None:
        p = CACHE / "_merge.json"
        json.dump(payload, open(p, "w"), ensure_ascii=False)
        args.append(str(p))
    r = subprocess.run(args, capture_output=True, text=True, cwd=ROOT, timeout=300, env=env)
    i = r.stdout.find("{")
    if i < 0:
        # api.sh prints "HTTP <code> <METHOD> <path>" on stderr and the body on
        # stdout, so a 204 (what DELETE returns) leaves stdout empty.
        if r.returncode == 0 and re.search(r"HTTP 2\d\d", r.stderr):
            return {}
        if re.search(r"HTTP 404", r.stderr):
            raise NotFound(path)
        raise RuntimeError(f"{method} {path}: {r.stdout.strip()[-200:]} {r.stderr.strip()[-200:]}")
    return json.loads(r.stdout[i:])


def build(p, attrs, live):
    """The PUT body for the surviving product, from the live records."""
    def vid(code, label):
        try:
            return attrs[code]["values"][label]
        except KeyError:
            raise SystemExit(f"attribute value missing: {code} = {label!r} — "
                             f"run scripts/sync-attributes.py first")

    ptype = product_type(p["attribute_family_id"])
    allowed = {a["id"] for a in ptype.get("attributes") or []}
    amap = attributes()
    variants, order, new_skus = [], 0, set()
    for pv in p["variants"]:
        src = live[pv["from_product"]]
        v = next(x for x in src["variants"] if x["sku"] == pv["sku"])
        out = to_variant_payload(v, allowed)
        out["name"] = pv["label"]
        out["sort_order"] = order
        out["is_default"] = (order == 0)
        av = dict(out.get("attribute_values") or {})
        for code, label in pv["axes"].items():
            if code == "product-weight":
                continue          # retired: the size is measure_type/content, carried over above
            if code not in amap:
                raise SystemExit(f"attribute '{code}' does not exist any more — re-plan the merge")
            av[str(amap[code]["id"])] = [vid(code, label)]
        out["attribute_values"] = av
        # the target's own variants keep their ids; the absorbed ones are new
        if pv["from_product"] != p["target"]:
            out.pop("id", None)
            out["initial_stock"] = int(v.get("available_quantity") or 0)
            new_skus.add(out["sku"])
        order += 1
        variants.append(out)

    body = product_body(live[p["target"]])
    body.update({"name": p["name"], "slug": p["slug"], "category_ids": p["category_ids"],
                 "brand_id": p["brand_id"], "attribute_family_id": p["attribute_family_id"],
                 "is_best_seller": False, "is_on_sale": False,
                 "is_discontinued": bool(live[p["target"]].get("is_discontinued")),
                 "variants": variants})
    check(p, body, ptype, new_skus)
    return body


def check(p, body, ptype, new_skus=()):
    v = body["variants"]
    want = [x["sku"] for x in p["variants"]]
    got = [x["sku"] for x in v]
    assert got == want, f"{p['name']}: sku list changed {got} != {want}"
    assert len(set(got)) == len(got), f"{p['name']}: duplicate sku"
    assert sum(1 for x in v if x["is_default"]) == 1, f"{p['name']}: not exactly one default"
    for x in v:
        # price is the pack price for every variant (catalog model 2026-09-29)
        assert (x.get("price") or 0) > 0, f"{p['name']} {x['sku']}: no price"
        if x.get("cost_price"):
            assert x["price"] > x["cost_price"], \
                f"{p['name']} {x['sku']}: price {x['price']} does not beat cost {x['cost_price']}"
    errs, warns = check_variants(v, ptype, set(new_skus))
    for w in warns:
        print(f"  ⚠ {p['name']}: {w}", file=sys.stderr)
    assert not errs, f"{p['name']}: " + "; ".join(errs)


def translate(pid, lang, name, texts, en):
    """PUT the product in `lang`. Single-language fields come from the en body."""
    body = product_body(en)
    body.update({"locale": lang, "name": name, "variants": []})
    allowed = {a["id"] for a in product_type(en["attribute_family_id"]).get("attributes") or []}
    for v in en["variants"]:
        out = to_variant_payload(v, allowed)
        for k in VTEXT:
            out.pop(k, None)
        out.update(texts.get(v["sku"], {}))
        body["variants"].append(out)
    api("PUT", f"/products/{pid}", body, lang=lang)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", default=None)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--only", default="", help="comma-separated target ids")
    ap.add_argument("--run", default=None, help="run folder for the plan, backups and state (default runs/<today>)")
    a = ap.parse_args()

    day = datetime.date.today().isoformat()
    run = pathlib.Path(a.run) if a.run else ROOT / "runs" / day
    plan = json.load(open(a.plan or run / "merge-plan.json"))["plan"]
    attrs = json.load(open(ROOT / "reference/attribute-values.json"))
    only = {int(x) for x in a.only.split(",") if x.strip()}
    backup = run / "merge-backup"; backup.mkdir(parents=True, exist_ok=True)
    state_f = run / "merge-state.json"
    state = json.load(open(state_f)) if state_f.exists() else {"done": [], "idmap": []}

    for p in plan:
        if only and p["target"] not in only: continue
        if p["target"] in state["done"]:
            continue
        ids = p["group"]
        def read(i, lang=None):
            """Live record, or the backup if a previous run already deleted it."""
            f = backup / (f"{i}.json" if lang is None else f"{i}.{lang}.json")
            try:
                d = api("GET", f"/products/{i}", lang=lang)["data"]
                f.write_text(json.dumps(d, ensure_ascii=False, indent=1))
                return d
            except NotFound:
                if not f.exists():
                    raise
                print(f"  product {i} already deleted — using the backup", file=sys.stderr)
                return json.load(open(f))

        live = {i: read(i) for i in ids}
        tr = {}
        for lang in ("ru", "hy"):
            tr[lang] = {}
            for i in ids:
                d = read(i, lang)
                for v in d["variants"]:
                    tr[lang][v["sku"]] = {k: v.get(k) for k in
                                          ("about_this_item", "ingredient_information",
                                           "feeding_instructions") if v.get(k)}

        body = build(p, attrs, live)
        print(f"{p['name']}: {len(ids)} products → 1, {len(body['variants'])} variants "
              f"(target {p['target']}, delete {p['absorb']})", file=sys.stderr)
        if a.dry_run:
            continue

        for i in p["absorb"]:
            try:
                api("DELETE", f"/products/{i}")
            except NotFound:
                pass          # a previous run already removed it
        after = api("PUT", f"/products/{p['target']}", body)
        got = api("GET", f"/products/{p['target']}")["data"]
        assert len(got["variants"]) == len(body["variants"]), \
            f"{p['name']}: read back {len(got['variants'])} variants, expected {len(body['variants'])}"
        newid = {v["sku"]: v["id"] for v in got["variants"]}
        for pv in p["variants"]:
            state["idmap"].append({"sku": pv["sku"], "old_product": pv["from_product"],
                                   "old_variant": pv["old_variant_id"],
                                   "new_product": p["target"], "new_variant": newid[pv["sku"]],
                                   "old_slug": None, "new_slug": got["slug"]})

        for lang, nm in (("ru", p["name_ru"]), ("hy", p["name_hy"])):
            if nm:
                translate(p["target"], lang, nm, tr[lang], got)

        state["done"].append(p["target"])
        json.dump(state, open(state_f, "w"), ensure_ascii=False, indent=1)

    if not a.dry_run:
        with open(run / "variant-id-map.csv", "w", newline="") as f:
            w = csv.DictWriter(f, ["sku", "old_product", "old_variant", "new_product",
                                   "new_variant", "old_slug", "new_slug"])
            w.writeheader(); w.writerows(state["idmap"])
        print(f"wrote {run/'variant-id-map.csv'} ({len(state['idmap'])} variants)", file=sys.stderr)


if __name__ == "__main__":
    main()
