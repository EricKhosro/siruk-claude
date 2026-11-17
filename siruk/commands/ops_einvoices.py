"""`siruk ops einvoices …` and `siruk ops goods-links …`: a supplier e-invoice from pulled to received.

Every write is a dry run until `--apply <code>`. `post`, `settle` and `goods-links link` are irreversible and
their code is bound to the invoice (or good) as the dry run showed it. Not here by decision: the tax-service
sign-in (the owner types it in the Ops app) and acknowledging a replacement (owner only).
"""
from siruk import output
from siruk.ops import client as _ops, einvoices as E, guard, resolve, units

READ_ROLES = "owner, manager, warehouse"
MANAGER = "owner, manager"
FIND = ["GET /einvoices", "GET /einvoices/:id"]  # an invoice is named by id or serial


def _cols(inv):
    return {**inv, "total": units.minor_to_amd(inv.get("totalMinor") or "0"),
            "lines": f"{inv.get('lineCount')} ({inv.get('unmatchedCount')} unmatched)"}


def cmd_list(a):
    params = {k: v for k, v in (("status", a.status), ("q", a.search), ("from", a.date_from), ("to", a.date_to),
                                ("page", a.page), ("pageSize", a.page_size)) if v is not None}
    r = _ops.default().get("/einvoices", params) or {}
    if a.json:
        output.dump(r)
        return 0
    output.table([_cols(x) for x in r.get("items") or []],
                 [("id", "id"), ("serial", "serial"), ("status", "status"), ("supplierName", "supplier"),
                  ("issuedAt", "issued"), ("total", "AMD"), ("lines", "lines"), ("purchaseOrderId", "order")])
    print(f"{len(r.get('items') or [])} of {r.get('total')} (page {r.get('page')})")
    return 0


def print_lines(inv):
    rows = []
    for x in inv.get("lines") or []:
        v = x.get("variant") or {}
        rows.append({**x, "qty": f"{x.get('quantityText')} {x.get('unit') or ''}".strip(),
                     "amd": units.minor_to_amd(x.get("totalMinor") or "0"),
                     "match": f"{v.get('sku')} {units.format_quantity(x['quantityBase'], v.get('stockUnit'))}"
                              if x.get("variantId") and x.get("quantityBase") is not None else "UNMATCHED"})
    output.table(rows, [("seqNo", "#"), ("name", "line"), ("qty", "qty"), ("amd", "AMD"), ("match", "matched to"),
                        ("matchNote", "note")])


def cmd_show(a):
    inv = E.find(a.invoice)
    if a.json:
        output.dump(inv)
        return 0
    order, receipt = inv.get("purchaseOrder") or {}, inv.get("receipt") or {}
    print(f"{inv.get('serial')}  {inv.get('status')}  {inv.get('supplierName')}  "
          f"total {units.minor_to_amd(inv.get('totalMinor') or '0')} AMD "
          f"(lines {units.minor_to_amd(inv.get('linesTotalMinor') or '0')}, "
          f"difference {units.minor_to_amd(inv.get('totalDifferenceMinor') or '0')})\n"
          f"id {inv.get('id')}  order {order.get('number') or '-'}  receipt "
          f"{receipt.get('number') or '-'} {receipt.get('status') or ''}".rstrip())
    print_lines(inv)
    if inv.get("blockers"):
        print("blockers:", ", ".join(inv["blockers"]))
    for p in inv.get("problems") or []:
        print(f"problem: line {p.get('seqNo')} {p.get('kind')}: {p.get('message')}")
    for r in inv.get("webOrderReasons") or []:
        print("web order:", r)
    s = inv.get("suggestedPurchaseOrder")
    if s:
        print(f"suggested order: {s.get('purchaseOrderId')} {s.get('number')} (via {s.get('via')}, "
              f"{'fits' if s.get('fits') else 'does not fit'}; a person confirms with `link`)")
    return 0


def _run(a, inv, built, tier, state=None, show_lines=False):
    steps, summary = built
    if show_lines and not a.apply and not a.json:
        print_lines(inv)
    return guard.run(a, steps=steps, summary=summary, tier=tier, shown_state=state,
                     verify=f"siruk ops einvoices show {inv['id']}")


def cmd_pull(a):
    steps, summary = E.pull(a.date_from, a.date_to)
    return guard.run(a, steps=steps, summary=summary, tier="real-world",
                     verify=f"siruk ops einvoices list --from {a.date_from} --to {a.date_to}")


def cmd_rematch(a):
    inv = E.find(a.invoice)
    return _run(a, inv, E.rematch(inv), "draft")


def cmd_match(a):
    inv = E.find(a.invoice)
    return _run(a, inv, E.match(inv, E.line_of(inv, a.line), resolve.variant(a.variant), a.quantity), "draft")


