#!/usr/bin/env python3
"""Compare every Siruk variant's sale price with hafo.am and (optionally) fix it.

How hafo prices work (learned in the browser, 2026-09-10):
  * A hafo listing (`/products/filter?search=<sku>`) covers every size of a
    product; each size is a row in `product_additional_information[]` with its
    own `id`, `sku`, `price`, `wholesale_price`, `qty_in_stock`,
    `image_color_name`, `discount_price`, `unique_price`, `kg_price`.
  * The product page renders a `<select name=product_data_id>` whose option
    values are those row ids. Picking one fires
        POST /product/change   color-id=<row id>&image-color=<image_color_name>&product_id=<listing id>
    (needs the XSRF-TOKEN cookie echoed as `x-csrf-token`, else 302) and the
    page shows the returned `price`. That `price` is the same number as the
    row's `price` in the listing — the description's hand-typed table is NOT
    (3275Tx: table says 3100, page and API say 2750).
  * So: the row price is the storefront price. This script finds the row from
    the listing API, then re-asks /product/change for the same row as a
    cross-check, and flags any disagreement or any discount marker instead of
    guessing.

Siruk SKUs for Trixie are the article number without the `Tx` suffix, so both
`<sku>` and `<sku>Tx` are tried. Sale price on Siruk = `price` (fixed) or
`price_per_kg × weight` (per_kg).

    scripts/check-hafo-prices.py            # report only → runs/<date>/price-check.csv
    scripts/check-hafo-prices.py --apply    # also PUT the corrected sale prices
    scripts/check-hafo-prices.py --only 204,207
"""
import csv, datetime, importlib.util, json, os, re, subprocess, sys, time, urllib.parse, urllib.request
from http.cookiejar import CookieJar

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, ".siruk-cache")
spec = importlib.util.spec_from_file_location("hafo", os.path.join(ROOT, "scripts/hafo-lookup.py"))
hafo = importlib.util.module_from_spec(spec); spec.loader.exec_module(hafo)
UA = hafo.UA
TRIXIE_BRAND_ID = 8
MAKER_ALIASES = {"simba": {"monge"}, "gemon": {"monge"}}  # sub-brand → hafo product_maker
VKEYS = ("id", "name", "about_this_item", "ingredient_information", "feeding_instructions", "pricing_type", "sku",
         "price", "price_per_kg", "min_allowed_price", "cost_price", "compare_at_price", "weight", "is_default",
         "stock", "vendor_stock", "sort_order", "images", "attribute_value_ids")
KEEP = ("name", "slug", "category_ids", "brand_id", "attribute_family_id", "is_best_seller", "is_on_sale", "is_discontinued")


def api(method, path, payload=None):
    env = dict(os.environ, SIRUK_NO_PACE="1")
    args = [os.path.join(ROOT, "scripts/api.sh"), method, path]
    if payload is not None:
        p = os.path.join(CACHE, "_pricefix.json")
        json.dump(payload, open(p, "w"), ensure_ascii=False)
        args.append(p)
    r = subprocess.run(args, capture_output=True, text=True, cwd=ROOT, env=env, timeout=180)
    i = r.stdout.find("{")
    return json.loads(r.stdout[i:]) if i >= 0 else {"_err": r.stderr[-300:]}


