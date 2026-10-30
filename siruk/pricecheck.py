"""The after-import hafo price recheck (CLAUDE.md rule 4) — the port of
scripts/check-hafo-prices.py.

How hafo prices work (learned in the browser, 2026-09-10): a listing
(`/products/filter?search=<sku>`) covers every size; each size is a row of
`product_additional_information[]` with its own price. The product page's size
picker fires POST /product/change (XSRF cookie echoed as x-csrf-token) and shows
that row's price — the description's hand-typed table is NOT the price
(3275Tx: table 3100, page and API 2750). So: find the row, re-ask
/product/change for it as a cross-check, flag any disagreement or discount
marker instead of guessing. Trixie SKUs are tried bare and with "Tx".

check() reports; fixes() lists the unflagged mismatches; apply() writes them
(price only, never at or below cost, one PUT per product, read back).
A zoovet/nemo-priced row needs its own recheck against that source (rule 4).
"""
import csv, datetime, json, os, time, urllib.parse, urllib.request
from collections import Counter
from http.cookiejar import CookieJar

from siruk import client as _client
from siruk import lookups, products
from siruk import payload as P
from siruk.config import CACHE, ROOT

TRIXIE_BRAND_ID = 8
MAKER_ALIASES = {"simba": {"monge"}, "gemon": {"monge"}}  # sub-brand → hafo product_maker
# hafo-lookup.sku_matches strips ANY trailing letters off a Trixie-form match, so our
# Trixie 4123 matched hafo's 04123IVS (an Iv San Bernard 3 l shampoo, empty
# product_maker) and the recheck proposed 300 → 54550 (2026-10-26). For a Trixie product,
# a hafo SKU ending in letters other than Trixie's own (Tx / Trx / TXN) is not our article.
TRIXIE_SUFFIXES = ("tx", "trx", "txn")
WHOLESALE_RATIO = 3   # hafo wholesale vs our cost beyond 3× either way → check the identity by hand


def foreign_suffix(hafo_sku, sku, brand_id=TRIXIE_BRAND_ID):
    """The trailing letters of a Trixie match that belong to another supplier, else None."""
    if brand_id != TRIXIE_BRAND_ID:
        return None
    import re
    tail = re.search(r"[a-z]+$", re.sub(r"[^a-z0-9]", "", (hafo_sku or "").lower()))
    ours = re.search(r"[a-z]+$", (sku or "").lower())
    if not tail or tail.group() in TRIXIE_SUFFIXES or (ours and ours.group() == tail.group()):
        return None
    return tail.group()
COLUMNS = ["product_id", "product", "variant", "sku", "siruk_price", "siruk_cost", "sale_mode", "hafo_listing",
           "hafo_sku", "hafo_price", "hafo_wholesale", "hafo_change_price", "hafo_stock", "flags", "status"]


