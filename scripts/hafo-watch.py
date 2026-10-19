#!/usr/bin/env python3
"""hafo.am stock watch tower: show hafo's stock as "Ships from supplier" on variants we are out of.

User, 2026-10-15: hafo agreed we may show their availability on Siruk; they give no API, so we
read the same public listing their storefront uses (`/products/filter`, 40 per page, ~168 pages,
~3 min). Every row carries `qty_in_stock`. hafo refreshes it from their own system every 30 min,
at about :15 and :45 between ~09:00 and ~22:00 Yerevan, so this runs at :20 and :50, 07:00–24:00.

    scripts/hafo-watch.py crawl                 # snapshot hafo now and list what changed (read-only)
    scripts/hafo-watch.py link                  # plan: live variants ↔ hafo rows by EAN → runs/<date>/hafo-links-plan.csv
    scripts/hafo-watch.py link --apply [--only 12 13] [--limit 5]
                                                # create supplier "hafo", one supplier link per matched
                                                # variant, and switch those variants to out_of_stock_policy=dropship
    scripts/hafo-watch.py sync                  # crawl + list the stock/availability writes it would make
    scripts/hafo-watch.py sync --apply          # … and make them (the scheduled job, scripts/launchd/)
    scripts/hafo-watch.py off | on              # kill switch: deactivate / reactivate the whole supplier (1 call)
    scripts/hafo-watch.py status                # last crawl / sync, link counts

How Siruk shows it (siruk-web StockStatusService, read 2026-10-15): a variant with policy `dropship`
and an active supplier link with `dropship_allowed` is "Ships from supplier" (ru/hy translated) with
the supplier's `default_lead_days` (1) whenever OUR free stock is 0. Our own stock > 0 always wins, so
products we have are untouched. `sync` keeps each link's `stock_qty` = hafo's count and
`dropship_allowed` = (hafo count >= --min-qty).

Matching is by EAN only: our variant `barcode` == hafo row `barcode` (unique on hafo, checked
2026-10-15). The link stores hafo's article as `supplier_sku`, which is unique on hafo too, and sync
joins on it. Loose 1 kg variants (`-KG`, barcode = scale PLU) and discontinued products are never linked.

Safety:
  - an incomplete crawl (a failed page, < 98% of hafo's own product total, or < 90% of the last
    snapshot's rows) writes nothing;
  - a hafo row missing from one crawl is left as it was; only missing twice in a row counts as gone;
  - if one cycle would switch off more than 25% of the live links (min 10), nothing is written
    (a hafo-side glitch looks like that) unless --force;
  - if crawls keep failing for --stale-hours (2), the supplier is switched off, and the next good
    sync switches it back on. A manual `off` is never undone automatically.
Known gap (developer item): the server ignores `stock_qty` / `stock_updated_at` when deciding
availability, so `dropship_allowed` is the switch and a stopped job leaves the last state showing.

Files: .siruk-cache/hafo-watch/ (snapshot.json, snapshot-prev.json, state.json,
changes-YYYY-MM.csv, sync.log). Admin writes go through scripts/api.sh (paced, config.json);
the product PUT that sets the policy is built by siruk_payload.put_body.
"""
import argparse, csv, datetime as dt, gzip, json, math, os, subprocess, sys, time, urllib.request
from collections import Counter, defaultdict
from zoneinfo import ZoneInfo

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from siruk_payload import PayloadError, api, put_body  # noqa: E402

DIR = os.path.join(ROOT, ".siruk-cache", "hafo-watch")
SNAP = os.path.join(DIR, "snapshot.json")
PREV = os.path.join(DIR, "snapshot-prev.json")
STATE = os.path.join(DIR, "state.json")
LIVE = os.path.join(ROOT, ".siruk-cache", "live", "products")
TZ = ZoneInfo("Asia/Yerevan")
WINDOW = (7, 24)        # local hours [07:00, 24:00)
HAFO = ("https://hafo.am/products/filter?page={p}&order_by=order-desc&min_price=0&max_price=2000000"
        "&animal=&brand=&weight=&age=&type=&is_new=false&search=")
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")
SUPPLIER = {"code": "hafo", "name": "hafo.am", "currency": "AMD", "default_lead_days": 1,
            "notes": "Stock watch tower (scripts/hafo-watch.py): availability read from hafo.am every "
                     "30 min. Turn it off with `scripts/hafo-watch.py off` or the is_active switch."}


