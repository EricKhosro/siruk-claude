#!/usr/bin/env python3
"""Check worker cards against the hard rules before anything is written.

    scripts/validate-card.py --run runs/<date>                 # every cards/*.json
    scripts/validate-card.py --run runs/<date> 41116Tx 4020Tx  # just these codes

Card format: reference/card-schema.md. Reads rows.jsonl (scripts/prepare-run.py),
reference/types.json, reference/attribute-values.json, .siruk-cache/live-ids.json
and .siruk-cache/catalogue-snapshot.json. Prints one line per card —

    PASS <code>
    FAIL <code> <rule>: <what>          (one line per failure)
    WARN <code> <rule>: <what>          (does not block)

— then a summary, and writes runs/<date>/validation.json for the assembler.
Exit status 1 when any card fails. A FAIL line is meant to be fixed by the worker
that wrote the card (or the card turned into status "hold"), not argued with.
"""
import argparse, glob, importlib.util, json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _mod(name, file):
    spec = importlib.util.spec_from_file_location(name, os.path.join(ROOT, "scripts", file))
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m


prep = _mod("prep", "prepare-run.py")      # pack_of(), norm()
live_ids = _mod("live_ids", "live-ids.py")

SOURCE_KINDS = {"brand-site", "country-site", "barcode", "4lapy", "zoovet", "petshop", "hafo", "web"}
VISUAL = {"packaging", "color-family"}   # facts you see on the pack, not read in the text
TEXT_KEYS = ("about_this_item", "ingredient_information", "feeding_instructions")


def squash(s):
    """Compare quotes loosely: case, whitespace, quote marks and dashes don't matter."""
    s = (s or "").lower()
    s = re.sub(r"[‘’“”«»`'\"]", "", s)
    s = re.sub(r"[‐-―-]", "-", s)
    return re.sub(r"\s+", " ", s).strip()


def grams(label):
    p = prep.pack_of(label)
    if not p:
        return None
    return (round(p["kg"] * 1000, 3), "w") if p["kg"] is not None else \
        (round(p["value"] * (1000 if p["unit"] == "l" else 1), 3), "v")


