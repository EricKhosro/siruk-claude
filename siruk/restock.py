"""The restock check (user, 2026-11-15): what a received invoice changes on Siruk.

A restock used to change nothing on api.siruk.am, so a variant kept the cost of its
first import and a sale price nobody had looked at since. For every received line
(ArmSoft good code or SKU + the invoice cost incl. VAT) this:

1. **Cost** — compares the invoice cost with the variant's `cost_price` and proposes
   the new one. The variants made from the same pack follow it by rule 8a:
   `<sku>-KG` = pack cost ÷ pack kg, `<sku>-100G` = ÷ (pack g / 100), `<sku>-1` =
   ÷ pack_count. A move over 15 % is flagged, not applied (another size, or a case
   booked as a piece).
2. **Sale price** — re-reads the three rivals live and proposes the **highest**
   (reference/pricing.md): hafo by article code (pricecheck.Hafo), zoovet.am and
   nemo.am only on a page whose identity was confirmed by hand — the variant's own
   `price_source_url`, or its row in state/rival-urls.csv (`none` = confirmed not
   sold there). A name search is never a price, so a shop with no confirmed page is
   "not checked".
   - highest > ours → RAISE (safe: the highest of three is at least that).
   - highest < ours → LOWER only when all three shops are settled; otherwise
     CHECK BY HAND, since the unchecked shop may be the one holding our price.
   - a move over 30 %, a hafo discount marker, or a price at or below the new cost
     is flagged and never applied.
   The 1 kg / 100 g / single variants keep their price: their rival price is a
   per-kg or single-unit listing, checked by hand.

check() only reads; fixes() lists what is safe to write; apply() writes it through
products.update_variant (dry run first, one PUT per variant, read back).
"""
import csv, datetime, json, os, time, urllib.parse

from siruk import export, lookups, pricecheck, products
from siruk import payload as P
from siruk.config import ROOT

RIVAL_URLS = os.path.join(ROOT, "state", "rival-urls.csv")
OUTSIDE_GAP = 1.5      # seconds between calls to an outside site (CLAUDE.md, 2026-11-12)
COST_JUMP = 0.15       # receive-invoices stops an invoice on the same move
PRICE_JUMP = 0.30
SHOPS = ("hafo", "zoovet", "nemo")
HOSTS = {"hafo.am": "hafo", "zoovet.am": "zoovet", "nemo.am": "nemo"}
ROLES = (("-KG", "1 kg"), ("-100G", "100 g"), ("-1", "single"))
COLUMNS = ["line_code", "product_id", "product", "variant", "sku", "role", "siruk_cost", "new_cost",
           "cost_status", "siruk_price", "hafo", "zoovet", "nemo", "highest", "highest_source",
           "source_url", "price_status", "flags"]

_last_outside = [0.0]


def _pause():
    wait = OUTSIDE_GAP - (time.time() - _last_outside[0])
    if wait > 0:
        time.sleep(wait)
    _last_outside[0] = time.time()


class PacedHafo(pricecheck.Hafo):
    """pricecheck.Hafo, read live (no listing cache) and at the outside-site pace."""

    def __init__(self):
        super().__init__()
        self.cache = {}

    def listings(self, q):
        if q not in self.cache:
            _pause()
            self.cache[q] = self.h.fetch(q).get("data", [])
        return self.cache[q]

    def change(self, listing_id, row):
        _pause()
        return super().change(listing_id, row)


