"""The ONE place that builds product/variant bodies for the admin API.

Moved here from scripts/siruk_payload.py on 2026-10-26; that file is now a shim
that re-exports this module, so every script that imports it shares these rules.
API calls go through siruk.client (same token, config.json pacing and retries as
scripts/api.sh).

Since the 2026-09-29 catalog model (siruk-web docs/catalog-model.md) the API
refuses the old variant fields (pricing_type, price_per_kg, weight, unit,
net_quantity, stock, attribute_value_ids, item_content …) and checks every
variant against its product type. This module mirrors the admin form's own
`toVariantPayload` (siruk-web backend/resources/js/catalog/products/variantPayload.js)
so a re-sent unmodified variant never bounces, and it checks a variant against
the live product type before anything is written.

As a library (Python writers):   from siruk.payload import …   (or the old `from siruk_payload import …`)
As a CLI (the shell writers, through the shim):
  siruk_payload.py put-body   <get.json> [<new-variant.json>] [--patch-sku SKU --patch JSON [--replace-attrs]]
  siruk_payload.py post-body  <payload.json>
Both print the body on stdout, or exit 1 with the reasons on stderr.

A NEW variant is written in the new shape:
  { "sku": "…", "name": "2 kg", "price": 9000, "cost_price": 6500,
    "sale_mode": "pack",                        # default: the product type's default_sale_mode
    "measure_type": "mass", "content": 2000,    # g / ml / pcs; content may have 3 decimals (0.4 ml)
    "pack_count": 1,                            # 12 for "12 × 85 g"
    "initial_stock": 10,                        # new variants only — stock is a ledger now
    "attribute_values": {"flavor": [38], "lifestage": [27]},   # attribute id OR code → [value ids]
    "images": [8293],
    "barcode": "4048422122074",                 # the pack's EAN; a "-KG" 1 kg loose variant: its 5-digit PLU
    "accounting_code": "1111",                  # ArmSoft good code (a bag and its 1 kg share one)
    "price_source_url": "https://hafo.am/products/…" }   # the page the price came from; omit for a register price
The three code fields are import-only (the admin form never sends them) and a PUT that leaves
them out keeps them, so to_variant_payload never copies them back (check_codes validates them).
merch_boost / pinned / complement fields are the PM's and are refused (MERCH_REFUSED).

Two server models (siruk-web price types, 2026-11): a legacy one with a flat price /
compare_at_price / min_allowed_price and initial_stock, and a price-types one that refuses
those and wants `prices` rows (exactly one website row; a barcode and the other types on
the other rows) on every variant, with stock received in Siruk Ops. server_model() tells
them apart; adapt_variant() turns one variant into the server's own shape. Input stays
simple: flat price keys = the website price, or `prices` {type code: {price, compare_at_price,
min_allowed_price, barcode} | null (remove)}; a `prices` list is the server's rows.
Legacy input is converted where it is mechanical (attribute_value_ids → attribute_values,
stock → initial_stock, pricing_type "fixed" dropped) and refused where it is not
(pricing_type "per_kg", weight, unit, net_quantity, product-weight — give the pack price
and measure_type/content instead).
"""
import json, os, re, sys

from siruk import client as _client
from siruk.config import ROOT

PRODUCT_KEYS = ("name", "slug", "category_ids", "brand_id", "attribute_family_id",
                "is_best_seller", "is_on_sale", "is_discontinued", "show_unit_price")
# toVariantPayload's keys, in its order. suppliers is left out on purpose: an absent key
# leaves a variant's supplier rows untouched.
VARIANT_KEYS = ("id", "sku", "name", "about_this_item", "ingredient_information", "feeding_instructions",
                "is_default", "attribute_values", "images", "sale_mode", "measure_type", "content",
                "pack_count", "qty_step", "qty_min", "qty_max", "price", "compare_at_price",
                "min_allowed_price", "cost_price", "track_inventory", "out_of_stock_policy",
                "backorder_lead_days", "low_stock_threshold", "reorder_point", "reorder_qty")
