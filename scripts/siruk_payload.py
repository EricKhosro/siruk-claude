#!/usr/bin/env python3
"""The ONE place that builds product/variant bodies for the admin API.

Since the 2026-09-29 catalog model (siruk-web docs/catalog-model.md) the API
refuses the old variant fields (pricing_type, price_per_kg, weight, unit,
net_quantity, stock, attribute_value_ids, item_content …) and checks every
variant against its product type. This module mirrors the admin form's own
`toVariantPayload` (siruk-web backend/resources/js/catalog/products/variantPayload.js)
so a re-sent unmodified variant never bounces, and it checks a variant against
the live product type before anything is written.

As a library (Python writers):   from siruk_payload import …
As a CLI (the shell writers):
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
    "images": [8293] }
Legacy input is converted where it is mechanical (attribute_value_ids → attribute_values,
stock → initial_stock, pricing_type "fixed" dropped) and refused where it is not
(pricing_type "per_kg", weight, unit, net_quantity, product-weight — give the pack price
and measure_type/content instead).
"""
import json, os, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

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
VTEXT = ("about_this_item", "ingredient_information", "feeding_instructions")
LEGACY_REFUSED = ("price_per_kg", "weight", "unit", "net_quantity", "vendor_stock", "item_content",
                  "min_quantity", "quantity_step", "max_quantity")
MEASURE_TYPES = ("mass", "volume", "count")


class PayloadError(Exception):
    pass


def api(method, path, payload=None, lang=None):
    env = dict(os.environ)
    if lang:
        env["SIRUK_LANG"] = lang
    args = [os.path.join(ROOT, "scripts/api.sh"), method, path]
    if payload is not None:
        args.append("-")
    r = subprocess.run(args, input=json.dumps(payload, ensure_ascii=False) if payload is not None else None,
                       capture_output=True, text=True, cwd=ROOT, timeout=180, env=env)
    i = r.stdout.find("{")
    if i < 0:
        raise PayloadError(f"api {method} {path} failed: {r.stderr.strip()[-300:]}")
    return json.loads(r.stdout[i:])


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
    return out


def product_body(p):
    return {k: p[k] for k in PRODUCT_KEYS if k in p}


def _attr_id(key, amap):
    if str(key).isdigit():
        return int(key)
    if key not in amap:
        raise PayloadError(f"unknown attribute '{key}'")
    return amap[key]["id"]


def normalize_new(v, ptype):
    """A new variant from our planners → the new shape. Raises on anything not mechanical."""
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
    if v["sale_mode"] == "pack":
        if v.get("content") is not None and not v.get("measure_type"):
            v["measure_type"] = ptype.get("measureType")
        if v.get("measure_type") and v["measure_type"] not in MEASURE_TYPES:
            errs.append(f"measure_type '{v['measure_type']}' is not one of {MEASURE_TYPES}")
        v.setdefault("pack_count", 1)
    v["images"] = v.get("images") or []
    if errs:
        raise PayloadError(f"variant {v.get('sku')}: " + "; ".join(errs))
    return v


def check_variants(variants, ptype, new_skus=()):
    """ProductRequest's product-type checks plus ours. Returns (errors, warnings)."""
    errs, warns = [], []
    pivot = {a["id"]: a for a in ptype.get("attributes") or []}
    amap_by_id = {a["id"]: a for a in attributes().values()}
    for v in variants:
        tag = f"variant {v.get('sku')}"
        if not v.get("sku"):
            errs.append("a variant has no sku")
        price = v.get("price") or 0
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


def put_body(get_data, new_variant=None, patch_sku=None, patch=None, replace_attrs=False):
    """Full PUT body from a fresh GET, optionally appending one new variant or patching one."""
    p = get_data
    if not (p.get("attribute_family_id") or 0) > 0:
        raise PayloadError(f"product {p.get('id')} has no product type — every product needs one")
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
        v.update(patch)
    if new_variant is not None:
        nv = normalize_new(new_variant, ptype)
        if any(v["sku"] == nv["sku"] for v in variants):
            raise PayloadError(f"product {p['id']} already has a variant with sku {nv['sku']}")
        nv.setdefault("sort_order", len(variants))
        nv["is_default"] = not any(v.get("is_default") for v in variants)
        variants.append(nv)
        new_skus.add(nv["sku"])
    errs, warns = check_variants(variants, ptype, new_skus | ({patch_sku} if patch_sku else set()))
    for w in warns:
        print(f"⚠ {w}", file=sys.stderr)
    if errs:
        raise PayloadError("; ".join(errs))
    body = product_body(p)
    body["variants"] = variants
    return body


def post_body(payload):
    body = {k: payload[k] for k in payload if k != "variants"}
    if not (body.get("attribute_family_id") or 0) > 0:
        raise PayloadError("payload has no attribute_family_id — every product needs a product type")
    ptype = product_type(body["attribute_family_id"])
    variants = [normalize_new(v, ptype) for v in payload.get("variants") or []]
    if variants and not any(v.get("is_default") for v in variants):
        variants[0]["is_default"] = True
    for i, v in enumerate(variants):
        v.setdefault("sort_order", i)
        v.setdefault("is_default", False)
    errs, warns = check_variants(variants, ptype, {v["sku"] for v in variants})
    for w in warns:
        print(f"⚠ {w}", file=sys.stderr)
    if errs:
        raise PayloadError("; ".join(errs))
    body["variants"] = variants
    return body


def main(argv):
    if len(argv) < 2 or argv[0] not in ("put-body", "post-body"):
        sys.exit(__doc__)
    try:
        data = json.load(open(argv[1]))
        if argv[0] == "post-body":
            out = post_body(data)
        else:
            get_data = data.get("data", data)
            new = json.load(open(argv[2])) if len(argv) > 2 and not argv[2].startswith("--") else None
            sku = argv[argv.index("--patch-sku") + 1] if "--patch-sku" in argv else None
            patch = json.loads(argv[argv.index("--patch") + 1]) if "--patch" in argv else None
            out = put_body(get_data, new, sku, patch, "--replace-attrs" in argv)
    except PayloadError as e:
        print(f"error: {e}", file=sys.stderr)
        sys.exit(1)
    print(json.dumps(out, ensure_ascii=False))


if __name__ == "__main__":
    main(sys.argv[1:])
