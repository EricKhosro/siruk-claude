"""Variant and product lifecycle, suppliers, warehouses and the Ops order resend on the admin API.

A plan reads the live records, refuses what the server refuses plus rule 9a (every option set on every
variant of a product, no two variants with the same options + size) before any call, and returns
(steps, summary, shown_state). Rules read from siruk-web/backend: Http/Requests/Admin/Product/
{MoveVariantRequest,MergeProductRequest}, Http/Requests/Admin/Inventory/*, Services/Catalog/
{VariantMoveService,ProductMergeService,VariantArchiveService}.
"""
import json, re

from siruk import client as _client
from siruk.admin import resource as R
from siruk.admin.guard import Step
from siruk.payload import PayloadError

OPTION, ATTRIBUTE, MULTISELECT = "option", "attribute", "multiselect"   # AttributeRole, AttributeInputType
WEIGHT = "weight"                                                       # SaleMode::WEIGHT
PUSH_FAILED = "failed"                                                  # OpsPushStatus::FAILED
OWN, DROPSHIP = "own", "dropship"                                       # WarehouseType
OPS_STOCK_SOURCES = ("hafo",)                                           # OpsStockSource
CODE = re.compile(r"[a-z0-9-]+")
UUID = re.compile(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}")

INVENTORY = "Http/Requests/Admin/Inventory/"
SUPPLIERS = R.Resource("supplier", "/suppliers", required=("code", "name"),
                       volatile=("stock_checked_at", "ops_stock_pulled_at", "products_count",
                                 "open_purchase_orders_count", "open_fulfillments_count", "updatedAt"),
                       source=INVENTORY + "SupplierRequest.php, Controllers/Admin/Inventory/SupplierController.php")
WAREHOUSES = R.Resource("warehouse", "/warehouses", deletable=False,
                        source=INVENTORY + "WarehouseRequest.php, Controllers/Admin/Inventory/WarehouseController.php")
SUPPLIER_PRODUCT_SOURCE = INVENTORY + "SupplierProductRequest.php"
VARIANTS = R.Resource("variant", "/product-variants", source="Controllers/Admin/Catalog/ProductVariantController.php")

SUPPLIER_PRODUCT_FIELDS = ("supplier_sku", "cost_price", "min_order_qty", "pack_multiple", "lead_days",
                           "is_preferred", "dropship_allowed", "is_active")
WAREHOUSE_FIELDS = ("code", "type", "name", "supplier_id", "lead_days", "skip_non_working_days", "is_active")


# ------------------------------------------------------------------ reads ----
def _get(path):
    r = _client.default().get(path)
    return r.get("data", r) if isinstance(r, dict) else r


def _id(x, what):
    try:
        n = int(str(x))
    except ValueError:
        n = 0
    if n < 1:
        raise PayloadError(f"{what} must be a whole number above 0, got {x!r}")
    return n


def _product(pid):
    p = _get(f"/products/{pid}")
    if not isinstance(p, dict) or not p.get("id"):
        raise PayloadError(f"product {pid} not found")
    return p


def _family(p):
    fid = p.get("attribute_family_id")
    if not fid:
        raise PayloadError(f"product {p['id']} has no product type")
    f = _get(f"/attribute-families/{fid}")
    return {**f, "attributes": f.get("attributes") or []} if isinstance(f, dict) else {"attributes": []}


def _variant_of(p, vid):
    v = next((v for v in p.get("variants") or [] if v.get("id") == vid), None)
    if v is None:
        raise PayloadError(f"variant {vid} is not a live variant of product {p['id']} (--product)")
    return v


def _title(p):
    return f"#{p['id']} {p.get('name')!s}"


def _values_of(v):
    """attribute id -> value ids of a GET variant (an empty set comes as [])."""
    av = v.get("attribute_values")
    return {int(k): [int(i) for i in ids] for k, ids in av.items()} if isinstance(av, dict) else {}


def _size(v):
    """The server's VariantSize::key."""
    if v.get("sale_mode") == WEIGHT:
        return WEIGHT
    ic = v.get("item_content")
    return None if ic is None else f"{ic}x{1 if v.get('pack_count') is None else v['pack_count']}"


def _entry(v, values=None, new=False):
    return {"id": v.get("id"), "sku": v.get("sku"), "size": _size(v), "new": new,
            "values": _values_of(v) if values is None else {int(k): ids for k, ids in values.items()}}


