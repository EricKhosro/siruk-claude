#!/usr/bin/env python3
"""Identify a CODELESS register row by name (CLAUDE.md rule 6, 2026-09-17).

For every register row without an article code, search hafo by its Armenian
name (no cost-equality gate — that is what `hafo-by-name-cost.py` adds) and
list EVERY `product_additional_information[]` row of every hit, with sku,
name, price, wholesale price and barcode, so a person can decide whether one
of them is the exact product (brand + line + flavour + pack — and size/colour
for accessories — all matching). The decision goes into
`state/register/identified-by-name.csv` and the code into
`state/register/match-overrides.json` (see --accept).

Step 0 (2026-10-01) is the **whole hafo catalogue**, matched locally
(`scripts/hafo-catalogue.py` caches it): hafo's search box finds some products
only in one script (the Мяу bags answer "Мяу", not "ՄՅԱՈՒ"), and 82 register
rows whose hafo row carries the register's exact name at our exact cost were
never returned by it. A row whose normalised name equals exactly one hafo
row's name, at equal cost, is tier `exact` — the same evidence every earlier
"accept" in identified-by-name.csv rests on — and `--accept-exact` logs it.
Everything else stays a candidate for a person.

Search queries are tried in every script: the Armenian name, plus each brand
form in `reference/name-aliases.json` (Latin, Russian, Ukrainian) and a
Russian rendering of the name for zoovet.am (Russian-language).

    scripts/identify-by-name.py --status state/register/register-status.json \
        --out state/register/hafo-name-candidates.json [--only 00011,00013]
    scripts/identify-by-name.py --accept-exact state/register/hafo-name-candidates.json \
        --log state/register/identified-by-name.csv --overrides state/register/match-overrides.json
    scripts/identify-by-name.py --accept state/register/identified-by-name.csv \
        --overrides state/register/match-overrides.json
"""
import argparse, csv, json, os, re, subprocess, sys, time, unicodedata, urllib.parse, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
API = ("https://hafo.am/products/filter?page=1&order_by=order-desc"
       "&min_price=0&max_price=200000&animal=&brand=&weight=&age=&type=&is_new=false&search=")
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")


ALIASES = json.load(open(os.path.join(ROOT, "reference/name-aliases.json")))
CATALOGUE = os.path.join(ROOT, ".siruk-cache/hafo-catalogue.json")


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


def brand_forms(name):
    """Every other-script spelling of a brand the name contains."""
    low = (name or "").lower()

    def has(form):  # whole word only: "ԳԱՎ" must not fire inside "կարգավորվող"
        return re.search(r"(?<![\w԰-֏])" + re.escape(form.lower()) + r"(?![\w԰-֏])", low)
    out = []
    for b in ALIASES["brands"]:
        if any(has(h) for h in b["hy"]) or any(has(f) for f in b["forms"]):
            out += [f for f in b["forms"] if not has(f)]
    return out


def russian(name):
    """A rough Russian query for a brandless Armenian name: glossary words in
    name order (longest Armenian phrase first), plus the pack numbers."""
    n = unicodedata.normalize("NFKC", name or "")
    hits = []
    for hy, ru in sorted(ALIASES["terms"].items(), key=lambda kv: -len(kv[0])):
        if len(hy) < 3:
            continue
        for m in re.finditer(re.escape(hy), n, re.I):
            if not any(a <= m.start() < b for a, b, _ in hits):
                hits.append((m.start(), m.end(), ru))
    words = [ru for _, _, ru in sorted(hits)]
    nums = re.findall(r"(\d+(?:[.,]\d+)?)\s*(կգ|գր|գ|մլ|սմ|հաբ|հատ)", n)
    words += [f"{v} {ALIASES['terms'].get(u, u)}" for v, u in nums[:1]]
    seen, out = set(), []
    for w in words:
        if w not in seen:
            seen.add(w)
            out.append(w)
    return " ".join(out[:5])


def cnorm(s):
    s = unicodedata.normalize("NFKC", s or "").lower()
    s = re.sub(r"[`՝’“”‘'«»]", "", s)
    s = re.sub(r"(\d)\s*(կգ|գր|գ|մլ|սմ|մմ|լ|հատ|հաբ)\b", r"\1\2", s)
    return re.sub(r"\s+", " ", re.sub(r"[^\w԰-֏.*]+", " ", s)).strip()


def ckey(s):
    return re.sub(r"[\s.,/*x]+", "", cnorm(s))


def stems(s):
    return {w[:5] for w in cnorm(s).split() if norm(w) not in STOP and not re.match(r"^[\d.*x]+", w)}


def load_catalogue():
    if not os.path.exists(CATALOGUE) or time.time() - os.path.getmtime(CATALOGUE) > 7 * 86400:
        subprocess.run([sys.executable, os.path.join(ROOT, "scripts/hafo-catalogue.py")], check=True)
    rows = json.load(open(CATALOGUE))["rows"]
    for c in rows:
        c["_key"], c["_st"] = ckey(c["name"]), stems(c["name"])
    return rows


