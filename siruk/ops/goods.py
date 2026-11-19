"""What an Ops good, location or open-bag write may carry, and the plan that shows it before it is sent.

Ops owns only fiscalName, adgCode, lowStockAt and the reorder levels (stock/dto/update-goods.dto.ts);
siruk's price and name are never sent. Every rule below is a DTO rule checked here first, so a refused
value never costs a call. Quantities are base units (g, ml, pcs).
"""
import re, urllib.parse

from siruk.ops import guard, units
from siruk.payload import PayloadError

# CLI/file key -> the DTO field it sets (stock/dto/update-goods.dto.ts)
FIELDS = {"fiscal_name": "fiscalName", "adg": "adgCode", "low_stock_at": "lowStockAt",
          "reorder_mode": "reorderMode", "reorder_point": "reorderPoint", "reorder_target": "reorderTarget"}
REORDER_FIELDS = {"reorderMode", "reorderPoint", "reorderTarget"}
REORDER_MODES = ("global", "custom", "never")   # ops/packages/contracts/src/api/hafo.ts ReorderMode
FISCAL_MAX, ADG_MAX, ADG_RE = 50, 16, re.compile(r"[0-9.]+")
BARCODE_RE = re.compile(r"[0-9A-Za-z-]{4,32}")
PLU_MAX, UNITS_MAX, QTY_MAX = 99_999, 10_000, 1_000_000_000
LOCATION_CODE_RE = re.compile(r"[0-9A-Za-z_-]{1,16}")
OWN_KINDS = ("shop", "storeroom")
STOCK_UNITS = ("pack", "loose")
PLU_RE = re.compile(r"\d{1,5}")


def good_id(good):
    return urllib.parse.quote(str(good["variantId"]), safe="")


def name_of(good):
    names = good.get("productName") or {}
    name = next((names[k] for k in ("en", "hy", "ru") if names.get(k)), "?")
    return f"{name} {good['label']}" if good.get("label") else name


def title(good):
    return f"{name_of(good)} (SKU {good.get('sku')})"


def shown(v, unit=None):
    if v is None:
        return "(empty)"
    if unit and isinstance(v, int):
        return units.format_quantity(v, unit)
    return repr(v) if isinstance(v, str) else str(v)


def block(head, lines):
    """One summary string: the guard prints it after a fixed label, so continuation lines are indented to match."""
    return ("\n" + " " * 11).join([head, *lines])


def _int(raw, key, top=QTY_MAX):
    if isinstance(raw, bool) or not isinstance(raw, (int, str)) or not re.fullmatch(r"\d+", str(raw).strip()):
        raise PayloadError(f"{key} must be a whole number of 0 or more, got {raw!r}")
    n = int(str(raw).strip())
    if n > top:
        raise PayloadError(f"{key} is at most {top}, got {n}")
    return n


def check_fields(raw):
    """Static rules for the keys of FIELDS; no call is made. A None value clears the field."""
    unknown = sorted(set(raw) - set(FIELDS))
    if unknown:
        raise PayloadError(f"unknown field {', '.join(unknown)}; the Ops-only fields are {', '.join(FIELDS)}")
    out = {}
    for k, v in raw.items():
        if v is None:
            if k == "reorder_mode":
                raise PayloadError("reorder_mode cannot be cleared; use global to go back to the shop defaults")
            out[k] = None
        elif k == "fiscal_name":
            s = str(v).strip()
            if not s or len(s.encode("utf-16-le")) // 2 > FISCAL_MAX:
                raise PayloadError(f"fiscal_name is 1 to {FISCAL_MAX} characters (the HDM cuts longer names), "
                                   f"got {len(s)}: {s!r}")
            out[k] = s
        elif k == "adg":
            s = str(v).strip()
            if not ADG_RE.fullmatch(s) or len(s) > ADG_MAX:
                raise PayloadError(f"adg is digits and dots only, up to {ADG_MAX} characters, got {s!r}")
            out[k] = s
        elif k == "reorder_mode":
            if v not in REORDER_MODES:
                raise PayloadError(f"reorder_mode is one of {', '.join(REORDER_MODES)}, got {v!r}")
            out[k] = v
        elif k == "low_stock_at":
            if not isinstance(v, int) and not re.fullmatch(r"\d+(\.\d+)?\s*[a-zA-Z]*", str(v).strip()):
                raise PayloadError(f"low_stock_at is a quantity in base units or with a unit (5kg, 500g), got {v!r}")
            out[k] = v
        else:
            out[k] = _int(v, k)
    if not out:
        raise PayloadError("nothing to set: give at least one of " + ", ".join(FIELDS))
    return out


def set_body(checked, good):
    """The PATCH body (DTO names) for a good: low_stock_at is converted by the good's own stock unit."""
    body = {}
    for k, v in checked.items():
        if k == "low_stock_at" and v is not None:
            v = units.parse_quantity(v, good.get("stockUnit"))
            if v > QTY_MAX:
                raise PayloadError(f"low_stock_at is at most {QTY_MAX}")
        body[FIELDS[k]] = v
    return body


