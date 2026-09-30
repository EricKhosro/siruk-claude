#!/usr/bin/env python3
"""Step 1 of a token-lean import: every deterministic decision for every CSV
row, made in code, written to files — so no model re-derives price, identity
routing, pack weight or "already live?" from the prose rules.

    scripts/prepare-run.py csv/products.csv [--run runs/<date>] [--limit N]
        [--only CODE,CODE] [--sale-column "<col>"] [--batch-size 15]
        [--reuse-hafo .siruk-cache/hafo-all.json] [--no-register]

Writes into the run folder:
  rows.jsonl      one JSON object per CSV row: the facts + the price decision + a route
  batches.json    worker batches (ready / needs-price rows, grouped by brand + type)
  not-found.csv   rows hafo cannot identify           (reference/pricing.md columns)
  holds.csv       rows stopped by a price guard        (at/below cost, suspect register jump)
  hafo.json       per-code hafo lookups (resumable; re-run skips codes already in it)
and prints ~10 summary lines, nothing per row.

Routes:
  live            the SKU is already a live variant — not imported (price sync is register-price-sync.py)
  ready           identified and priced, price > cost — a worker fills the card. A register
                  row with a `Kg` rate is priced fixed + a 1 kg loose twin (price.twin)
  needs-price     hafo confirmed the code but has no price for our row — a worker may try a
                  CONFIRMED zoovet/nemo price; the sibling fallback is checked by validate-card.py
  hold            priced, but a guard stopped it (rule 5 / rule 2c) — for the user
  not-found       code not confirmed on hafo — not-found.csv
  needs-identity  no article code — identify-by-name.py first (rule 6), not a worker job

Price chain (CLAUDE.md rules 1, 2, 2c, 3, 5): the user-named sale column (only with
--sale-column) > the PM's register (state/register/register-status.json) > hafo's own
variant row (price_source "variant"). Never the listing price, never arithmetic.
A register price at/below cost holds the row (rule 2c/5); a register price >= 2.5x cost
AND >= 2x the hafo price is held as SUSPECT (the rule's "2x current" — a new row has no
current price, so hafo's stands in; with no hafo price either, >= 2.5x cost alone holds it).
An unnamed filled `Sale Price (AMD)` column is
recorded (`csv_sale_unnamed`) but never used.
"""
import argparse, csv, importlib.util, json, os, re, sys, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))


def _mod(name, file):
    spec = importlib.util.spec_from_file_location(name, os.path.join(ROOT, "scripts", file))
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m


hafo = _mod("hafo", "hafo-lookup.py")
live_ids = _mod("live_ids", "live-ids.py")

# ---------------------------------------------------------------- helpers

COLS = {  # canonical -> accepted CSV headers (Shape C and the register-derived extracts)
    "code": ["Article Code", "Կոդ", "SKU"],
    "name": ["Product Name (as printed)", "Product Name", "Անվանում"],
    "brand": ["Brand", "Brand / Vendor"],
    "species": ["Species"],
    "category": ["Category"],
    "cost": ["Buy Price (AMD)", "Unit H/S Cost", "Cost"],
    "qty": ["Qty Received", "Qty"],
    "sale": ["Sale Price (AMD)"],
    "ean": ["EAN"],
    "brand_source": ["Brand Source"],
}


def col(row, key):
    for h in COLS[key]:
        if h in row and row[h] is not None:
            return row[h].strip()
    return ""


def num(x):
    x = re.sub(r"[^\d.]", "", str(x or "").replace(",", ""))
    try:
        return float(x) if x else None
    except ValueError:
        return None


UNIT = {"կգ": "kg", "kg": "kg", "գ": "g", "գր": "g", "g": "g", "gr": "g", "gm": "g",
        "մլ": "ml", "ml": "ml", "լ": "l", "l": "l", "lt": "l"}
PACK_RE = re.compile(r"(?:(\d+)\s*[xх×]\s*)?(\d+(?:[.,]\d+)?)\s*(կգ|kg|գր|գ|gr|gm|g|մլ|ml|լ|lt|l)(?![\w])",
                     re.I)