NEW_ONLY = ("initial_stock", "initial_stock_warehouse_id", "initial_stock_unit_cost")
LEGACY, PRICE_TYPES = "legacy", "price-types"
WEBSITE = "website"
FLAT_PRICE_KEYS = ("price", "compare_at_price", "min_allowed_price")
ROW_FIELDS = FLAT_PRICE_KEYS + ("barcode",)
RECEIVE_IN_OPS = "stock is received in Siruk Ops: `siruk ops docs new receipt …`"
VTEXT = ("about_this_item", "ingredient_information", "feeding_instructions")
LEGACY_REFUSED = ("price_per_kg", "weight", "unit", "net_quantity", "vendor_stock", "item_content",
                  "min_quantity", "quantity_step", "max_quantity")
MEASURE_TYPES = ("mass", "volume", "count")
# siruk-web bc49dfbf (2026-10-09): written by imports only — the admin form never sends them, and the
# server changes only the keys a request carries, so they are NOT in VARIANT_KEYS: a re-sent variant
# leaves them alone. Set them on a new variant, or with --patch / a backfill.
CODE_KEYS = ("barcode", "accounting_code", "price_source_url")
PRICE_SOURCE_HOSTS = ("hafo.am", "zoovet.am", "nemo.am")
# Merchandising and machine fields: the PM's (boost/pins/complements) or the nightly jobs' — never ours.
MERCH_REFUSED = ("merch_boost", "relevance_score", "sales_count", "pinned_product_ids",
                 "complement_category_ids")


class PayloadError(Exception):
    pass


def api(method, path, payload=None, lang=None):
    """The scripts' old entry point (13 of them import it): parsed JSON, PayloadError on failure."""
    try:
        out = _client.default().request(method, path, body=payload, lang=lang) or {}
    except _client.ApiError as e:
        raise PayloadError(f"api {method} {path} failed: {e}") from e
    if method.upper() == "GET" and re.fullmatch(r"/products/\d+(\?.*)?", path) and isinstance(out.get("data"), dict):
        add_flat_prices(out["data"])
    return out


# ------------------------------------------------------------ server model ----
_model, _ptypes = None, None


def price_types():
    """{code: {id, code, name}} of the active price types; {} on a legacy server.
    Probes GET /price-types?forSelect=1 once per process: 200 = price-types, 404 = legacy."""
    global _model, _ptypes
    if _ptypes is None:
        try:
            data = _client.default().get("/price-types?forSelect=1")
        except _client.ApiError as e:
            if e.status != 404:
                raise
            _model, _ptypes = LEGACY, {}
        else:
            _model = PRICE_TYPES
            _ptypes = {t["code"]: t for t in (data or {}).get("data") or []}
    return _ptypes


def server_model(product=None):
    """"price-types" or "legacy": from a product GET when it has variants, else from the probe."""
    variants = (product or {}).get("variants") or []
    if any(isinstance(v.get("prices"), list) for v in variants):
        return PRICE_TYPES
    if variants:
        return LEGACY
    price_types()
    return _model


def _amd(x):
    if x in (None, ""):
        return None
    f = float(x)
    return int(f) if f.is_integer() else f


def _is_website(row):
    if row.get("price_type_code") is not None:
        return row["price_type_code"] == WEBSITE
    wid = (price_types().get(WEBSITE) or {}).get("id")
    return wid is not None and row.get("price_type_id") == wid


def website_price(v, key="price"):
    """The website price (or compare_at_price / min_allowed_price) of a variant in any shape:
    a `prices` dict by code, flat keys, or a `prices` list of rows. The one place a price is read."""
    rows = v.get("prices")
    if isinstance(rows, dict) and isinstance(rows.get(WEBSITE), dict) and key in rows[WEBSITE]:
        return _amd(rows[WEBSITE][key])
    if key in v:
        return _amd(v[key])
    if isinstance(rows, list):
        row = next((r for r in rows if _is_website(r)), None)
        return _amd(row.get(key)) if row else None
    return None


def set_website_price(v, price):
    row = next((r for r in v["prices"] if _is_website(r)), None) if isinstance(v.get("prices"), list) else None
    if row is not None:
        row["price"] = price
    else:
        v["price"] = price


def add_flat_prices(product):
    """Give every price-types variant the flat website keys, so readers of a GET keep working."""
    for v in (product or {}).get("variants") or []:
        if isinstance(v.get("prices"), list):
            for k in FLAT_PRICE_KEYS:
                v[k] = website_price({"prices": v["prices"]}, k)
    return product