def cmd_unmatch(a):
    inv = E.find(a.invoice)
    return _run(a, inv, E.unmatch(inv, E.line_of(inv, a.line)), "draft")


def cmd_link(a):
    inv = E.find(a.invoice)
    po = E.purchase_order(a.purchase_order)
    return _run(a, inv, E.link(inv, po), "irreversible", E.link_state(inv, po))


def cmd_unlink(a):
    inv = E.find(a.invoice)
    return _run(a, inv, E.unlink(inv), "irreversible", E.totals(inv))


def cmd_receive(a):
    inv = E.find(a.invoice)
    built = E.receive(inv, resolve.location(a.location), a.override)
    return _run(a, inv, built, "draft", E.shown(inv), show_lines=True)


def cmd_post(a):
    inv = E.find(a.invoice)
    return _run(a, inv, E.post(inv), "irreversible", E.shown(inv), show_lines=True)


def cmd_discard(a):
    inv = E.find(a.invoice)
    return _run(a, inv, E.discard(inv), "draft")


def cmd_settle(a):
    inv = E.find(a.invoice)
    return _run(a, inv, E.settle(inv, a.accept_differences), "irreversible", E.shown(inv), show_lines=True)


def cmd_not_stock(a):
    inv = E.find(a.invoice)
    return _run(a, inv, E.not_stock(inv), "irreversible", E.totals(inv))


def cmd_links_list(a):
    rows = E.unlinked()
    if a.json:
        output.dump(rows)
        return 0
    output.table([{**g, "invoices": ", ".join(sorted({x.get("serial") for x in g.get("lines") or []})),
                   "hafo": len(g.get("hafoCandidates") or []),
                   "stock": sum(s.get("quantity") or 0 for s in g.get("stock") or [])} for g in rows],
                 [("variantId", "id"), ("sku", "sku"), ("name", "name"), ("barcode", "barcode"),
                  ("stock", "stock"), ("hafo", "hafo candidates"), ("invoices", "invoices")])
    return 0


def cmd_links_link(a):
    source, target = resolve.variant(a.good), resolve.variant(a.target)
    steps, summary, state = E.goods_link(source, target, a.factor, a.evidence, a.source)
    return guard.run(a, steps=steps, summary=summary, tier="irreversible", shown_state=state,
                     verify="siruk ops goods-links list")


