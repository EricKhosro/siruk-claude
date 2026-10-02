#!/usr/bin/env python3
"""Create many NEW products in one call: POST /api/admin/products/bulk (siruk-web 2026-10-01,
ProductController::bulkStore → ProductBulkCreateService).

    scripts/bulk-create.py <payload.json>… [--dry-run] [--en-only] [--out results.json]

What the endpoint does (read from siruk-web, not guessed):
  * body {"products": [<the same body POST /products takes>, …]}, at most
    catalog.bulk_create_max (100) items — over the cap the WHOLE batch is 422'd;
  * every item is validated by ProductRequest and saved on its own: a bad item fails
    alone and leaves nothing behind, the response is 200 either way —
    {"data": [{"index", "status": "created", "id", "slug"} | {"index", "status": "failed",
    "errors": {field: [msg]}}], "summary": {"created", "failed"}};
  * a slug or SKU repeated inside one batch fails the later item;
  * translatable fields may be an object keyed en/hy/ru — product `name` (≤ 255 per
    locale) and each variant's about_this_item / ingredient_information /
    feeding_instructions. `en` is required for the name. So ru/hy ship WITH the create
    and set-translation.py is not needed afterwards (CLAUDE.md 13).
  * creates only — a row for an existing product still goes through add-variant.sh.

Payload files are create-product.sh payloads (shape: scripts/siruk_payload.py). The
translations go either inline (name / variant texts as {en, ru, hy}) or as a
"translations" block in set-translation.py's file shape:
  "translations": {"ru": {"name": "…", "variants": {"<sku>": {"about_this_item": "…"}}},
                   "hy": {…}}
A product missing its ru or hy name is refused unless --en-only (then translate after
with set-translation.py, as before).

Every item gets create-product.sh's pre-flight first (name/slug/categories, sku + price,
price above cost unless ALLOW_BELOW_COST=1, product type, at least one image unless
ALLOW_NO_IMAGE=1, no similar live product unless FORCE=1) and the siruk_payload.py body
build; a refused item is reported and never sent. Batches are chunked by
config.json → bulk.max_per_request. The POST is not auto-retried (a lost response would
leave the outcome unknown); on a failed request every item's slug is looked up instead.
Created products are read back and checked (skus, prices, image counts, ru/hy names),
then scripts/verify-translations.py --only <ids> reports the locales.
Results (file → status, id, slug, errors) go to --out, default .siruk-cache/bulk-<time>.json.
Exit 1 if any item failed or was refused.
"""
import json, os, subprocess, sys, time, urllib.parse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from siruk_payload import PayloadError, VTEXT, post_body  # noqa: E402

LOCALES = ("en", "hy", "ru")
NAME_MAX = 255


def cfg():
    try:
        c = json.load(open(os.environ.get("SIRUK_CONFIG") or os.path.join(ROOT, "config.json")))
    except (OSError, ValueError):
        c = {}
    b = c.get("bulk") or {}
    return int(b.get("max_per_request") or 25), int(b.get("timeout_seconds") or 300)


def api(method, path, body=None, lang=None, retries=None, timeout=None):
    """→ (http status, parsed JSON or None, stderr tail). Never raises on HTTP errors."""
    env = dict(os.environ)
    if lang:
        env["SIRUK_LANG"] = lang
    if retries is not None:
        env["SIRUK_RETRIES"] = str(retries)
    if timeout:
        env["SIRUK_TIMEOUT"] = str(timeout)
    args = [os.path.join(ROOT, "scripts/api.sh"), method, path] + (["-"] if body is not None else [])
    r = subprocess.run(args, input=json.dumps(body, ensure_ascii=False) if body is not None else None,
                       capture_output=True, text=True, cwd=ROOT, env=env)
    code = 0
    for line in r.stderr.splitlines():
        if line.startswith("HTTP "):
            try:
                code = int(line.split()[1])
            except ValueError:
                pass
    data = None
    i = r.stdout.find("{")
    if i >= 0:
        try:
            data = json.loads(r.stdout[i:])
        except ValueError:
            pass
    return code, data, r.stderr.strip()[-600:]


def locale_map(value):
    if isinstance(value, dict):
        return dict(value)
    return {"en": value} if value not in (None, "") else {}


def merge_translations(p):
    """Fold a set-translation-shaped "translations" block into {en, ru, hy} maps."""
    tr = p.pop("translations", None) or {}
    p["name"] = locale_map(p.get("name"))
    for v in p.get("variants") or []:
        for f in VTEXT:
            if f in v:
                v[f] = locale_map(v[f])
    for lang, t in tr.items():
        if lang not in ("ru", "hy"):
            raise PayloadError(f"translations: unknown locale '{lang}' (ru, hy)")
        if t.get("name"):
            p["name"][lang] = t["name"]
        by_sku = {v.get("sku"): v for v in p.get("variants") or []}
        for sku, texts in (t.get("variants") or {}).items():
            if sku not in by_sku:
                raise PayloadError(f"translations.{lang}: sku {sku} is not a variant of this product")
            for f, text in texts.items():
                if f not in VTEXT:
                    raise PayloadError(f"translations.{lang}.{sku}: '{f}' is not translatable (only {VTEXT})")
                m = by_sku[sku].setdefault(f, {})
                if not isinstance(m, dict):
                    m = by_sku[sku][f] = locale_map(m)
                m[lang] = text
    # an empty English text ("" / null — a collar has no feeding guide) maps to {}, and the
    # API refuses an empty object ("must be an object keyed by en, hy, ru", 2026-10-02):
    # leave such a field out of the create instead.
    for v in p.get("variants") or []:
        for f in VTEXT:
            if f in v and not any((v[f] or {}).values()):
                del v[f]
    return p