def _proj(p):
    """What a dry run pins: ids, skus, option values and sizes, not stock or dates."""
    return {"id": p["id"], "type": p.get("attribute_family_id"),
            "variants": [{"id": v["id"], "sku": v.get("sku"), "size": _size(v),
                          "values": sorted(i for ids in _values_of(v).values() for i in ids)}
                         for v in p.get("variants") or []]}


def _labels(v):
    got = ", ".join(f"{x.get('attributeName')}={x.get('label')}" for x in v.get("attribute_value_labels") or []
                    if x.get("role") == OPTION)
    return got or "no options"


def _block(p, incoming=()):
    lines = [f"  {_title(p)}  (type {p.get('attribute_family_name')}, {len(p.get('variants') or [])} variants)"]
    lines += [f"    {v['id']}  {v.get('sku')}  size {_size(v)}  {_labels(v)}" for v in p.get("variants") or []]
    lines += [f"    {text}  <- incoming" for text in incoming]
    return "\n".join(lines)


# ---------------------------------------------------- the target's rules ----
def _values(fam, raw, where):
    """The incoming attribute_values checked against the target's product type (VariantAttributeRules)."""
    if not isinstance(raw, dict):
        raise PayloadError(f"{where}: attribute_values must be an object {{attribute id: [value ids]}}")
    attrs = {a["id"]: a for a in fam["attributes"]}
    codes = {a.get("code"): a["id"] for a in fam["attributes"]}
    out, errs = {}, []
    for k, v in raw.items():
        aid = int(k) if str(k).isdigit() else codes.get(k)
        a = attrs.get(aid)
        if a is None:
            errs.append(f"{k!r} is not part of the target's product type {fam.get('name')!r}")
            continue
        try:
            ids = [int(i) for i in (v if isinstance(v, list) else [v]) if i not in (None, "")]
        except (TypeError, ValueError):
            errs.append(f"{a['name']}: value ids must be numbers")
            continue
        if aid in out:
            errs.append(f"{a['name']} is given twice")
        elif len(ids) != len(set(ids)):
            errs.append(f"{a['name']}: duplicate value")
        elif len(ids) > 1 and not (a.get("role") == ATTRIBUTE and a.get("inputType") == MULTISELECT):
            errs.append(f"{a['name']} takes one value, got {len(ids)}")
        elif ids:
            out[aid] = ids
    errs += [f"{a['name']} is required by the product type" for a in attrs.values()
             if a.get("isRequired") and a["id"] not in out]
    if errs:
        raise PayloadError(f"{where}: " + "; ".join(errs))
    return {str(a): out[a] for a in sorted(out)}


def _measure(fam, v):
    want, have = fam.get("measureType"), v.get("measure_type")
    if want and have and want != have:
        raise PayloadError(f"variant {v.get('sku')} is measured in {have}, the target type "
                           f"{fam.get('name')!r} in {want}: change the variant's size first")


def _rule_9a(fam, siblings, incoming):
    """(errors, warnings) for the product the variants land on. A gap the target already had among its
    own variants is a warning; one the incoming variants cause or share is an error."""
    opts = {a["id"]: a for a in fam["attributes"] if a.get("role") == OPTION}
    final = siblings + incoming
    errs, warns = [], []
    if len(final) < 2:
        return errs, warns
    for aid, a in opts.items():
        has = lambda e: bool(e["values"].get(aid))
        if not any(has(e) for e in final):
            continue
        lack_in = [e["sku"] for e in incoming if not has(e)]
        lack_sib = [e["sku"] for e in siblings if not has(e)]
        if lack_in:
            errs.append(f"{a['name']} is set on some variants but not on the incoming {', '.join(lack_in)} (rule 9a)")
        elif lack_sib and any(has(e) for e in siblings):
            warns.append(f"{a['name']} is already missing on the target's {', '.join(lack_sib)}")
        elif lack_sib:
            errs.append(f"{a['name']} would be set on the incoming variants but not on the target's "
                        f"{', '.join(lack_sib)}: set it there first (rule 9a)")
    seen = {}
    for e in final:
        sig = (tuple(sorted({i for aid in opts for i in e["values"].get(aid, [])})), e["size"])
        first = seen.setdefault(sig, e)
        if first is not e:
            (errs if e["new"] or first["new"] else warns).append(
                f"variants {first['sku']} and {e['sku']} have the same options and size: "
                "the storefront cannot tell them apart")
    return errs, warns


