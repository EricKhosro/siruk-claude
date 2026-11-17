"""Supplier e-invoices in Ops, as the CLI reaches them: find one, match its lines, link it to an order,
make the draft receipt, post it. Paths and bodies follow ops/apps/api/src/modules/einvoices (controllers + dto/).

Rules (ops/docs/DESIGN.md "E-invoices (received)"): no partial receipt, one variant per line, cost checks are
overridden only by an explicit flag, and `post` / `settle` are bound to the lines and matches the dry run showed.
"""
import datetime, urllib.parse

from siruk.ops import client as _ops, guard, resolve, units
from siruk.payload import PayloadError

STATUSES = ("new", "matched", "received", "passthrough", "not_stock", "replaced")  # EInvoiceStatus
LINK_SOURCES = ("claude", "hand")  # goods-link.service.ts LINK_SOURCES
NO_MATCH = "No barcode match and no earlier invoice line with this name and price"  # einvoice-rules.ts NO_MATCH
PAGE_MAX = 200  # ListEInvoicesDto pageSize @Max


def _id(x):
    return urllib.parse.quote(str(x), safe="")


def base(inv_id):
    return f"/einvoices/{_id(inv_id)}"


def find(ref):
    """The invoice's detail, by id or exact serial (A6840667000)."""
    ref = str(ref).strip()
    if resolve.UUID.fullmatch(ref):
        return _ops.default().get(base(ref))
    r = _ops.default().get("/einvoices", {"q": ref, "pageSize": PAGE_MAX}) or {}
    hit = [x for x in r.get("items") or [] if str(x.get("serial") or "").lower() == ref.lower()]
    if len(hit) != 1:
        extra = "" if hit or int(r.get("total") or 0) <= PAGE_MAX else "; too many results, use the id"
        raise PayloadError(f"{len(hit)} e-invoices have the serial {ref!r}{extra}")
    return _ops.default().get(base(hit[0]["id"]))


def line_of(inv, ref):
    """A line of the invoice by its id or its number on the invoice (seqNo)."""
    ref = str(ref).strip()
    lines = inv.get("lines") or []
    hit = [x for x in lines if x.get("id") == ref] or \
          [x for x in lines if ref.isdigit() and x.get("seqNo") == int(ref)]
    if len(hit) != 1:
        raise PayloadError(f"{inv.get('serial')} has no line {ref!r} (lines 1..{len(lines)} or a line id)")
    return hit[0]


def shown(inv):
    """What a dry run showed of the invoice: the state `post` and `settle` are bound to."""
    keep = lambda d, keys: {k: d.get(k) for k in keys} if d else None
    return {"id": inv.get("id"), "serial": inv.get("serial"), "status": inv.get("status"),
            "totalMinor": inv.get("totalMinor"), "linesTotalMinor": inv.get("linesTotalMinor"),
            "totalDifferenceMinor": inv.get("totalDifferenceMinor"),
            "purchaseOrderId": inv.get("purchaseOrderId"),
            "receipt": keep(inv.get("receipt"), ("documentId", "status", "locationId", "totalMinor")),
            "lines": [keep(x, ("id", "seqNo", "quantityText", "totalMinor", "variantId", "quantityBase"))
                      for x in inv.get("lines") or []],
            "blockers": inv.get("blockers") or [],
            "problems": [keep(x, ("lineId", "variantId", "kind")) for x in inv.get("problems") or []]}


def _total(inv):
    return f"{units.minor_to_amd(inv.get('totalMinor') or '0')} AMD"


def pull(date_from, date_to):
    try:
        a, b = datetime.date.fromisoformat(date_from), datetime.date.fromisoformat(date_to)
    except ValueError:
        raise PayloadError("from and to are days, YYYY-MM-DD")
    if a > b:
        raise PayloadError(f"from ({date_from}) is after to ({date_to})")
    step = guard.Step("POST", "/einvoices/pull", {"from": date_from, "to": date_to}, "pull from the tax service")
    return [step], f"pull received invoices {date_from}..{date_to} from the tax service (the owner's saved login)"