# ------------------------------------------------------------------ inputs ----
def load_lines(args):
    """Each arg: CODE=COST, CODE=COST/kg (cost per kg of a loose-sale bag), a JSON file
    ([{code, cost, per?}]) or a CSV file (code,cost[,per]). → [{code, cost, per}]."""
    out = []
    for a in args:
        if os.path.exists(a):
            with open(a, encoding="utf-8-sig") as f:
                rows = json.load(f) if a.lower().endswith(".json") else list(csv.DictReader(f))
        elif "=" in a:
            code, cost = a.split("=", 1)
            per = "pack"
            if cost.lower().endswith("/kg"):
                cost, per = cost[:-3], "kg"
            rows = [{"code": code, "cost": cost, "per": per}]
        else:
            raise P.PayloadError(f"'{a}' is neither a file nor CODE=COST")
        for r in rows:
            try:
                cost = float(str(r["cost"]).replace(",", "").strip())
            except (KeyError, ValueError):
                raise P.PayloadError(f"line {r}: needs code and a numeric cost")
            if cost <= 0 or not str(r.get("code") or "").strip():
                raise P.PayloadError(f"line {r}: needs code and a cost above zero")
            out.append({"code": str(r["code"]).strip(), "cost": cost,
                        "per": (r.get("per") or "pack").strip().lower()})
    if not out:
        raise P.PayloadError("no lines given")
    return out


def rival_urls(path=None):
    """state/rival-urls.csv → {sku: {"zoovet": url | "none" | "", "nemo": …}}."""
    out = {}
    try:
        with open(path or RIVAL_URLS, encoding="utf-8-sig") as f:
            for r in csv.DictReader(f):
                out[(r.get("sku") or "").strip()] = {s: (r.get(f"{s}_url") or "").strip() for s in ("zoovet", "nemo")}
    except OSError:
        pass
    return out


def shop_of(url):
    host = (url or "").split("//")[-1].split("/")[0].lower().removeprefix("www.")
    return HOSTS.get(host)


# -------------------------------------------------------------------- cost ----
def _num(x):
    try:
        return float(x or 0)
    except (TypeError, ValueError):
        return 0.0


def _money(x):
    x = round(x, 2)
    return int(x) if float(x).is_integer() else x


def pack_grams(v):
    return _num(v.get("content")) * (int(_num(v.get("pack_count"))) or 1) if v.get("measure_type") == "mass" else 0


def derived(p, base):
    """[(variant, role, divisor)] — the variants of product p made from `base`'s pack (rule 8a)."""
    out = []
    for v in p.get("variants") or []:
        for suffix, role in ROLES:
            if v.get("sku") != f"{base['sku']}{suffix}":
                continue
            if role == "single":
                div = int(_num(base.get("pack_count")))
                div = div if div > 1 else None
            else:
                g = pack_grams(base)
                div = (g / (1000 if role == "1 kg" else 100)) or None
            out.append((v, role, div))
    return out


def _cost_status(old, new):
    if not old:
        return "COST CHANGE", ""
    if abs(new - old) < 0.5:
        return "same", ""
    move = (new - old) / old
    if abs(move) > COST_JUMP:
        return "COST FLAGGED", (f"cost moved {move:+.0%} ({_money(old)} → {_money(new)}) — another size, "
                                "or a case booked as a piece? not applied")
    return "COST CHANGE", ""


# ------------------------------------------------------------------ rivals ----
def _hafo_side(row):
    """One pricecheck row → {state, price, url, note}."""
    st, flags = row.get("status") or "", row.get("flags") or ""
    slug = (row.get("hafo_listing") or "").partition(" ")[2]
    url = f"https://hafo.am/products/{slug}" if slug else ""
    if st.startswith(("match", "MISMATCH")):
        if flags or "flagged" in st:
            return {"state": "unknown", "price": row.get("hafo_price"), "url": url, "note": f"hafo: {flags}"}
        return {"state": "confirmed", "price": int(row["hafo_price"]), "url": url, "note": ""}
    if st.startswith("not on hafo") or "sibling" in st.lower():
        return {"state": "none", "price": None, "url": "", "note": ""}
    return {"state": "unknown", "price": None, "url": url, "note": f"hafo: {st}"}