def _verdict(errs, warns):
    if errs:
        raise PayloadError("; ".join(errs))
    return "".join(f"\n  warning: {w}" for w in warns)


def _drops(variant, values):
    """[(label, is_descriptive)] for each value the variant holds now that the sent values do not carry:
    the server syncs the variant's whole value set to what is sent."""
    kept = {i for ids in values.values() for i in ids}
    return [(f"{x.get('attributeName')}={x.get('label')}", x.get("role") != OPTION)
            for x in variant.get("attribute_value_labels") or [] if x.get("valueId") not in kept]


def _drop_note(entries, allow):
    """The summary lines for dropped values; refuses a dropped descriptive value unless `allow`."""
    lines, hard = [], []
    for sku, drops in entries:
        if drops:
            lines.append(f"\n  drops on {sku}: " + ", ".join(label for label, _ in drops))
            hard += [f"{label} on {sku}" for label, descriptive in drops if descriptive]
    if hard and not allow:
        raise PayloadError("this would drop values the target does not receive: " + "; ".join(hard)
                           + ". Send them in the values, or pass --drop-values to drop them")
    return "".join(lines)


def _new_text(fam, values):
    names = {a["id"]: a["name"] for a in fam["attributes"] if a.get("role") == OPTION}
    got = ", ".join(f"{names[int(k)]}={ids}" for k, ids in values.items() if int(k) in names)
    return got or "no options"


# ------------------------------------------------------- move and merge ----
def plan_move(variant_id, source_id, target_id, values, drop_values=False):
    vid, sid, tid = _id(variant_id, "variant id"), _id(source_id, "--product"), _id(target_id, "--to")
    if sid == tid:
        raise PayloadError("the variant already belongs to that product")
    src, tgt = _product(sid), _product(tid)
    var = _variant_of(src, vid)
    fam = _family(tgt)
    _measure(fam, var)
    vals = _values(fam, values, "attribute_values")
    sibs = [_entry(v) for v in tgt.get("variants") or []]
    note = _verdict(*_rule_9a(fam, sibs, [_entry(var, vals, new=True)]))
    drops = _drops(var, {int(k): v for k, v in vals.items()})
    note += _drop_note([(var.get("sku"), drops)], drop_values)
    if len(src.get("variants") or []) == 1:
        note += f"\n  warning: product {sid} is left with no variants"
    incoming = f"{vid}  {var.get('sku')}  size {_size(var)}  {_new_text(fam, vals)}"
    summary = (f"move variant {vid} ({var.get('sku')}) from product {_title(src)} to {_title(tgt)}; its stock, "
               f"orders, carts and gifts follow it\n{_block(src)}\n{_block(tgt, [incoming])}{note}")
    body = {"target_product_id": tid, "attribute_values": vals}
    shown = {"source": _proj(src), "target": _proj(tgt), "variant": vid, "values": vals, "drops": drops}
    return [Step("POST", f"/product-variants/{vid}/move", body, f"move variant {vid} to product {tid}")], summary, shown