def catalogue_candidates(r, cat):
    """Local match against the whole hafo catalogue: equal cost first, then
    the share of word stems (5-letter prefixes, so Armenian case endings
    don't matter). tier `exact` = same normalised name and same cost."""
    cost = float(r["cost"] or 0)
    k, st = ckey(r["name_hy"]), stems(r["name_hy"])
    out = []
    for c in cat:
        if abs(c["wholesale"] - cost) >= 0.5:
            continue
        j = len(st & c["_st"]) / max(1, len(st | c["_st"]))
        exact = c["_key"] == k
        if exact or j >= 0.25:
            out.append({k2: v for k2, v in c.items() if not k2.startswith("_")}
                       | {"cost_eq": True, "score": round(1.0 if exact else j, 3),
                          "tier": "exact" if exact else "cost+stems", "query": "catalogue"})
    out.sort(key=lambda c: -c["score"])
    return out[:12]


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
    forms = brand_forms(name_hy)
    ru = russian(name_hy)
    nemo_q = qs[:3] + forms[:2]
    zoo_q = lat[:2] + forms[:2] + ([f"{forms[0]} {ru}" if forms else ru] if ru else [])
    for shop, script, qlist in (("nemo.am", "nemo-lookup.py", nemo_q),
                                ("zoovet.am", "zoovet-lookup.py", zoo_q)):
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
    cat = load_catalogue()
    print(f"{len(rows)} codeless rows, {len(done)} already searched", file=sys.stderr)
    for n, r in enumerate(rows, 1):
        if r["reg_no"] in done:
            continue
        want = set(norm(r["name_hy"]).split())
        local = catalogue_candidates(r, cat)
        exact = [c for c in local if c["tier"] == "exact"]
        if len({c["sku"] for c in exact}) == 1:
            done[r["reg_no"]] = {"name_hy": r["name_hy"], "cost": r["cost"], "sale": r["sale_price"],
                                 "kg": r.get("kg"), "tier": "exact", "candidates": exact[:1]}
            continue
        cands, seen = list(local), {(c["url"].rsplit("/", 1)[-1], c["sku"]) for c in local}
        for q in queries(r["name_hy"]) + brand_forms(r["name_hy"])[:3]:
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
                             "kg": r.get("kg"), "tier": "ambiguous-exact" if exact else "candidates",
                             "candidates": cands[:12]}
        strong = any(c["cost_eq"] and c["score"] >= SHOP_SCORE for c in cands)
        if shops == "always" or (shops == "weak" and not strong):
            done[r["reg_no"]]["shop_candidates"] = shop_candidates(r["name_hy"], want)
        if n % 5 == 0:
            json.dump(done, open(out, "w"), ensure_ascii=False, indent=1)
            print(f"  {n}/{len(rows)}", file=sys.stderr)
    json.dump(done, open(out, "w"), ensure_ascii=False, indent=1)
    print(f"done -> {out}", file=sys.stderr)


def accept_exact(cands_path, log_path, overrides_path):
    """Log every tier-`exact` row (one hafo row, same name, same cost) as
    accepted, the way the earlier hand accepts were worded, and write its code
    to the overrides. A row already in the log is left alone."""
    cands = json.load(open(cands_path))
    logged = {r["Register row"] for r in csv.DictReader(open(log_path))} if os.path.exists(log_path) else set()
    new = []
    for reg, d in cands.items():
        if d.get("tier") != "exact" or reg in logged:
            continue
        c = d["candidates"][0]
        new.append({"Register row": reg, "Register name": d["name_hy"], "Source": "hafo catalogue",
                    "Hit url": c["url"], "Code": c["sku"], "Decision": "accept",
                    "Evidence": f"exact hafo row name, cost {c['wholesale']:g} equal, only such row; "
                                f"hafo price {c['price']}, barcode {c.get('barcode') or '-'} "
                                f"({time.strftime('%Y-%m-%d')}, catalogue match)"})
    if new:
        fields = ["Register row", "Register name", "Source", "Hit url", "Code", "Decision", "Evidence"]
        fresh = not os.path.exists(log_path)
        with open(log_path, "a", newline="") as f:
            w = csv.DictWriter(f, fields)
            if fresh:
                w.writeheader()
            w.writerows(new)
    print(f"{len(new)} exact rows logged to {log_path}", file=sys.stderr)
    accept(log_path, overrides_path)


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
    ap.add_argument("--accept-exact", help="a candidates file: log its tier-exact rows (needs --log, --overrides)")
    ap.add_argument("--log", default=os.path.join(ROOT, "state/register/identified-by-name.csv"))
    ap.add_argument("--overrides")
    a = ap.parse_args()
    if a.accept_exact:
        accept_exact(a.accept_exact, a.log, a.overrides)
        return
    if a.accept:
        accept(a.accept, a.overrides)
        return
    status = json.load(open(a.status))
    search(status, a.out, set(a.only.split(",")) if a.only else None, a.sleep,
           None if a.no_shops else a.shops)


main()