def _shop_side(shop, v, urls):
    url = (urls.get(v.get("sku")) or {}).get(shop) or ""
    if not url and shop_of(v.get("price_source_url")) == shop:
        url = v["price_source_url"]
    if url.lower() == "none":
        return {"state": "none", "price": None, "url": "", "note": ""}
    if not url:
        return {"state": "unknown", "price": None, "url": "", "note": ""}
    _pause()
    try:
        # nemo's stored urls carry Armenian letters, which urllib refuses unescaped
        safe = urllib.parse.quote(url, safe=":/?&=%#+,;@")
        price = (getattr(lookups, shop)(url=safe) or {}).get("price")
    except Exception as e:    # a dead page or a blocked request is "not checked", never a price
        return {"state": "unknown", "price": None, "url": url, "note": f"{shop}: page not read ({e})"}
    if not price:
        return {"state": "unknown", "price": None, "url": url, "note": f"{shop}: no price on the page"}
    return {"state": "confirmed", "price": int(price), "url": url, "note": ""}


def _decide(sale, cost, sides):
    """→ (status, highest, source, url, flags). cost = the cost the variant will have."""
    flags = [s["note"] for s in sides.values() if s["note"]]
    known = {k: s for k, s in sides.items() if s["state"] == "confirmed"}
    unchecked = [k for k, s in sides.items() if s["state"] == "unknown"]
    if not known:
        return ("no rival price" if not unchecked else "not checked"), "", "", "", flags
    src = max(known, key=lambda k: known[k]["price"])
    top, url = known[src]["price"], known[src]["url"]
    if top == sale:
        return "match", top, src, url, flags
    if cost and top <= cost:
        flags.append(f"highest rival {top} is at or below our cost {_money(cost)} — check the identity")
        return "PRICE FLAGGED", top, src, url, flags
    if sale and abs(top - sale) / sale > PRICE_JUMP:
        flags.append(f"price would move {(top - sale) / sale:+.0%} — per-kg listing or another pack? check by hand")
        return "PRICE FLAGGED", top, src, url, flags
    if top > sale:
        return "RAISE", top, src, url, flags
    if unchecked:
        flags.append(f"ours is above the highest checked rival; not checked: {', '.join(unchecked)} "
                     "(no confirmed page — add it to state/rival-urls.csv, or 'none')")
        return "CHECK BY HAND", top, src, url, flags
    return "LOWER", top, src, url, flags


# ------------------------------------------------------------------- check ----
def _row(line, p, v, role):
    r = dict.fromkeys(COLUMNS, "")
    r.update(line_code=line["code"], product_id=p.get("id"), product=p.get("name"), variant=v.get("name"),
             sku=v.get("sku"), role=role, siruk_cost=_money(_num(v.get("cost_price"))),
             siruk_price=int(_num(v.get("price"))))
    return r