def preflight(p, en_only):
    """create-product.sh's checks plus the translation-map checks. Returns (errors, warnings)."""
    errs, warns = [], []
    name = p.get("name") or {}
    if not (name.get("en") and p.get("slug") and isinstance(p.get("category_ids"), list) and p["category_ids"]):
        errs.append("needs name (with en), slug and a non-empty category_ids array")
    for k, m in [("name", name)] + [(f"variants.{v.get('sku')}.{f}", v[f])
                                    for v in p.get("variants") or [] for f in VTEXT if isinstance(v.get(f), dict)]:
        bad = set(m) - set(LOCALES)
        if bad:
            errs.append(f"{k}: unknown locale(s) {sorted(bad)} — only {LOCALES}")
        if k == "name":
            for lang, s in m.items():
                if s and len(s) > NAME_MAX:
                    errs.append(f"name.{lang} is {len(s)} characters (max {NAME_MAX})")
    missing = [lang for lang in ("ru", "hy") if not name.get(lang)]
    for v in p.get("variants") or []:
        for f in VTEXT:
            m = v.get(f) or {}
            if isinstance(m, dict) and m.get("en"):
                missing += [f"{v.get('sku')}.{f}.{lang}" for lang in ("ru", "hy") if not m.get(lang)]
    if missing:
        (warns if en_only else errs).append(
            f"no translation for {', '.join(missing[:6])}{' …' if len(missing) > 6 else ''}"
            + (" — run set-translation.py after" if en_only else " (CLAUDE.md 13; --en-only to translate later)"))
    vs = p.get("variants") or []
    if not vs or not all(v.get("sku") and (v.get("price") or 0) > 0 for v in vs):
        errs.append("every variant needs sku and price (the pack price)")
    below = [f"{v.get('sku')} sale={v.get('price')} cost={v.get('cost_price')}" for v in vs
             if (v.get("cost_price") or 0) > 0 and (v.get("price") or 0) <= v["cost_price"]]
    if below:
        msg = "sale price at or below cost (wrong hafo row or invented price): " + "; ".join(below)
        (warns if os.environ.get("ALLOW_BELOW_COST") == "1" else errs).append(msg)
    if not (p.get("attribute_family_id") or 0) > 0:
        errs.append("no attribute_family_id — every product needs its product type (CLAUDE.md 8b)")
    if not any(v.get("images") for v in vs) and os.environ.get("ALLOW_NO_IMAGE") != "1":
        errs.append("no variant has any images (ALLOW_NO_IMAGE=1 to override)")
    return errs, warns


def similar(name_en):
    code, data, _ = api("GET", "/products?search=" + urllib.parse.quote(name_en))
    return [(d.get("id"), d.get("name"), d.get("slug")) for d in (data or {}).get("data") or []]


def build(path, en_only, seen_slugs, seen_skus):
    p = json.load(open(path))
    if p.get("existing_id"):
        raise PayloadError(f"existing_id {p['existing_id']} — the bulk endpoint only creates; use add-variant.sh")
    p = merge_translations(p)
    errs, warns = preflight(p, en_only)
    slug = (p.get("slug") or "").lower()
    if slug in seen_slugs:
        errs.append(f"slug {slug} repeats {seen_slugs[slug]} in this batch")
    for v in p.get("variants") or []:
        s = (v.get("sku") or "").lower()
        if s in seen_skus:
            errs.append(f"sku {v.get('sku')} repeats {seen_skus[s]} in this batch")
    if errs:
        raise PayloadError("; ".join(errs))
    if os.environ.get("FORCE") != "1":
        hit = [h for h in similar(p["name"]["en"]) if h[0]]
        if hit:
            raise PayloadError("the catalog already has a similar product " + ", ".join(f"{i} {n}" for i, n, _ in hit)
                               + " — same product → add-variant.sh; FORCE=1 to create anyway")
    no_size = p.pop("_allow_no_size", False)  # card-import.py --queue: a sizeless card (ALLOW_NO_SIZE for it alone)
    old = os.environ.get("ALLOW_NO_SIZE")
    if no_size:
        os.environ["ALLOW_NO_SIZE"] = "1"
    try:
        body = post_body(p)                   # product-type checks; raises PayloadError
    finally:
        if no_size:
            os.environ.pop("ALLOW_NO_SIZE", None) if old is None else os.environ.__setitem__("ALLOW_NO_SIZE", old)
    seen_slugs[slug] = os.path.basename(path)
    for v in body["variants"]:
        seen_skus[v["sku"].lower()] = os.path.basename(path)
    return body, warns