def pack_of(*texts):
    """First printed pack size in the texts. Volumes stay volumes (rule 12)."""
    for t in texts:
        for m in PACK_RE.finditer(t or ""):
            count, v, u = m.group(1), float(m.group(2).replace(",", ".")), UNIT[m.group(3).lower()]
            if u == "g" and v >= 1000:
                v, u = v / 1000, "kg"
            if u == "kg" and v < 1:
                v, u = v * 1000, "g"
            fmt = lambda f: ("%g" % round(f, 3))
            kg = v if u == "kg" else v / 1000 if u == "g" else None
            return {"value": v, "unit": u, "label": f"{fmt(v)} {u}", "kg": kg,
                    "count": int(count) if count else None, "raw": m.group(0)}
    return None


def norm(s):
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


BRAND_ALIAS = {"4թաթ": "Club 4 Paws", "4 թաթ": "Club 4 Paws", "club4paws": "Club 4 Paws", "մյաու": "Myau", "интеко": "Inteko", "moor": "Mooor", "kormell": "KorMell", "8in1": "8in1",
               "ivsanbernard": "Iv San Bernard", "mrfresh": "Mr. Fresh"}


def brand_id_of(name, brands):
    raw = (name or "").strip().lower()
    n = norm(name) or raw
    alias = BRAND_ALIAS.get(n) or BRAND_ALIAS.get(raw) or BRAND_ALIAS.get(raw.replace(" ", ""))
    for bid, bn in brands.items():
        if norm(bn) == n or (alias and bn == alias):
            return int(bid)
    return None


def latin_tokens(*texts):
    out = set()
    for t in texts:
        out |= {w.lower() for w in re.findall(r"[A-Za-z]{3,}", t or "")}
    return out - {"for", "and", "the", "with", "dog", "cat", "dogs", "cats", "trixie", "monge"}


