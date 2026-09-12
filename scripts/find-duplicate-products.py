#!/usr/bin/env python3
"""Find products in the catalogue that are really variants of ONE product.

An import that treats every CSV row as its own product leaves the catalogue
full of sibling products: "Premium Collar, S, 25-40 cm/15 mm, fuchsia" and
"Premium Collar, S-M, 30-45 cm/15 mm, black" are one Trixie product with two
options on it, not two products (reference/product-rules.md, the shelf test;
size and colour are variant axes for accessories per the `accessories` skill).

Three signals, in order of authority:

  A  trixie.de   — the article codes sit on the same official product page.
  C  trixie.shop — the article codes are options of the same Shopify product
                   in Trixie's own store.
  B  name        — identical product name once the variant label is stripped
                   off the end, plus the same brand and the same categories.

A and C work both ways: they merge, and they SPLIT. Two articles Trixie sells
as different products never merge however alike their names are — that is what
keeps the three different "Stainless Steel Bowl" lines and the six "Soft Brush"
lines apart. B only merges where no official signal contradicts it; where a
name spans several official products, a member with no official key of its own
is undecidable and goes to the review list rather than into a merge.

    scripts/find-duplicate-products.py            # uses the cached catalogue
    scripts/find-duplicate-products.py --refresh  # re-read the admin API first

Writes .siruk-cache/dedup/groups.json (list of id lists) and review.json.
"""
import argparse, collections, json, os, pathlib, sys, time, urllib.request
from concurrent.futures import ThreadPoolExecutor

ROOT = pathlib.Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CACHE = ROOT / ".siruk-cache" / "dedup"
API = os.environ.get("SIRUK_API", "https://demo-api.siruk.am/api/admin")
UA = "siruk-dedup/1.0"

# Hand-checked exceptions: (product id, group-mate) pairs that the name signal
# joins but the brand's own catalogue separates.  Each carries its evidence.
SPLIT_OFF = {
    803: "trixie.shop: article 2007xx is Premium Verlangerungsleine DOPPELLAGIG, "
         "a different product from the 2013xx single-layer lead",
    423: "trixiecz 35263 = 'Geometricke zvire, plneny latex, 13 cm' — a different "
         "line from the 3503x/3506x Longie",
}


def token():
    return (ROOT / ".siruk-token").read_text().strip()


def get(path, lang=None, tries=4):
    h = {"Authorization": "Bearer " + token(), "Accept": "application/json", "User-Agent": UA}
    if lang:
        h["Content-Language"] = lang
    req = urllib.request.Request(API + path, headers=h)
    for a in range(tries):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read())
        except Exception:
            if a == tries - 1:
                raise
            time.sleep(2 * (a + 1))


def refresh():
    """Re-read every product (list + detail + ru/hy) into the cache."""
    (CACHE / "detail").mkdir(parents=True, exist_ok=True)
    first = get("/products?page=1")
    rows = list(first["data"])
    with ThreadPoolExecutor(4) as ex:
        for d in ex.map(lambda p: get(f"/products?page={p}")["data"],
                        range(2, first["meta"]["last_page"] + 1)):
            rows.extend(d)
    (CACHE / "list.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1))
    ids = [r["id"] for r in rows]
    for lang in (None, "ru", "hy"):
        d = CACHE / (lang or "detail")
        d.mkdir(exist_ok=True)
        def one(pid, d=d, lang=lang):
            (d / f"{pid}.json").write_text(json.dumps(get(f"/products/{pid}", lang), ensure_ascii=False))
        with ThreadPoolExecutor(4) as ex:
            list(ex.map(one, ids))
    print(f"refreshed {len(ids)} products", file=sys.stderr)


def load_products():
    out = {}
    for f in (CACHE / "detail").glob("*.json"):
        d = json.load(open(f))["data"]
        out[d["id"]] = d
    return out


def base_name(p):
    """The product name with the trailing variant label removed."""
    n = p["name"]
    for v in p["variants"]:
        lbl = (v.get("name") or "").strip()
        if lbl and n.endswith(lbl) and len(n) > len(lbl):
            return n[: len(n) - len(lbl)].rstrip(" ,–-")
    return n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--refresh", action="store_true")
    a = ap.parse_args()
    if a.refresh:
        refresh()

    prod = load_products()
    a2p = json.load(open(CACHE / "trixie-map.json"))["a2p"]
    shop = json.load(open(CACHE / "shop-map.json"))

    def official(p):
        keys = set()
        for v in p["variants"]:
            s = (v.get("sku") or "").strip()
            if a2p.get(s): keys.add(("page", a2p[s]))
            if shop.get(s): keys.add(("shop", shop[s]))
        return keys

    parent = {}
    def find(x):
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]; x = parent[x]
        return x
    def union(x, y):
        rx, ry = find(x), find(y)
        if rx != ry: parent[ry] = rx

    for i in prod: find(i)

    bykey = collections.defaultdict(list)
    for i, p in prod.items():
        for k in official(p): bykey[k].append(i)
    for ids in bykey.values():
        for j in ids[1:]: union(ids[0], j)

    comp_keys = collections.defaultdict(set)
    for i, p in prod.items(): comp_keys[find(i)] |= official(p)

    byname = collections.defaultdict(list)
    for i, p in prod.items():
        byname[(p["brand_id"], base_name(p), tuple(sorted(p["category_ids"])))].append(i)

    review = []
    for key, ids in sorted(byname.items(), key=lambda x: str(x[0])):
        if len(ids) < 2: continue
        roots = {find(i) for i in ids}
        if len(roots) < 2: continue
        if len({r for r in roots if comp_keys[r]}) > 1:
            loose = sorted(i for i in ids if not comp_keys[find(i)])
            if loose:
                review.append({"reason": "no official product key, and the name spans several",
                               "base": key[1], "ids": loose,
                               "siblings": sorted(set(ids) - set(loose))})
            continue
        for j in ids[1:]: union(ids[0], j)

    groups = collections.defaultdict(list)
    for i in prod: groups[find(i)].append(i)
    merge = []
    for v in groups.values():
        if len(v) < 2: continue
        kept = sorted(i for i in v if i not in SPLIT_OFF)
        for i in sorted(set(v) & set(SPLIT_OFF)):
            review.append({"reason": "hand-checked split", "base": prod[i]["name"],
                           "ids": [i], "siblings": kept, "evidence": SPLIT_OFF[i]})
        if len(kept) > 1: merge.append(kept)
    merge.sort(key=lambda v: (-len(v), v[0]))

    CACHE.mkdir(parents=True, exist_ok=True)
    json.dump(merge, open(CACHE / "groups.json", "w"), indent=1)
    json.dump(review, open(CACHE / "review.json", "w"), indent=1, ensure_ascii=False)
    print(f"{len(merge)} groups, {sum(len(v) for v in merge)} products "
          f"→ {sum(len(v) for v in merge) - len(merge)} duplicates to fold away", file=sys.stderr)
    print(f"{len(review)} sent to review", file=sys.stderr)


if __name__ == "__main__":
    main()