class Hafo:
    """Listing lookup + /product/change cross-check with one Laravel session."""
    def __init__(self):
        self.jar = CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.jar))
        self.csrf = None
        self.cache_path = os.path.join(CACHE, "hafo-price-cache.json")
        self.cache = json.load(open(self.cache_path)) if os.path.exists(self.cache_path) else {}
        self.brands = {b["id"]: b["name"] for b in api("GET", "/brands?forProducts=true").get("data", [])}

    def session(self):
        if self.csrf:
            return
        req = urllib.request.Request("https://hafo.am/", headers={"User-Agent": UA})
        self.opener.open(req, timeout=30).read()
        for c in self.jar:
            if c.name == "XSRF-TOKEN":
                self.csrf = urllib.parse.unquote(c.value)
        if not self.csrf:
            raise SystemExit("no XSRF-TOKEN cookie from hafo.am")

    def listings(self, q):
        if q in self.cache:
            return self.cache[q]
        d = hafo.fetch(q)
        self.cache[q] = d.get("data", [])
        json.dump(self.cache, open(self.cache_path, "w"), ensure_ascii=False)
        time.sleep(0.3)
        return self.cache[q]

    def change(self, listing_id, row):
        self.session()
        body = urllib.parse.urlencode({"color-id": row["id"], "image-color": row.get("image_color_name") or "", "product_id": listing_id}).encode()
        req = urllib.request.Request("https://hafo.am/product/change", data=body, headers={
            "User-Agent": UA, "x-csrf-token": self.csrf, "x-requested-with": "XMLHttpRequest", "Accept": "*/*",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8", "Referer": "https://hafo.am/"})
        try:
            with self.opener.open(req, timeout=30) as r:
                out = json.load(r)
            time.sleep(0.3)
            return out[0] if isinstance(out, list) and out else None
        except Exception as e:
            return {"_err": str(e)}

    def find(self, sku, brand_id, cost=0):
        """→ (listing, row, note). Tries the bare sku and, for Trixie, sku+'Tx'."""
        # hafo's search is a substring match on the SKU, so the BARE number finds the
        # listing even when hafo writes it 'TX 040201'; the row matcher then needs the
        # 'Tx' form to apply its zero-pad/variant-digit tolerance (hafo-lookup.py).
        forms = [sku] + ([sku + "Tx"] if brand_id == TRIXIE_BRAND_ID and not sku.lower().endswith("tx") else [])
        brand = (self.brands.get(brand_id) or "").lower()
        # hafo's product_maker names the manufacturer, not the sub-brand: Simba and
        # Gemon listings say "Monge" (2026-09-10). Accept the group maker too.
        makers = {brand} | MAKER_ALIASES.get(brand, set())
        hits, other_brand = [], 0
        for q in forms:
            for item in self.listings(q):
                # match on the article SKU only — hafo's internal `code` field ("02812")
                # collides with unrelated products
                for r in item.get("product_additional_information") or []:
                    art = r.get("sku") or r.get("article") or ""
                    if any(hafo.sku_matches(art, f) for f in forms):
                        maker = (item.get("product_maker") or "").lower()
                        if brand and not any(m in maker or maker in m for m in makers if m):
                            other_brand += 1
                            continue
                        hits.append((item, r))
            if hits:
                break
        if not hits:
            return None, None, "not on hafo" + (f" under {brand} ({other_brand} other-brand hits)" if other_brand else "")
        exact = [(i, r) for i, r in hits if hafo.norm_sku(r.get("sku")) in {hafo.norm_sku(f) for f in forms}]
        if len(exact) == 1:
            return exact[0][0], exact[0][1], ""
        # tie-break: hafo's per-row wholesale equals our invoice cost only on the right row
        # (listings with an empty product_maker slip past the brand filter — 4097 matched a
        # Trixie ball set AND a Monge kibble row '004097'; wholesale 965 == cost 965 picks the balls)
        if cost:
            byws = [(i, r) for i, r in hits if r.get("wholesale_price") == cost]
            if len({(i["id"], r["id"]) for i, r in byws}) == 1:
                return byws[0][0], byws[0][1], ""
        uniq = {(i["id"], r["id"]) for i, r in hits}
        if len(uniq) > 1:
            return None, None, "ambiguous: " + ", ".join(f"{i['id']}/{r['sku']}" for i, r in hits)
        return hits[0][0], hits[0][1], ""


def siruk_sale(v):
    if v.get("pricing_type") == "per_kg":
        return round((v.get("price_per_kg") or 0) * (v.get("weight") or 0))
    return int(v.get("price") or 0)


def main():
    apply = "--apply" in sys.argv
    only = None
    if "--only" in sys.argv:
        only = {int(x) for x in sys.argv[sys.argv.index("--only") + 1].split(",")}
    H = Hafo()
    ids, page = [], 1
    while True:
        d = api("GET", f"/products?page={page}")
        ids += [p["id"] for p in d.get("data", [])]
        if page >= (d.get("meta") or {}).get("last_page", 1):
            break
        page += 1
    ids = sorted(set(ids))
    if only:
        ids = [i for i in ids if i in only]

    rows, fixes = [], {}
    for pid in ids:
        p = api("GET", f"/products/{pid}").get("data") or {}
        for v in p.get("variants", []):
            sale = siruk_sale(v)
            cost = int(v.get("cost_price") or 0)
            listing, row, note = H.find(v["sku"], p.get("brand_id"), cost)
            rec = {"product_id": pid, "product": p.get("name"), "variant": v.get("name"), "sku": v["sku"],
                   "siruk_price": sale, "siruk_cost": cost, "pricing_type": v.get("pricing_type"),
                   "hafo_listing": "", "hafo_sku": "", "hafo_price": "", "hafo_wholesale": "", "hafo_change_price": "",
                   "hafo_stock": "", "flags": "", "status": ""}
            if not row:
                # sibling-price fallback (CLAUDE.md rule 2a): a variant hafo cannot price is
                # allowed to carry the hafo price of a same-product variant with the same cost.
                sib = [s for s in p.get("variants", []) if s is not v and int(s.get("cost_price") or 0) == cost and cost]
                sib_prices = set()
                for s in sib:
                    sl, sr, _ = H.find(s["sku"], p.get("brand_id"), cost)
                    if sr and sr.get("price") is not None:
                        sib_prices.add(sr["price"])
                if len(sib_prices) == 1 and sale == next(iter(sib_prices)):
                    rec["status"] = "sibling match"; rec["hafo_price"] = next(iter(sib_prices))
                    rec["flags"] = "priced from sibling " + ",".join(s["sku"] for s in sib) + f" ({note})"
                elif sib_prices:
                    rec["status"] = "SIBLING MISMATCH"; rec["hafo_price"] = "/".join(str(x) for x in sorted(sib_prices))
                    rec["flags"] = f"not on hafo; same-cost siblings priced {sorted(sib_prices)} ({note})"
                else:
                    rec["status"] = note
                rows.append(rec); continue
            chg = H.change(listing["id"], row) or {}
            rec.update(hafo_listing=f'{listing["id"]} {listing.get("slug")}', hafo_sku=row.get("sku"),
                       hafo_price=row.get("price"), hafo_wholesale=row.get("wholesale_price"),
                       hafo_change_price=chg.get("price", chg.get("_err", "")), hafo_stock=row.get("qty_in_stock"))
            flags = []
            if listing.get("discount") or listing.get("max_discount") or row.get("unique_price"):
                flags.append(f"discount markers: discount={listing.get('discount')} max_discount={listing.get('max_discount')} unique_price={row.get('unique_price')}")
            if chg.get("price") is not None and chg.get("price") != row.get("price"):
                flags.append(f"/product/change says {chg.get('price')} vs listing row {row.get('price')}")
            if cost and row.get("wholesale_price") not in (None, cost):
                flags.append(f"hafo wholesale {row.get('wholesale_price')} != our cost {cost}")
            if row.get("price") is not None and cost and row["price"] <= cost:
                flags.append("hafo price at or below our cost")
            rec["flags"] = "; ".join(flags)
            hp = row.get("price")
            if hp is None:
                rec["status"] = "hafo row has no price"
            elif hp == sale:
                rec["status"] = "match"
            else:
                rec["status"] = "MISMATCH" + ("" if not flags else " (flagged — not auto-fixed)")
                if not flags:
                    fixes.setdefault(pid, {})[v["sku"]] = hp
            rows.append(rec)
        print(f"{pid:>4} {p.get('name','')[:40]:<40} " + "  ".join(
            f"{r['sku']}:{r['siruk_price']}→{r['hafo_price'] or '?'} {r['status'][:9]}" for r in rows if r["product_id"] == pid))

    day = datetime.date.today().isoformat()
    outdir = os.path.join(ROOT, "runs", day); os.makedirs(outdir, exist_ok=True)
    out = os.path.join(outdir, "price-check.csv")
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    from collections import Counter
    c = Counter(r["status"].split(" (")[0] for r in rows)
    print("\n== summary ==", dict(c), "\n→", out)

    if not apply:
        print(f"{sum(len(v) for v in fixes.values())} variant(s) would be updated; run with --apply")
        return
    for pid, skus in fixes.items():
        p = api("GET", f"/products/{pid}")["data"]
        body = {k: p.get(k) for k in KEEP}
        body["variants"] = []
        for v in p["variants"]:
            nv = {k: v.get(k) for k in VKEYS if k in v}
            nv["images"] = nv.get("images") or []; nv["attribute_value_ids"] = nv.get("attribute_value_ids") or {}
            if v["sku"] in skus:
                hp = skus[v["sku"]]
                if (nv.get("cost_price") or 0) >= hp:
                    print(f"  !! {pid}/{v['sku']}: refusing {hp} <= cost {nv.get('cost_price')}"); continue
                if nv.get("pricing_type") == "per_kg" and nv.get("weight"):
                    nv["price_per_kg"] = round(hp / nv["weight"], 2)
                else:
                    nv["price"] = hp
            body["variants"].append(nv)
        api("PUT", f"/products/{pid}", body)
        back = api("GET", f"/products/{pid}")["data"]
        got = {v["sku"]: siruk_sale(v) for v in back["variants"]}
        ok = all(abs(got.get(s, -1) - hp) <= 1 for s, hp in skus.items())
        print(f"{'ok ' if ok else '!! '} {pid} {p['name']}: " + ", ".join(f"{s}→{hp}" for s, hp in skus.items()))


if __name__ == "__main__":
    main()