def _type_id(code, baseline):
    t = price_types().get(code)
    if t:
        return t["id"]
    row = next((r for r in baseline if r.get("price_type_code") == code), None)
    if row:
        return row["price_type_id"]   # a type deactivated since: its row stays editable
    raise PayloadError(f"unknown price type '{code}' (active: {', '.join(price_types())})")


def adapt_variant(v, baseline=(), model=None):
    """Put one variant's price and stock input into the server's own shape, in place. → warnings.
    Dict beats flat keys beats `baseline` (the server's rows, kept with their ids)."""
    model = model or server_model()
    tag = f"variant {v.get('sku')}"
    given = v.pop("prices", None)
    flat = {k: v.pop(k) for k in FLAT_PRICE_KEYS if k in v}
    if model == LEGACY:
        if isinstance(given, list):
            given = {r.get("price_type_code"): r for r in given}
        if given:
            other = [c for c in given if c != WEBSITE]
            if other:
                raise PayloadError(f"{tag}: this server has one flat price — a price for {other} needs the price-types backend")
            site = given[WEBSITE]
            if site is None:
                raise PayloadError(f"{tag}: the website price cannot be removed")
            if not isinstance(site, dict):
                raise PayloadError(f"{tag}: price 'website' must be an object like {{\"price\": 2000}}")
            flat.update({k: site[k] for k in FLAT_PRICE_KEYS if k in site})
            if site.get("barcode"):
                raise PayloadError(f"{tag}: the website price has no barcode of its own")
        v.update(flat)
        return []
    warns = []
    present = [k for k in NEW_ONLY if k in v]
    for k in present:
        del v[k]
    if present:
        warns.append(f"{tag}: {', '.join(present)} dropped — {RECEIVE_IN_OPS}")
    if isinstance(given, list):
        baseline, given = given, None

    def website_id():
        site = next((r for r in baseline if r.get("price_type_code") == WEBSITE), None)
        return site["price_type_id"] if site else (price_types().get(WEBSITE) or {}).get("id")

    rows = {r["price_type_id"]: {k: r[k] for k in ("id", "price_type_id") + ROW_FIELDS if k in r} for r in baseline}
    if flat:
        rows.setdefault(website_id(), {"price_type_id": website_id()}).update(flat)
    for code, spec in (given or {}).items():
        tid = _type_id(code, baseline)
        if spec is None:
            if tid == website_id():
                raise PayloadError(f"{tag}: the website price cannot be removed")
            rows.pop(tid, None)
            continue
        if not isinstance(spec, dict):
            raise PayloadError(f"{tag}: price '{code}' must be an object like {{\"price\": 2000}} or null")
        bad = set(spec) - set(ROW_FIELDS)
        if bad:
            raise PayloadError(f"{tag}: price '{code}' has no field {sorted(bad)} (only {ROW_FIELDS})")
        if tid == website_id() and spec.get("barcode"):
            raise PayloadError(f"{tag}: the website price has no barcode of its own — put it on the variant's barcode")
        rows.setdefault(tid, {"price_type_id": tid}).update(spec)
    out = []
    for tid, r in sorted(rows.items(), key=lambda kv: kv[0] != website_id()):
        row = {"price_type_id": tid} if "id" not in r else {"id": r["id"], "price_type_id": tid}
        row.update({k: _amd(r.get(k)) for k in FLAT_PRICE_KEYS})
        if tid != website_id():
            bc = r.get("barcode")
            bc = str(bc).strip() if bc not in (None, "") else None
            if bc and len(bc) > 32:
                raise PayloadError(f"{tag}: barcode '{bc}' of price {tid} is longer than 32")
            row["barcode"] = bc or None
        out.append(row)
    v["prices"] = out
    return warns


def _emit(warns, sink):
    """Warnings go to `sink` (a list) when the caller collects them, else to stderr as before."""
    if sink is not None:
        sink.extend(warns)
    else:
        for w in warns:
            print(f"⚠ {w}", file=sys.stderr)


