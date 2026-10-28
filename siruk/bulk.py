"""Create many NEW products in one call — the port of scripts/bulk-create.py.

POST /api/admin/products/bulk (siruk-web 2026-10-01, ProductBulkCreateService):
  * body {"products": [<the body POST /products takes>, …]}, at most
    catalog.bulk_create_max (100) — over the cap the WHOLE batch is 422'd;
  * each item is validated and saved on its own; the response is 200 either way:
    {"data": [{"index", "status": "created", "id", "slug"} | {"index", "status":
    "failed", "errors"}], "summary": {"created", "failed"}};
  * a slug or SKU repeated inside one batch fails the later item;
  * translatable fields may be {en, hy, ru} maps (product name, the three variant
    texts) — so ru/hy ship WITH the create (CLAUDE.md 13);
  * creates only — an existing product still gets add_variant.

Every item gets create's pre-flight (name/slug/categories, sku + price, above
cost, product type, an image, no similar live product) and siruk.payload's
build; a refused item is reported and never sent. Chunked by config.json →
bulk.max_per_request; never auto-retried (a lost response would leave the
outcome unknown) — on a failed request each item's slug is looked up instead.
Created products are read back (skus, prices, image counts, ru/hy names).
"""
import copy, os

from siruk import client as _client
from siruk import config, products, seo
from siruk import payload as P

LOCALES = ("en", "hy", "ru")
NAME_MAX = 255
VTEXT = P.VTEXT
PayloadError = P.PayloadError


def _flag(value, var):
    return (os.environ.get(var) == "1") if value is None else bool(value)


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
    # an empty English text maps to {}, which the API refuses (2026-10-02): leave it out
    for v in p.get("variants") or []:
        for f in VTEXT:
            if f in v and not any((v[f] or {}).values()):
                del v[f]
    return p


def preflight(p, en_only, allow_below_cost=None, allow_no_image=None):
    """create's checks plus the translation-map checks. → (errors, warnings)."""
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
            + (" — translate after" if en_only else " (CLAUDE.md 13; en_only to translate later)"))
    vs = p.get("variants") or []
    if not vs or not all(v.get("sku") and (v.get("price") or 0) > 0 for v in vs):
        errs.append("every variant needs sku and price (the pack price)")
    below = [f"{v.get('sku')} sale={v.get('price')} cost={v.get('cost_price')}" for v in vs
             if (v.get("cost_price") or 0) > 0 and (v.get("price") or 0) <= v["cost_price"]]
    if below:
        msg = "sale price at or below cost (wrong hafo row or invented price): " + "; ".join(below)
        (warns if _flag(allow_below_cost, "ALLOW_BELOW_COST") else errs).append(msg)
    if not (p.get("attribute_family_id") or 0) > 0:
        errs.append("no attribute_family_id — every product needs its product type (CLAUDE.md 8b)")
    if not any(v.get("images") for v in vs) and not _flag(allow_no_image, "ALLOW_NO_IMAGE"):
        errs.append("no variant has any images")
    return errs, warns


def similar(name_en):
    return [(d["id"], d["name"], d["slug"]) for d in products.find(name_en, max_pages=1)]


def build(payload, en_only=False, seen_slugs=None, seen_skus=None, label="item", force=None,
          allow_below_cost=None, allow_no_image=None):
    """One payload → (body, warnings), or PayloadError. seen_* catch repeats within the batch."""
    seen_slugs = {} if seen_slugs is None else seen_slugs
    seen_skus = {} if seen_skus is None else seen_skus
    p = copy.deepcopy(payload)
    if p.get("_unreadable"):
        raise PayloadError(f"cannot read the payload: {p['_unreadable']}")
    if p.get("existing_id"):
        raise PayloadError(f"existing_id {p['existing_id']} — the bulk endpoint only creates; use add_variant")
    p = merge_translations(p)
    errs, warns = preflight(p, en_only, allow_below_cost, allow_no_image)
    slug = (p.get("slug") or "").lower()
    if slug in seen_slugs:
        errs.append(f"slug {slug} repeats {seen_slugs[slug]} in this batch")
    for v in p.get("variants") or []:
        s = (v.get("sku") or "").lower()
        if s in seen_skus:
            errs.append(f"sku {v.get('sku')} repeats {seen_skus[s]} in this batch")
    if errs:
        raise PayloadError("; ".join(errs))
    if not _flag(force, "FORCE"):
        hit = [h for h in similar(p["name"]["en"]) if h[0]]
        if hit:
            raise PayloadError("the catalogue already has a similar product " + ", ".join(f"{i} {n}" for i, n, _ in hit)
                               + " — same product → add_variant; force to create anyway")
    no_size = p.pop("_allow_no_size", False)  # card-import.py --queue: a sizeless card, for this item alone
    old = os.environ.get("ALLOW_NO_SIZE")
    if no_size:
        os.environ["ALLOW_NO_SIZE"] = "1"
    try:
        body = P.post_body(p, warnings=warns)
    finally:
        if no_size:
            if old is None:
                os.environ.pop("ALLOW_NO_SIZE", None)
            else:
                os.environ["ALLOW_NO_SIZE"] = old
    seen_slugs[slug] = label
    for v in body["variants"]:
        seen_skus[v["sku"].lower()] = label
    return body, warns


