#!/usr/bin/env python3
"""Fill barcode / accounting_code / price_source_url on live variants (siruk-web bc49dfbf).

    scripts/backfill-variant-codes.py --run runs/<date>            # plan only (default) — no writes
    scripts/backfill-variant-codes.py --run runs/<date> --apply    # PUT the planned changes
    … --apply --only 1200 1201                                     # just these products
    … --overwrite                                                  # also replace a different live value

The user's rules (2026-10-12):
  barcode          pack → its EAN; 1 kg loose variant ("<bag sku>-KG") → its 5-digit scale PLU
  accounting_code  the ArmSoft good code (a bag and its 1 kg variant share one)
  price_source_url the page the sale price came from (hafo / zoovet / nemo); left empty when the
                   price came from a register file or a user decision
Sources: final/siruk-source-of-truth.csv (Barcode, PLU, Source link — keyed by the /dp/<variant id>
in "Siruk link"), Scale/scale-codes-per-kg.csv (siruk_variant_id → good_code) and csv/all-xml-scale.xml
(the ArmSoft target — every barcode is checked against its good's barcodes there).
Live state: the raw GETs from scripts/dump-products.py (.siruk-cache/live/products/).

Writes <run>/variant-codes-plan.csv (one row per live variant) and variant-codes-report.md.
--apply re-reads each product fresh, builds the body with siruk_payload.put_body (nothing else
changes), sets the codes on the planned variants, PUTs, and reads back. A value already set live is
kept unless --overwrite; a conflict is reported, never silently replaced. Discontinued products
are skipped (product 678 is a retired copy of 1102 with the same EANs).
"""
import csv, json, os, re, subprocess, sys, time
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from siruk_payload import CODE_KEYS, PRICE_SOURCE_HOSTS, PayloadError, api, check_codes, put_body  # noqa: E402

LIVE = os.path.join(ROOT, ".siruk-cache", "live", "products")
TRUTH = os.path.join(ROOT, "final", "siruk-source-of-truth.csv")
SCALE = os.path.join(ROOT, "Scale", "scale-codes-per-kg.csv")
XML = os.path.join(ROOT, "csv", "all-xml-scale.xml")


def is_loose(v):
    return str(v.get("sku") or "").upper().endswith(("-KG", "-100G"))


def price_url(link):
    link = (link or "").strip()
    if any(re.match(rf"https?://(www\.)?{re.escape(h)}/", link) for h in PRICE_SOURCE_HOSTS):
        return link
    return None


def armsoft_goods():
    """good code → set of every barcode ArmSoft holds for it (main + per unit)."""
    xml = open(XML, encoding="utf-8-sig").read()
    out = {}
    for g in re.findall(r"<Goods[ >].*?</Goods>", xml, re.S):
        code = re.search(r"<Code>([^<]*)</Code>", g).group(1)
        out[code] = set(re.findall(r"<BarCode>([^<]+)</BarCode>", g))
    return out


def load_sources():
    truth = {}
    for r in csv.DictReader(open(TRUTH, encoding="utf-8-sig")):
        m = re.search(r"/dp/(\d+)", r["Siruk link"])
        if m:
            truth[int(m.group(1))] = r
    scale = {int(r["siruk_variant_id"]): r for r in csv.DictReader(open(SCALE, encoding="utf-8-sig"))
             if r["siruk_variant_id"]}
    return truth, scale


def plan(products, truth, scale, goods, overwrite):
    rows = []
    for p in products:
        if p.get("is_discontinued"):    # a retired duplicate must not hold a live variant's barcode
            continue
        by_sku = {v["sku"]: v for v in p["variants"]}
        for v in p["variants"]:
            vid, loose = v["id"], is_loose(v)
            t, s = truth.get(vid), scale.get(vid)
            want, why = {}, []
            if t:
                want["barcode"] = (t["PLU"] if loose else t["Barcode"]) or None
                want["price_source_url"] = price_url(t["Source link"])
                if loose and not t["PLU"]:
                    why.append("1 kg variant has no PLU in the source of truth")
                if not loose and t["PLU"] and not t["Barcode"]:
                    why.append("PLU on a pack variant (SKU has no -KG) — barcode left empty")
                    want["barcode"] = None
            else:
                why.append("not in final/siruk-source-of-truth.csv")
            code = s["good_code"] if s else None
            if not code and loose:                      # a 1 kg variant shares its bag's ArmSoft good
                bag = by_sku.get(v["sku"][:-3])
                if bag and scale.get(bag["id"]):
                    code, _ = scale[bag["id"]]["good_code"], why.append("ArmSoft code taken from its bag")
            if not code:
                why.append("no ArmSoft good code")
            want["accounting_code"] = code
            if code and want.get("barcode") and code in goods and want["barcode"] not in goods[code]:
                if loose:   # the PLU is assigned (source of truth) but ArmSoft lacks the good's 303 unit yet
                    why.append(f"ArmSoft good {code} has no 303 unit / PLU {want['barcode']} yet — add it via /armsoft-sync")
                else:
                    why.append(f"barcode {want['barcode']} is not on ArmSoft good {code} — left empty")
                    want["barcode"] = None
            if code and code not in goods:
                why.append(f"ArmSoft good {code} is not in csv/all-xml-scale.xml")
            if t and int(float(t["Price (AMD)"] or 0)) != int(float(v.get("price") or 0)):
                why.append(f"price differs: live {v.get('price')} vs truth {t['Price (AMD)']} (truth may be stale)")
            change, conflict = {}, []
            for k in CODE_KEYS:
                new, cur = want.get(k), v.get(k)
                if not new or new == cur:
                    continue
                if cur and not overwrite:
                    conflict.append(f"{k}: live {cur} ≠ planned {new}")
                    continue
                change[k] = new
            errs, warns = check_codes({"sku": v["sku"], **{k: want.get(k) for k in CODE_KEYS}})
            if errs:
                why += errs
                change = {}
            rows.append({"product_id": p["id"], "product": p["name"], "variant_id": vid, "sku": v["sku"],
                         "label": v.get("label") or v.get("name"), "loose_1kg": "yes" if loose else "",
                         **{f"live_{k}": v.get(k) or "" for k in CODE_KEYS},
                         **{f"new_{k}": want.get(k) or "" for k in CODE_KEYS},
                         "change": ",".join(change), "_change": change,
                         "conflict": "; ".join(conflict), "notes": "; ".join(why + warns)})
    return rows