def rematch(inv):
    return [guard.Step("POST", f"{base(inv['id'])}/rematch", None, "match again by barcode and supplier map")], \
        f"rematch the lines of {inv.get('serial')}"


def match(inv, line, good, quantity):
    n = units.parse_quantity(quantity, good.get("stockUnit"))
    if n < 1:
        raise PayloadError("a matched line receives at least 1 base unit")
    body = {"variantId": good["variantId"], "quantityBase": n}
    note = " (DISCONTINUED)" if good.get("isDiscontinued") else ""
    return [guard.Step("PUT", f"{base(inv['id'])}/lines/{_id(line['id'])}/match", body,
                       f"line {line.get('seqNo')}")], \
        (f"match {inv.get('serial')} line {line.get('seqNo')} '{line.get('name')}' ({line.get('quantityText')} "
         f"{line.get('unit') or ''}) to {good.get('sku')}{note}: {units.format_quantity(n, good.get('stockUnit'))}")


def unmatch(inv, line):
    return [guard.Step("DELETE", f"{base(inv['id'])}/lines/{_id(line['id'])}/match", None,
                       f"line {line.get('seqNo')}")], \
        f"clear the match of {inv.get('serial')} line {line.get('seqNo')} '{line.get('name')}'"


def purchase_order(ref):
    """The order the invoice would be linked to (hafo.ts HafoPurchaseOrder: id, number, kind, status)."""
    return _ops.default().get(f"/purchase-orders/{_id(str(ref).strip())}")


def totals(inv):
    """The part of the invoice `link`, `unlink` and `not-stock` are bound to."""
    return {k: inv.get(k) for k in ("id", "status", "purchaseOrderId", "totalMinor", "vatMinor", "linesTotalMinor")}


def link_state(inv, po):
    return {"invoice": {"id": inv.get("id"), "status": inv.get("status")},
            "order": {k: po.get(k) for k in ("id", "kind")}}


def link(inv, po):
    if po.get("kind") == "web_order":
        what = ("a web order: if the invoice fits it PASSES THROUGH now (cost onto the web order's lines, the "
                "supplier owed), otherwise it only links")
    else:
        what = f"a {po.get('kind')} order: it only links, nothing is booked until the invoice is received"
    return [guard.Step("POST", f"{base(inv['id'])}/link", {"purchaseOrderId": po["id"]})], \
        f"link {inv.get('serial')} to {po.get('number')}, {what}"


def unlink(inv):
    what = "a pass-through is undone: cost off the web order, the supplier payable REVERSED by a ledger adjustment" \
        if inv.get("status") == "passthrough" else "no payable is booked on it, so only the link goes"
    return [guard.Step("DELETE", f"{base(inv['id'])}/link")], f"take {inv.get('serial')} off its order; {what}"


def receive(inv, location, override=False):
    if inv.get("status") != "new":
        raise PayloadError(f"{inv.get('serial')} is {inv.get('status')}: only a new invoice gets a receipt draft")
    if not inv.get("lines"):
        raise PayloadError(f"{inv.get('serial')} has no goods lines")
    left = [x for x in inv.get("lines") or [] if not x.get("variantId")]
    held = [x for x in left if x.get("matchNote") != NO_MATCH]
    if held:
        raise PayloadError(f"{inv.get('serial')} line(s) {', '.join(str(x.get('seqNo')) for x in held)} are "
                           "unmatched and not for the server to place (cleared by hand or refused): match them "
                           "first")
    problems = inv.get("problems") or []
    if problems and not override:
        raise PayloadError(f"{inv.get('serial')} fails cost checks: "
                           + "; ".join(f"line {p.get('seqNo')} {p.get('message')}" for p in problems)
                           + ". A person accepts them with --override")
    body = {"locationId": location["id"]}
    if override:
        body["override"] = True
    flag = " WITH OVERRIDE of the cost checks" if override and problems else " WITH OVERRIDE" if override else ""
    flag += f"; {len(left)} unmatched line(s) get a good made from the line (it stays even if the draft is " \
            "discarded; see goods-links list)" if left else ""
    return [guard.Step("POST", f"{base(inv['id'])}/receive", body)], \
        f"make the draft receipt of {inv.get('serial')} at {location.get('code')}, total {_total(inv)}{flag}"


