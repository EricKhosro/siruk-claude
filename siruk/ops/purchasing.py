"""Ops purchasing rules: suppliers and balances, purchase orders, the hafo reorder list. No printing here.

Money is AMD on the command line and minor-unit strings on the wire; quantities are whole packs.
Receiving is per line with a request id, so a retry is one receipt (siruk-web/ops/docs/DESIGN.md
"Supplier orders and receiving from the order"). `place` and `release` are not here: the policy refuses them.
"""
import datetime, re

from siruk.ops import client as _ops, guard, resolve, units
from siruk.payload import PayloadError

YEREVAN = datetime.timezone(datetime.timedelta(hours=4))
MAX_MINOR_DIGITS = 15
METHODS = ("bank", "cash")


def minor(amd):
    s = units.amd_to_minor(str(amd).strip())
    if len(s) > MAX_MINOR_DIGITS:
        raise PayloadError(f"{amd} AMD is more than the API takes")
    return s


def today():
    return datetime.datetime.now(YEREVAN).date().isoformat()


def day(text, what="date"):
    try:
        return datetime.date.fromisoformat(str(text).strip()).isoformat()
    except ValueError:
        raise PayloadError(f"{what} must look like 2026-11-16, got {text!r}")


def month(text):
    if not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", str(text).strip()):
        raise PayloadError(f"month must look like 2026-10, got {text!r}")
    return text.strip()


def _put(body, **fields):
    body.update({k: v for k, v in fields.items() if v is not None})
    return body


# siruk-web/ops/apps/api/src/modules/suppliers/dto/create-supplier.dto.ts
def supplier_body(name, tin=None, armsoft_code=None, connector=None):
    if not str(name or "").strip():
        raise PayloadError("a supplier needs a name")
    return _put({"name": name.strip()}, tin=tin, armsoftCode=armsoft_code, connector=connector)


# .../suppliers/dto/update-supplier.dto.ts: `null` clears tin, armsoftCode, connector
def supplier_patch(name=None, tin=None, armsoft_code=None, connector=None, active=None, clear=()):
    fields = {"tin": tin, "armsoftCode": armsoft_code, "connector": connector}
    cleared = {"tin": "tin", "armsoft-code": "armsoftCode", "connector": "connector"}
    body = _put({}, name=name.strip() if name else None, isActive=active, **fields)
    for c in clear:
        if cleared[c] in body:
            raise PayloadError(f"--{c} and --clear {c} together")
        body[cleared[c]] = None
    if not body:
        raise PayloadError("nothing to change: give --name, --tin, --armsoft-code, --connector, "
                           "--active or --inactive, or --clear")
    return body


def _signed(amd):
    s = str(amd).strip()
    if s[:1] in "+-" and s[1:2] in ("+", "-"):
        raise PayloadError(f"not an amount in AMD: {s!r} (one sign at most)")
    m = minor(s[1:] if s[:1] in "+-" and s else s)
    if int(m) == 0:
        raise PayloadError("an amount cannot be zero")
    return "-" + m if s.startswith("-") else m


# .../suppliers/dto/record-payment.dto.ts
def payment_step(sup, amd, date, method, note=None):
    if method not in METHODS:
        raise PayloadError(f"method is one of {', '.join(METHODS)}")
    m = _signed(amd)
    if m.startswith("-"):
        raise PayloadError("a payment is a positive amount; use `suppliers adjust` to take a balance down")
    date = day(date)
    note = (note or "").strip() or None
    body = _put({"amountMinor": m, "date": date, "method": method}, note=note)
    body["clientPaymentId"] = guard.idem_uuid("supplier-payment", sup["id"], body)
    return guard.Step("POST", f"/suppliers/{sup['id']}/payments", body, f"pay {sup['name']}")


# .../suppliers/dto/record-adjustment.dto.ts: positive = we owe more, negative = we owe less
def adjustment_step(sup, amd, date, note):
    note = (note or "").strip()
    if len(note) < 3:
        raise PayloadError("an adjustment needs a note saying why (3 characters or more)")
    body = {"amountMinor": _signed(amd), "date": day(date), "note": note}
    body["clientAdjustmentId"] = guard.idem_uuid("supplier-adjustment", sup["id"], body)
    return guard.Step("POST", f"/suppliers/{sup['id']}/adjustments", body, f"adjust {sup['name']}")


