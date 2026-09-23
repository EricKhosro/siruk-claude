#!/usr/bin/env python3
"""Audit the PM's register (`csv/AllAngineProduct.xlsx`) against the live catalogue.

The register is the source of truth (user rule 2026-09-15). For every row it
answers four questions:

  1. **Does it exist?**  by article code against the catalogue snapshot.
  2. **Is our price right?**  only where the register fills `Վաճառքի գին`;
     that price outranks hafo. Blank means hafo/zoovet still decide.
  3. **Does it need a per-kg twin?**  the `Kg` column, when filled, is an
     explicit per-kilo rate (NOT `sale ÷ weight` — it runs 2-3% above), and
     means the row is ALSO sold loose by the kilo.
  4. **Does the product carry an attribute family?**  a product with none
     serves no filter facets at all (`reference/product-rules.md`).
  5. **Is the live variant complete?**  images (none / only hafo's watermarked
     placeholder, rule 7), our cost vs the register's, `product-weight` on a
     food pack (rule 8a), the variant-axis attributes its siblings carry
     (rule 9a), and whether a register price would be held (rule 2c: at or
     below cost, or a typo-level jump).
It also lists every live variant NO register row points at
(`register-extras.csv`) — on the site but not in the PM's stock list.

Reads the codes hafo recovery already resolved (`register-status.json`) but
re-resolves "live" against the CURRENT snapshot, so it never reports from a
stale read.

    scripts/register-audit.py [--run state/register] [--tolerance 1]
"""
import argparse, collections, csv, json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SNAP = os.path.join(ROOT, ".siruk-cache/catalogue-snapshot.json")
MEDIA_CACHE = os.path.join(ROOT, ".siruk-cache/media-cache.json")
HAFO_CDN = "d1b3l6j8a0ngef.cloudfront.net"     # hafo.am's image host
FOOD_FAMILIES = {1, 2, 3}                       # a pack weight is printed on these


def hafo_placeholder_ids():
    """Media ids uploaded from hafo's CDN — watermarked placeholders (rule 7a)."""
    try:
        m = json.load(open(MEDIA_CACHE))
    except (OSError, ValueError):
        return set()
    return {mid for u, mid in m.items() if HAFO_CDN in u and mid}


def num(x):
    try:
        return float(str(x).replace(",", "").strip())
    except (TypeError, ValueError):
        return None


def price(x):
    """A price the register left blank arrives as 0.0, not as an empty cell —
    and a zero price is never a real one, so both mean 'not given'."""
    v = num(x)
    return v if v else None