def post(inv):
    receipt = inv.get("receipt") or {}
    if inv.get("status") != "matched" or receipt.get("status") not in ("draft", "posted"):
        raise PayloadError(f"{inv.get('serial')} is {inv.get('status')} with no receipt: "
                           "`receive` makes the draft first")
    effect = "stock comes in and the supplier is owed" if receipt.get("status") == "draft" else \
        "the receipt is already posted (documents screen): this books the supplier payable and marks it received"
    return [guard.Step("POST", f"{base(inv['id'])}/post")], \
        (f"POST receipt {receipt.get('number')} of {inv.get('serial')} ({inv.get('supplierName')}, "
         f"{len(inv.get('lines') or [])} lines, {_total(inv)}): {effect}")


def discard(inv):
    return [guard.Step("POST", f"{base(inv['id'])}/discard-draft")], \
        f"discard the draft receipt of {inv.get('serial')} (goods made from its lines stay)"


def settle(inv, accept_differences=False):
    order = inv.get("purchaseOrder") or {}
    if inv.get("status") != "new" or not order.get("orderReceived"):
        raise PayloadError(f"{inv.get('serial')} ({inv.get('status')}) settles only when it is new and linked to "
                           "an order already received from; otherwise use `receive`")
    if not inv.get("lines") or inv.get("unmatchedCount"):
        raise PayloadError(f"{inv.get('serial')} needs every line matched before it settles")
    body = {"acceptDifferences": True} if accept_differences else {}
    flag = " ACCEPTING quantity differences" if accept_differences else ""
    return [guard.Step("POST", f"{base(inv['id'])}/settle-order", body)], \
        f"settle {inv.get('serial')} ({_total(inv)}) against order {order.get('number')}: cost corrected, " \
        f"supplier owed, no stock{flag}"


def not_stock(inv):
    return [guard.Step("POST", f"{base(inv['id'])}/not-stock")], \
        f"mark {inv.get('serial')} not stock (services, supplies, equipment): no receipt, " \
        f"BOOKS {_total(inv)} owed to the supplier, with no undo"


def unlinked():
    return _ops.default().get("/goods-links/unlinked") or []


def goods_link(source, target, factor=None, evidence="", src=None):
    """Merge the invoice-made good `source` onto the siruk variant `target`: its stock moves, no way back."""
    entry = next((g for g in unlinked() if g.get("variantId") == source.get("variantId")), None)
    if entry is None:
        raise PayloadError(f"{source.get('sku')} is not in `goods-links list`: it is already linked or was not "
                           "made from an invoice line")
    if target.get("sirukVariantId") is None or not target.get("isActive", True) \
            or target.get("variantId") == source.get("variantId"):
        raise PayloadError(f"{target.get('sku')} is not an active siruk variant to link onto")
    if not (evidence or "").strip():
        raise PayloadError("a link needs --evidence: why it is the same product (an EAN, the hafo code and its EAN)")
    body = {"targetVariantId": target["variantId"]}
    if factor is not None:
        if not 0 < factor <= 10_000:
            raise PayloadError("--factor is above 0 and at most 10000")
        body["factor"] = int(factor) if factor == int(factor) else factor
    body["evidence"] = evidence.strip()
    if src:
        body["source"] = src
    state = {"source": {k: entry.get(k) for k in ("variantId", "sku", "stock", "lines")},
             "target": {k: target.get(k) for k in ("variantId", "sku", "sirukVariantId", "stockUnit")}}
    return [guard.Step("POST", f"/goods-links/{_id(source['variantId'])}/link", body)], \
        f"merge {source.get('sku')} (its stock and invoice lines) onto {target.get('sku')}", state