def order(ref):
    """The order's full view from its id or its number (PO-…)."""
    ref, c = str(ref).strip(), _ops.default()
    if resolve.UUID.fullmatch(ref):
        return c.get(f"/purchase-orders/{ref}")
    rows = [r for r in c.get("/purchase-orders", {"q": ref}) or [] if str(r.get("number") or "").lower() == ref.lower()]
    row = resolve.one(ref, "purchase order", rows, lambda r: f"{r.get('id')} {r.get('number')} {r.get('status')}")
    return c.get(f"/purchase-orders/{row['id']}")


def pick(rows, ref, kind="line"):
    """The one row a person's reference names: its id, variantId, sku or barcode."""
    want = str(ref).strip().lower()
    hit = [r for r in rows if want in {str(r.get(k) or "").lower() for k in ("id", "variantId", "sku", "barcode")}]
    return resolve.one(ref, kind, hit, lambda r: f"{r.get('id')} {r.get('sku')} {r.get('productName') or ''}".strip())


def parse_line(spec, minimum=1):
    """REF=QUANTITY[@UNIT_COST_AMD] -> (ref, packs, unitCostMinor or None)."""
    ref, eq, rest = str(spec).rpartition("=")
    qty, _, cost = rest.partition("@")
    if not (eq and ref.strip() and qty.strip()):
        raise PayloadError(f"a line looks like REF=QUANTITY[@UNIT_COST_AMD], got {spec!r}")
    n = units.parse_quantity(qty.strip(), "pack")
    if n < minimum:
        raise PayloadError(f"{spec!r}: a quantity is at least {minimum}")
    return ref.strip(), n, minor(cost) if cost.strip() else None


def need_status(po, allowed, action):
    if po.get("status") not in allowed:
        raise PayloadError(f"{po.get('number')} is {po.get('status')}: only a {' or '.join(allowed)} order can be {action}")


# siruk-web/ops/apps/api/src/modules/hafo/dto/purchase-line.dto.ts
def purchase_lines(specs):
    out, seen = [], set()
    for spec in specs:
        ref, qty, cost = parse_line(spec)
        g = resolve.variant(ref)
        if g.get("stockUnit") == "loose":
            raise PayloadError(f"{g.get('sku')} is a loose good: no order takes it (open a bag instead)")
        if g["variantId"] in seen:
            raise PayloadError(f"{ref} is on the order twice")
        seen.add(g["variantId"])
        out.append(_put({"variantId": g["variantId"], "quantity": qty}, unitCostMinor=cost))
    return out


def create_body(supplier_id, note, specs):
    return _put({}, supplierId=supplier_id, note=(note or "").strip() or None, lines=purchase_lines(specs) or None)


def lines_plan(po, specs):
    """(body, shown_state) for PUT /purchase-orders/:id/lines, which replaces every line of a draft."""
    need_status(po, ("draft",), "edited")
    if not specs:
        raise PayloadError("give the whole new set of lines: --line REF=QUANTITY[@UNIT_COST_AMD], repeated")
    now = [{k: l.get(k) for k in ("variantId", "quantity", "unitCostMinor")} for l in po["lines"]]
    return {"lines": purchase_lines(specs)}, {"order": po["number"], "status": po["status"], "lines": now}


def sent_body(po, ref):
    need_status(po, ("draft",), "marked sent")
    ref = (ref or "").strip()
    if po.get("isHafo") and not ref:
        raise PayloadError("hafo's order number is required: --ref <number from hafo>")
    if len(ref) > 64:
        raise PayloadError("the supplier's order number is at most 64 characters")
    return {"externalRef": ref} if ref else {}