def plan_merge(source_id, target_id, variants, drop_values=False):
    sid, tid = _id(source_id, "source product id"), _id(target_id, "--to")
    if sid == tid:
        raise PayloadError("pick another product to merge into")
    if not isinstance(variants, dict):
        raise PayloadError('--variants is {"<source variant id>": {"attribute_values": {...}}, ...}')
    src, tgt = _product(sid), _product(tid)
    fam = _family(tgt)
    live = {v["id"]: v for v in src.get("variants") or []}
    given = {}
    for k, v in variants.items():
        if not str(k).isdigit() or not isinstance(v, dict) or "attribute_values" not in v:
            raise PayloadError(f'--variants entry {k!r} must be "<variant id>": {{"attribute_values": {{...}}}}')
        given[int(k)] = v["attribute_values"]
    missing, extra = sorted(set(live) - set(given)), sorted(set(given) - set(live))
    if missing or extra:
        said = [f"set the options for every variant: missing {', '.join(map(str, missing))}" if missing else "",
                f"not live variants of product {sid}: {', '.join(map(str, extra))}" if extra else ""]
        raise PayloadError("; ".join(x for x in said if x))
    vals = {}
    for vid in sorted(live):
        _measure(fam, live[vid])
        vals[vid] = _values(fam, given[vid], f"variant {live[vid].get('sku')}")
    sibs = [_entry(v) for v in tgt.get("variants") or []]
    note = _verdict(*_rule_9a(fam, sibs, [_entry(live[i], vals[i], new=True) for i in sorted(live)]))
    drops = {i: _drops(live[i], {int(k): v for k, v in vals[i].items()}) for i in sorted(live)}
    note += _drop_note([(live[i].get("sku"), drops[i]) for i in sorted(live)], drop_values)
    incoming = [f"{i}  {live[i].get('sku')}  size {_size(live[i])}  {_new_text(fam, vals[i])}" for i in sorted(live)]
    summary = (f"merge product {_title(src)} into {_title(tgt)}: its {len(live)} variants move, "
               f"then the source is deleted, or discontinued if it keeps history\n"
               f"{_block(src)}\n{_block(tgt, incoming)}{note}")
    body = {"target_product_id": tid, "variants": {str(i): {"attribute_values": vals[i]} for i in sorted(live)}}
    shown = {"source": _proj(src), "target": _proj(tgt), "values": {str(i): vals[i] for i in sorted(live)},
             "drops": {str(i): d for i, d in drops.items()}}
    return [Step("POST", f"/products/{sid}/merge", body, f"merge product {sid} into {tid}")], summary, shown


def plan_discontinue(product_id):
    pid = _id(product_id, "product id")
    p = _product(pid)
    if p.get("is_discontinued"):
        raise PayloadError(f"product {_title(p)} is already discontinued")
    return ([Step("POST", f"/products/{pid}/discontinue", None, f"discontinue product {pid}")],
            f"discontinue product {_title(p)} ({len(p.get('variants') or [])} variants)",
            {"id": pid, "is_discontinued": False})


# ------------------------------------------------------------- variants ----
def plan_archive(variant_id, product_id):
    vid, pid = _id(variant_id, "variant id"), _id(product_id, "--product")
    p = _product(pid)
    v = _variant_of(p, vid)
    if len(p.get("variants") or []) < 2:
        raise PayloadError(f"variant {v.get('sku')} is the last variant of its product, so it can't be removed")
    blockers = v.get("delete_blockers") or []
    if blockers:
        raise PayloadError(f"variant {v.get('sku')} can't be removed: {' and '.join(blockers)}")
    if v.get("will_archive"):
        what = (f"archive (soft delete, history kept; {v.get('stock_to_write_off') or 0} on hand written off "
                "unless stock is in Ops)")
    else:
        what = "delete for good (no stock history or orders)"
    summary = (f"{what}: variant {vid} ({v.get('sku')}, {v.get('name')!s}) of product {_title(p)}"
               + ("; the next variant becomes the default" if v.get("is_default") else ""))
    shown = {"product": pid, "variants": [x["id"] for x in p["variants"]],
             "variant": {k: v.get(k) for k in ("id", "sku", "is_default", "will_archive", "stock_to_write_off")}}
    return [Step("DELETE", f"/product-variants/{vid}", None, f"remove variant {vid}")], summary, shown


def _archived(variant_id, product_id=None):
    vid = _id(variant_id, "variant id")
    row = next((r for r in _archived_rows(product_id) if r.get("id") == vid), None)
    if row is None:
        raise PayloadError(f"variant {vid} is not in the archived list (newest 500; pass --product to narrow it)")
    return vid, row


def _archived_rows(product_id):
    q = f"?product_id={_id(product_id, '--product')}" if product_id else ""
    r = _client.default().get(f"/product-variants/archived{q}")
    return (r.get("data") if isinstance(r, dict) else r) or []


def plan_restore(variant_id, product_id=None):
    vid, row = _archived(variant_id, product_id)
    back = row.get("released_sku")
    summary = (f"restore archived variant {vid} ({row.get('sku')}) to product "
               f"{row.get('product_id')} {row.get('product_name')!s}"
               + (f"; its SKU returns to {back}, refused if another variant uses it" if back else ""))
    return [Step("POST", f"/product-variants/{vid}/restore", None, f"restore variant {vid}")], summary, row