def register(reg):
    inv = "<invoice: id or serial>"
    p = reg.command(("ops", "einvoices", "list"), cmd_list, "received supplier e-invoices", api=["GET /einvoices"],
                    roles=READ_ROLES, example="siruk ops einvoices list --status new")
    p.add_argument("--status", choices=E.STATUSES)
    p.add_argument("--search", help="serial, supplier name or TIN")
    p.add_argument("--from", dest="date_from", metavar="YYYY-MM-DD")
    p.add_argument("--to", dest="date_to", metavar="YYYY-MM-DD")
    p.add_argument("--page", type=int)
    p.add_argument("--page-size", type=int)

    p = reg.command(("ops", "einvoices", "show"), cmd_show, "one invoice: lines, matches, blockers, receipt",
                    api=["GET /einvoices", "GET /einvoices/:id"], roles=READ_ROLES,
                    example="siruk ops einvoices show A6840667000")
    p.add_argument("invoice", metavar=inv)

    p = reg.command(("ops", "einvoices", "pull"), cmd_pull,
                    "pull received invoices from the tax service (uses the owner's saved login)",
                    api=["POST /einvoices/pull"], tier="real-world", roles=MANAGER,
                    example="siruk ops einvoices pull --from 2026-11-01 --to 2026-11-15")
    p.add_argument("--from", dest="date_from", required=True, metavar="YYYY-MM-DD")
    p.add_argument("--to", dest="date_to", required=True, metavar="YYYY-MM-DD")

    p = reg.command(("ops", "einvoices", "rematch"), cmd_rematch, "match the lines again by barcode and supplier map",
                    api=[*FIND, "POST /einvoices/:id/rematch"], tier="draft",
                    roles=READ_ROLES, example="siruk ops einvoices rematch A6840667000")
    p.add_argument("invoice", metavar=inv)

    p = reg.command(("ops", "einvoices", "match"), cmd_match, "match one line to a good and the base units it receives",
                    api=[*FIND, "GET /goods", "GET /goods/:variantId",
                         "PUT /einvoices/:id/lines/:lineId/match"],
                    tier="draft", roles=READ_ROLES,
                    example="siruk ops einvoices match A6840667000 3 RC-MED-4KG 2pcs")
    p.add_argument("invoice", metavar=inv)
    p.add_argument("line", help="line number on the invoice, or its id")
    p.add_argument("variant", help="the good: id, SKU, barcode or accounting code")
    p.add_argument("quantity", help="what the line receives: base units, or with a unit (2pcs, 1.5kg, 500g)")

    p = reg.command(("ops", "einvoices", "unmatch"), cmd_unmatch, "clear one line's match",
                    api=[*FIND, "DELETE /einvoices/:id/lines/:lineId/match"], tier="draft",
                    roles=READ_ROLES, example="siruk ops einvoices unmatch A6840667000 3")
    p.add_argument("invoice", metavar=inv)
    p.add_argument("line", help="line number on the invoice, or its id")

    p = reg.command(("ops", "einvoices", "link"), cmd_link,
                    "link the invoice to its purchase order (on a web order it passes through and books what we owe)",
                    api=[*FIND, "GET /purchase-orders/:id", "POST /einvoices/:id/link"], tier="irreversible",
                    roles=MANAGER,
                    example="siruk ops einvoices link A6840667000 <purchase order id>")
    p.add_argument("invoice", metavar=inv)
    p.add_argument("purchase_order", metavar="<purchase order id>")

    p = reg.command(("ops", "einvoices", "unlink"), cmd_unlink,
                    "take the invoice off its purchase order (undoing a pass-through reverses the payable)",
                    api=[*FIND, "DELETE /einvoices/:id/link"], tier="irreversible", roles=MANAGER,
                    example="siruk ops einvoices unlink A6840667000")
    p.add_argument("invoice", metavar=inv)

    p = reg.command(("ops", "einvoices", "receive"), cmd_receive,
                    "make the draft receipt (--override accepts the listed cost checks)",
                    api=[*FIND, "GET /locations", "POST /einvoices/:id/receive"], tier="draft",
                    roles=READ_ROLES + " (override: owner, manager)",
                    example="siruk ops einvoices receive A6840667000 --location MAIN")
    p.add_argument("invoice", metavar=inv)
    p.add_argument("--location", required=True, help="where the goods go: id or code")
    p.add_argument("--override", action="store_true", help="accept the cost checks the invoice failed")

    p = reg.command(("ops", "einvoices", "post"), cmd_post, "post the draft receipt: stock in, supplier owed",
                    api=[*FIND, "POST /einvoices/:id/post"], tier="irreversible", roles=READ_ROLES,
                    example="siruk ops einvoices post A6840667000")
    p.add_argument("invoice", metavar=inv)

    p = reg.command(("ops", "einvoices", "discard"), cmd_discard, "delete the draft receipt of an invoice",
                    api=[*FIND, "POST /einvoices/:id/discard-draft"], tier="draft",
                    roles=READ_ROLES, example="siruk ops einvoices discard A6840667000")
    p.add_argument("invoice", metavar=inv)

    p = reg.command(("ops", "einvoices", "settle"), cmd_settle,
                    "settle the invoice of an order already received from: cost and what we owe, no stock",
                    api=[*FIND, "POST /einvoices/:id/settle-order"], tier="irreversible",
                    roles=READ_ROLES + " (accept differences: owner, manager)",
                    example="siruk ops einvoices settle A6840667000")
    p.add_argument("invoice", metavar=inv)
    p.add_argument("--accept-differences", action="store_true", help="settle although quantities differ")

    p = reg.command(("ops", "einvoices", "not-stock"), cmd_not_stock,
                    "mark the invoice not stock (services, supplies): books what we owe, no undo",
                    api=[*FIND, "POST /einvoices/:id/not-stock"], tier="irreversible", roles=MANAGER,
                    example="siruk ops einvoices not-stock A6840667000")
    p.add_argument("invoice", metavar=inv)

    reg.command(("ops", "goods-links", "list"), cmd_links_list, "goods made from invoice lines, waiting for a link",
                api=["GET /goods-links/unlinked"], roles=READ_ROLES, example="siruk ops goods-links list")
    p = reg.command(("ops", "goods-links", "link"), cmd_links_link,
                    "merge an invoice-made good onto its siruk variant (its stock moves, no way back)",
                    api=["GET /goods", "GET /goods/:variantId", "GET /goods-links/unlinked",
                         "POST /goods-links/:variantId/link"],
                    tier="irreversible", roles=READ_ROLES,
                    example="siruk ops goods-links link <good> <siruk variant> --evidence 'EAN 4607...'")
    p.add_argument("good", help="the invoice-made good: id, SKU or barcode")
    p.add_argument("target", help="the siruk variant: id, SKU or barcode")
    p.add_argument("--evidence", default="", help="why it is the same product (required)")
    p.add_argument("--factor", type=float, help="target units per unit of the good (default: from the units)")
    p.add_argument("--source", choices=E.LINK_SOURCES, help="who decided")