def changes(good, body):
    """[(field, before, after)] of what actually differs; a field already at its value is left out."""
    return [(f, good.get(f), v) for f, v in body.items() if good.get(f) != v]


def change_lines(rows, unit=None):
    return [f"{f}: {shown(b, unit if f == 'lowStockAt' else None)} → {shown(a, unit if f == 'lowStockAt' else None)}"
            for f, b, a in rows]


def plan_set(good, checked):
    """(steps, summary, shown_state) for one good, or None when every field is already at its value."""
    body = set_body(checked, good)
    rows = changes(good, body)
    if not rows:
        return None
    patch = {f: a for f, _, a in rows}
    steps = [guard.Step("PATCH", f"/goods/{good_id(good)}", patch, label=f"{good.get('sku')}")]
    lines = change_lines(rows, good.get("stockUnit"))
    if "lowStockAt" in patch:
        lines.append("Ops then queues the good to siruk (stock push, when that setting is on)")
    if REORDER_FIELDS & set(patch):
        lines.append("reorderSource becomes manual")
    summary = block(f"set Ops fields of {title(good)}", lines)
    return steps, summary, {"variantId": good["variantId"], "before": {f: b for f, b, _ in rows}}


def check_barcode(code, units_n=None):
    if not BARCODE_RE.fullmatch(str(code)):
        raise PayloadError(f"a barcode is 4 to 32 letters, digits or dashes, got {code!r}")
    if units_n is not None and not 1 <= units_n <= UNITS_MAX:
        raise PayloadError(f"--units is 1 to {UNITS_MAX}, got {units_n}")


def barcodes_text(good):
    extra = [f"{b['code']} (x{b['units']}{'' if b.get('sellable', True) else ', receiving only'})"
             for b in good.get("extraBarcodes") or []]
    return f"main {good.get('barcode') or '(none)'}; extra {', '.join(extra) or '(none)'}"


def _held(good, code):
    return str(code).lower() in [str(c).lower() for c in
                                 [good.get("barcode"), *[b.get("code") for b in good.get("extraBarcodes") or []]]]


def plan_barcode_add(good, code, units_n, sellable):
    check_barcode(code, units_n)
    if _held(good, code):
        raise PayloadError(f"{code} is already a barcode of {title(good)}")
    body = {"code": code}
    if units_n is not None:
        body["units"] = units_n
    if sellable is not None:
        body["sellable"] = sellable
    scans = f"one scan counts {units_n or 1} unit(s)" + ("" if sellable is not False else ", receiving only")
    summary = block(f"add extra barcode {code} to {title(good)}", [f"now {barcodes_text(good)}", scans])
    state = {"variantId": good["variantId"], "barcode": good.get("barcode"),
             "extra": [b.get("code") for b in good.get("extraBarcodes") or []]}
    return [guard.Step("POST", f"/goods/{good_id(good)}/barcodes", body, label=f"{good.get('sku')}")], summary, state


def plan_barcode_rm(good, code):
    check_barcode(code)
    extra = [b.get("code") for b in good.get("extraBarcodes") or []]
    if code not in extra:
        raise PayloadError(f"{code} is not an extra barcode of {title(good)} ({barcodes_text(good)}); "
                           "the main barcode cannot be removed here")
    summary = block(f"remove extra barcode {code} from {title(good)}", [f"now {barcodes_text(good)}"])
    path = f"/goods/{good_id(good)}/barcodes/{urllib.parse.quote(code, safe='')}"
    return [guard.Step("DELETE", path, label=f"{good.get('sku')}")], summary, \
        {"variantId": good["variantId"], "barcode": good.get("barcode"), "extra": extra}


def plan_plu(good, plu):
    if not 1 <= plu <= PLU_MAX:
        raise PayloadError(f"a PLU is 1 to {PLU_MAX}, got {plu}")
    if good.get("stockUnit") != "loose":
        raise PayloadError(f"only a loose good takes a PLU; {title(good)} is {good.get('stockUnit')}")
    main = good.get("barcode")
    if main and PLU_RE.fullmatch(str(main)):
        raise PayloadError(f"{title(good)} already has PLU {main}")
    moved = (f"its current barcode {main} moves to the extra barcodes (1 unit per scan, sellable)"
             if main else "it has no other main barcode")
    summary = block(f"make {plu} the main barcode (PLU) of {title(good)}",
                    [f"main barcode: {shown(main)} → {plu}", moved, "a PLU is not given back from the CLI"])
    return [guard.Step("PUT", f"/goods/{good_id(good)}/plu", {"plu": plu}, label=f"{good.get('sku')}")], \
        summary, {"variantId": good["variantId"], "barcode": main}