def check(card, row, ctx):
    fails, warns = [], []
    F = lambda rule, msg: fails.append((rule, msg))
    W = lambda rule, msg: warns.append((rule, msg))
    types, menu, ids, snap, run = ctx["types"], ctx["menu"], ctx["ids"], ctx["snap"], ctx["run"]

    if row is None:
        F("R-code", "code not in rows.jsonl — only rows prepare-run.py produced can be imported")
        return fails, warns
    if card.get("status") == "hold":
        if not card.get("hold_reason"):
            F("R-hold", "status hold needs a hold_reason")
        return fails, warns
    if card.get("status") != "ready":
        F("R-status", "status must be 'ready' or 'hold'")
        return fails, warns
    if row["route"] not in ("ready", "needs-price"):
        F("R-route", f"row route is '{row['route']}' — not a worker row")
        return fails, warns

    # --- type / family
    t = types.get(card.get("type") or "")
    if row.get("type") and card.get("type") != row["type"]:
        if not card.get("type_reason"):
            F("R-type", f"type '{card.get('type')}' differs from the CSV's '{row['type']}' — add type_reason")
        else:
            W("R-type", f"type changed {row['type']} → {card.get('type')}: {card['type_reason'][:80]}")
    if not t:
        F("R-type", f"type '{card.get('type')}' is not in reference/types.json")
        return fails, warns
    fam = ids["families"].get(str(t["family"]))
    if not fam:
        F("R-family", f"family {t['family']} for {card['type']} does not exist live (rule 8b — create it first)")
        return fails, warns

    # --- brand
    bid = card.get("brand_id")
    if str(bid) not in ids["brands"]:
        F("R-brand", f"brand_id {bid} is not a live brand (/create-brand first)")
    elif not row.get("brand_id"):
        W("R-brand", f"prepare found no admin brand for '{row.get('brand_csv')}' — check {ids['brands'][str(bid)]} is right")
    elif bid != row["brand_id"]:
        W("R-brand", f"brand_id {bid} differs from prepare's {row['brand_id']} — say why in the report")

    # --- price (rules 1, 2, 2a, 2b, 5)
    cost = row.get("cost")
    pr = card.get("price") or {}
    src = pr.get("source")
    amount = None
    if src == "prepared":
        if row["route"] != "ready":
            F("R-price", "row has no prepared price (route needs-price) — use zoovet/nemo/sibling or hold")
        amount = (row.get("price") or {}).get("amount")
        if pr.get("amount") not in (None, amount):
            F("R-price", f"card amount {pr.get('amount')} != prepared {amount} — never change a prepared price")
    elif src in ("zoovet", "nemo"):
        if row["route"] != "needs-price":
            F("R-price", f"{src} is only for rows hafo cannot price (route is {row['route']})")
        amount = pr.get("amount")
        for k in ("amount", "url", "how_confirmed"):
            if not pr.get(k):
                F("R-price", f"{src} price needs '{k}'")
        if pr.get("url") and src not in pr["url"]:
            F("R-price", f"url is not a {src}.am page")
    elif src == "sibling":
        if row["route"] != "needs-price":
            F("R-price", f"sibling fallback is only for unpriced rows (route is {row['route']})")
        p = snap.get(str(card.get("existing_id")))
        sibs = [v for v in (p or {}).get("variants") or [] if v.get("cost_price") == cost]
        prices = {v.get("price") for v in sibs}
        if not p:
            F("R-price", "sibling price needs existing_id of a live product")
        elif not sibs:
            F("R-price", f"product {p['id']} has no variant with cost {cost:g} — no sibling (rule 2a)")
        elif len(prices) > 1:
            F("R-price", f"same-cost siblings disagree {sorted(prices)} — 'sibling prices differ', hold it")
        else:
            amount = prices.pop()
            if pr.get("amount") not in (None, amount):
                F("R-price", f"card amount {pr.get('amount')} != sibling price {amount}")
    else:
        F("R-price", "price.source must be prepared | zoovet | nemo | sibling")
    if amount is not None and cost is not None and float(amount) <= cost:
        F("R-price", f"price {amount} <= cost {cost:g} (rule 5) — wrong row, hold it")
    rp = row.get("price") or {}
    if t["pricing"] == "per_kg" and src == "prepared" and rp.get("pricing_type") != "fixed" \
            and not rp.get("weight"):
        F("R-perkg", "dry food needs a pack weight in kg for per_kg pricing — none was parsed")

    # --- name / label (rule 12, rule 9)
    name = (card.get("name") or "").strip()
    if not name:
        F("R-name", "name is empty")
    else:
        for b in ids["brands"].values():
            if len(b) > 2 and re.search(r"(?<![\w])" + re.escape(b.lower()) + r"(?![\w])", name.lower()):
                F("R-name", f"name contains the brand '{b}' — the storefront prints it already")
        if prep.pack_of(name):
            F("R-name", f"name carries a pack size ('{prep.pack_of(name)['raw']}') — it goes in the label")
        for axis in ("flavor", "color-family", "pet-weight-range"):
            for lab in (menu.get(axis) or {}).get("values", {}):
                if len(lab) > 3 and re.search(r"(?<![\w])" + re.escape(lab.lower()) + r"(?![\w])", name.lower()):
                    W("R-name", f"name carries {axis} '{lab}' — fine only while single-variant (rule 9)")
    if not (card.get("label") or "").strip():
        F("R-label", "label is empty")

    # --- existing product (rule 9)
    ex = card.get("existing_id")
    if ex is not None:
        p = snap.get(str(ex))
        if not p:
            F("R-exists", f"existing_id {ex} is not in the catalogue snapshot")
        else:
            if p.get("attribute_family_id") not in (None, t["family"]):
                F("R-exists", f"product {ex} is family {p.get('attribute_family_id')}, card type is family {t['family']}")
            if p.get("brand_id") != bid:
                F("R-exists", f"product {ex} is brand {p.get('brand_id')}, card says {bid}")
    else:
        own = (row.get("bench_live") or {}).get("product_id")
        same = [p["id"] for p in snap.values()
                if p["id"] != own and p.get("brand_id") == bid and (p.get("name") or "").strip().lower() == name.lower()]
        if same:
            F("R-exists", f"live product(s) {same} already have this name — set existing_id (rule 9)")

    # --- categories (rule 7)
    cats = card.get("category_ids") or []
    if not cats:
        F("R-cat", "category_ids is empty")
    species = set()
    for c in cats:
        info = ids["categories"].get(str(c))
        if not info:
            F("R-cat", f"category {c} does not exist (13 Accessories is not a product category)")
            continue
        if not info["leaf"]:
            F("R-cat", f"category {c} '{info['name']}' is a parent — leaves only")
        elif c not in t["leaves"]:
            F("R-cat", f"category {c} '{info['name']}' is not a {card['type']} leaf ({t['leaves']})")
        species.add({1: "dog", 8: "cat"}.get(info["species_root"]))
    sp = (row.get("species_csv") or "").lower()
    if sp in ("dog", "cat") and species - {sp}:
        W("R-cat", f"CSV says {sp} only but categories include {sorted(species - {sp})} — the pack must say both")

    # --- attributes (rule 8, 8a)
    attrs = card.get("attributes") or {}
    evidence = ctx["evidence"](card, row)
    for code, pick in attrs.items():
        if code not in fam["attrs"]:
            F("R-attr", f"'{code}' is not in family {t['family']} {fam['attrs']}")
            continue
        if not isinstance(pick, dict) or not pick.get("value"):
            F("R-attr", f"'{code}' needs {{value, quote}}")
            continue
        if pick["value"] not in (menu.get(code) or {}).get("values", {}):
            F("R-attr", f"'{code}' = '{pick['value']}' is not in the closed menu — null it and list it as wanted-but-missing")
        q = squash(pick.get("quote"))
        if not q and pick.get("basis") == "photo" and code in VISUAL:
            W("R-evidence", f"'{code}' = '{pick['value']}' read off the photo, not the text")
        elif not q:
            F("R-evidence", f"'{code}' has no quote" + (" (packaging/colour may use basis: photo)" if code in VISUAL else ""))
        elif q not in evidence:
            F("R-evidence", f"'{code}' quote not found in the evidence: \"{pick.get('quote')[:60]}\"")
    pack = row.get("pack")
    if pack and "product-weight" in fam["attrs"]:
        pw = (attrs.get("product-weight") or {}).get("value")
        if pack["kg"] is not None and not pw:
            F("R-weight", f"pack prints {pack['label']} — product-weight is required (rule 8a)")
        if pw and grams(pw) and grams(pack["label"]) and grams(pw) != grams(pack["label"]):
            F("R-weight", f"product-weight '{pw}' != the CSV pack {pack['label']} (CSV wins)")

    # --- images (rule 7)
    imgs = card.get("images") or []
    if not imgs:
        F("R-img", "no images — no product ships with an empty gallery")
    for u in imgs:
        if not re.match(r"https?://", str(u)):
            F("R-img", f"not a URL: {str(u)[:60]}")
    if len(imgs) == 1 and (card.get("source") or {}).get("kind") in ("brand-site", "country-site"):
        W("R-img", "one image from a brand site — was that really the whole gallery?")
    if imgs and card.get("first_image") != "packshot":
        W("R-img", "first image is not a clean packshot — goes on needs-packshot.csv")
    if imgs and all("hafo" in str(u) or "cloudfront" in str(u) for u in imgs):
        W("R-img", "hafo placeholder only — goes on needs-image.csv")

    # --- texts / source
    texts = ctx["texts"](card)
    if not (texts.get("about_this_item") or "").strip():
        F("R-text", "about_this_item is empty")
    s = card.get("source") or {}
    if s.get("kind") not in SOURCE_KINDS:
        F("R-source", f"source.kind must be one of {sorted(SOURCE_KINDS)}")
    if not s.get("url"):
        F("R-source", "source.url is missing")
    if s.get("kind") == "petshop" and imgs and any("petshop" in str(u) for u in imgs):
        F("R-img", "petshop.ru is for texts only, never its photos")
    return fails, warns


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", required=True)
    ap.add_argument("codes", nargs="*")
    ap.add_argument("--quiet", action="store_true", help="print FAIL lines and the summary only")
    a = ap.parse_args()
    run = a.run if os.path.isabs(a.run) else os.path.join(ROOT, a.run)

    rows = {}
    for line in open(os.path.join(run, "rows.jsonl")):
        r = json.loads(line)
        rows[r["code"]] = r
    types = {k: v for k, v in json.load(open(os.path.join(ROOT, "reference/types.json"))).items()
             if not k.startswith("_")}
    menu = json.load(open(os.path.join(ROOT, "reference/attribute-values.json")))
    snap_path = os.path.join(ROOT, ".siruk-cache/catalogue-snapshot.json")
    snap = json.load(open(snap_path)) if os.path.exists(snap_path) else {}

    def texts(card):
        if card.get("texts_file"):
            p = os.path.join(run, card["texts_file"])
            return json.load(open(p)) if os.path.exists(p) else {}
        return card.get("texts") or {}

    def evidence(card, row):
        parts = [row.get("name_csv")]
        h = row.get("hafo") or {}
        parts += [h.get("title_hy"), h.get("variant_name_hy"), h.get("meta_keywords")]
        parts += [texts(card).get(k) for k in TEXT_KEYS]
        if card.get("evidence_file"):
            p = os.path.join(run, card["evidence_file"])
            if os.path.exists(p):
                parts.append(open(p, encoding="utf-8", errors="replace").read())
        return squash("\n".join(x for x in parts if x))

    ctx = {"types": types, "menu": menu, "ids": live_ids.load(), "snap": snap, "run": run,
           "texts": texts, "evidence": evidence}

    files = sorted(glob.glob(os.path.join(run, "cards", "*.json")))
    files = [f for f in files if not f.endswith(".texts.json")]
    if a.codes:
        files = [os.path.join(run, "cards", f"{c}.json") for c in a.codes]
    result, n_fail, n_warn, n_hold = {}, 0, 0, 0
    for f in files:
        code = os.path.basename(f)[:-5]
        try:
            card = json.load(open(f))
        except Exception as e:
            print(f"FAIL {code} R-json: {e}")
            result[code] = {"status": "fail", "fails": [["R-json", str(e)]], "warns": []}
            n_fail += 1
            continue
        if card.get("code") != code:
            fails, warns = [("R-code", f"card code '{card.get('code')}' != file name")], []
        else:
            fails, warns = check(card, rows.get(code), ctx)
        status = "fail" if fails else ("hold" if card.get("status") == "hold" else "pass")
        result[code] = {"status": status, "fails": fails, "warns": warns}
        if fails:
            n_fail += 1
            for rule, msg in fails:
                print(f"FAIL {code} {rule}: {msg}")
        elif status == "hold":
            n_hold += 1
            if not a.quiet:
                print(f"HOLD {code} {card.get('hold_reason')}")
        elif not a.quiet:
            print(f"PASS {code}")
        if warns:
            n_warn += 1
            if not a.quiet:
                for rule, msg in warns:
                    print(f"WARN {code} {rule}: {msg}")

    pending = [c for c, r in rows.items() if r["route"] in ("ready", "needs-price") and c not in result]
    json.dump(result, open(os.path.join(run, "validation.json"), "w"), ensure_ascii=False, indent=1)
    print(f"validate-card: {len(result)} cards — {len(result) - n_fail - n_hold} pass, {n_fail} fail, "
          f"{n_hold} hold, {n_warn} with warnings; {len(pending)} worker rows have no card yet")
    sys.exit(1 if n_fail else 0)


if __name__ == "__main__":
    main()
