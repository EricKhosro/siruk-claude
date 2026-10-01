#!/usr/bin/env python3
"""Make every live variant's sale price equal the register's `Վաճառքի գին`.

The PM's register (csv/Product.numbers, re-sent 2026-09-16 with a sale price on
every row) is the source of truth for the sale price (user rule 2026-09-16:
"the price of the products SHOULD match this column"). This reads the audit
that scripts/register-audit.py wrote and, for every row whose live price
differs, writes the register price through scripts/set-variant.sh.

What it refuses, and lists instead of writing (CLAUDE.md rule 5 — a sale
price must beat cost):
  * a register price at or below the row's own cost (69 rows on 2026-09-16
    carry the cost in the sale column);
  * two register rows for one variant that disagree on the price;
  * a register price that looks like a typo: at least --max-ratio-cost (2.5)
    times the cost AND at least --max-ratio-ours (2.0) times what we charge
    today (2026-09-16: a 150 g paté at 9,600 next to 1,000 siblings). Those
    are written as SUSPECT for the PM to confirm, never applied blind.

Every live variant is sale_mode "pack" since the 2026-09-29 catalog model and
`price` is always the pack price, so the register price is written straight to
`price` (the old per_kg / price_per_kg branch is gone). set-variant.sh rebuilds
the body through scripts/siruk_payload.py and refuses a failing check.

    scripts/register-price-sync.py --run state/register            # dry run, writes price-sync.csv
    scripts/register-price-sync.py --run state/register --apply
"""
import argparse, collections, csv, json, os, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SNAP = os.path.join(ROOT, ".siruk-cache/catalogue-snapshot.json")


def num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def set_variant(pid, sku, patch):
    r = subprocess.run([os.path.join(ROOT, "scripts/set-variant.sh"), str(pid), str(sku), json.dumps(patch)],
                       capture_output=True, text=True, cwd=ROOT, timeout=300)
    return r.returncode == 0, (r.stderr or r.stdout)[-300:]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--tolerance", type=float, default=1.0)
    ap.add_argument("--max-ratio-cost", type=float, default=2.5)
    ap.add_argument("--max-ratio-ours", type=float, default=2.0)
    a = ap.parse_args()

    audit = json.load(open(os.path.join(a.run, "register-audit.json")))
    # the register code may carry a brand suffix (31846Tx) that the live SKU
    # does not (31846) — set-variant.sh needs the live SKU
    live_sku = {v["id"]: v["sku"] for p in json.load(open(SNAP)).values() for v in p["variants"]}
    by_variant = collections.defaultdict(list)
    for r in audit:
        if r.get("exists") and r.get("price_verdict") == "MISMATCH":
            by_variant[r["variant_id"]].append(r)

    rows, todo = [], []
    for vid, rs in by_variant.items():
        r = rs[0]
        prices = {num(x["reg_sale"]) for x in rs}
        cost = num(r["cost"]) or 0
        rec = {"reg_no": "; ".join(x["reg_no"] for x in rs), "code": r["code"], "sku": live_sku.get(vid, r["code"]), "product_id": r["product_id"],
               "product": r["product"], "variant_id": vid, "variant": r["variant"],
               "cost": cost, "our_price": r["our_pack_price"],
               "register_price": r["reg_sale"], "action": "", "note": ""}
        if len(prices) > 1:
            rec["action"] = "SKIP"; rec["note"] = f"register rows disagree: {sorted(prices)}"
        elif num(r["reg_sale"]) <= cost:
            rec["action"] = "SKIP"; rec["note"] = "register price at or below cost (rule 5) — needs the PM's eye"
        elif (cost and num(r["reg_sale"]) >= a.max_ratio_cost * cost
              and num(r["our_pack_price"]) and num(r["reg_sale"]) >= a.max_ratio_ours * num(r["our_pack_price"])):
            rec["action"] = "SKIP"; rec["note"] = (f"SUSPECT: {r['reg_sale']} is {num(r['reg_sale'])/cost:.1f}x cost and "
                                                   f"{num(r['reg_sale'])/num(r['our_pack_price']):.1f}x our price — confirm before applying")
        else:
            reg = num(r["reg_sale"])
            todo_patch = {"price": int(reg) if reg == int(reg) else reg}
            rec["action"] = "WRITE"; rec["patch"] = json.dumps(todo_patch)
            todo.append((rec, todo_patch))
        rows.append(rec)

    out = os.path.join(a.run, "price-sync.csv")
    print(f"{len(rows)} mismatched variants: {sum(1 for r in rows if r['action']=='WRITE')} to write, "
          f"{sum(1 for r in rows if r['action']=='SKIP')} skipped", file=sys.stderr)
    if a.apply:
        ok = bad = 0
        for rec, patch in todo:
            good, msg = set_variant(rec["product_id"], rec["sku"], patch)
            rec["action"] = "WRITTEN" if good else "FAILED"
            rec["note"] = "" if good else msg.replace("\n", " ")
            ok += good; bad += not good
            print(f"  {'ok ' if good else 'BAD'} {rec['product_id']}/{rec['code']}: {rec['our_price']} -> {rec['register_price']}"
                  + ("" if good else f"  {msg[-120:]}"), file=sys.stderr)
        print(f"written {ok}, failed {bad}", file=sys.stderr)

    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["reg_no", "code", "sku", "product_id", "product", "variant_id", "variant",
                                          "cost", "our_price", "register_price", "action", "note", "patch"])
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in w.fieldnames})
    print(f"wrote {out}", file=sys.stderr)


if __name__ == "__main__":
    main()
