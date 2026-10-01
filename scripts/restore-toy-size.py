#!/usr/bin/env python3
"""Put `toy-size` back on every toy variant, derived from the variant label.

The attribute was deleted 2026-09-10 and recreated (hidden from filters) the
same day. Every toy variant's label carries its size ("22 cm", "Red 15 cm"),
so the value is recoverable without guessing. One PUT per product, body rebuilt
from a fresh GET through scripts/siruk_payload.py (PUT replaces the whole
variants array; catalog model 2026-09-29: attribute_values keyed by attribute
id, checked against the product type before the write); variants that already
carry toy-size or whose label has no "<n> cm" are left alone and reported.
toy-size is a dimension of the toy, an attribute — not the pack size
(measure_type/content), which this script does not touch.

    scripts/restore-toy-size.py [--dry-run] [--only id,id]
"""
import argparse, json, os, re, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, ".siruk-cache")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from siruk_payload import attributes, check_variants, product_body, product_type, to_variant_payload  # noqa: E402


def api(method, path, payload=None):
    args = [os.path.join(ROOT, "scripts/api.sh"), method, path]
    if payload is not None:
        p = os.path.join(CACHE, "_rts.json")
        json.dump(payload, open(p, "w"), ensure_ascii=False)
        args.append(p)
    r = subprocess.run(args, capture_output=True, text=True, cwd=ROOT, timeout=180)
    i = r.stdout.find("{")
    return json.loads(r.stdout[i:]) if i >= 0 else {"_err": r.stderr}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--only", default="")
    a = ap.parse_args()
    menu = json.load(open(os.path.join(ROOT, "reference/attribute-values.json")))
    sizes = menu["toy-size"]["values"]                      # label -> id
    bynum = {re.sub(r"\s*cm$", "", k): v for k, v in sizes.items()}
    live = attributes().get("toy-size")
    if not live:
        raise SystemExit("attribute toy-size does not exist on the live site")
    tsid = str(live["id"])
    bynum = {k: v for k, v in bynum.items() if v in live["values"]}   # stale menu ids never written

    ids = []
    page = 1
    while True:
        d = api("GET", f"/products?page={page}")
        ids += [p["id"] for p in d.get("data", [])]
        if page >= (d.get("meta") or {}).get("last_page", 1):
            break
        page += 1
    if a.only:
        ids = [int(x) for x in a.only.split(",")]

    done, skipped, nosize = 0, [], []
    for pid in sorted(set(ids)):
        p = api("GET", f"/products/{pid}").get("data") or {}
        if p.get("attribute_family_id") != 5:
            continue
        ptype = product_type(5)
        if not any(str(x["id"]) == tsid for x in ptype.get("attributes") or []):
            raise SystemExit("toy-size is not part of the Toys product type — add it there first")
        # built without put_body's up-front check: a missing toy-size is exactly what
        # makes two sizes indistinguishable, so the check runs after the fill
        allowed = {x["id"] for x in ptype.get("attributes") or []}
        body = product_body(p)
        body["variants"] = variants = [to_variant_payload(v, allowed) for v in p["variants"]]
        changed = False
        for nv in variants:
            avi = nv["attribute_values"]
            if not avi.get(tsid):
                m = re.search(r"(\d+(?:[.,]\d+)?)\s*cm\b", nv.get("name") or "")
                num = m.group(1).replace(",", ".") if m else None
                if num and num in bynum:
                    avi[tsid] = [bynum[num]]; changed = True
                else:
                    nosize.append((pid, nv.get("id"), nv.get("name")))
        if not changed:
            continue
        errs, _ = check_variants(variants, ptype)
        if errs:
            skipped.append((pid, "refused before writing: " + "; ".join(errs))); continue
        if len(variants) != len(p["variants"]) or {x["id"] for x in variants} != {x["id"] for x in p["variants"]}:
            skipped.append((pid, "variant set mismatch — refusing to PUT")); continue
        if a.dry_run:
            print(f"would PUT {pid} {p['name']}: {[ (x['name'], x['attribute_values'].get(tsid)) for x in variants]}")
            done += 1; continue
        r = api("PUT", f"/products/{pid}", body)
        back = api("GET", f"/products/{pid}").get("data") or {}
        ok = all((x.get("attribute_values") or {}).get(tsid) for x in back.get("variants", [])
                 if re.search(r"\d\s*cm\b", x.get("name") or ""))
        print(f"{'ok ' if ok else '!! '} {pid} {p['name']} ({len(variants)} variants)")
        if not ok:
            skipped.append((pid, "verify failed: " + str(r)[:200]))
        done += 1
    print(f"\nproducts updated: {done}")
    if nosize:
        print("variants with no '<n> cm' in the label (left without toy-size):")
        for t in nosize: print("  ", t)
    if skipped:
        print("skipped:")
        for t in skipped: print("  ", t)


if __name__ == "__main__":
    main()