def _row_code(r):
    return WEBSITE if _is_website(r) else r.get("price_type_code") or f"type-{r.get('price_type_id')}"


def type_prices(v, baseline=()):
    """{type code: price} a variant will carry: the server's `baseline` rows, then flat price, then the
    `prices` dict by code (null removes a type) — the order adapt_variant applies. A `prices` list replaces the baseline."""
    given = v.get("prices")
    if isinstance(given, list):
        baseline, given = given, None
    out = {WEBSITE: None, **{_row_code(r): _amd(r.get("price")) for r in baseline}}
    if "price" in v:
        out[WEBSITE] = _amd(v["price"])
    for c, spec in (given if isinstance(given, dict) else {}).items():
        if spec is None:
            out.pop(c, None)
        elif isinstance(spec, dict) and "price" in spec:
            out[c] = _amd(spec["price"])
    return out


def set_codes(patch):
    """The price type codes a patch gives a price for (barcode-only and removed rows are not among them)."""
    rows, codes = patch.get("prices"), set()
    if "price" in patch:
        codes.add(WEBSITE)
    if isinstance(rows, list):
        codes |= {_row_code(r) for r in rows if r.get("price") is not None}
    elif isinstance(rows, dict):
        codes |= {c for c, spec in rows.items() if isinstance(spec, dict) and "price" in spec}
    return codes


def below_cost(variants, baseline=(), only=None):
    """["sku=… type=… sale=… cost=…"] for every price (any type) at or below its variant's cost.
    No cost, or none above zero: no check. `baseline`: the server's rows of the one variant;
    `only`: just these type codes."""
    bad = []
    for v in variants:
        cost = _amd(v.get("cost_price")) or 0
        if cost <= 0:
            continue
        bad += [f"sku={v.get('sku')} type={c} sale={p or 0} cost={cost}" for c, p in type_prices(v, baseline).items()
                if (only is None or c in only) and (p is not None or c == WEBSITE) and (p or 0) <= cost]
    return bad


def price_guard(variants, allow=None, baseline=(), only=None):
    """lib.sh price_guard (CLAUDE.md rule 5): a sale price of any type at or below cost is the wrong hafo row
    or an invented price. Raises unless allowed (ALLOW_BELOW_COST=1 — the user's explicit say-so)."""
    bad = below_cost(variants, baseline, only)
    if not bad:
        return []
    if allow is None:
        allow = os.environ.get("ALLOW_BELOW_COST") == "1"
    if not allow:
        raise PayloadError("sale price at or below cost — the wrong hafo row or an invented price: "
                           + "; ".join(bad) + " (override only on the user's explicit approval)")
    return [f"below cost, allowed by the user: {b}" for b in bad]


def image_guard(variants, existing=(), allow=None):
    """No product ships with an empty gallery (user rule 2026-09-23; ALLOW_NO_IMAGE=1 overrides)."""
    if any(v.get("images") for v in list(variants) + list(existing)):
        return
    if allow is None:
        allow = os.environ.get("ALLOW_NO_IMAGE") == "1"
    if not allow:
        raise PayloadError("no variant has any images — every product needs at least one")


_types, _attrs = {}, None


def product_type(type_id):
    """The live product type (roles, flags, measure_type) — never a cached doc."""
    if type_id not in _types:
        _types[type_id] = api("GET", f"/attribute-families/{type_id}").get("data") or {}
    if not _types[type_id].get("id"):
        raise PayloadError(f"product type {type_id} does not exist")
    return _types[type_id]


def attributes():
    """code → {id, inputType, values: {value id}}, from the live attribute list."""
    global _attrs
    if _attrs is None:
        data = api("GET", "/attributes?forProducts=true").get("data") or []
        _attrs = {a["code"]: {"id": a["id"], "inputType": a.get("inputType"),
                              "values": {v["id"] for v in a.get("values") or []}} for a in data}
    return _attrs