# ---------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("csv")
    ap.add_argument("--run", default=os.path.join("runs", time.strftime("%Y-%m-%d")))
    ap.add_argument("--limit", type=int)
    ap.add_argument("--only")
    ap.add_argument("--sale-column", help="ONLY when the user named this column as the sale price for this run")
    ap.add_argument("--batch-size", type=int, default=15)
    ap.add_argument("--bench", action="store_true",
                    help="benchmark: route live rows as if new (never import a bench run)")
    ap.add_argument("--reuse-hafo", help="seed hafo lookups from an older batch file (prices may be stale)")
    ap.add_argument("--no-register", action="store_true", help="skip the PM register (rule 2c)")
    ap.add_argument("--register", default="state/register/register-status.json")
    a = ap.parse_args()

    run = os.path.join(ROOT, a.run) if not os.path.isabs(a.run) else a.run
    os.makedirs(run, exist_ok=True)
    rows = list(csv.DictReader(open(os.path.join(ROOT, a.csv) if not os.path.isabs(a.csv) else a.csv,
                                    encoding="utf-8-sig")))
    if a.sale_column and rows and a.sale_column not in rows[0]:
        sys.exit(f"--sale-column '{a.sale_column}' is not a column of {a.csv}")
    if a.only:
        keep = {c.strip() for c in a.only.split(",")}
        rows = [r for r in rows if col(r, "code") in keep]
    if a.limit:
        rows = rows[:a.limit]

    types = {k: v for k, v in json.load(open(os.path.join(ROOT, "reference/types.json"))).items()
             if not k.startswith("_")}
    cat2type = {c.lower(): t for t, v in types.items() for c in v["csv_category"]}
    ids = live_ids.load()
    brands = ids["brands"]

    snap_path = os.path.join(ROOT, ".siruk-cache/catalogue-snapshot.json")
    snap = json.load(open(snap_path)) if os.path.exists(snap_path) else {}
    if not snap:
        print("WARN no .siruk-cache/catalogue-snapshot.json — 'live' and existing-product hints are off "
              "(scripts/catalogue-snapshot.py)", file=sys.stderr)
    live_sku = {}
    for p in snap.values():
        for v in p.get("variants") or []:
            if v.get("sku"):
                live_sku.setdefault(norm(v["sku"]), []).append((p, v))

    def live_hit(code, brand_id, cost):
        """The live variant for our code. Admin often stores Trixie without its
        supplier suffix ('4020' for our '4020Tx'), so a suffix-stripped match is
        accepted — but only on the same brand, never across brands."""
        if norm(code) in live_sku:
            return live_sku[norm(code)][0]
        for suf in hafo.SUFFIXES:
            if code.lower().endswith(suf.lower()) and len(code) > len(suf):
                core = norm(code[:-len(suf)])
                for p, v in live_sku.get(core, []):
                    if brand_id and p.get("brand_id") == brand_id:
                        return p, v
                # Trixie's trailing variant digit (our 40261Tx is live as '4026'), the
                # same tolerance hafo-lookup.py applies — here only with an equal cost
                if suf.lower() == "tx" and core.isdigit() and len(core) > 3:
                    for p, v in live_sku.get(core[:-1], []):
                        if brand_id and p.get("brand_id") == brand_id and v.get("cost_price") == cost:
                            return p, v
        return None

    reg = {}
    if not a.no_register and os.path.exists(os.path.join(ROOT, a.register)):
        for r in json.load(open(os.path.join(ROOT, a.register))):
            if r.get("code") and r.get("sale_price"):
                reg[norm(r["code"])] = r

    hafo_path = os.path.join(run, "hafo.json")
    hcache = json.load(open(hafo_path)) if os.path.exists(hafo_path) else {}
    if a.reuse_hafo:
        for k, v in json.load(open(os.path.join(ROOT, a.reuse_hafo))).items():
            hcache.setdefault(k, v)

    out, n_lookups = [], 0
    for i, r in enumerate(rows, 1):
        code, name = col(r, "code"), col(r, "name")
        cost = num(col(r, "cost"))
        qty = num(col(r, "qty"))
        rec = {"row": i, "code": code, "name_csv": name, "brand_csv": col(r, "brand"),
               "species_csv": col(r, "species"), "category_csv": col(r, "category"),
               "cost": cost, "stock": 10 if qty in (None, 1) else int(qty),
               "type": cat2type.get(col(r, "category").lower()), "notes": []}
        if col(r, "sale") and not (a.sale_column and a.sale_column == "Sale Price (AMD)"):
            rec["csv_sale_unnamed"] = num(col(r, "sale"))

        if not code:
            rec["route"] = "needs-identity"
            rec["notes"].append("no article code — scripts/identify-by-name.py (rule 6)")
            out.append(rec); continue

        # hafo (resumable per code)
        h = hcache.get(code)
        if h is None:
            h = hafo.lookup(code, name)
            hcache[code] = h
            n_lookups += 1
            if n_lookups % 10 == 0:
                json.dump(hcache, open(hafo_path, "w"), ensure_ascii=False)
            time.sleep(0.8)
        confirmed = bool(h.get("hafo_id")) and h.get("confirmed", False)
        hafo_price = h.get("price_amd") if confirmed and h.get("price_source") == "variant" else None
        rec["hafo"] = {k: h.get(k) for k in ("hafo_id", "url", "title_hy", "brand", "price_source",
                                             "variant_name_hy", "wholesale_price_amd", "meta_keywords",
                                             "image")} if h.get("hafo_id") else None
        if rec["hafo"]:
            rec["hafo"]["confirmed"] = confirmed
            rec["hafo"]["price"] = hafo_price
            rec["hafo"]["barcodes"] = (h.get("barcodes") or [])[:4]
        rec["pack"] = pack_of(name, h.get("variant_name_hy") if confirmed else None)

        # brand: the CSV's article-code-suffix brand is reliable (csv-formats.md);
        # else hafo's product_maker; else the CSV; hafo's title/meta match last.
        bid_csv = brand_id_of(rec["brand_csv"], brands)
        bid_hafo = brand_id_of(h.get("brand"), brands) if confirmed else None
        # a brand printed in the invoice name itself also beats hafo, whose product_maker
        # can be wrong (hafo says TRIXIE for "MONGE Grain Free Vet Dermatosis", 014507)
        csv_strong = col(r, "brand_source").startswith("article-code suffix") or bool(
            bid_csv and re.search(r"(?<![\w])" + re.escape(brands[str(bid_csv)].lower()) + r"(?![\w])", name.lower()))
        hafo_strong = h.get("brand_source") == "product_maker"
        if csv_strong and bid_csv:
            rec["brand_id"] = bid_csv
        elif hafo_strong and bid_hafo:
            rec["brand_id"] = bid_hafo
        else:
            rec["brand_id"] = bid_csv or bid_hafo
        if bid_hafo and bid_csv and bid_hafo != bid_csv:
            rec["notes"].append(f"brand conflict: CSV says {brands[str(bid_csv)]}, hafo says "
                                f"{brands[str(bid_hafo)]} — took {brands[str(rec['brand_id'])]}; "
                                "check the EAN prefix")

        # already live?
        hit = live_hit(code, rec["brand_id"], cost)
        if hit and a.bench:
            # benchmark: treat the live row as new, keep what is live for the comparison,
            # and keep its own product out of the worker's hints
            p, v = hit
            rec["bench_live"] = {"product_id": p["id"], "variant_id": v["id"]}
        elif hit:
            p, v = hit
            rec.update(route="live", live={"product_id": p["id"], "product": p["name"],
                                           "sku": v.get("sku"), "variant_id": v["id"],
                                           "price": v.get("price"), "price_per_kg": v.get("price_per_kg")})
            out.append(rec); continue
        if not rec["brand_id"]:
            rec["notes"].append(f"brand not in admin: CSV '{rec['brand_csv']}', hafo '{h.get('brand') or ''}'"
                                " — /create-brand before this row")

        # price chain
        reg_r = reg.get(norm(code))
        reg_price = float(reg_r["sale_price"]) if reg_r else None
        price, source = None, None
        if a.sale_column:
            price, source = num(r.get(a.sale_column)), "user-column"
        if price is None and reg_price is not None:
            if cost is not None and reg_price <= cost:
                rec.update(route="hold", hold_reason=f"register price {reg_price:g} <= cost {cost:g} "
                           f"(rule 5; hafo has {hafo_price or 'none'})")
            elif cost and hafo_price and reg_price >= 2.5 * cost and reg_price >= 2 * hafo_price:
                rec.update(route="hold", hold_reason=f"SUSPECT register {reg_price:g}: "
                           f"{reg_price / cost:.1f}x cost, {reg_price / hafo_price:.1f}x hafo {hafo_price:g}")
            elif cost and not hafo_price and reg_price >= 2.5 * cost:
                # rule 2c's second test ("2x current") has nothing to compare against on a
                # new row hafo can't price — hold rather than trust a 2.5x+ jump blind
                # (the 85 g pouch at 8,300 against a 225 cost was exactly this)
                rec.update(route="hold", hold_reason=f"SUSPECT register {reg_price:g}: "
                           f"{reg_price / cost:.1f}x cost and no hafo price to cross-check")
            else:
                price, source = reg_price, "register"
        if price is None and "route" not in rec and hafo_price:
            price, source = float(hafo_price), "hafo"
        if reg_price and hafo_price and abs(reg_price - hafo_price) / hafo_price > 0.25:
            rec["notes"].append(f"register {reg_price:g} vs hafo {hafo_price:g} differ >25% — pack size?")
        rec["price"] = {"amount": price, "source": source, "hafo": hafo_price, "register": reg_price}

        t = types.get(rec["type"] or "")
        reg_kg = num(reg_r.get("kg")) if reg_r else None
        if price and reg_kg:
            # The register sells this bag BOTH ways (make-perkg-twin.py): the pack at its
            # fixed register price, plus a 1 kg loose twin at the register's own Kg rate —
            # never price ÷ weight (the Kg rate carries a deliberate 2-3% premium).
            rec["price"]["pricing_type"] = "fixed"
            twin = {"sku": f"{code}-KG", "pricing_type": "per_kg", "price_per_kg": reg_kg, "weight": 1,
                    "product-weight": "1 kg"}
            if rec["pack"] and rec["pack"]["kg"] and cost:
                twin["cost_price"] = round(cost / rec["pack"]["kg"])
                if reg_kg <= twin["cost_price"]:
                    twin = None
                    rec["notes"].append(f"register Kg rate {reg_kg:g} <= cost per kg — no loose twin (rule 5)")
            else:
                twin = None
                rec["notes"].append("register has a Kg rate but no kg pack weight was parsed — no loose twin")
            rec["price"]["twin"] = twin
        elif price and t and t["pricing"] == "per_kg":
            if rec["pack"] and rec["pack"]["kg"]:
                rec["price"]["pricing_type"] = "per_kg"
                rec["price"]["weight"] = rec["pack"]["kg"]
                rec["price"]["price_per_kg"] = round(price / rec["pack"]["kg"], 2)
            else:
                rec["notes"].append("dry food without a printed kg pack weight — per_kg needs one")
        elif price:
            rec["price"]["pricing_type"] = "fixed"

        if "route" not in rec:
            if price is not None and cost is not None and price <= cost:
                rec.update(route="hold", hold_reason=f"wrong row: {source} price {price:g} <= cost {cost:g} (rule 5)")
            elif price is not None:
                rec["route"] = "ready"
                if not confirmed:
                    rec["notes"].append("hafo does not confirm this code — identity rests on the "
                                        "register/code; check the pack matches")
            elif confirmed:
                rec["route"] = "needs-price"
                rec["why_no_price"] = "on hafo, size missing" if h.get("price_source") == "UNRESOLVED" else "not on hafo"
            else:
                rec["route"] = "not-found"

        # hints for the worker: same-brand live products that share words, and same-cost siblings
        if rec["route"] in ("ready", "needs-price") and rec["brand_id"]:
            toks = latin_tokens(name, (rec["hafo"] or {}).get("meta_keywords"))
            scored = []
            sib = []
            own = (rec.get("bench_live") or {}).get("product_id")
            for p in snap.values():
                if p.get("brand_id") != rec["brand_id"] or p["id"] == own:
                    continue
                s = len(toks & latin_tokens(p.get("name"), p.get("slug", "").replace("-", " ")))
                if s:
                    scored.append((s, p["id"], p["name"]))
                for v in p.get("variants") or []:
                    if cost is not None and v.get("cost_price") == cost:
                        sib.append({"product_id": p["id"], "product": p["name"], "sku": v.get("sku"),
                                    "label": v.get("label"), "price": v.get("price")})
            rec["existing_candidates"] = [{"id": i_, "name": n_} for s_, i_, n_ in sorted(scored, reverse=True)[:5]]
            if rec["route"] == "needs-price":
                rec["sibling_candidates"] = sib[:6]
        out.append(rec)
        if i % 50 == 0:
            print(f"  {i}/{len(rows)}", file=sys.stderr, flush=True)

    json.dump(hcache, open(hafo_path, "w"), ensure_ascii=False)
    with open(os.path.join(run, "rows.jsonl"), "w") as f:
        for rec in out:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    # worker batches: one brand + type per batch, so a worker learns one site once
    groups = {}
    for rec in out:
        if rec["route"] in ("ready", "needs-price"):
            key = (brands.get(str(rec["brand_id"])) or rec["brand_csv"] or "?", rec["type"] or "unknown")
            groups.setdefault(key, []).append(rec["code"])
    batches, n = [], 0
    for (b, t), codes in sorted(groups.items()):
        for j in range(0, len(codes), a.batch_size):
            n += 1
            batches.append({"id": f"b{n:03d}", "brand": b, "type": t, "codes": codes[j:j + a.batch_size]})
    json.dump(batches, open(os.path.join(run, "batches.json"), "w"), ensure_ascii=False, indent=1)

    today = time.strftime("%Y-%m-%d")
    with open(os.path.join(run, "not-found.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Article Code", "Brand", "Invoice Name (as printed)", "Buy Price (AMD)", "Qty",
                    "hafo candidate", "Why", "Date"])
        for rec in out:
            if rec["route"] == "not-found":
                hc = rec.get("hafo") or {}
                w.writerow([rec["code"], rec["brand_csv"], rec["name_csv"], rec["cost"], rec["stock"],
                            hc.get("url") or "", "no article-code match on hafo", today])
    with open(os.path.join(run, "holds.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Article Code", "Brand", "Invoice Name (as printed)", "Buy Price (AMD)",
                    "Register price", "hafo price", "Why held", "Date"])
        for rec in out:
            if rec["route"] == "hold":
                p = rec.get("price") or {}
                w.writerow([rec["code"], rec["brand_csv"], rec["name_csv"], rec["cost"],
                            p.get("register") or "", p.get("hafo") or "", rec["hold_reason"], today])

    from collections import Counter
    c = Counter(rec["route"] for rec in out)
    src = Counter((rec.get("price") or {}).get("source") for rec in out if rec["route"] == "ready")
    rel = os.path.relpath(run, ROOT)
    print(f"prepare-run: {len(out)} rows -> {rel}/rows.jsonl  ({n_lookups} new hafo lookups)")
    print("  routes: " + ", ".join(f"{k} {v}" for k, v in c.most_common()))
    print("  ready priced by: " + ", ".join(f"{k} {v}" for k, v in src.most_common()))
    print(f"  worker batches: {len(batches)} in {rel}/batches.json")
    print(f"  untyped rows (CSV Category empty — worker decides): "
          f"{sum(1 for x in out if x['route'] in ('ready', 'needs-price') and not x['type'])}")
    print(f"  brand missing in admin: {sum(1 for x in out if any('brand not in admin' in n for n in x['notes']))}"
          f", brand conflicts: {sum(1 for x in out if any('brand conflict' in n for n in x['notes']))}")


if __name__ == "__main__":
    main()