def plan_release_sku(variant_id, product_id=None):
    vid, row = _archived(variant_id, product_id)
    if row.get("released_sku"):
        raise PayloadError(f"variant {vid} already released SKU {row['released_sku']}")
    summary = f"release SKU {row.get('sku')} of archived variant {vid}: renamed <sku>~archived-{vid}, free to reuse"
    return [Step("POST", f"/product-variants/{vid}/release-sku", None, f"release SKU of variant {vid}")], summary, row


# ------------------------------------------------------------ suppliers ----
def _check_supplier(body, updating=False):
    errs = []
    if updating:
        errs += [f"{k} is required by SupplierRequest; other keys left out stay as they are"
                 for k in SUPPLIERS.required if body.get(k) in (None, "")]
    code = body.get("code")
    if code not in (None, "") and not (isinstance(code, str) and CODE.fullmatch(code) and len(code) <= 40):
        errs.append("code is lower-case letters, digits and dashes, up to 40")
    if body.get("ops_stock_source") not in (None, *OPS_STOCK_SOURCES):
        errs.append(f"ops_stock_source is one of {', '.join(OPS_STOCK_SOURCES)} or null")
    if "currency" in body and not (isinstance(body["currency"], str) and len(body["currency"]) == 3):
        errs.append("currency is 3 letters")
    lead = body.get("default_lead_days")
    if lead is not None and not (isinstance(lead, int) and not isinstance(lead, bool) and 0 <= lead <= 365):
        errs.append("default_lead_days is 0 to 365")
    if errs:
        raise PayloadError(f"supplier body: {'; '.join(errs)} (see {SUPPLIERS.source})")


def plan_supplier_create(body):
    if isinstance(body, dict):
        _check_supplier(body)
    return R.plan_create(SUPPLIERS, body)


def plan_supplier_update(id, body):
    if isinstance(body, dict):
        _check_supplier(body, updating=True)
    return R.plan_update(SUPPLIERS, id, body)


def _supplier(sid):
    s = _get(f"/suppliers/{_id(sid, 'supplier id')}")
    if not isinstance(s, dict) or not s.get("id"):
        raise PayloadError(f"supplier {sid} not found")
    return s


def _check_fields(body, allowed):
    errs = [f"{k} is not a field of the form" for k in body if k not in allowed]
    ints = {"min_order_qty": (1, None), "pack_multiple": (1, None), "lead_days": (0, 365)}
    for k, v in body.items():
        if k in ints and v is not None:
            lo, hi = ints[k]
            if not (isinstance(v, int) and not isinstance(v, bool) and v >= lo and (hi is None or v <= hi)):
                errs.append(f"{k} is a whole number from {lo}" + (f" to {hi}" if hi else ""))
        elif k == "cost_price" and v is not None:
            if isinstance(v, bool) or not isinstance(v, (int, float)) or v < 0:
                errs.append("cost_price is a number from 0")
        elif k in ("is_preferred", "dropship_allowed", "is_active") and not isinstance(v, bool):
            errs.append(f"{k} is true or false")
    return errs


def _short(v, n=40):
    s = json.dumps(v, ensure_ascii=False, default=str)
    return s if len(s) <= n else s[:n - 1] + "…"


def _changes(cur, body):
    changed = [f"{k}: {_short(cur.get(k))} → {_short(v)}" for k, v in body.items() if cur.get(k) != v]
    return "; ".join(changed) if changed else "no sent key differs"


def plan_add_supplier_product(supplier_id, body):
    sup = _supplier(supplier_id)
    if not isinstance(body, dict):
        raise PayloadError("the supplier product body must be a JSON object")
    errs = _check_fields({k: v for k, v in body.items() if k != "product_variant_id"}, SUPPLIER_PRODUCT_FIELDS)
    vid = body.get("product_variant_id")
    if not (isinstance(vid, int) and not isinstance(vid, bool) and vid > 0):
        errs.append("product_variant_id is required (a variant id)")
    if errs:
        raise PayloadError(f"supplier product body: {'; '.join(errs)} (see {SUPPLIER_PRODUCT_SOURCE})")
    return ([Step("POST", f"/suppliers/{sup['id']}/products", body, f"link variant {vid} to supplier {sup['id']}")],
            f"link variant {vid} to supplier {sup['id']} ({sup.get('name')})", {"supplier": sup["id"], "variant": vid})