def read_back(pid, body):
    """Compare the live product with what was sent. → list of problems."""
    probs = []
    try:
        live = products.get(pid)
    except _client.ApiError as e:
        return [f"read-back failed: {e}"]
    if not live:
        return ["read-back failed: product not found"]
    lv = {v.get("sku"): v for v in live.get("variants") or []}
    for v in body["variants"]:
        got = lv.get(v["sku"])
        if not got:
            probs.append(f"variant {v['sku']} missing")
            continue
        if int(got.get("price") or 0) != int(v["price"]):
            probs.append(f"{v['sku']} price {got.get('price')} ≠ {v['price']}")
        if len(got.get("images") or []) != len(v.get("images") or []):
            probs.append(f"{v['sku']} {len(got.get('images') or [])} images ≠ {len(v.get('images') or [])} sent")
    if set(lv) != {v["sku"] for v in body["variants"]}:
        probs.append(f"live skus {sorted(lv)} ≠ sent")
    for lang in ("ru", "hy"):
        want = body["name"].get(lang)
        if want:
            got = products.get(pid, lang=lang).get("name")
            if got != want:
                probs.append(f"{lang} name reads back as {got!r}")
    return probs


def create(items, dry_run=False, en_only=False, force=None, allow_below_cost=None, allow_no_image=None,
           log=lambda m: None):
    """items: [(label, payload)]. → {label: {status, id?, slug?, errors?, warnings?, read_back?, body?}}.
    status: ready (dry run) | refused | created | failed | created? | unknown."""
    cfg = config.load()["bulk"]
    chunk = max(1, min(int(float(cfg["max_per_request"])), 100))
    timeout = float(cfg["timeout_seconds"])
    results, batch, seen_slugs, seen_skus = {}, [], {}, {}
    for label, payload in items:
        try:
            body, warns = build(payload, en_only, seen_slugs, seen_skus, label, force,
                                allow_below_cost, allow_no_image)
        except (PayloadError, ValueError) as e:
            results[label] = {"status": "refused", "errors": str(e)}
            log(f"✗ {label}: {e}")
            continue
        for w in warns:
            log(f"⚠ {label}: {w}")
        batch.append((label, body))
        results[label] = {"status": "ready", "name": body["name"]["en"], "variants": len(body["variants"]),
                          "warnings": warns, "body": body}
        log(f"✓ {label}: {body['name']['en']}  ({len(body['variants'])} variant(s))")
    if dry_run:
        return results

    for start in range(0, len(batch), chunk):
        part = batch[start:start + chunk]
        try:
            data = _client.default().request("POST", "/products/bulk", body={"products": [b for _, b in part]},
                                             retry=False, timeout=timeout) or {}
        except _client.ApiError as e:
            if e.status == 404:
                raise PayloadError("POST /products/bulk does not exist on this server — create one by one") from e
            data, err = None, str(e)
        else:
            err = "" if "data" in data else f"unexpected response {str(data)[:200]}"
        if not data or "data" not in data:
            log(f"✗ bulk request failed: {err} — looking up each slug")
            for label, b in part:
                hit = [h for h in similar(b["name"]["en"]) if h[2] == b["slug"]]
                results[label] = {"status": "created?" if hit else "unknown", "id": hit[0][0] if hit else None,
                                  "slug": b["slug"], "errors": f"request failed ({err}); check by hand"}
            break
        for item in data["data"]:
            label, b = part[item["index"]]
            if item["status"] == "created":
                probs = read_back(item["id"], b)
                results[label] = {"status": "created", "id": item["id"], "slug": item["slug"],
                                  "read_back": probs or "ok"}
                # a bulk body can't carry per-product meta (HasSeo reads the top-level request)
                try:
                    results[label]["seo"] = seo.apply_meta(item["id"], langs=seo.LANGS if not en_only else ("en",))
                    results[label]["image_alts"] = len(seo.set_image_alts(item["id"]))
                except (PayloadError, ValueError, _client.ApiError) as e:
                    results[label]["seo"] = f"failed: {e}"
                    log(f"⚠ {label}: SEO meta / image alt not set — {e}")
            else:
                results[label] = {"status": "failed", "errors": item.get("errors")}
                log(f"✗ {label}: {item.get('errors')}")
        s = data.get("summary") or {}
        log(f"batch {start // chunk + 1}: created {s.get('created')}, failed {s.get('failed')}")
    return results


def ok(results):
    return all(r["status"] in ("created", "ready") and r.get("read_back", "ok") == "ok" for r in results.values())
