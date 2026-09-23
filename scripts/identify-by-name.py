#!/usr/bin/env python3
"""Identify a CODELESS register row by name (CLAUDE.md rule 6, 2026-09-17).

For every register row without an article code, search hafo by its Armenian
name (no cost-equality gate — that is what `hafo-by-name-cost.py` adds) and
list EVERY `product_additional_information[]` row of every hit, with sku,
name, price, wholesale price and barcode, so a person can decide whether one
of them is the exact product (brand + line + flavour + pack — and size/colour
for accessories — all matching). Nothing is accepted automatically: the
decision goes into `state/register/identified-by-name.csv` and the code into
`state/register/match-overrides.json` (see --accept).

    scripts/identify-by-name.py --status state/register/register-status.json \
        --out state/register/hafo-name-candidates.json [--only 00011,00013]
    scripts/identify-by-name.py --accept state/register/identified-by-name.csv \
        --overrides state/register/match-overrides.json
"""
import argparse, csv, json, os, re, subprocess, sys, time, unicodedata, urllib.parse, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
API = ("https://hafo.am/products/filter?page=1&order_by=order-desc"
       "&min_price=0&max_price=200000&animal=&brand=&weight=&age=&type=&is_new=false&search=")
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")


def fetch(q, tries=3):
    url = API + urllib.parse.quote(q)
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
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


STOP = {"կեր", "շների", "կատուների", "համար", "կատ", "շն", "չոր", "հյուրասիրություն", "ձագերի",
        "փոքր", "ցեղատեսակի", "վզնոց", "խաղալիք", "կերային", "հավելում"}


def queries(name):
    n = re.sub(r"\s+", " ", (name or "").strip())
    # a trailing "/12345" vendor code is the most selective token there is
    out = []
    m = re.search(r"/\s*([A-Za-z0-9-]{4,})\s*$", n)
    if m:
        out.append(m.group(1))
    words = [w for w in re.split(r"[\s,/()]+", n) if len(w) > 2]
    lat = [w for w in words if re.search(r"[A-Za-z]{3,}", w)]
    if lat:
        out.append(" ".join(lat[:3]))
        if len(lat) > 1:
            out.append(lat[0])
    sel = [w for w in words if norm(w) not in STOP and not re.search(r"[A-Za-z]", w)]
    if len(sel) >= 3:
        out.append(" ".join(sel[:3]))
    if len(sel) >= 2:
        out.append(" ".join(sel[:2]))
    if sel:
        out.append(sel[0])
    seen, uniq = set(), []
    for q in out:
        q = q.strip()
        if q and q not in seen:
            seen.add(q)
            uniq.append(q)
    return uniq[:5]


SHOP_SCORE = 0.5


def shop_search(script, q, limit=5):
    """Candidates from nemo-lookup.py / zoovet-lookup.py --search, tagged with
    the shop. A failed fetch is an empty list, never a crash mid-run."""
    try:
        r = subprocess.run([sys.executable, os.path.join(ROOT, "scripts", script),
                            "--search", q, "--limit", str(limit)],
                           capture_output=True, text=True, timeout=120)
        return json.loads(r.stdout).get("candidates") or []
    except Exception:
        return []


def shop_candidates(name_hy, want):
    out, seen = [], set()
    qs = queries(name_hy)
    lat = [q for q in qs if re.search(r"[A-Za-z]{3,}", q)]
    for shop, script, qlist in (("nemo.am", "nemo-lookup.py", qs[:3]),
                                ("zoovet.am", "zoovet-lookup.py", lat[:2])):
        for q in qlist:
            for c in shop_search(script, q):
                if c.get("url") in seen:
                    continue
                seen.add(c.get("url"))
                got = set(norm(c.get("name") or "").split())
                out.append({"shop": shop, "name": c.get("name"), "url": c.get("url"),
                            "price": c.get("price"), "image": c.get("image"), "query": q,
                            "score": round(len(want & got) / max(1, len(want | got)), 3)})
    out.sort(key=lambda c: -c["score"])
    return out[:12]