def _supplier_product(supplier_id, spid):
    sid, pid = _id(supplier_id, "--supplier"), _id(spid, "supplier product id")
    rows = R.list_rows(R.Resource("supplier product", f"/suppliers/{sid}/products", label="supplier_sku"),
                       page="all", params={"perPage": 100})
    row = next((r for r in rows if r.get("id") == pid), None)
    if row is None:
        raise PayloadError(f"supplier product {pid} is not a row of supplier {sid}")
    return sid, pid, row


def _row_state(row, *more):
    """The form fields of a row, not its stock or dates: an Ops pull rewrites those between dry run and apply."""
    return {k: row.get(k) for k in ("id", "ops_managed", *SUPPLIER_PRODUCT_FIELDS, *more)} | {
        "variant": (row.get("variant") or {}).get("id")}


def plan_supplier_product_set(supplier_id, spid, body):
    sid, pid, row = _supplier_product(supplier_id, spid)
    if not isinstance(body, dict):
        raise PayloadError("the supplier product body must be a JSON object")
    errs = _check_fields({k: v for k, v in body.items() if k != "product_variant_id"}, SUPPLIER_PRODUCT_FIELDS)
    if "product_variant_id" in body and body["product_variant_id"] != (row.get("variant") or {}).get("id"):
        errs.append("product_variant_id cannot change: a row is never re-linked")
    if errs:
        raise PayloadError(f"supplier product body: {'; '.join(errs)} (see {SUPPLIER_PRODUCT_SOURCE})")
    note = ("; cost_price is ignored: Siruk Ops keeps the cost of this row"
            if row.get("ops_managed") and "cost_price" in body else "")
    if body.get("is_preferred") and not row.get("is_preferred"):
        note += "; the variant's rows at other suppliers stop being preferred"
    if any(k in body and not body[k] for k in ("min_order_qty", "pack_multiple")):
        note += "; a null min_order_qty or pack_multiple is stored as 1"
    return ([Step("PUT", f"/supplier-products/{pid}", body, f"update supplier product {pid}")],
            f"update supplier {sid} row {pid} ({row.get('supplier_sku')}) — {_changes(row, body)}{note}",
            _row_state(row))


def plan_supplier_product_rm(supplier_id, spid):
    sid, pid, row = _supplier_product(supplier_id, spid)
    if row.get("ops_managed"):
        raise PayloadError("Siruk Ops keeps this row: turn is_active off instead")
    return ([Step("DELETE", f"/supplier-products/{pid}", None, f"remove supplier product {pid}")],
            f"remove supplier {sid} row {pid} ({row.get('supplier_sku')}, "
            f"variant {(row.get('variant') or {}).get('sku')})", _row_state(row))


def plan_supplier_product_stock(supplier_id, spid, qty):
    sid, pid, row = _supplier_product(supplier_id, spid)
    if not str(qty).isdigit():
        raise PayloadError(f"stock_qty is a whole number from 0, got {qty!r}")
    n = int(qty)
    sup = _supplier(sid)
    note = ("; warning: Siruk Ops keeps this row, so its next pull overwrites the quantity"
            if row.get("ops_managed") or sup.get("ops_stock_source") else "")
    return ([Step("PUT", f"/supplier-products/{pid}/stock", {"stock_qty": n}, f"set stock of supplier product {pid}")],
            f"set the stock of supplier {sid} row {pid} ({row.get('supplier_sku')}): "
            f"{row.get('stock_qty')} → {n}{note}",
            _row_state(row, "stock_qty"))


def plan_stock_check(supplier_id):
    s = _supplier(supplier_id)
    return ([Step("POST", f"/suppliers/{s['id']}/stock-check", None, f"stock check of supplier {s['id']}")],
            f"mark every stock level of supplier {s['id']} ({s.get('name')}) as read now: "
            "unchanged levels count as fresh",
            {"id": s["id"], "code": s.get("code")})


def plan_ops_stock_sync(supplier_id):
    s = _supplier(supplier_id)
    if not s.get("ops_stock_source"):
        raise PayloadError(f'supplier {s["id"]} reads no stock from Siruk Ops: set "ops_stock_source" and save first')
    return ([Step("POST", f"/suppliers/{s['id']}/ops-stock-sync", None, f"read stock of supplier {s['id']} from Ops")],
            f"queue a read of supplier {s['id']} ({s.get('name')}) stock from Siruk Ops ({s['ops_stock_source']})",
            {"id": s["id"], "ops_stock_source": s["ops_stock_source"]})