def to_variant_payload(v, allowed_ids=None):
    """A GET variant → what the API accepts back (server-only fields stripped)."""
    out = {k: v[k] for k in VARIANT_KEYS if k in v}
    if out.get("sale_mode") != "weight":
        out.pop("qty_step", None)
        out.pop("qty_min", None)
    else:
        # a weight variant reads back measure_type "mass" (set by the server) but refuses
        # measure_type / content / pack_count on write (ProductRequest::weightRules)
        for k in ("measure_type", "content", "pack_count"):
            out.pop(k, None)
    if out.get("out_of_stock_policy") == "deny":
        out["backorder_lead_days"] = None
    av = out.get("attribute_values")
    if isinstance(av, dict) and allowed_ids is not None:
        out["attribute_values"] = {k: ids for k, ids in av.items() if int(k) in allowed_ids}
    elif not av:
        out["attribute_values"] = {}
    out["images"] = out.get("images") or []
    if isinstance(v.get("prices"), list):
        for k in FLAT_PRICE_KEYS:
            out.pop(k, None)   # products.get() puts the website price back on the variant; the API refuses it
        adapt_variant(out, v["prices"], PRICE_TYPES)
    return out


def product_body(p):
    return {k: p[k] for k in PRODUCT_KEYS if k in p}


def _attr_id(key, amap):
    if str(key).isdigit():
        return int(key)
    if key not in amap:
        raise PayloadError(f"unknown attribute '{key}'")
    return amap[key]["id"]


def normalize_new(v, ptype, model=None, warns=None):
    """A new variant from our planners → the new shape. Raises on anything not mechanical.
    Price and stock input is put in the server's shape (adapt_variant); its warnings go to `warns`."""
    v = dict(v)
    errs = []
    if "id" in v:
        errs.append("a new variant must not carry an id")
    for k in LEGACY_REFUSED:
        if k in v:
            errs.append(f"'{k}' is gone — give the pack price in price and the size as measure_type/content/pack_count")
    pt = v.pop("pricing_type", None)
    if pt not in (None, "fixed"):
        errs.append(f"pricing_type '{pt}' is gone — price is the pack price (sale_mode weight = price per kg)")
    if "stock" in v:
        v.setdefault("initial_stock", v.pop("stock"))
    amap = attributes()
    legacy = v.pop("attribute_value_ids", None) or {}
    av = {}
    for key, ids in list(legacy.items()) + list((v.pop("attribute_values", None) or {}).items()):
        if key == "product-weight":
            errs.append("product-weight is retired — the pack size goes in measure_type/content")
            continue
        try:
            aid = _attr_id(key, amap)
        except PayloadError as e:
            errs.append(str(e)); continue
        ids = ids if isinstance(ids, list) else [ids]
        av.setdefault(str(aid), [])
        av[str(aid)] += [int(i) for i in ids if int(i) not in av[str(aid)]]
    v["attribute_values"] = av
    v.setdefault("sale_mode", ptype.get("defaultSaleMode") or "pack")
    if v["sale_mode"] == "weight" and os.environ.get("ALLOW_WEIGHT_SALE") != "1":
        # PM 2026-10-01: by-weight sale is paused until its UI is tested — sell a 1 kg pack instead
        errs.append("sale_mode 'weight' is paused (CLAUDE.md 8a) — add a 1 kg pack variant instead")
    if v["sale_mode"] == "pack":
        if v.get("content") is not None and not v.get("measure_type"):
            v["measure_type"] = ptype.get("measureType")
        if v.get("measure_type") and v["measure_type"] not in MEASURE_TYPES:
            errs.append(f"measure_type '{v['measure_type']}' is not one of {MEASURE_TYPES}")
        v.setdefault("pack_count", 1)
    v["images"] = v.get("images") or []
    try:
        w = adapt_variant(v, (), model)
    except PayloadError as e:
        errs.append(str(e).removeprefix(f"variant {v.get('sku')}: "))
    else:
        if warns is not None:
            warns.extend(w)
    if errs:
        raise PayloadError(f"variant {v.get('sku')}: " + "; ".join(errs))
    return v