def dup_barcodes(rows):
    seen = defaultdict(set)
    for r in rows:
        bc = r["new_barcode"] or r["live_barcode"]
        if bc:
            seen[bc].add(r["product_id"])
    return {bc: sorted(ps) for bc, ps in seen.items() if len(ps) > 1}


def apply(rows, only):
    todo = defaultdict(dict)
    for r in rows:
        if r["_change"] and (not only or r["product_id"] in only):
            todo[r["product_id"]][r["variant_id"]] = r["_change"]
    done = failed = 0
    for pid, changes in todo.items():
        try:
            t0 = time.time()
            p = api("GET", f"/products/{pid}")["data"]
            body = put_body(p)
            fresh = {v["id"]: v for v in p["variants"]}
            for vid, ch in changes.items():     # someone set a value since the plan: keep theirs
                for k in list(ch):
                    cur = fresh.get(vid, {}).get(k)
                    if cur == ch[k]:            # already there (a resumed run)
                        ch.pop(k)
                    elif cur not in (None, ""):
                        print(f"  {pid}/{vid}: {k} changed live since the plan — kept", file=sys.stderr)
                        ch.pop(k)
                if vid not in fresh:
                    print(f"  {pid}/{vid}: variant gone since the plan — skipped", file=sys.stderr)
            changes = {vid: ch for vid, ch in changes.items() if ch and vid in fresh}
            if not changes:
                continue
            for bv in body["variants"]:
                bv.update(changes.get(bv.get("id"), {}))
            t1 = time.time()
            api("PUT", f"/products/{pid}", body)
            t2 = time.time()
            back = {v["id"]: v for v in api("GET", f"/products/{pid}")["data"]["variants"]}
            bad = [(vid, k) for vid, ch in changes.items() for k, val in ch.items()
                   if (back.get(vid) or {}).get(k) != val]
            if bad:
                raise PayloadError(f"read-back mismatch {bad}")
            done += 1
            print(f"  {pid}: {sum(len(c) for c in changes.values())} fields on {len(changes)} variants "
                  f"(get+build {t1 - t0:.1f}s, put {t2 - t1:.1f}s, read-back {time.time() - t2:.1f}s)", file=sys.stderr)
        except Exception as e:                          # keep going; report at the end
            failed += 1
            print(f"  {pid}: FAILED {e}", file=sys.stderr)
        subprocess.run([os.path.join(ROOT, "scripts/pace.sh"), "product"], cwd=ROOT)
    print(f"applied {done} products, {failed} failed", file=sys.stderr)


def main(argv):
    if "--run" not in argv:
        sys.exit(__doc__)
    run = os.path.join(ROOT, argv[argv.index("--run") + 1])
    os.makedirs(run, exist_ok=True)
    only = {int(a) for a in argv[argv.index("--only") + 1:] if a.isdigit()} if "--only" in argv else set()
    ids = json.load(open(os.path.join(LIVE, "index.json")))
    missing = [i for i in ids if not os.path.exists(os.path.join(LIVE, f"{i}.json"))]
    if missing:
        sys.exit(f"{len(missing)} products not dumped yet — run scripts/dump-products.py first")
    products = [json.load(open(os.path.join(LIVE, f"{i}.json"))) for i in ids]
    truth, scale = load_sources()
    rows = plan(products, truth, scale, armsoft_goods(), "--overwrite" in argv)
    live_vids = {r["variant_id"] for r in rows}
    stale = sorted(set(truth) - live_vids)
    dups = dup_barcodes(rows)

    cols = [k for k in rows[0] if not k.startswith("_")]
    with open(os.path.join(run, "variant-codes-plan.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    c = Counter()
    for r in rows:
        for k in r["_change"]:
            c[k] += 1
    note_kinds = Counter(re.sub(r"[\d]{4,}|live \S+|truth \S+", "…", n).strip()
                         for r in rows for n in r["notes"].split("; ") if n)
    rep = [f"# Variant code backfill — plan", "",
           f"{len(products)} live products, {len(rows)} variants.", "",
           "| field | variants to set |", "|---|---|"] + [f"| {k} | {c[k]} |" for k in CODE_KEYS] + [
           "", f"Products touched: {len({r['product_id'] for r in rows if r['_change']})}",
           f"Conflicts kept (live value differs, no --overwrite): {sum(1 for r in rows if r['conflict'])}",
           f"Source-of-truth variant ids no longer live: {len(stale)} {stale[:20]}",
           f"Barcodes on more than one product: {len(dups)}"] + [f"- {bc}: products {ps}" for bc, ps in list(dups.items())[:30]] + [
           "", "## Notes by kind", ""] + [f"- {n}: {k}" for n, k in note_kinds.most_common()]
    open(os.path.join(run, "variant-codes-report.md"), "w").write("\n".join(rep) + "\n")
    print("\n".join(rep))
    if "--apply" in argv:
        apply(rows, only)


if __name__ == "__main__":
    main(sys.argv[1:])