def check(lines, urls=None, progress=None):
    """→ rows (COLUMNS). lines: [{code, cost, per}] — code = ArmSoft good code or SKU."""
    urls = rival_urls() if urls is None else urls
    recs = export.records()
    H, got, hafo_rows, rows = PacedHafo(), {}, {}, []
    for line in lines:
        code = line["code"]
        hits = [r for r in recs if code in (str(r.get("accounting_code") or ""), str(r.get("sku") or ""))]
        bases = []
        for pid in sorted({r["product_id"] for r in hits}):
            p = got.setdefault(pid, products.get(pid))
            made = {d[0]["sku"] for b in p.get("variants") or [] for d in derived(p, b)}
            skus = {r["sku"] for r in hits if r["product_id"] == pid}
            bases += [(p, v) for v in p.get("variants") or [] if v["sku"] in skus and v["sku"] not in made]
        if len(bases) != 1:
            r = dict.fromkeys(COLUMNS, "")
            r.update(line_code=code, new_cost=_money(line["cost"]),
                     cost_status="NOT IN SIRUK" if not bases else "AMBIGUOUS",
                     flags="no live variant carries this code" if not bases else
                     "several variants carry this code: " + ", ".join(f"{p['id']}/{v['sku']}" for p, v in bases))
            rows.append(r)
            continue
        p, base = bases[0]
        cost = line["cost"]
        if line["per"] == "kg":
            if not pack_grams(base):
                cost = None
            else:
                cost = cost * pack_grams(base) / 1000
        r = _row(line, p, base, "pack")
        flags = []
        if p.get("is_discontinued"):
            flags.append("product is discontinued")
        if cost is None:
            r.update(cost_status="COST FLAGGED")
            flags.append("per-kg cost given but the variant has no mass content")
            new_cost = _num(base.get("cost_price"))
        else:
            st, note = _cost_status(_num(base.get("cost_price")), cost)
            r.update(new_cost=_money(cost), cost_status=st)
            flags += [note] if note else []
            new_cost = cost if st == "COST CHANGE" else _num(base.get("cost_price"))
        if base.get("sale_mode") == "pack":
            if p["id"] not in hafo_rows:
                hafo_rows[p["id"]] = {x["sku"]: x for x in pricecheck._check_product(H, p)}
            sides = {"hafo": _hafo_side(hafo_rows[p["id"]].get(base["sku"]) or {})}
            for shop in ("zoovet", "nemo"):
                sides[shop] = _shop_side(shop, base, urls)
            st, top, src, url, pflags = _decide(int(_num(base.get("price"))), new_cost, sides)
            r.update({k: (sides[k]["price"] if sides[k]["price"] is not None else
                          {"none": "not sold", "unknown": "not checked"}[sides[k]["state"]]) for k in SHOPS})
            r.update(price_status=st, highest=top, highest_source=src, source_url=url)
            flags += pflags
        final_price = r["highest"] if r["price_status"] in ("RAISE", "LOWER") else r["siruk_price"]
        if r["cost_status"] == "COST CHANGE" and final_price and new_cost >= final_price:
            r["cost_status"] = "COST FLAGGED"
            flags.append(f"new cost {_money(new_cost)} is at or above the sale price {final_price} — "
                         "the price has to be settled first; not applied")
        r["flags"] = "; ".join(flags)
        rows.append(r)
        for v, role, div in derived(p, base):
            d = _row(line, p, v, role)
            if r["cost_status"] not in ("COST CHANGE", "same") or cost is None:
                d.update(cost_status="COST FLAGGED", flags="its pack's cost is flagged")
            elif not div:
                d.update(cost_status="COST FLAGGED", flags="cannot derive: the pack has no size / pack count")
            else:
                dc = cost / div
                st, note = _cost_status(_num(v.get("cost_price")), dc)
                if st == "COST CHANGE" and dc >= _num(v.get("price")) > 0:
                    st, note = "COST FLAGGED", f"new cost {_money(dc)} is at or above its price {d['siruk_price']}"
                d.update(new_cost=_money(dc), cost_status=st, flags=note)
            d["price_status"] = "by hand (per-kg / single-unit listing)"
            rows.append(d)
        if progress:
            progress(r)
    return rows


def fixes(rows):
    """{product id: {sku: patch}} — only the unflagged changes."""
    out = {}
    for r in rows:
        patch = {}
        if r["cost_status"] == "COST CHANGE":
            patch["cost_price"] = r["new_cost"]
        if r["price_status"] in ("RAISE", "LOWER"):
            patch["price"] = r["highest"]
            if r["source_url"]:
                patch["price_source_url"] = r["source_url"]
        if patch:
            out.setdefault(r["product_id"], {})[r["sku"]] = patch
    return out


def summary(rows):
    out = {}
    for r in rows:
        for k in (r["cost_status"], r["price_status"]):
            if k:
                out[k] = out.get(k, 0) + 1
    return out


def write_csv(rows, path=None):
    path = path or os.path.join(ROOT, "runs", datetime.date.today().isoformat(), "restock-check.csv")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader()
        w.writerows(rows)
    return path


def apply(pid, patches, dry_run=False):
    """Write {sku: patch} on one product, a guarded PUT per variant. → [WriteResult]."""
    return [products.update_variant(pid, sku, patch, dry_run=dry_run) for sku, patch in patches.items()]