def check_codes(v):
    """barcode / accounting_code / price_source_url of one variant. Returns (errors, warnings).

    The user's rule (2026-10-12): a pack's barcode is its EAN; a loose-sale 1 kg variant (SKU
    "<bag sku>-KG", CLAUDE.md 8a) — or a treat's 100 g loose variant, "<bag sku>-100G" (2026-10-15) —
    carries the 5-digit scale PLU instead. accounting_code is the
    ArmSoft good code (4 digits; a bag and its 1 kg variant share one). price_source_url is the
    page the sale price came from — empty when the price came from a register file, not a site."""
    errs, warns = [], []
    tag = f"variant {v.get('sku')}"
    loose = str(v.get("sku") or "").upper().endswith(("-KG", "-100G"))
    bc = v.get("barcode")
    if bc not in (None, ""):
        bc = str(bc)
        if not bc.isdigit() or len(bc) > 32:
            errs.append(f"{tag}: barcode '{bc}' must be digits only, ≤32")
        elif loose and len(bc) != 5:
            errs.append(f"{tag}: a loose variant's barcode is the 5-digit PLU, got '{bc}'")
        elif not loose and len(bc) not in (8, 12, 13, 14):
            warns.append(f"{tag}: barcode '{bc}' is not an EAN-8/UPC-12/EAN-13/GTIN-14")
    elif loose:
        warns.append(f"{tag}: loose variant without its PLU barcode")
    ac = v.get("accounting_code")
    if ac not in (None, ""):
        ac = str(ac)
        if len(ac) > 16:
            errs.append(f"{tag}: accounting_code '{ac}' is longer than 16")
        elif not re.fullmatch(r"\d{4}", ac):
            warns.append(f"{tag}: accounting_code '{ac}' is not a 4-digit ArmSoft good code")
    url = v.get("price_source_url")
    if url not in (None, ""):
        if not re.match(r"https?://", str(url)) or len(str(url)) > 2048:
            errs.append(f"{tag}: price_source_url must be an http(s) url ≤2048, got '{url}'")
        elif not any(re.match(rf"https?://(www\.)?{re.escape(h)}/", str(url)) for h in PRICE_SOURCE_HOSTS):
            warns.append(f"{tag}: price_source_url host is not one of {PRICE_SOURCE_HOSTS}: {url}")
    return errs, warns


def check_prices(variants, main_barcodes=()):
    """VariantRules' price checks for variants whose prices are rows: one website row, price > 0 and a
    multiple of 10, compare-at above price, a type barcode unique in the product and never a main barcode."""
    errs = []
    mains = {str(v["barcode"]) for v in variants if v.get("barcode")} | {str(b) for b in main_barcodes}
    seen = {}
    for v in variants:
        tag, rows = f"variant {v.get('sku')}", v["prices"]
        if sum(1 for r in rows if _is_website(r)) != 1:
            errs.append(f"{tag}: exactly one website price is required")
        for r in rows:
            who = f"{tag} price type {r.get('price_type_id')}"
            price, cmp_, low = r.get("price"), r.get("compare_at_price"), r.get("min_allowed_price")
            if price is None or price <= 0 or price % 10:
                errs.append(f"{who}: price {price} must be > 0 and a multiple of 10")
            if cmp_ is not None and (cmp_ < 0 or cmp_ % 10):
                errs.append(f"{who}: compare-at {cmp_} must be a multiple of 10")
            if cmp_ is not None and price is not None and cmp_ <= price:
                errs.append(f"{who}: compare-at {cmp_} must be above the price {price}")
            if low is not None and price is not None and price < low:
                errs.append(f"{who}: price {price} is below the minimum allowed {low}")
            bc = r.get("barcode")
            if bc:
                if bc in mains:
                    errs.append(f"{who}: barcode {bc} is a variant's main barcode")
                elif bc in seen:
                    errs.append(f"{who}: barcode {bc} is already on {seen[bc]}")
                seen.setdefault(bc, f"{tag} price type {r.get('price_type_id')}")
        if len({r.get("price_type_id") for r in rows}) != len(rows):
            errs.append(f"{tag}: a price type appears twice")
    return errs


