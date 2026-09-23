#!/usr/bin/env python3
"""Build the per-row import ledger for csv/ALL_SIRUK_PRODUCTS.csv.

One line per CSV row:

    product name, product code, imported, siruk link, info source, price source

`imported` is decided against the LIVE catalogue (the article code is a variant
SKU), not against any run log. The info source is the page the product's name,
images and description came from, recovered from the run reports; the price
source is the hafo.am listing the sale price was read off — or the zoovet page
/ sibling code where rule 2a/2b applied.

    scripts/build-import-ledger.py --out runs/<date>/import-ledger.csv
"""
import argparse, csv, glob, json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, ".siruk-cache")
# the storefront addresses a variant, not a product: /product/<slug>/dp/<variant id>
STORE = "https://demo.siruk.am"


def art(code):
    return re.sub(r"(Tx|TXN)$", "", code.strip())


def report_sources():
    """article code -> the first brand-site url a run report recorded for it."""
    out = {}
    for f in sorted(glob.glob(os.path.join(ROOT, "runs/**/*.md"), recursive=True)):
        for line in open(f, errors="replace"):
            if not line.lstrip().startswith("|"):
                continue
            codes = re.findall(r"\[([0-9]{3,7}(?:Tx|TXN|MG|IVS|PCHL|M|V|K|J)?)\](?!\()", line)
            urls = [u.split()[0].rstrip(",;") for u in
                    re.findall(r"\]\((https?://[^)]+)\)", line)
                    if "hafo.am" not in u]
            for c in codes:
                if urls and c not in out:
                    out[c] = urls[0]
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--diff", required=True, help="runs/<date>/csv-vs-live.json")
    a = ap.parse_args()

    diff = json.load(open(a.diff))
    live = {r["Article Code"]: r for r in diff["live"]}
    hafo = json.load(open(os.path.join(CACHE, "hafo-all.json")))
    # state/import-sources.json holds everything the runs up to 2026-09-23
    # recorded (their folders were cleared then); newer run reports add to it
    kept = json.load(open(os.path.join(ROOT, "state/import-sources.json")))
    srcs = dict(kept["info"])
    srcs.update(report_sources())

    # rule 2a / 2b overrides: the kept ones, plus any a newer run recorded
    sib, zoo = dict(kept["sibling_priced"]), dict(kept["zoovet_priced"])
    zoo.update(kept.get("nemo_priced") or {})
    for f in glob.glob(os.path.join(ROOT, "runs/*/sibling-priced.csv")):
        for r in csv.DictReader(open(f)):
            c = (r.get("Article Code") or "").strip()
            if c:
                sib[c] = (r.get("Priced from (sibling code)") or "").strip()
    for f in glob.glob(os.path.join(ROOT, "runs/*/zoovet-priced.csv")):
        for r in csv.DictReader(open(f)):
            c = (r.get("Article Code") or "").strip()
            if c:
                zoo[c] = (r.get("zoovet url") or "").strip()

    rows = list(csv.DictReader(open(os.path.join(ROOT, "csv/ALL_SIRUK_PRODUCTS.csv"))))
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    w = csv.writer(open(a.out, "w", newline=""))
    w.writerow(["Product name", "Product code", "Imported", "Siruk link",
                "Info source (name / images / description)", "Price source",
                "Why not imported"])
    n_imported = 0
    for r in rows:
        code = r["Article Code"].strip()
        hit = live.get(code)
        link = (f"{STORE}/product/{hit['_slug']}/dp/{hit['_variant_id']}/"
                if hit and hit.get("_variant_id") else "")
        name = hit["_product"] if hit else r["Product Name (as printed)"]
        if hit and hit.get("_variant") and hit["_variant"] not in (name or ""):
            name = f'{name} — {hit["_variant"]}'
        info = srcs.get(code) or srcs.get(art(code)) or ""
        h = hafo.get(code) or {}
        if code in zoo and zoo[code]:
            price = zoo[code]
        elif code in sib and sib[code]:
            price = f"sibling price of article {sib[code]} (hafo)"
        elif h.get("price_source") == "variant" and h.get("url"):
            price = h["url"]
        else:
            price = ""
        if hit and not info:
            info = h.get("url", "") and f'{h["url"]} (hafo listing — no brand page found)'
        if not hit:
            price = price if price else ""
        why = ""
        if not hit:
            cost = float(r["Buy Price (AMD)"] or 0)
            if not h.get("confirmed"):
                why = ("no hafo listing keyed to this article code — identity unconfirmed (rule 6)"
                       if not h.get("hafo_id") else
                       "hafo hit is a name guess, not an article-code match — identity unconfirmed (rule 6)")
            elif h.get("price_source") != "variant":
                why = "on hafo, but the listing has no row for this size — no sale price (rule 3)"
            elif h.get("price_amd") and h["price_amd"] <= cost:
                why = f"hafo price {h['price_amd']} is at or below our cost {int(cost)} — wrong hafo row (rule 5)"
            else:
                why = "importable, not reached this run"
            if code == "03623K":
                why = "brand \u0418\u043d\u0442\u0435\u043a\u043e has no official site and no findable logo — skipped on the user's call, 2026-09-15"
        n_imported += bool(hit)
        w.writerow([name, code, "TRUE" if hit else "FALSE", link, info, price, why])
    print(f"{a.out}: {len(rows)} rows, {n_imported} imported, {len(rows)-n_imported} not",
          file=sys.stderr)


main()