def now():
    return dt.datetime.now(TZ)


def log(msg):
    line = f"[{now():%Y-%m-%d %H:%M:%S}] {msg}"
    print(line, file=sys.stderr)
    os.makedirs(DIR, exist_ok=True)
    with open(os.path.join(DIR, "sync.log"), "a") as f:
        f.write(line + "\n")


def load(path, default=None):
    try:
        with open(path) as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def save(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(data, f, ensure_ascii=False)
    os.replace(tmp, path)


def norm_sku(s):
    return "".join(str(s or "").split())        # "MG\xa0013147" → "MG013147", "TX 040201" → "TX040201"


def digits(s):
    """The article's number without hafo's brand wrapping: "MS 009027" / "2329Tx" → "9027" / "2329"."""
    return "".join(c for c in str(s or "") if c.isdigit()).lstrip("0")


def same_article(hafo_sku, our_sku):
    """Information only (the EAN decides): Trixie's "TX 040201" is article 4020 + a variant digit."""
    h, o = digits(hafo_sku), digits(our_sku)
    return h == o or (norm_sku(hafo_sku).upper().startswith("TX") and h[:-1] == o)


def norm_ean(s):
    s = str(s or "").strip()
    return s if s.isdigit() and len(s) >= 8 else ""


# ------------------------------------------------------------------ hafo ----

def fetch(p, tries=4):
    for i in range(tries):
        try:
            req = urllib.request.Request(HAFO.format(p=p), headers={
                "User-Agent": UA, "Accept": "application/json", "Accept-Encoding": "gzip"})
            with urllib.request.urlopen(req, timeout=60) as r:
                b = r.read()
                if r.headers.get("Content-Encoding") == "gzip":
                    b = gzip.decompress(b)
            return json.loads(b)
        except Exception as e:
            if i == tries - 1:
                raise
            time.sleep(3 * (i + 1))
            log(f"  hafo page {p}: {e}; retry")


def crawl(sleep):
    """Every hafo row, keyed by normalised article. Returns (snapshot, problem or None)."""
    t0 = time.time()
    first = fetch(1)
    last, totals, items = first["last_page"], [first["total"]], {}
    for it in first["data"]:
        items[it["id"]] = it
    for p in range(2, last + 1):
        time.sleep(sleep)
        d = fetch(p)
        totals.append(d["total"])
        for it in d["data"]:
            items[it["id"]] = it
    rows = {}
    for it in items.values():
        for r in it.get("product_additional_information") or []:
            sku = norm_sku(r.get("sku"))
            if not sku:
                continue
            try:
                qty = float(r.get("qty_in_stock") or 0)
            except (TypeError, ValueError):
                qty = 0.0
            rows[sku] = {"sku": r.get("sku"), "barcode": norm_ean(r.get("barcode")), "qty": qty,
                         "in_stock": int(r.get("in_stock") or 0), "price": r.get("price"),
                         "name": r.get("name"), "url": f"https://hafo.am/products/{it.get('slug')}",
                         "row_id": r.get("id")}
    snap = {"fetched": now().isoformat(timespec="seconds"), "seconds": round(time.time() - t0),
            "pages": last, "products": len(items), "hafo_total": max(totals), "rows": rows}
    problem = None
    if len(items) < 0.98 * max(totals):
        problem = f"only {len(items)} of hafo's {max(totals)} products came back"
    prev = load(SNAP)
    if not problem and prev and len(rows) < 0.9 * len(prev["rows"]):
        problem = f"{len(rows)} rows vs {len(prev['rows'])} last time"
    snap["complete"] = problem is None
    return snap, problem


def diff(prev, cur):
    """(sku, change, before, after) for every row that differs between two snapshots."""
    out = []
    a, b = prev["rows"], cur["rows"]
    for sku, r in b.items():
        o = a.get(sku)
        if o is None:
            out.append((sku, "new", "", r["qty"]))
            continue
        if bool(o["in_stock"]) != bool(r["in_stock"]):
            out.append((sku, "back in stock" if r["in_stock"] else "sold out", o["qty"], r["qty"]))
        elif o["qty"] != r["qty"]:
            out.append((sku, "qty", o["qty"], r["qty"]))
        if o["price"] != r["price"]:
            out.append((sku, "price", o["price"], r["price"]))
    out += [(sku, "gone", a[sku]["qty"], "") for sku in a if sku not in b]
    return out


def record(prev, cur):
    changes = diff(prev, cur) if prev else []
    os.makedirs(DIR, exist_ok=True)
    path = os.path.join(DIR, f"changes-{now():%Y-%m}.csv")
    new = not os.path.exists(path)
    with open(path, "a", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["time", "hafo_sku", "barcode", "name", "change", "before", "after"])
        rows = {**prev["rows"], **cur["rows"]} if prev else cur["rows"]
        for sku, ch, before, after in changes:
            r = rows[sku]
            w.writerow([cur["fetched"], r["sku"], r["barcode"], r["name"], ch, before, after])
    return changes


def take_snapshot(sleep):
    """Crawl, and on a complete crawl rotate snapshot → snapshot-prev and log the changes."""
    snap, problem = crawl(sleep)
    if problem:
        return snap, problem, []
    prev = load(SNAP)
    changes = record(prev, snap)
    if prev:
        save(PREV, prev)
    save(SNAP, snap)
    return snap, None, changes


def fresh_snapshot(max_age_min, sleep):
    snap = load(SNAP)
    if snap and (now() - dt.datetime.fromisoformat(snap["fetched"])).total_seconds() < max_age_min * 60:
        return snap
    log("crawling hafo (no snapshot younger than %d min)" % max_age_min)
    snap, problem, _ = take_snapshot(sleep)
    if problem:
        raise SystemExit(f"hafo crawl incomplete: {problem}")
    return snap


def want(row, min_qty):
    qty = max(0, math.floor(row["qty"])) if row else 0
    return qty, bool(row and row["in_stock"] and qty >= min_qty)


# ----------------------------------------------------------------- Siruk ----

def get_supplier():
    for s in api("GET", "/suppliers").get("data") or []:
        if s.get("code") == SUPPLIER["code"]:
            return s
    return None


def ensure_supplier():
    s = get_supplier()
    if s:
        return s
    s = api("POST", "/suppliers", SUPPLIER)["data"]
    log(f"created supplier {s['id']} ({SUPPLIER['name']}, lead {SUPPLIER['default_lead_days']} day)")
    return s


def set_supplier_active(s, active):
    api("PUT", f"/suppliers/{s['id']}", {"code": s["code"], "name": s["name"], "is_active": active})


def get_links(sid):
    out, page = [], 1
    while True:
        d = api("GET", f"/suppliers/{sid}/products?perPage=100&page={page}")
        out += d.get("data") or []
        meta = d.get("meta") or {}
        if page >= (meta.get("last_page") or 1):
            return out
        page += 1


def our_variants():
    """Every live variant from the dump-products.py cache, with its product's flags."""
    ids = load(os.path.join(LIVE, "index.json"))
    if not ids:
        raise SystemExit("no live dump — run scripts/dump-products.py first")
    oldest, out = time.time(), []
    for pid in ids:
        path = os.path.join(LIVE, f"{pid}.json")
        p = load(path)
        if not p:
            continue
        oldest = min(oldest, os.path.getmtime(path))
        for v in p.get("variants") or []:
            out.append({"product_id": p["id"], "product": p.get("name"), "discontinued": bool(p.get("is_discontinued")),
                        "variant_id": v["id"], "sku": v.get("sku"), "barcode": norm_ean(v.get("barcode")),
                        "loose": str(v.get("sku") or "").upper().endswith("-KG") or v.get("sale_mode") == "weight",
                        "policy": v.get("out_of_stock_policy"), "price": v.get("price")})
    age_h = (time.time() - oldest) / 3600
    if age_h > 24:
        log(f"⚠ the live dump's oldest product is {age_h:.0f} h old — `scripts/dump-products.py --refresh` "
            f"for an exact plan (--apply re-reads every product anyway)")
    return out


# ------------------------------------------------------------------ link ----

def plan_links(snap, links):
    by_ean = {r["barcode"]: r for r in snap["rows"].values() if r["barcode"]}
    linked = {l["variant"]["id"]: l for l in links if l.get("variant")}
    ours = our_variants()
    live_eans = Counter(v["barcode"] for v in ours if v["barcode"] and not v["discontinued"] and not v["loose"])
    plan = []
    for v in ours:
        r = by_ean.get(v["barcode"])
        if v["discontinued"]:
            action = "skip: discontinued"
        elif v["loose"]:
            action = "skip: loose 1 kg"
        elif not v["barcode"]:
            action = "skip: no barcode"
        elif live_eans[v["barcode"]] > 1:
            action = "skip: barcode on several of our variants"
        elif not r:
            action = "skip: not on hafo"
        elif v["variant_id"] in linked:
            action = "linked" if v["policy"] == "dropship" else "policy"
        else:
            action = "link"
        plan.append({"action": action, "product_id": v["product_id"], "variant_id": v["variant_id"],
                     "our_sku": v["sku"], "product": v["product"], "barcode": v["barcode"],
                     "hafo_sku": r["sku"] if r else "", "hafo_name": r["name"] if r else "",
                     "hafo_qty": r["qty"] if r else "", "hafo_price": r["price"] if r else "",
                     "our_price": v["price"],
                     "sku_agrees": "yes" if r and same_article(r["sku"], v["sku"]) else "",
                     "policy_now": v["policy"], "hafo_url": r["url"] if r else ""})
    return plan


def apply_links(plan, snap, sid, links, min_qty, only, limit):
    linked = {l["variant"]["id"]: l for l in links if l.get("variant")}
    todo = defaultdict(list)
    for row in plan:
        if row["action"] in ("link", "policy") and (not only or row["product_id"] in only):
            todo[row["product_id"]].append(row)
    pids = list(todo)[:limit] if limit else list(todo)
    done = failed = new_links = 0
    for n, pid in enumerate(pids, 1):
        try:
            p = api("GET", f"/products/{pid}")["data"]
            if p.get("is_discontinued"):
                log(f"  {pid}: discontinued since the plan, skipped")
                continue
            fresh = {v["id"]: v for v in p["variants"]}
            targets = []
            for row in todo[pid]:
                v = fresh.get(row["variant_id"])
                if not v or norm_ean(v.get("barcode")) != row["barcode"]:
                    log(f"  {pid}/{row['variant_id']}: variant or barcode changed since the plan, skipped")
                    continue
                targets.append(row)
            for row in targets:
                if row["variant_id"] in linked:
                    continue
                hafo = snap["rows"].get(norm_sku(row["hafo_sku"]))
                qty, allow = want(hafo, min_qty)
                l = api("POST", f"/suppliers/{sid}/products", {
                    "product_variant_id": row["variant_id"], "supplier_sku": norm_sku(row["hafo_sku"]),
                    "is_preferred": True, "dropship_allowed": allow, "is_active": True})["data"]
                api("PUT", f"/supplier-products/{l['id']}/stock", {"stock_qty": qty})
                new_links += 1
            need = {row["variant_id"] for row in targets if fresh[row["variant_id"]].get("out_of_stock_policy") != "dropship"}
            if need:
                body = put_body(p)
                for bv in body["variants"]:
                    if bv.get("id") in need:
                        bv["out_of_stock_policy"] = "dropship"
                        bv["backorder_lead_days"] = None
                api("PUT", f"/products/{pid}", body)
                back = {v["id"]: v for v in api("GET", f"/products/{pid}")["data"]["variants"]}
                bad = [vid for vid in need if back.get(vid, {}).get("out_of_stock_policy") != "dropship"]
                if bad:
                    raise PayloadError(f"read-back: policy not dropship on {bad}")
            done += 1
            log(f"  {pid} ({n}/{len(pids)}): {len(targets)} variants linked, {len(need)} switched to dropship")
        except Exception as e:                          # keep going; report at the end
            failed += 1
            log(f"  {pid}: FAILED {e}")
        subprocess.run([os.path.join(ROOT, "scripts/pace.sh"), "product"], cwd=ROOT)
    log(f"link: {done} products done, {failed} failed, {new_links} new links")
    return failed


def cmd_link(a):
    snap = fresh_snapshot(60, a.sleep)
    s = get_supplier()
    links = get_links(s["id"]) if s else []
    plan = plan_links(snap, links)
    out = a.out or os.path.join(ROOT, "runs", f"{now():%Y-%m-%d}")
    os.makedirs(out, exist_ok=True)
    path = os.path.join(out, "hafo-links-plan.csv")
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(plan[0]))
        w.writeheader()
        w.writerows(sorted(plan, key=lambda r: (r["action"], r["product_id"], r["variant_id"])))
    for action, n in sorted(Counter(r["action"] for r in plan).items()):
        print(f"  {n:5d}  {action}")
    act = [r for r in plan if r["action"] in ("link", "policy")]
    print(f"{len(act)} variants on {len({r['product_id'] for r in act})} products to link → {path}")
    if a.apply:
        s = s or ensure_supplier()
        return apply_links(plan, snap, s["id"], links, a.min_qty, set(a.only or []), a.limit) and 1 or 0
    return 0