def check_variants(variants, ptype, new_skus=(), main_barcodes=()):
    """ProductRequest's product-type checks plus ours. Returns (errors, warnings).
    main_barcodes: the variants' saved barcodes (a body carries none), for the price-barcode clash."""
    errs, warns = [], []
    if variants and all(isinstance(v.get("prices"), list) for v in variants):
        errs += check_prices(variants, main_barcodes)
    pivot = {a["id"]: a for a in ptype.get("attributes") or []}
    amap_by_id = {a["id"]: a for a in attributes().values()}
    for v in variants:
        tag = f"variant {v.get('sku')}"
        if any(k in v for k in CODE_KEYS):
            e, w = check_codes(v)
            errs += e
            warns += w
        if not v.get("sku"):
            errs.append("a variant has no sku")
        if not isinstance(v.get("prices"), list):
            price = website_price(v) or 0
            if price <= 0 or price % 10:
                errs.append(f"{tag}: price {price} must be > 0 and a multiple of 10")
        for aid_s, ids in (v.get("attribute_values") or {}).items():
            aid = int(aid_s)
            a = pivot.get(aid)
            if a is None:
                errs.append(f"{tag}: attribute {aid} is not part of product type '{ptype.get('name')}'")
                continue
            known = (amap_by_id.get(aid) or {}).get("values") or set()
            if any(i not in known for i in ids):
                errs.append(f"{tag}: a value of {a['name']} does not belong to it ({ids})")
            multi = a["role"] == "attribute" and a.get("inputType") == "multiselect"
            if len(ids) > 1 and not multi:
                errs.append(f"{tag}: {a['name']} takes one value, got {len(ids)}")
        for a in pivot.values():
            if a.get("isRequired") and not (v.get("attribute_values") or {}).get(str(a["id"])):
                errs.append(f"{tag}: {a['name']} is required by the product type")
        if v.get("sale_mode") == "pack" and v.get("sku") in new_skus and ptype.get("measureType") \
                and v.get("content") is None:
            msg = f"{tag}: product type '{ptype.get('name')}' is sized ({ptype['measureType']}) but the variant has no measure_type/content"
            (warns if os.environ.get("ALLOW_NO_SIZE") == "1" else errs).append(msg)
    # rule 9a: an option set on one variant must be set on all, or that variant loses its tile row
    if len(variants) > 1:
        for a in pivot.values():
            if a["role"] != "option":
                continue
            have = [bool((v.get("attribute_values") or {}).get(str(a["id"]))) for v in variants]
            if any(have) and not all(have):
                missing = [v.get("sku") for v, h in zip(variants, have) if not h]
                (errs if set(missing) & set(new_skus) else warns).append(
                    f"option {a['name']} is set on some variants but not on {missing}")
        # two variants the customer cannot tell apart (same options + same size)
        seen = {}
        for v in variants:
            sig = (tuple(sorted((k, tuple(sorted(ids))) for k, ids in (v.get("attribute_values") or {}).items()
                                if pivot.get(int(k), {}).get("role") == "option")),
                   v.get("sale_mode"), v.get("measure_type"), _num(v.get("content")), v.get("pack_count") or 1)
            if sig in seen:
                errs.append(f"variants {seen[sig]} and {v.get('sku')} have the same options and size — "
                            "the storefront cannot tell them apart")
            seen[sig] = v.get("sku")
    defaults = sum(1 for v in variants if v.get("is_default"))
    if defaults != 1:
        errs.append(f"exactly one variant must be default, got {defaults}")
    return errs, warns


def _num(x):
    return None if x is None else round(float(x), 3)


