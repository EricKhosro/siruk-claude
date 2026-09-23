#!/usr/bin/env python3
"""Match the PM's register rows to the invoice CSV, which is where the article
codes live.

The register carries only an Armenian name, a quantity and prices; the CSV
carries the article code. The two name strings come from the same source but
the register's have been retyped, so matching is exact-first, then fuzzy on a
normalised form, then a cost cross-check to keep a fuzzy hit honest: a pair
whose buy prices differ is not the same row, however alike the names look.

    scripts/match-register.py [--reg state/register/register.csv] [--out state/register/register-match.json]
"""
import argparse, collections, csv, difflib, json, os, re, sys, unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REG = os.path.join(ROOT, "state/register/register.csv")
INV = os.path.join(ROOT, "csv/ALL_SIRUK_PRODUCTS.csv")


def num(x):
    try:
        return float(str(x).replace(",", "").strip() or 0)
    except ValueError:
        return 0.0


def norm(s):
    s = unicodedata.normalize("NFKC", s or "").lower()
    for ch in "`՝’“”‘’":
        s = s.replace(ch, "")
    s = re.sub(r"[^\w԰-֏]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(ROOT, "state/register/register-match.json"))
    ap.add_argument("--cutoff", type=float, default=0.86)
    ap.add_argument("--reg", default=REG, help="register CSV from scripts/read-register.py --csv")
    a = ap.parse_args()

    reg = list(csv.DictReader(open(a.reg)))
    inv = list(csv.DictReader(open(INV)))
    by_name = collections.defaultdict(list)
    for x in inv:
        by_name[norm(x["Product Name (as printed)"])].append(x)
    keys = list(by_name)

    out = []
    for r in reg:
        k = norm(r["name_hy"])
        cost = num(r["cost"])
        rec = {"reg_no": r["reg_no"], "name_hy": r["name_hy"], "qty": r["qty"],
               "cost": cost, "sale_price": num(r["sale_price"]), "kg": r["kg"],
               "match": None, "how": None, "score": None}
        cands = by_name.get(k)
        if cands:
            # same name; if several, the one whose buy price agrees
            pick = next((c for c in cands if num(c["Buy Price (AMD)"]) == cost), None)
            if pick:
                rec.update(match=pick["Article Code"], how="exact-name", score=1.0, cost_agrees=True)
            else:
                # the same name at another cost is NOT a match: the invoice CSV has
                # a block (Trixie 427xx cat treats) whose names are out of step with
                # their codes+costs, and trusting the name there put register
                # prices on sibling variants (found 2026-09-23). Hand-decide it.
                rec.update(match=None, how="exact-name, cost differs", score=1.0,
                           near=cands[0]["Article Code"], near_cost=num(cands[0]["Buy Price (AMD)"]))
        else:
            near = difflib.get_close_matches(k, keys, n=3, cutoff=a.cutoff)
            best = None
            for nk in near:
                for c in by_name[nk]:
                    if num(c["Buy Price (AMD)"]) == cost:
                        best = (c, difflib.SequenceMatcher(None, k, nk).ratio())
                        break
                if best:
                    break
            if best:
                rec.update(match=best[0]["Article Code"], how="fuzzy-name+cost",
                           score=round(best[1], 3), cost_agrees=True)
            elif near:
                c = by_name[near[0]][0]
                rec.update(match=None, how="fuzzy-name, cost differs",
                           score=round(difflib.SequenceMatcher(None, k, near[0]).ratio(), 3),
                           near=c["Article Code"], near_cost=num(c["Buy Price (AMD)"]))
        out.append(rec)

    json.dump(out, open(a.out, "w"), ensure_ascii=False, indent=1)
    c = collections.Counter(r["how"] or "no match" for r in out)
    for k2, v in c.most_common():
        print(f"{v:5} {k2}", file=sys.stderr)
    print(f"-> {a.out}", file=sys.stderr)


main()