def search(status, out, only=None, sleep=0.7, shops="weak"):
    rows = [r for r in status if not r.get("code") and r.get("name_hy") and r["reg_no"] != "Ընդամենը"]
    if only:
        rows = [r for r in rows if r["reg_no"] in only]
    done = json.load(open(out)) if os.path.exists(out) else {}
    print(f"{len(rows)} codeless rows, {len(done)} already searched", file=sys.stderr)
    for n, r in enumerate(rows, 1):
        if r["reg_no"] in done:
            continue
        want = set(norm(r["name_hy"]).split())
        cands, seen = [], set()
        for q in queries(r["name_hy"]):
            d = fetch(q)
            for item in (d.get("data") or []):
                for row in (item.get("product_additional_information") or []):
                    key = (item.get("slug"), row.get("sku"))
                    if key in seen:
                        continue
                    seen.add(key)
                    got = set(norm(row.get("name") or item.get("title") or "").split())
                    score = len(want & got) / max(1, len(want | got))
                    try:
                        wp = float(row.get("wholesale_price") or 0)
                    except (TypeError, ValueError):
                        wp = 0
                    cands.append({"sku": (row.get("sku") or "").replace(" ", ""),
                                  "name": row.get("name"), "title": item.get("title"),
                                  "maker": (item.get("product_maker") or {}).get("title") if isinstance(item.get("product_maker"), dict) else item.get("product_maker"),
                                  "url": f"https://hafo.am/products/{item.get('slug')}",
                                  "price": row.get("price"), "wholesale": wp,
                                  "cost_eq": abs(wp - float(r["cost"] or 0)) < 0.5,
                                  "barcode": row.get("barcode"), "query": q,
                                  "score": round(score, 3)})
            time.sleep(sleep)
        cands.sort(key=lambda c: (-c["cost_eq"], -c["score"]))
        done[r["reg_no"]] = {"name_hy": r["name_hy"], "cost": r["cost"], "sale": r["sale_price"],
                             "kg": r.get("kg"), "candidates": cands[:12]}
        strong = any(c["cost_eq"] and c["score"] >= SHOP_SCORE for c in cands)
        if shops == "always" or (shops == "weak" and not strong):
            done[r["reg_no"]]["shop_candidates"] = shop_candidates(r["name_hy"], want)
        if n % 5 == 0:
            json.dump(done, open(out, "w"), ensure_ascii=False, indent=1)
            print(f"  {n}/{len(rows)}", file=sys.stderr)
    json.dump(done, open(out, "w"), ensure_ascii=False, indent=1)
    print(f"done -> {out}", file=sys.stderr)


def accept(path, overrides_path):
    ov = json.load(open(overrides_path)) if os.path.exists(overrides_path) else {}
    n = 0
    for r in csv.DictReader(open(path)):
        if (r.get("Code") or "").strip() and r.get("Decision", "").lower().startswith("accept"):
            ov[r["Register row"]] = r["Code"].strip()
            n += 1
    json.dump(ov, open(overrides_path, "w"), ensure_ascii=False, indent=1)
    print(f"{n} codes written to {overrides_path} ({len(ov)} total)", file=sys.stderr)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--status")
    ap.add_argument("--out")
    ap.add_argument("--only")
    ap.add_argument("--sleep", type=float, default=0.7)
    ap.add_argument("--shops", choices=["weak", "always"], default="weak",
                    help="also search nemo.am/zoovet.am: only when hafo is weak (default) or for every row")
    ap.add_argument("--no-shops", action="store_true", help="hafo only")
    ap.add_argument("--accept", help="identified-by-name.csv with Register row, Code, Decision columns")
    ap.add_argument("--overrides")
    a = ap.parse_args()
    if a.accept:
        accept(a.accept, a.overrides)
        return
    status = json.load(open(a.status))
    search(status, a.out, set(a.only.split(",")) if a.only else None, a.sleep,
           None if a.no_shops else a.shops)


main()