# .../hafo/dto/receive-purchase-order.dto.ts
def receive_plan(po, specs, everything, location_id=None):
    """(step, shown_state) for one receive press. The request id covers the open quantities, so a second
    press after more arrived is a new receipt, and the same press repeated is one."""
    need_status(po, ("placed",), "received")
    if bool(specs) == bool(everything):
        raise PayloadError("name the lines to receive (--line REF=QUANTITY[@UNIT_COST_AMD]) or take everything open (--all)")
    opened = [l for l in po["lines"] if l["openQuantity"] > 0]
    if everything:
        picks = [(l, l["openQuantity"], None) for l in opened]
    else:
        picks = []
        for spec in specs:
            ref, qty, cost = parse_line(spec)
            l = pick(po["lines"], ref)
            if any(p[0]["id"] == l["id"] for p in picks):
                raise PayloadError(f"{ref} is on the list twice: a line is received once per press")
            if qty > l["openQuantity"]:
                raise PayloadError(f"{ref}: {qty} is more than the {l['openQuantity']} still open")
            picks.append((l, qty, cost))
    if not picks:
        raise PayloadError(f"nothing is open on {po['number']}")
    lines = [_put({"lineId": l["id"], "quantity": q}, unitCostMinor=c) for l, q, c in picks]
    state = {"order": po["number"], "status": po["status"],
             "open": [{"lineId": l["id"], "sku": l["sku"], "open": l["openQuantity"]} for l in opened]}
    rid = guard.idem_uuid("po-receive", po["id"], location_id, lines, state["open"])
    body = _put({"requestId": rid}, locationId=location_id)
    body["lines"] = lines
    return guard.Step("POST", f"/purchase-orders/{po['id']}/receive", body, f"receive on {po['number']}"), state


def close_plan(po, refs, everything, action):
    """(lineIds, shown_state) for `not-received` (lines still open) or `reopen` (lines marked not received)."""
    field = "openQuantity" if action == "not-received" else "closedQuantity"
    eligible = [l for l in po["lines"] if l[field] > 0]
    if bool(refs) == bool(everything):
        raise PayloadError("name the lines (--line REF, repeated) or take them all (--all)")
    chosen = eligible if everything else [pick(po["lines"], r) for r in refs]
    for l in chosen:
        if l[field] <= 0:
            raise PayloadError(f"{l['sku']} has nothing to {'mark not received' if field == 'openQuantity' else 'reopen'}")
    if not chosen:
        raise PayloadError(f"no line of {po['number']} can be {'marked not received' if field == 'openQuantity' else 'reopened'}")
    ids = list(dict.fromkeys(l["id"] for l in chosen))
    state = {"order": po["number"], "status": po["status"],
             "lines": [{"lineId": l["id"], "sku": l["sku"], "open": l["openQuantity"], "closed": l["closedQuantity"]}
                       for l in chosen]}
    return ids, state


def sent_state(po):
    now = [{k: l.get(k) for k in ("variantId", "quantity", "unitCostMinor")} for l in po["lines"]]
    return {"order": po["number"], "status": po["status"], "lines": now}


def order_state(po):
    return {"order": po["number"], "status": po["status"], "received": po.get("receivedQuantity")}


def current_list():
    lst = (_ops.default().get("/hafo/reorder/list") or {}).get("list")
    if not lst:
        raise PayloadError("there is no pending reorder list: build one with `siruk ops reorder build`")
    return lst


def auto_place_on():
    """The `reorder.autoPlace` setting; refuses when it cannot be read, since accepting would then be a guess."""
    rows = _ops.default().get("/settings") or []
    row = next((r for r in rows if r.get("key") == "reorder.autoPlace"), None)
    if row is None or not isinstance(row.get("value"), bool):
        raise PayloadError("cannot read the reorder.autoPlace setting: accept it in the Ops app")
    return row["value"]


def list_state(lst):
    return {"list": lst["id"], "status": lst["status"],
            "lines": [{"lineId": l["id"], "sku": l["sku"], "quantity": l["quantity"], "dropped": l["dropped"]}
                      for l in lst["lines"]]}


# .../hafo/dto/update-reorder-lines.dto.ts: quantity (pieces, marks the line edited) and dropped, per lineId
def reorder_edit(lst, sets, drops, keeps):
    if lst.get("status") != "pending":
        raise PayloadError(f"the reorder list is {lst.get('status')}: only a pending list is edited")
    edits = {}

    def edit(ref, **kw):
        edits.setdefault(pick(lst["lines"], ref)["id"], {}).update(kw)

    for spec in sets:
        ref, qty, cost = parse_line(spec, minimum=0)
        if cost is not None:
            raise PayloadError(f"{spec!r}: a reorder line has no cost")
        edit(ref, quantity=qty)
    for ref in drops:
        edit(ref, dropped=True)
    for ref in keeps:
        edit(ref, dropped=False)
    if not edits:
        raise PayloadError("nothing to change: --set REF=QUANTITY, --drop REF or --keep REF")
    return {"lines": [{"lineId": i, **kw} for i, kw in edits.items()]}