def pack_kg(name):
    """The pack weight the register prints in the Armenian name, in kg."""
    m = re.search(r"([\d]+[.,]?[\d]*)\s*կգ", name or "")
    if m:
        return float(m.group(1).replace(",", "."))
    m = re.search(r"([\d]+)\s*գ\b", name or "")
    return float(m.group(1)) / 1000 if m else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", default=os.path.join(ROOT, "state/register"))
    ap.add_argument("--max-ratio-cost", type=float, default=2.5)
    ap.add_argument("--max-ratio-current", type=float, default=2.0)
    ap.add_argument("--tolerance", type=float, default=1.0,
                    help="AMD difference below which a price counts as matching")
    a = ap.parse_args()

    status = json.load(open(os.path.join(a.run, "register-status.json")))
    snap = json.load(open(SNAP))

    by_sku, by_pid = {}, {}
    for p in snap.values():
        by_pid[int(p["id"])] = p
        for v in p["variants"]:
            if v.get("sku"):
                by_sku[re.sub(r"\s+", " ", str(v["sku"]).replace("\xa0", " ")).strip()] = (p, v)

    def find(code):
        if not code:
            return None
        # hafo writes some codes with a no-break space ("MG\xa0004807")
        code = re.sub(r"\s+", " ", code.replace("\xa0", " ")).strip()
        cands = [code, re.sub(r"(Tx|TXN)$", "", code), code.lstrip("0"),
                 code.zfill(6), code.zfill(5)]
        for c in cands:
            if c in by_sku:
                return by_sku[c]
        return None

    placeholders = hafo_placeholder_ids()
    matched_variants = set()
    rows = []
    for r in status:
        code = r.get("code")
        hit = find(code)
        p, v = hit if hit else (None, None)
        reg_sale = price(r.get("sale_price"))
        reg_kg = price(r.get("kg"))
        weight = pack_kg(r["name_hy"])
        hafo = r.get("hafo") or {}

        # --- what we charge today, normalised to a pack price -------------
        our_pack = our_rate = None
        if v:
            if v.get("pricing_type") == "per_kg":
                our_rate = price(v.get("price_per_kg"))
                if our_rate and num(v.get("weight")):
                    our_pack = our_rate * num(v["weight"])
            else:
                our_pack = price(v.get("price"))

        # --- price verdict -------------------------------------------------
        if not v:
            price_verdict, delta = "not-live", None
        elif reg_sale is None:
            price_verdict, delta = "no-register-price", None
        elif our_pack is None:
            price_verdict, delta = "no-live-price", None
        else:
            delta = round(our_pack - reg_sale, 2)
            price_verdict = "ok" if abs(delta) <= a.tolerance else "MISMATCH"

        # --- price source, per the rule chain ------------------------------
        if reg_sale is not None:
            price_source = "register"
        elif hafo.get("price_amd"):
            price_source = "hafo"
        else:
            price_source = "none-yet (hafo blank -> zoovet/sibling)"

        # --- per-kg twin ---------------------------------------------------
        twin = None
        if p:
            # the twin is `<sku>-KG` (make-perkg-twin.py / archive/plan-register-food.py); a
            # multi-flavour product carries one twin per flavour
            twin = next((vv for vv in p["variants"] if str(vv.get("sku")) == f"{(v or {}).get('sku')}-KG"), None)
            if twin is None:
                for vv in p["variants"]:
                    if vv.get("pricing_type") == "per_kg" and vv["id"] != (v or {}).get("id"):
                        twin = vv
                        break
        if reg_kg is None:
            twin_verdict = "not-sold-by-kg"
            # a row with NO Kg must not be per_kg at all
            if v and v.get("pricing_type") == "per_kg":
                twin_verdict = "WRONG-per_kg (register has no Kg)"
        elif not v:
            twin_verdict = "needs-twin (product not live)"
        elif twin:
            tr = price(twin.get("price_per_kg"))
            twin_verdict = ("ok" if tr and abs(tr - reg_kg) <= a.tolerance
                            else f"TWIN-RATE-WRONG ({tr} vs {reg_kg})")
        else:
            twin_verdict = "MISSING-twin"

        if v:
            matched_variants.add(v["id"])
            twin_v = twin if (twin and twin["id"] != v["id"]) else None
            if twin_v:
                matched_variants.add(twin_v["id"])

        # --- held prices (rule 2c): never written, listed for the PM ---------
        cost = num(r.get("cost")) or 0
        hold = ""
        if reg_sale is not None and cost and reg_sale <= cost:
            hold = "at/below cost"
        elif (reg_sale is not None and cost and our_pack
              and reg_sale >= a.max_ratio_cost * cost and reg_sale >= a.max_ratio_current * our_pack):
            hold = "typo-level jump"
        if hold and price_verdict == "MISMATCH":
            price_verdict = f"HELD ({hold})"

        # --- completeness of the live variant -------------------------------
        issues = []
        if v:
            ids = [i for i in (v.get("image_ids") or []) if i]
            n_img = v.get("images") or 0
            if not n_img:
                issues.append("no images")
            elif ids and all(i in placeholders for i in ids):
                issues.append("only hafo placeholder image")
            elif ids and ids[0] in placeholders:
                issues.append("hafo placeholder leads the gallery")
            live_cost = num(v.get("cost_price"))
            if cost and live_cost is not None and abs(live_cost - cost) > a.tolerance:
                issues.append(f"cost {live_cost:g} vs register {cost:g}")
            if (weight and p.get("attribute_family_id") in FOOD_FAMILIES
                    and not (v.get("attrs") or {}).get("product-weight")):
                issues.append("no product-weight (rule 8a)")
            if len(p["variants"]) > 1:
                have = set((v.get("attrs") or {}))
                sib = set()
                for vv in p["variants"]:
                    if vv["id"] != v["id"] and vv.get("pricing_type") == v.get("pricing_type"):
                        sib |= {k for k, val in (vv.get("attrs") or {}).items()
                                if val and val != (v.get("attrs") or {}).get(k)}
                axes = {"product-weight", "flavor", "texture", "size", "color-family",
                        "pet-weight-range", "toy-size"}
                missing = sorted((sib & axes) - have)
                if missing:
                    issues.append("missing axis attr: " + ",".join(missing))
            if p.get("is_discontinued"):
                issues.append("product marked discontinued")

        fam = p.get("attribute_family_id") if p else None
        rows.append({
            "reg_no": r["reg_no"],
            "name_hy": r["name_hy"],
            "code": code or "",
            "code_from": r.get("code_from") or "",
            "exists": bool(v),
            "product_id": p["id"] if p else "",
            "product": p["name"] if p else "",
            "variant_id": v["id"] if v else "",
            "variant": v["label"] if v else "",
            "pricing_type": (v or {}).get("pricing_type", ""),
            "cost": r.get("cost") or "",
            "reg_sale": reg_sale if reg_sale is not None else "",
            "our_pack_price": round(our_pack, 2) if our_pack is not None else "",
            "price_delta": delta if delta is not None else "",
            "price_verdict": price_verdict,
            "price_source": price_source,
            "hafo_price": hafo.get("price_amd") or "",
            "pack_kg": weight or "",
            "reg_kg_rate": reg_kg if reg_kg is not None else "",
            "our_kg_rate": round(our_rate, 2) if our_rate is not None else "",
            "twin_verdict": twin_verdict,
            "family_id": fam or "",
            "family": (p.get("attribute_family_name") or "") if p else "",
            "family_verdict": ("" if not p else ("ok" if fam else "MISSING-family")),
            "stock": (v or {}).get("stock", ""),
            "images": (v or {}).get("images", ""),
            "variant_issues": "; ".join(issues),
        })

    os.makedirs(a.run, exist_ok=True)
    out = os.path.join(a.run, "register-audit.csv")
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    json.dump(rows, open(os.path.join(a.run, "register-audit.json"), "w"),
              ensure_ascii=False, indent=1)

    # --- the PM-facing ledger, in the shape of runs/*/import-ledger.csv ----
    led = os.path.join(a.run, "register-ledger.csv")
    with open(led, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Product name", "Product code", "Exists",
                    "Register sale price", "Our price", "Price check",
                    "Sold per kg", "Per-kg variant", "Attribute family",
                    "Price source", "What is needed"])
        for r in rows:
            todo = []
            if not r["exists"]:
                todo.append("create product" if r["code"] else "identify article code")
            if r["price_verdict"] == "MISMATCH":
                todo.append(f"fix price ({r['our_pack_price']} -> {r['reg_sale']})")
            if r["twin_verdict"].startswith("MISSING"):
                todo.append(f"add per-kg variant @ {r['reg_kg_rate']}/kg")
            if r["twin_verdict"].startswith("TWIN-RATE"):
                todo.append(f"fix per-kg rate -> {r['reg_kg_rate']}")
            if r["twin_verdict"].startswith("WRONG-per_kg"):
                todo.append("switch to fixed pack price")
            if r["family_verdict"] == "MISSING-family":
                todo.append("assign attribute family")
            if r["price_verdict"].startswith("HELD"):
                todo.append(f"PM to confirm register price {r['reg_sale']} ({r['price_verdict']})")
            if r["variant_issues"]:
                todo.append(r["variant_issues"])
            w.writerow([r["name_hy"], r["code"], "TRUE" if r["exists"] else "FALSE",
                        r["reg_sale"], r["our_pack_price"], r["price_verdict"],
                        "yes" if r["reg_kg_rate"] != "" else "no",
                        r["twin_verdict"], r["family"] or r["family_verdict"],
                        r["price_source"], "; ".join(todo)])
    print(f"ledger -> {led}", file=sys.stderr)

    # --- live variants no register row points at ---------------------------
    extras = []
    for p in snap.values():
        for v in p["variants"]:
            if v["id"] not in matched_variants:
                extras.append({"product_id": p["id"], "product": p["name"], "brand": p.get("brand") or "",
                               "variant_id": v["id"], "variant": v["label"], "sku": v.get("sku"),
                               "pricing_type": v.get("pricing_type"),
                               "price": v.get("price") if v.get("pricing_type") != "per_kg" else v.get("price_per_kg"),
                               "stock": v.get("stock")})
    ext = os.path.join(a.run, "register-extras.csv")
    with open(ext, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["product_id", "product", "brand", "variant_id", "variant",
                                          "sku", "pricing_type", "price", "stock"])
        w.writeheader()
        w.writerows(extras)
    print(f"  live variants in no register row: {len(extras)} -> {ext}", file=sys.stderr)

    def c(key):
        return dict(collections.Counter(r[key] for r in rows))

    print(f"{len(rows)} register rows -> {out}", file=sys.stderr)
    print(f"  exists          : {sum(1 for r in rows if r['exists'])}", file=sys.stderr)
    print(f"  missing, coded  : {sum(1 for r in rows if not r['exists'] and r['code'])}", file=sys.stderr)
    print(f"  missing, no code: {sum(1 for r in rows if not r['code'])}", file=sys.stderr)
    print("  price  :", c("price_verdict"), file=sys.stderr)
    print("  per-kg :", {k: v for k, v in c("twin_verdict").items()}, file=sys.stderr)
    print("  family :", c("family_verdict"), file=sys.stderr)


main()