def put_body(get_data, new_variant=None, patch_sku=None, patch=None, replace_attrs=False, warnings=None):
    """Full PUT body from a fresh GET, optionally appending one new variant or patching one.
    Pass a list as `warnings` to collect the warnings instead of printing them."""
    p = get_data
    if not (p.get("attribute_family_id") or 0) > 0:
        raise PayloadError(f"product {p.get('id')} has no product type — every product needs one")
    model = server_model(p)
    stock_warns = []
    ptype = product_type(p["attribute_family_id"])
    allowed = {a["id"] for a in ptype.get("attributes") or []}
    variants = [to_variant_payload(v, allowed) for v in p["variants"]]
    new_skus = set()
    if patch_sku:
        hit = [v for v in variants if v["sku"] == patch_sku]
        if not hit:
            raise PayloadError(f"product {p['id']} has no variant with sku {patch_sku}")
        v = hit[0]
        patch = dict(patch)
        for k in LEGACY_REFUSED + ("pricing_type", "stock", "attribute_value_ids"):
            if k in patch:
                raise PayloadError(f"patch field '{k}' is gone in the new model (stock: use the stock endpoints)")
        if "attribute_values" in patch:
            amap = attributes()
            conv = {str(_attr_id(k, amap)): (ids if isinstance(ids, list) else [ids])
                    for k, ids in patch.pop("attribute_values").items()}
            v["attribute_values"] = conv if replace_attrs else {**v["attribute_values"], **conv}
            v["attribute_values"] = {k: ids for k, ids in v["attribute_values"].items() if ids}
        price_in = {k: patch.pop(k) for k in FLAT_PRICE_KEYS + ("prices",) if k in patch}
        rows = next(x for x in p["variants"] if x["sku"] == patch_sku).get("prices")
        baseline = rows if isinstance(rows, list) else []   # the GET's own rows, which still name their type codes
        v.pop("prices", None)
        v.update(patch)
        v.update(price_in)
        stock_warns += adapt_variant(v, baseline, model)
    if new_variant is not None:
        nv = normalize_new(new_variant, ptype, model, stock_warns)
        if any(v["sku"] == nv["sku"] for v in variants):
            raise PayloadError(f"product {p['id']} already has a variant with sku {nv['sku']}")
        nv.setdefault("sort_order", len(variants))
        nv["is_default"] = not any(v.get("is_default") for v in variants)
        variants.append(nv)
        new_skus.add(nv["sku"])
    mains = [v["barcode"] for v in p["variants"] if v.get("barcode")]
    errs, warns = check_variants(variants, ptype, new_skus | ({patch_sku} if patch_sku else set()), mains)
    _emit(stock_warns + warns, warnings)
    if errs:
        raise PayloadError("; ".join(errs))
    body = product_body(p)
    body["variants"] = variants
    return body


SIZE_IN_NAME = re.compile(r"(?<![–\-\d.,])\b\d+(?:[.,]\d+)?\s*(?:kg|g|ml|кг|г|мл|կգ|գ|մլ)\.?\s*$", re.I)


def post_body(payload, warnings=None):
    body = {k: payload[k] for k in payload if k != "variants"}
    merch = [k for k in MERCH_REFUSED if k in body]
    if merch:
        raise PayloadError(f"{merch} belong to the PM / the nightly jobs — an import never sends them")
    names = body.get("name")      # a string, or {en, ru, hy} for POST /products/bulk
    for n in (names.values() if isinstance(names, dict) else [names]):
        if SIZE_IN_NAME.search(n or ""):
            # CLAUDE.md 12 (user 2026-10-01): the storefront appends the size label to the name
            raise PayloadError(f"name '{n}' ends in a pack size — the size belongs in the variant only")
    if not (body.get("attribute_family_id") or 0) > 0:
        raise PayloadError("payload has no attribute_family_id — every product needs a product type")
    ptype = product_type(body["attribute_family_id"])
    stock_warns, model = [], server_model()
    variants = [normalize_new(v, ptype, model, stock_warns) for v in payload.get("variants") or []]
    if variants and not any(v.get("is_default") for v in variants):
        variants[0]["is_default"] = True
    for i, v in enumerate(variants):
        v.setdefault("sort_order", i)
        v.setdefault("is_default", False)
    errs, warns = check_variants(variants, ptype, {v["sku"] for v in variants})
    _emit(stock_warns + warns, warnings)
    if errs:
        raise PayloadError("; ".join(errs))
    body["variants"] = variants
    return body


def main(argv):
    if len(argv) < 2 or argv[0] not in ("put-body", "post-body"):
        sys.exit(__doc__)
    try:
        data = json.load(open(argv[1], encoding="utf-8"))
        if argv[0] == "post-body":
            out = post_body(data)
        else:
            get_data = data.get("data", data)
            new = json.load(open(argv[2], encoding="utf-8")) if len(argv) > 2 and not argv[2].startswith("--") else None
            sku = argv[argv.index("--patch-sku") + 1] if "--patch-sku" in argv else None
            patch = json.loads(argv[argv.index("--patch") + 1]) if "--patch" in argv else None
            out = put_body(get_data, new, sku, patch, "--replace-attrs" in argv)
    except PayloadError as e:
        print(f"error: {e}", file=sys.stderr)
        sys.exit(1)
    sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False))
