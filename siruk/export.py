"""The catalogue export (siruk-web 4207c624 + efbf2d33): every product, one record per
variant, product columns repeated, in id order.

    GET /products/export?lang=en|ru|hy[&updated_since=<date>][&search=…][&dates=d/m/Y,d/m/Y]
        [&format=json]   → {"data": [record, …]}   (default format: an .xlsx download)

Records carry what the product form shows (SingleProductResource) in that locale:
product_id, product_name, slug, brand_id, brand, category_ids, categories,
product_type, is_discontinued, is_on_sale, is_best_seller, variant_id, sku,
variant_name, size, options, barcode, accounting_code, sale_mode, measure_type,
content, pack_count, price, compare_at_price, cost_price, unit_price,
stock_status, available, is_purchasable, price_source_url, image_ids,
image_urls, about_this_item (plain), about_this_item_html, ingredients,
feeding_instructions, updated_at. A product with no variants is one record
with the variant columns empty. `updated_since` also catches variant and
translation edits (their rows' updated_at); `dates` filters on created_at.

audit() turns one export into the catalogue-wide checks a run ends with: below
cost, missing codes, empty galleries, no price source, no size, unpurchasable,
duplicate barcodes and SKUs.
"""
import csv, datetime, json, os, urllib.parse
from collections import Counter, defaultdict

from siruk import client as _client
from siruk import config
from siruk.config import ROOT

LANGS = ("en", "ru", "hy")
FORMATS = ("xlsx", "json", "csv")
# the MCP default: no long texts, so a whole-catalogue page stays small
COMPACT = ("product_id", "product_name", "brand", "category_ids", "product_type", "is_discontinued",
           "variant_id", "sku", "variant_name", "size", "options", "barcode", "accounting_code",
           "sale_mode", "measure_type", "content", "pack_count", "price", "cost_price", "stock_status",
           "available", "is_purchasable", "price_source_url", "image_ids", "updated_at")


def _query(lang="en", updated_since=None, search=None, dates=None, fmt=None):
    if lang not in LANGS:
        raise ValueError(f"lang must be one of {LANGS}")
    q = {"lang": lang}
    if updated_since:
        q["updated_since"] = str(updated_since)
    if search:
        q["search"] = search
    if dates:
        q["dates"] = dates
    if fmt:
        q["format"] = fmt
    return "/products/export?" + urllib.parse.urlencode(q)


def _timeout():
    return float(config.load()["bulk"]["timeout_seconds"])   # a whole-catalogue export is a long call


def records(lang="en", updated_since=None, search=None, dates=None):
    """→ [record] (format=json)."""
    r = _client.default().get(_query(lang, updated_since, search, dates, "json"), timeout=_timeout()) or {}
    return r.get("data") or []


def default_path(lang, fmt):
    day = datetime.date.today().isoformat()
    return os.path.join(ROOT, "runs", day, f"products_{lang}_{day}.{fmt}")


def save(path=None, fmt="xlsx", lang="en", updated_since=None, search=None, dates=None):
    """Write the export to a file. xlsx is the server's own sheet (strings kept as text, so
    barcodes keep their zeros); json and csv are written here from the records.
    → {"path", "format", "rows"|"bytes"}."""
    if fmt not in FORMATS:
        raise ValueError(f"format must be one of {FORMATS}")
    path = os.path.abspath(path or default_path(lang, fmt))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if fmt == "xlsx":
        data, _ = _client.default().download(_query(lang, updated_since, search, dates), timeout=_timeout())
        if not data.startswith(b"PK"):
            raise _client.ApiError(200, "GET", "/products/export", f"not an xlsx: {data[:200]!r}")
        with open(path, "wb") as f:
            f.write(data)
        return {"path": path, "format": fmt, "bytes": len(data)}
    rows = records(lang, updated_since, search, dates)
    if fmt == "json":
        with open(path, "w", encoding="utf-8") as f:
            json.dump(rows, f, ensure_ascii=False, indent=1)
    else:
        cols = list(dict.fromkeys(k for r in rows for k in r)) or list(COMPACT)
        with open(path, "w", newline="", encoding="utf-8-sig") as f:   # BOM: Excel opens Armenian right
            w = csv.DictWriter(f, fieldnames=cols)
            w.writeheader()
            for r in rows:
                w.writerow({k: ", ".join(map(str, v)) if isinstance(v, list) else v for k, v in r.items()})
    return {"path": path, "format": fmt, "rows": len(rows)}