# ------------------------------------------------------------------ sync ----

def cmd_crawl(a):
    snap, problem, changes = take_snapshot(a.sleep)
    rows = snap["rows"].values()
    print(f"hafo {snap['fetched']}: {snap['products']} products, {len(snap['rows'])} rows, "
          f"{sum(1 for r in rows if r['in_stock'])} in stock ({snap['seconds']} s)")
    if problem:
        print(f"INCOMPLETE: {problem} — snapshot not saved")
        return 2
    for ch, n in sorted(Counter(c[1] for c in changes).items()):
        print(f"  {n:5d}  {ch}")
    return 0


def plan_sync(links, snap, prev, min_qty):
    writes, unseen = [], 0
    for l in links:
        if not l.get("is_active"):
            continue                                    # switched off by hand: leave it alone
        key = norm_sku(l.get("supplier_sku"))
        row = snap["rows"].get(key)
        if row is None and prev and key in prev["rows"]:
            unseen += 1                                 # missing once: wait for the next crawl
            continue
        qty, allow = want(row, min_qty)
        if l.get("stock_qty") != qty:
            writes.append(("stock", l, qty))
        if bool(l.get("dropship_allowed")) != allow:
            writes.append(("dropship", l, allow))
    return writes, unseen


def cmd_sync(a):
    t = now()
    if not a.any_time and not (WINDOW[0] <= t.hour < WINDOW[1]):
        return 0
    state = load(STATE, {})
    s = get_supplier()
    if not s:
        raise SystemExit("no hafo supplier yet — run `scripts/hafo-watch.py link --apply` first")
    try:
        snap, problem, changes = take_snapshot(a.sleep)
    except Exception as e:
        snap, problem, changes = None, f"crawl failed: {e}", []
    if problem:
        log(f"sync: {problem} — nothing written")
        last = state.get("last_good_crawl")
        stale = not last or (t - dt.datetime.fromisoformat(last)).total_seconds() > a.stale_hours * 3600
        if a.apply and stale and s.get("is_active") and state.get("off_by") != "manual":
            set_supplier_active(s, False)
            state["off_by"] = "auto"
            log(f"sync: no good crawl for {a.stale_hours} h — supplier switched OFF until the next good sync")
        save(STATE, state)
        return 2
    state["last_good_crawl"] = snap["fetched"]
    prev = load(PREV)
    links = get_links(s["id"])
    writes, unseen = plan_sync(links, snap, prev, a.min_qty)
    offs = sum(1 for kind, _, val in writes if kind == "dropship" and not val)
    ons = sum(1 for kind, _, val in writes if kind == "dropship" and val)
    active = sum(1 for l in links if l.get("is_active"))
    summary = (f"hafo {len(snap['rows'])} rows ({len(changes)} changes) · {active} links · "
               f"{ons} back on, {offs} off, {sum(1 for w in writes if w[0] == 'stock')} counts · {unseen} unseen")
    if offs > max(10, 0.25 * active) and not a.force:
        log(f"sync: {summary} — REFUSED: {offs} switch-offs at once looks like a hafo glitch (--force to apply)")
        save(STATE, state)
        return 3
    if not a.apply:
        for kind, l, val in writes:
            v = l.get("variant") or {}
            print(f"  {kind:8s} link {l['id']:5d}  {v.get('sku')}  {v.get('product_name')} → {val}")
        print(f"dry run: {summary}")
        save(STATE, state)
        return 0
    failed = 0
    for kind, l, val in writes:
        try:
            if kind == "stock":
                api("PUT", f"/supplier-products/{l['id']}/stock", {"stock_qty": val})
            else:
                api("PUT", f"/supplier-products/{l['id']}", {"dropship_allowed": val})
        except Exception as e:
            failed += 1
            log(f"  link {l['id']}: {kind} → {val} FAILED {e}")
    if state.get("off_by") == "auto" and not s.get("is_active"):
        set_supplier_active(s, True)
        state["off_by"] = None
        log("sync: good crawl again — supplier switched back ON")
    state["last_sync"] = now().isoformat(timespec="seconds")
    state["last_summary"] = summary
    save(STATE, state)
    log(f"sync: {summary}" + (f" · {failed} writes FAILED" if failed else ""))
    return 1 if failed else 0


