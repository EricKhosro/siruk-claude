#!/usr/bin/env python3
"""Recover an article code for a register row, which has no code of its own.

The PM's register carries only an Armenian name and our buy price. hafo's
`product_additional_information[]` rows store a `name` that is the same string
the invoice prints and a `wholesale_price` equal to our cost to the dram, so
**name search + cost equality** identifies the row and yields its `sku`
(CLAUDE.md rule 6 still applies: the code is a candidate until a code lookup
confirms it, which `--verify` does).

    scripts/hafo-by-name-cost.py --in state/register/register-match.json \
                                 --out state/register/hafo-recovered.json
"""
import argparse, json, os, re, sys, time, unicodedata, urllib.parse, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
API = ("https://hafo.am/products/filter?page=1&order_by=order-desc"
       "&min_price=0&max_price=200000&animal=&brand=&weight=&age=&type=&is_new=false&search=")
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")


def fetch(q, tries=3):
    url = API + urllib.parse.quote(q)
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA,
                                                       "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=40) as r:
                return json.load(r)
        except Exception as e:
            if i == tries - 1:
                return {"data": [], "_error": str(e)}
            time.sleep(1.5 * (i + 1))


def norm(s):
    s = unicodedata.normalize("NFKC", s or "").lower()
    for ch in "`՝’“”‘’":
        s = s.replace(ch, "")
    s = re.sub(r"[^\w԰-֏]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def queries(name):
    """A few progressively looser search strings for one register name."""
    n = re.sub(r"\s+", " ", (name or "").strip())
    words = [w for w in re.split(r"[\s,/]+", n) if len(w) > 2]
    out = []
    if len(words) >= 4:
        out.append(" ".join(words[:4]))
    if len(words) >= 3:
        out.append(" ".join(words[:3]))
    if len(words) >= 2:
        out.append(" ".join(words[:2]))
    # a latin brand/line token is the most selective thing in an Armenian name
    lat = [w for w in words if re.search(r"[A-Za-z]{3,}", w)]
    if lat:
        out.insert(0, " ".join(lat[:3]))
    seen, uniq = set(), []
    for q in out:
        if q not in seen:
            seen.add(q)
            uniq.append(q)
    return uniq[:4]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--limit", type=int)
    ap.add_argument("--sleep", type=float, default=0.7)
    a = ap.parse_args()

    rows = [r for r in json.load(open(a.inp)) if not r.get("match")]
    if a.limit:
        rows = rows[:a.limit]
    done = json.load(open(a.out)) if os.path.exists(a.out) else {}
    print(f"{len(rows)} uncoded rows, {len(done)} already resolved", file=sys.stderr)

    for n, r in enumerate(rows, 1):
        key = r["reg_no"]
        if key in done:
            continue
        cost = float(r["cost"] or 0)
        want = set(norm(r["name_hy"]).split())
        # Cost equality alone is NOT identity: two flavours of one line often
        # share a price to the dram (00005/00007 on 2026-09-16 both matched the
        # wrong flavour). Collect every cost-equal row and let the name decide.
        cands = []
        for q in queries(r["name_hy"]):
            d = fetch(q)
            for item in (d.get("data") or []):
                for row in (item.get("product_additional_information") or []):
                    if not row.get("sku"):
                        continue
                    try:
                        wp = float(row.get("wholesale_price"))
                    except (TypeError, ValueError):
                        continue
                    if not wp or abs(wp - cost) >= 0.5:
                        continue
                    got = set(norm(row.get("name") or "").split())
                    score = len(want & got) / max(1, len(want | got))
                    cands.append({"sku": row["sku"].replace(" ", ""),
                                  "raw_sku": row["sku"],
                                  "hafo_row_name": row.get("name"),
                                  "hafo_title": item.get("title"),
                                  "hafo_url": f"https://hafo.am/products/{item.get('slug')}",
                                  "price_amd": row.get("price"),
                                  "wholesale_price_amd": wp,
                                  "barcode": row.get("barcode"),
                                  "query": q, "name_score": round(score, 3)})
            time.sleep(a.sleep)
            if any(c["name_score"] >= 0.95 for c in cands):
                break
        cands.sort(key=lambda c: -c["name_score"])
        best = cands[0] if cands else None
        hit = None
        if best and best["name_score"] >= 0.95:
            hit = dict(best, accepted=True)
        elif best:
            hit = dict(best, accepted=False,
                       note="cost matches but the names differ — candidate only (rule 6)")
        done[key] = hit
        if n % 10 == 0 or hit:
            json.dump(done, open(a.out, "w"), ensure_ascii=False, indent=1)
        if n % 25 == 0:
            got = sum(1 for v in done.values() if v)
            print(f"  {n}/{len(rows)} — {got} recovered", file=sys.stderr)
    json.dump(done, open(a.out, "w"), ensure_ascii=False, indent=1)
    got = sum(1 for v in done.values() if v)
    print(f"{len(done)} checked, {got} codes recovered -> {a.out}", file=sys.stderr)


main()