def pick(rows, fields=None, limit=None, offset=0):
    fields = list(fields or COMPACT)
    out = [{k: r.get(k) for k in fields} for r in rows]
    return out[offset: offset + limit if limit else None]


# ------------------------------------------------------------------- audit ----
def _num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


CHECKS = {
    "below_cost": "sale price at or below cost (rule 5)",
    "no_barcode": "no barcode (rule 10b)",
    "no_accounting_code": "no ArmSoft code (rule 10b)",
    "no_images": "empty gallery (rule 7)",
    "no_price_source": "no price_source_url (fine for a register price)",
    "no_content": "sized product type, pack variant with no net content (rule 8a; ALLOW_NO_SIZE cases show here)",
    "not_purchasable": "not purchasable",
    "out_of_stock": "available ≤ 0",
    "no_variants": "product with no variants",
    "duplicate_barcode": "barcode shared by two or more variants",
    "duplicate_sku": "sku on two or more rows",
}


def sized_types():
    """Names of the product types that carry a size (measureType set) — Toys / Grooming /
    Accessories don't, so a missing content there is normal. From the live types."""
    from siruk import refdata
    return {t["name"] for t in refdata.ids("types") if t.get("measure_type")}


def audit(rows, examples=20, sized=None):
    """→ {"products", "variants", "counts": {check: n}, "examples": {check: [row refs]}, "checks"}."""
    sized = sized_types() if sized is None else set(sized)
    hits = defaultdict(list)
    by_bc, by_sku = defaultdict(list), defaultdict(list)

    def ref(r):
        return {"product_id": r.get("product_id"), "product": r.get("product_name"), "variant_id": r.get("variant_id"),
                "sku": r.get("sku"), "price": r.get("price"), "cost": r.get("cost_price")}

    for r in rows:
        if r.get("variant_id") is None:
            hits["no_variants"].append(ref(r))
            continue
        price, cost = _num(r.get("price")) or 0, _num(r.get("cost_price")) or 0
        if cost > 0 and price <= cost:
            hits["below_cost"].append(ref(r))
        if not r.get("barcode"):
            hits["no_barcode"].append(ref(r))
        else:
            by_bc[str(r["barcode"])].append(r)
        if not r.get("accounting_code"):
            hits["no_accounting_code"].append(ref(r))
        if not r.get("image_ids"):
            hits["no_images"].append(ref(r))
        if not r.get("price_source_url"):
            hits["no_price_source"].append(ref(r))
        if r.get("sale_mode") == "pack" and r.get("product_type") in sized and r.get("content") in (None, "", 0):
            hits["no_content"].append(ref(r))
        if r.get("is_purchasable") is False:
            hits["not_purchasable"].append(ref(r))
        if (_num(r.get("available")) or 0) <= 0:
            hits["out_of_stock"].append(ref(r))
        if r.get("sku"):
            by_sku[str(r["sku"]).lower()].append(r)
    for bc, rs in by_bc.items():
        if len(rs) > 1:
            hits["duplicate_barcode"].append({"barcode": bc, "variants": [ref(r) for r in rs]})
    for sku, rs in by_sku.items():
        if len(rs) > 1:
            hits["duplicate_sku"].append({"sku": sku, "variants": [ref(r) for r in rs]})
    return {"products": len({r.get("product_id") for r in rows}),
            "variants": sum(1 for r in rows if r.get("variant_id") is not None),
            "by_type": dict(Counter(r.get("product_type") for r in rows if r.get("variant_id") is not None)),
            "counts": {k: len(hits.get(k, [])) for k in CHECKS},
            "examples": {k: hits[k][:examples] for k in CHECKS if hits.get(k)},
            "checks": CHECKS}