# ------------------------------------------------------------ warehouses ----
def _check_warehouse(body, kind, creating):
    errs = [f"{k} is not a field of the form" for k in body if k not in WAREHOUSE_FIELDS]
    if creating:
        code = body.get("code")
        if not (isinstance(code, str) and CODE.fullmatch(code) and len(code) <= 40):
            errs.append("code is required: lower-case letters, digits and dashes, up to 40")
        if body.get("type") not in (OWN, DROPSHIP):
            errs.append(f"type is {OWN} or {DROPSHIP}")
    else:
        errs += [f"{k} cannot change after creation" for k in ("code", "type") if k in body]
    name = body.get("name")
    if not (isinstance(name, dict) and isinstance(name.get("en"), str) and name["en"].strip()):
        errs.append('name is required as {"en": "...", "hy": "...", "ru": "..."}')
    lead = body.get("lead_days")
    if not (isinstance(lead, int) and not isinstance(lead, bool) and 0 <= lead <= 365):
        errs.append("lead_days is required: 0 to 365")
    errs += [f"{k} is true or false" for k in ("skip_non_working_days", "is_active")
             if k in body and not isinstance(body[k], bool)]
    sup = body.get("supplier_id")
    if kind == DROPSHIP and not (isinstance(sup, int) and not isinstance(sup, bool) and sup > 0):
        errs.append("a dropship warehouse needs supplier_id")
    if kind != DROPSHIP and sup is not None:
        errs.append("supplier_id is only for a dropship warehouse")
    if errs:
        raise PayloadError(f"warehouse body: {'; '.join(errs)} (see {WAREHOUSES.source})")


def plan_warehouse_create(body):
    if not isinstance(body, dict):
        raise PayloadError("the warehouse body must be a JSON object")
    _check_warehouse(body, body.get("type"), True)
    if any(w.get("code") == body["code"] for w in R.list_rows(WAREHOUSES)):
        raise PayloadError(f"a warehouse with code {body['code']!r} already exists")
    sup = _supplier(body["supplier_id"]) if body.get("supplier_id") else None
    return ([Step("POST", WAREHOUSES.path, body, "create warehouse")],
            f"create {body['type']} warehouse {body['code']!r} ({body['name']['en']})"
            + (f" for supplier {sup['id']} ({sup.get('name')})" if sup else ""),
            {"supplier": sup and sup["id"]})


def plan_warehouse_update(id, body):
    wid = _id(id, "warehouse id")
    if not isinstance(body, dict):
        raise PayloadError("the warehouse body must be a JSON object")
    cur = next((w for w in R.list_rows(WAREHOUSES) if w.get("id") == wid), None)
    if cur is None:
        raise PayloadError(f"warehouse {wid} not found")
    _check_warehouse(body, cur.get("type"), False)
    form = {k: cur.get(k) for k in WAREHOUSE_FIELDS if k != "name"} | {"name": cur.get("name_translations")}
    return ([Step("PUT", f"{WAREHOUSES.path}/{wid}", body, f"update warehouse {wid}")],
            f"update warehouse {wid} ({cur.get('code')}) — {_changes(form, body)}", form)


# ------------------------------------------------------------- Ops reads ----
def uuid_arg(s, what):
    if not UUID.fullmatch(str(s)):
        raise PayloadError(f"{what} is an Ops id (uuid), got {s!r}")
    return str(s).lower()


def plan_resend(order_id):
    oid = _id(order_id, "order id")
    o = _get(f"/orders/{oid}")
    ops = (o or {}).get("ops") if isinstance(o, dict) else None
    if not ops or not ops.get("can_resend"):
        raise PayloadError(f"order {oid} has no failed Ops push to resend")
    pushes = [{k: p.get(k) for k in ("event", "status", "attempts")} for p in ops.get("pushes") or []]
    failed = [p for p in ops.get("pushes") or [] if p.get("status") == PUSH_FAILED]
    lines = "".join(f"\n  {p['event']}: {p['status']} after {p['attempts']} attempts"
                    + (f" — {p['error']}" if p.get("error") else "") for p in failed)
    return ([Step("POST", f"/ops/orders/{oid}/resend", None, f"resend order {oid} to Ops")],
            f"resend {len(failed)} failed Ops push(es) of order {o.get('order_number')} to Siruk Ops{lines}",
            {"order": oid, "pushes": pushes})