def cmd_switch(a):
    s = get_supplier()
    if not s:
        raise SystemExit("no hafo supplier yet")
    on = a.cmd == "on"
    set_supplier_active(s, on)
    state = load(STATE, {})
    state["off_by"] = None if on else "manual"
    save(STATE, state)
    log(f"supplier {s['id']} switched {'ON' if on else 'OFF'} by hand")
    return 0


def cmd_status(a):
    state, snap = load(STATE, {}), load(SNAP)
    if snap:
        rows = snap["rows"].values()
        print(f"last snapshot   {snap['fetched']}  {len(snap['rows'])} rows, {sum(1 for r in rows if r['in_stock'])} in stock")
    for k in ("last_good_crawl", "last_sync", "last_summary", "off_by"):
        print(f"{k:15s} {state.get(k)}")
    s = get_supplier()
    if s:
        links = get_links(s["id"])
        print(f"supplier        {s['id']} {s['name']}  active={s.get('is_active')}  "
              f"links={len(links)}  showing={sum(1 for l in links if l.get('is_active') and l.get('dropship_allowed'))}")
    else:
        print("supplier        not created yet")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("cmd", choices=["crawl", "link", "sync", "off", "on", "status"])
    ap.add_argument("--apply", action="store_true", help="write to Siruk (default: plan only)")
    ap.add_argument("--min-qty", type=int, default=1, help="hafo count needed to show a variant (default 1)")
    ap.add_argument("--sleep", type=float, default=0.5, help="seconds between hafo pages")
    ap.add_argument("--stale-hours", type=float, default=2)
    ap.add_argument("--any-time", action="store_true", help="sync outside 07:00–24:00 Yerevan too")
    ap.add_argument("--force", action="store_true", help="apply a cycle the mass-switch-off brake refused")
    ap.add_argument("--only", type=int, nargs="+", help="link: just these product ids")
    ap.add_argument("--limit", type=int, help="link: at most this many products (a canary run)")
    ap.add_argument("--out", help="link: plan folder (default runs/<today>)")
    a = ap.parse_args()
    return {"crawl": cmd_crawl, "link": cmd_link, "sync": cmd_sync, "off": cmd_switch,
            "on": cmd_switch, "status": cmd_status}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