class Hafo:
    """Listing lookup + /product/change cross-check with one Laravel session."""

    def __init__(self):
        self.h = lookups._script("hafo-lookup")
        self.jar = CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.jar))
        self.csrf = None
        self.cache_path = os.path.join(CACHE, "hafo-price-cache.json")
        try:
            with open(self.cache_path, encoding="utf-8") as f:
                self.cache = json.load(f)
        except (OSError, ValueError):
            self.cache = {}
        self.brands = {b["id"]: b["name"] for b in
                       (_client.default().get("/brands?forProducts=true") or {}).get("data", [])}

    def session(self):
        if self.csrf:
            return
        req = urllib.request.Request("https://hafo.am/", headers={"User-Agent": self.h.UA})
        self.opener.open(req, timeout=30).read()
        for c in self.jar:
            if c.name == "XSRF-TOKEN":
                self.csrf = urllib.parse.unquote(c.value)
        if not self.csrf:
            raise RuntimeError("no XSRF-TOKEN cookie from hafo.am")

    def listings(self, q):
        if q in self.cache:
            return self.cache[q]
        d = self.h.fetch(q)
        self.cache[q] = d.get("data", [])
        os.makedirs(CACHE, exist_ok=True)
        with open(self.cache_path, "w", encoding="utf-8") as f:
            json.dump(self.cache, f, ensure_ascii=False)
        time.sleep(0.3)
        return self.cache[q]

    def change(self, listing_id, row):
        try:
            self.session()
            body = urllib.parse.urlencode({"color-id": row["id"], "image-color": row.get("image_color_name") or "",
                                           "product_id": listing_id}).encode()
            req = urllib.request.Request("https://hafo.am/product/change", data=body, headers={
                "User-Agent": self.h.UA, "x-csrf-token": self.csrf, "x-requested-with": "XMLHttpRequest",
                "Accept": "*/*", "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                "Referer": "https://hafo.am/"})
            with self.opener.open(req, timeout=30) as r:
                out = json.load(r)
            time.sleep(0.3)
            return out[0] if isinstance(out, list) and out else None
        except Exception as e:
            return {"_err": str(e)}

    def find(self, sku, brand_id, cost=0):
        """→ (listing, row, note). Article SKU only — hafo's internal `code` collides."""
        h = self.h
        forms = [sku] + ([sku + "Tx"] if brand_id == TRIXIE_BRAND_ID and not sku.lower().endswith("tx") else [])
        brand = (self.brands.get(brand_id) or "").lower()
        makers = {brand} | MAKER_ALIASES.get(brand, set())
        hits, other_brand = [], 0
        for q in forms:
            for item in self.listings(q):
                for r in item.get("product_additional_information") or []:
                    art = r.get("sku") or r.get("article") or ""
                    if any(h.sku_matches(art, f) for f in forms) and not foreign_suffix(art, sku, brand_id):
                        maker = (item.get("product_maker") or "").lower()
                        if brand and not any(m in maker or maker in m for m in makers if m):
                            other_brand += 1
                            continue
                        hits.append((item, r))
            if hits:
                break
        if not hits:
            return None, None, "not on hafo" + (f" under {brand} ({other_brand} other-brand hits)" if other_brand else "")
        exact = [(i, r) for i, r in hits if h.norm_sku(r.get("sku")) in {h.norm_sku(f) for f in forms}]
        if len(exact) == 1:
            return exact[0][0], exact[0][1], ""
        # hafo's per-row wholesale equals our invoice cost only on the right row (4097, 2026-09)
        if cost:
            byws = [(i, r) for i, r in hits if r.get("wholesale_price") == cost]
            if len({(i["id"], r["id"]) for i, r in byws}) == 1:
                return byws[0][0], byws[0][1], ""
        uniq = {(i["id"], r["id"]) for i, r in hits}
        if len(uniq) > 1:
            return None, None, "ambiguous: " + ", ".join(f"{i['id']}/{r['sku']}" for i, r in hits)
        return hits[0][0], hits[0][1], ""


def _check_product(H, p):
    rows = []
    for v in p.get("variants", []):
        sale, cost = int(v.get("price") or 0), int(v.get("cost_price") or 0)
        listing, row, note = H.find(v["sku"], p.get("brand_id"), cost)
        rec = dict.fromkeys(COLUMNS, "")
        rec.update(product_id=p["id"], product=p.get("name"), variant=v.get("name"), sku=v["sku"],
                   siruk_price=sale, siruk_cost=cost, sale_mode=v.get("sale_mode"))
        if not row:
            # sibling-price fallback (rule 2a): a same-cost variant may carry its sibling's hafo price
            sib = [s for s in p.get("variants", []) if s is not v and int(s.get("cost_price") or 0) == cost and cost]
            sib_prices = set()
            for s in sib:
                _, sr, _ = H.find(s["sku"], p.get("brand_id"), cost)
                if sr and sr.get("price") is not None:
                    sib_prices.add(sr["price"])
            if len(sib_prices) == 1 and sale == next(iter(sib_prices)):
                rec.update(status="sibling match", hafo_price=next(iter(sib_prices)),
                           flags="priced from sibling " + ",".join(s["sku"] for s in sib) + f" ({note})")
            elif sib_prices:
                rec.update(status="SIBLING MISMATCH", hafo_price="/".join(str(x) for x in sorted(sib_prices)),
                           flags=f"not on hafo; same-cost siblings priced {sorted(sib_prices)} ({note})")
            else:
                rec["status"] = note
            rows.append(rec)
            continue
        chg = H.change(listing["id"], row) or {}
        rec.update(hafo_listing=f'{listing["id"]} {listing.get("slug")}', hafo_sku=row.get("sku"),
                   hafo_price=row.get("price"), hafo_wholesale=row.get("wholesale_price"),
                   hafo_change_price=chg.get("price", chg.get("_err", "")), hafo_stock=row.get("qty_in_stock"))
        flags = []
        if listing.get("discount") or listing.get("max_discount") or row.get("unique_price"):
            flags.append(f"discount markers: discount={listing.get('discount')} "
                         f"max_discount={listing.get('max_discount')} unique_price={row.get('unique_price')}")
        if chg.get("price") is not None and chg.get("price") != row.get("price"):
            flags.append(f"/product/change says {chg.get('price')} vs listing row {row.get('price')}")
        if row.get("price") is not None and cost and row["price"] <= cost:
            flags.append("hafo price at or below our cost")
        ws = row.get("wholesale_price")
        if ws and cost and not (cost / WHOLESALE_RATIO <= ws <= cost * WHOLESALE_RATIO):
            flags.append(f"hafo wholesale {ws} vs our cost {cost} — probably another product, check the identity")
        rec["flags"] = "; ".join(flags)
        hp = row.get("price")
        if hp is None:
            rec["status"] = "hafo row has no price"
        elif hp == sale:
            rec["status"] = "match"
        else:
            rec["status"] = "MISMATCH" + ("" if not flags else " (flagged — not auto-fixed)")
        rows.append(rec)
    return rows


def check(only=None, progress=None):
    """→ rows (COLUMNS), one per variant. only: product ids (None = the whole catalogue)."""
    H = Hafo()
    ids = sorted(set(only)) if only else sorted(
        {p["id"] for p in _client.default().paginate("/products", max_pages=1000)})
    rows = []
    for i, pid in enumerate(ids, 1):
        p = products.get(pid)
        if p:
            prow = _check_product(H, p)
            rows += prow
            if progress:
                progress(pid, p, prow)
    return rows


def fixes(rows):
    """{product id: {sku: hafo price}} — unflagged mismatches only (`--apply` fixes nothing else)."""
    out = {}
    for r in rows:
        if r["status"] == "MISMATCH":
            out.setdefault(r["product_id"], {})[r["sku"]] = r["hafo_price"]
    return out


def summary(rows):
    return dict(Counter(r["status"].split(" (")[0] for r in rows))


def write_csv(rows, path=None):
    if not rows:
        return None
    path = path or os.path.join(ROOT, "runs", datetime.date.today().isoformat(), "price-check.csv")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader()
        w.writerows(rows)
    return path


def apply_prices(pid, prices, dry_run=False):
    """Set {sku: hafo price} on one product in one PUT. Refuses a price at or below cost and a
    non-pack variant (the variant stays in the body unchanged — dropping it would delete it).
    The product-type check runs after the fix, so a bad old price cannot block it."""
    before = products.get(pid)
    if not before:
        raise P.PayloadError(f"product {pid} not found")
    ptype = P.product_type(before.get("attribute_family_id") or 0)
    allowed = {a["id"] for a in ptype.get("attributes") or []}
    body = P.product_body(before)
    body["variants"] = [P.to_variant_payload(v, allowed) for v in before["variants"]]
    skipped, applied = [], {}
    for nv in body["variants"]:
        if nv["sku"] not in prices:
            continue
        hp = int(prices[nv["sku"]])
        if nv.get("sale_mode") != "pack":
            skipped.append(f"{nv['sku']}: sale_mode {nv.get('sale_mode')} — not a pack price, left alone")
        elif (nv.get("cost_price") or 0) >= hp:
            skipped.append(f"{nv['sku']}: refusing {hp} <= cost {nv.get('cost_price')}")
        else:
            nv["price"] = hp
            applied[nv["sku"]] = hp
    unknown = set(prices) - {v["sku"] for v in body["variants"]}
    skipped += [f"{s}: not a variant of product {pid}" for s in sorted(unknown)]
    if not applied:
        raise P.PayloadError(f"product {pid}: nothing to apply — " + "; ".join(skipped))
    errs, warns = P.check_variants(body["variants"], ptype)
    if errs:
        raise P.PayloadError(f"product {pid}: refused before writing: " + "; ".join(errs))
    res = products._put(int(pid), before, body, "apply_hafo_prices", dry_run, warns + skipped)
    if not dry_run:
        got = {v["sku"]: int(v.get("price") or 0) for v in res.after["variants"]}
        bad = [s for s, hp in applied.items() if abs(got.get(s, -1) - hp) > 1]
        if bad:
            raise P.PayloadError(f"product {pid}: written but read-back shows other prices for {bad}")
    return res