def check_location(raw):
    """Static rules of create-location.dto.ts / update-location.dto.ts; keys are the DTO names."""
    out = dict(raw)
    if "code" in out and not LOCATION_CODE_RE.fullmatch(str(out["code"])):
        raise PayloadError(f"a location code is 1 to 16 letters, digits, dashes or underscores, got {out['code']!r}")
    if "name" in out:
        out["name"] = str(out["name"]).strip()
        if not 1 <= len(out["name"]) <= 100:
            raise PayloadError("a location name is 1 to 100 characters")
    if "kind" in out and out["kind"] not in OWN_KINDS:
        raise PayloadError(f"a location kind is one of {', '.join(OWN_KINDS)} (a supplier warehouse comes from the seed)")
    for k, top in (("sirukWarehouseCode", 50), ("armsoftStorage", 16)):
        if out.get(k) is not None and not 1 <= len(str(out[k])) <= top:
            raise PayloadError(f"{k} is 1 to {top} characters; to empty it use --clear")
    return out


def plan_location_create(body, existing_codes):
    if body["code"].lower() in [c.lower() for c in existing_codes]:
        raise PayloadError(f"a location with code {body['code']} already exists")
    lines = [f"{k}: {shown(v)}" for k, v in body.items()]
    return [guard.Step("POST", "/locations", body, label=body["code"])], \
        block(f"create location {body['code']}", lines), {"codes": sorted(existing_codes)}


def plan_location_set(loc, body):
    rows = [(f, loc.get(f), v) for f, v in body.items() if loc.get(f) != v]
    if loc.get("kind") == "supplier" and any(f != "sirukWarehouseCode" for f, _, _ in rows):
        # Ops (locations.service.ts) takes only the siruk link for a supplier warehouse; its connector
        # keeps the name, the switch and the ArmSoft storage.
        raise PayloadError(f"{loc.get('code')} is a supplier warehouse: only --siruk-warehouse-code "
                           "(or --clear siruk-warehouse-code) can be set; its connector manages the rest")
    if not rows:
        return None
    patch = {f: a for f, _, a in rows}
    return [guard.Step("PATCH", f"/locations/{urllib.parse.quote(str(loc['id']), safe='')}", patch,
                       label=loc.get("code") or "")], \
        block(f"change location {loc.get('code')} ({loc.get('name')})", change_lines(rows)), \
        {"id": loc["id"], "before": {f: b for f, b, _ in rows}}


def own_quantity(good, location_id):
    for s in good.get("stock") or []:
        if s.get("locationId") == location_id and s.get("kind") in OWN_KINDS:
            return s.get("quantity")
    return None


def plan_open_bag(loc, bag, bags, loose=None, tag=None):
    """(steps, summary, shown_state, on hand before). The count is part of the request id: a retry after a
    failed attempt keeps it, a genuine repeat after an opening sees a lower count and gets a new one."""
    if not 1 <= bags <= QTY_MAX:
        raise PayloadError(f"bags is 1 to {QTY_MAX}, got {bags}")
    if loc.get("kind") not in OWN_KINDS or loc.get("isActive") is False:
        raise PayloadError(f"bags are opened in an active shop or storeroom of ours, not {loc.get('code')}")
    if bag.get("stockUnit") != "pack":
        raise PayloadError(f"{title(bag)} is not a pack: only a bag (pack) is opened into its loose good")
    if loose is not None and loose.get("stockUnit") != "loose":
        raise PayloadError(f"{title(loose)} is not a loose good")
    have = own_quantity(bag, loc["id"])
    body = {"locationId": loc["id"], "bagVariantId": bag["variantId"], "bags": bags}
    if loose is not None:
        body["looseVariantId"] = loose["variantId"]
    body["clientRequestId"] = guard.idem_uuid("open-bag", loc["id"], bag["variantId"], bags,
                                              loose["variantId"] if loose else None, tag, have)
    after = f"{shown(have - bags, 'pack')}" if have is not None else "?"
    lines = [f"at {loc.get('code')}: {bag.get('sku')} on hand {shown(have, 'pack') if have is not None else '(none)'} "
             f"→ {after}",
             "the pour goes to " + (title(loose) if loose else "the product's loose good")]
    return [guard.Step("POST", "/stock/open-bag", body, label=f"{bags} x {bag.get('sku')}")], \
        block(f"open {bags} x {title(bag)} at {loc.get('code')}", lines), \
        {"bag": bag["variantId"], "at": loc["id"], "onHand": have}, have


class Recording:
    """The client, remembering each answer so the command can look at it after the guard has run."""

    def __init__(self, client):
        self.client, self.base, self.answers = client, client.base, []

    def write(self, method, path, body=None):
        self.answers.append(self.client.write(method, path, body))
        return self.answers[-1]


def replayed(before, now, bags):
    """True when the bag count at the location did not fall by `bags`: Ops handed back an earlier opening."""
    return before is not None and now is not None and now > before - bags