def read_back(pid, body):
    """Compare the live product with what was sent. → list of problems."""
    probs = []
    _, d, err = api("GET", f"/products/{pid}")
    live = (d or {}).get("data") or {}
    if not live:
        return [f"read-back failed: {err[-200:]}"]
    lv = {v.get("sku"): v for v in live.get("variants") or []}
    for v in body["variants"]:
        got = lv.get(v["sku"])
        if not got:
            probs.append(f"variant {v['sku']} missing"); continue
        if int(got.get("price") or 0) != int(v["price"]):
            probs.append(f"{v['sku']} price {got.get('price')} ≠ {v['price']}")
        if len(got.get("images") or []) != len(v.get("images") or []):
            probs.append(f"{v['sku']} {len(got.get('images') or [])} images ≠ {len(v.get('images') or [])} sent")
    if set(lv) != {v["sku"] for v in body["variants"]}:
        probs.append(f"live skus {sorted(lv)} ≠ sent")
    for lang in ("ru", "hy"):
        want = body["name"].get(lang)
        if want:
            _, t, _ = api("GET", f"/products/{pid}", lang=lang)
            if ((t or {}).get("data") or {}).get("name") != want:
                probs.append(f"{lang} name reads back as {((t or {}).get('data') or {}).get('name')!r}")
    return probs


def main(argv):
    files = [a for a in argv if not a.startswith("--")]
    out = argv[argv.index("--out") + 1] if "--out" in argv else \
        os.path.join(ROOT, ".siruk-cache", time.strftime("bulk-%Y%m%d-%H%M%S.json"))
    files = [f for f in files if f != out]
    dry, en_only = "--dry-run" in argv, "--en-only" in argv
    if not files:
        sys.exit(__doc__)
    chunk, timeout = cfg()
    chunk = max(1, min(chunk, 100))

    results, batch, seen_slugs, seen_skus = {}, [], {}, {}
    for f in files:
        try:
            body, warns = build(f, en_only, seen_slugs, seen_skus)
        except (PayloadError, ValueError, OSError) as e:
            results[f] = {"status": "refused", "errors": str(e)}
            print(f"✗ {f}: {e}", file=sys.stderr)
            continue
        for w in warns:
            print(f"⚠ {f}: {w}", file=sys.stderr)
        batch.append((f, body))
        print(f"✓ {f}: {body['name']['en']}  ({len(body['variants'])} variant(s))")

    if dry:
        print(f"\ndry run: {len(batch)} ready, {len(results)} refused — nothing sent")
        json.dump({f: b for f, b in batch}, open(out, "w"), ensure_ascii=False, indent=1)
        print(f"bodies → {out}")
        sys.exit(1 if results else 0)

    for start in range(0, len(batch), chunk):
        part = batch[start:start + chunk]
        code, data, err = api("POST", "/products/bulk", {"products": [b for _, b in part]},
                              retries=1, timeout=timeout)
        if code == 404 or "Cannot POST" in err:
            sys.exit("POST /products/bulk does not exist on this server yet (siruk-web 6af3eeb9 not deployed) — "
                     "use card-import.py --write / create-product.sh per product")
        if code != 200 or not data or "data" not in data:
            print(f"✗ bulk request failed (HTTP {code}): {err[-300:]} — looking up each slug", file=sys.stderr)
            for f, b in part:
                hit = [h for h in similar(b["name"]["en"]) if h[2] == b["slug"]]
                results[f] = {"status": "created?" if hit else "unknown", "id": hit[0][0] if hit else None,
                              "slug": b["slug"], "errors": f"request failed HTTP {code}; check by hand"}
            break
        for item in data["data"]:
            f, b = part[item["index"]]
            if item["status"] == "created":
                results[f] = {"status": "created", "id": item["id"], "slug": item["slug"], "sent": b}
            else:
                results[f] = {"status": "failed", "errors": item.get("errors")}
                print(f"✗ {f}: {json.dumps(item.get('errors'), ensure_ascii=False)}", file=sys.stderr)
        s = data.get("summary") or {}
        print(f"batch {start // chunk + 1}: created {s.get('created')}, failed {s.get('failed')}")

    ids = []
    for f, r in results.items():
        if r["status"] != "created":
            continue
        probs = read_back(r["id"], r.pop("sent"))
        r["read_back"] = probs or "ok"
        ids.append(str(r["id"]))
        print(f"  product {r['id']}  {r['slug']}  " + ("read-back ok" if not probs else "⚠ " + "; ".join(probs)))
    for r in results.values():
        r.pop("sent", None)
    json.dump(results, open(out, "w"), ensure_ascii=False, indent=1)
    print(f"results → {out}")
    if ids:
        print("\n# translations (CLAUDE.md 13 — report from this, not from what was sent):")
        subprocess.run([sys.executable, os.path.join(ROOT, "scripts/verify-translations.py"), "--only", ",".join(ids)],
                       cwd=ROOT)
    bad = [f for f, r in results.items() if r["status"] != "created" or r.get("read_back") != "ok"]
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main(sys.argv[1:])
