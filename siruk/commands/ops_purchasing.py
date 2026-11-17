"""`siruk ops suppliers | po | reorder | hafo stock` — suppliers and balances, purchase orders, the reorder list.

Reads print a table (AMD) or the API's own JSON with --json. Every write is a dry run until
`--apply <code>`. Placing an order on hafo stays in the Ops app, so no command here reaches it.
"""
from siruk import output
from siruk.ops import client as _ops, guard, purchasing as P, resolve, units
from siruk.payload import PayloadError

AMD = units.minor_to_amd


def _amd(x):
    return None if x is None else AMD(x)


def _get(a, path, params=None):
    data = _ops.default().get(path, params)
    if a.json:
        output.dump(data)
    return data


def _write(a, steps, summary, tier, state=None, verify=""):
    return guard.run(a, steps=steps, summary=summary, tier=tier, shown_state=state, verify=verify)


def _line_arg(p, what="a line REF=QUANTITY[@UNIT_COST_AMD] (REF: sku, barcode or id)"):
    p.add_argument("--line", action="append", default=[], metavar="LINE", help=what + "; repeat for more")


def cmd_suppliers_list(a):
    rows = _get(a, "/suppliers") or []
    if not a.json:
        output.table([{**r, "balance": _amd(r.get("balanceMinor")), "active": "yes" if r.get("isActive") else "no"}
                      for r in rows],
                     [("id", "id"), ("name", "name"), ("tin", "tin"), ("connector", "connector"),
                      ("active", "active"), ("balance", "we owe AMD")])
    return 0


def cmd_suppliers_show(a):
    s = _get(a, f"/suppliers/{resolve.supplier(a.supplier)['id']}") or {}
    if not a.json:
        for k, v in (("id", s.get("id")), ("name", s.get("name")), ("tin", s.get("tin")),
                     ("armsoft code", s.get("armsoftCode")), ("connector", s.get("connector")),
                     ("active", s.get("isActive")), ("we owe AMD", _amd(s.get("balanceMinor"))),
                     ("received, not invoiced AMD", _amd(s.get("receivedNotInvoicedMinor")))):
            print(f"{k:<28} {'-' if v is None else v}")
    return 0


def cmd_suppliers_create(a):
    body = P.supplier_body(a.name, a.tin, a.armsoft_code, a.connector)
    return _write(a, [guard.Step("POST", "/suppliers", body, "new supplier")], f"new supplier {a.name}", "draft",
                  verify="siruk ops suppliers list")


def cmd_suppliers_set(a):
    sup = resolve.supplier(a.supplier)
    active = True if a.active else False if a.inactive else None
    body = P.supplier_patch(a.name, a.tin, a.armsoft_code, a.connector, active, a.clear)
    return _write(a, [guard.Step("PATCH", f"/suppliers/{sup['id']}", body, sup["name"])], f"change {sup['name']}",
                  "draft", state={"supplier": sup["id"], "name": sup["name"], "tin": sup.get("tin"),
                                  "armsoftCode": sup.get("armsoftCode"), "connector": sup.get("connector"),
                                  "isActive": sup.get("isActive")},
                  verify=f"siruk ops suppliers show {sup['id']}")


def cmd_suppliers_ledger(a):
    sup = resolve.supplier(a.supplier)
    params = {k: P.day(v, f"--{k}") for k, v in (("from", a.date_from), ("to", a.to)) if v}
    r = _get(a, f"/suppliers/{sup['id']}/ledger", params or None) or {}
    if not a.json:
        print(f"{sup['name']}   opening {AMD(r['openingBalanceMinor'])}   invoiced {AMD(r['invoicedMinor'])}   "
              f"paid {AMD(r['paidMinor'])}   closing {AMD(r['closingBalanceMinor'])}   "
              f"owed now {AMD(r['currentBalanceMinor'])}  (AMD)")
        output.table([{**e, "date": (e.get("entryDate") or "")[:10], "amount": AMD(e["amountMinor"]),
                       "balance": AMD(e["runningBalanceMinor"])} for e in r.get("entries") or []],
                     [("date", "date"), ("kind", "kind"), ("amount", "AMD"), ("balance", "balance"),
                      ("invoiceSerial", "invoice"), ("method", "method"), ("note", "note")])
    return 0


def cmd_suppliers_pay(a):
    sup = resolve.supplier(a.supplier)
    step = P.payment_step(sup, a.amount_amd, a.date or P.today(), a.method, a.note)
    return _write(a, [step], f"pay {sup['name']} {a.amount_amd} AMD by {a.method}", "irreversible",
                  verify=f"siruk ops suppliers ledger {sup['id']}")


def cmd_suppliers_adjust(a):
    sup = resolve.supplier(a.supplier)
    step = P.adjustment_step(sup, a.amount_amd, a.date or P.today(), a.note)
    return _write(a, [step], f"adjust {sup['name']} by {a.amount_amd} AMD", "irreversible",
                  verify=f"siruk ops suppliers ledger {sup['id']}")


def cmd_suppliers_statement_check(a):
    sup = resolve.supplier(a.supplier)
    body = {"month": P.month(a.month), "statementTotalMinor": P.minor(a.statement_amd)}
    # a POST that only compares and records nothing, so there is no plan to confirm
    r = _ops.default().write("POST", f"/suppliers/{sup['id']}/statement-check", body) or {}
    if a.json:
        output.dump(r)
        return 0
    print(f"{sup['name']}  {r['month']}   ours {AMD(r['ourInvoicesMinor'])}   statement "
          f"{AMD(r['statementTotalMinor'])}   difference {AMD(r['differenceMinor'])}  (AMD)   "
          + ("matches" if r["matches"] else "DOES NOT MATCH"))
    output.table([{**i, "date": (i.get("entryDate") or "")[:10], "amount": AMD(i["amountMinor"])}
                  for i in r.get("invoices") or []],
                 [("date", "date"), ("invoiceSerial", "invoice"), ("amount", "AMD")])
    return 0


def _po_table(rows):
    output.table([{**r, "supplier": r.get("supplierName"), "lines": r.get("lineCount"),
                   "got": f"{r.get('receivedQuantity')}/{r.get('orderedQuantity')}",
                   "cost": _amd(r.get("knownCostMinor")) if r.get("allCostsKnown") else f"{AMD(r['knownCostMinor'])}+"}
                  for r in rows],
                 [("number", "number"), ("kind", "kind"), ("status", "status"), ("supplier", "supplier"),
                  ("externalRef", "their ref"), ("lines", "lines"), ("got", "received"), ("cost", "cost AMD")])


def cmd_po_list(a):
    params = {k: v for k, v in (("status", a.status), ("kind", a.kind), ("q", a.q)) if v}
    if a.supplier:
        params["supplierId"] = resolve.supplier(a.supplier)["id"]
    rows = _get(a, "/purchase-orders", params or None) or []
    if not a.json:
        _po_table(rows)
    return 0


def cmd_po_show(a):
    po = P.order(a.po)
    if a.json:
        output.dump(po)
        return 0
    print(f"{po['number']}  {po['kind']}  {po['status']}  {po['supplierName']}  their ref {po.get('externalRef') or '-'}"
          f"  id {po['id']}" + (f"\nnote: {po['note']}" if po.get("note") else ""))
    output.table([{**l, "cost": _amd(l.get("unitCostMinor")), "got": l["receivedQuantity"], "closed": l["closedQuantity"],
                   "open": l["openQuantity"]} for l in po["lines"]],
                 [("id", "line"), ("sku", "sku"), ("productName", "product"), ("label", "label"),
                  ("quantity", "ordered"), ("got", "received"), ("closed", "not recvd"), ("open", "open"),
                  ("cost", "cost AMD")])
    for r in po.get("receipts") or []:
        print(f"receipt {r.get('documentNumber') or r['id']}  {r.get('locationName') or '-'}  "
              f"{_amd(r.get('valueMinor')) or '-'} AMD  {r.get('createdAt')}")
    return 0


def cmd_po_create(a):
    sup = resolve.supplier(a.supplier) if a.supplier else None
    body = P.create_body(sup and sup["id"], a.note, a.line)
    return _write(a, [guard.Step("POST", "/purchase-orders", body, "new draft order")],
                  f"new draft order for {sup['name'] if sup else 'hafo'}", "draft",
                  verify="siruk ops po list --status draft")


def cmd_po_lines(a):
    po = P.order(a.po)
    body, state = P.lines_plan(po, a.line)
    return _write(a, [guard.Step("PUT", f"/purchase-orders/{po['id']}/lines", body, "replace every line")],
                  f"replace the lines of {po['number']}", "draft", state, f"siruk ops po show {po['number']}")


def cmd_po_sent(a):
    po = P.order(a.po)
    body = P.sent_body(po, a.ref)
    return _write(a, [guard.Step("POST", f"/purchase-orders/{po['id']}/placed", body, "record that it was sent")],
                  f"record {po['number']} as sent" + (f" as {body['externalRef']}" if body else ""), "irreversible",
                  P.sent_state(po), f"siruk ops po show {po['number']}")


def cmd_po_receive(a):
    po = P.order(a.po)
    loc = resolve.location(a.location)["id"] if a.location else None
    step, state = P.receive_plan(po, a.line, a.all, loc)
    got = sum(l["quantity"] for l in step.body["lines"])
    return _write(a, [step], f"receive {got} pcs on {po['number']} ({len(step.body['lines'])} lines)", "irreversible",
                  state, f"siruk ops po show {po['number']} and plan again from the open quantities it shows "
                  "(the request id changes once the first attempt landed)")


def _close(action, path):
    def cmd(a):
        po = P.order(a.po)
        ids, state = P.close_plan(po, a.line, a.all, action)
        return _write(a, [guard.Step("POST", f"/purchase-orders/{po['id']}/{path}", {"lineIds": ids}, action)],
                      f"{action} {len(ids)} line(s) of {po['number']}", "draft", state, f"siruk ops po show {po['number']}")
    return cmd


def _move(path, allowed, past, verb):
    def cmd(a):
        po = P.order(a.po)
        P.need_status(po, allowed, past)
        return _write(a, [guard.Step("POST", f"/purchase-orders/{po['id']}/{path}", None, verb)],
                      f"{verb} {po['number']}", "irreversible", P.order_state(po), f"siruk ops po show {po['number']}")
    return cmd


def cmd_po_from_web_order(a):
    if not resolve.UUID.fullmatch(a.web_order.strip()):
        raise PayloadError("give the web order's Ops id (a UUID), not its number")
    return _write(a, [guard.Step("POST", f"/purchase-orders/from-web-order/{a.web_order.strip()}", None,
                                 "get or create its order")],
                  f"draft order for web order {a.web_order.strip()}", "draft", verify="siruk ops po list --kind web_order")


def cmd_reorder_show(a):
    rows = _get(a, "/hafo/reorder") or []
    if not a.json:
        output.table([{**r, "name": f"{r.get('productName')} {r.get('label') or ''}".strip(),
                       "due": "due" if r.get("due") else "", "hafo": r.get("hafoQuantity")}
                      for r in rows if r.get("due") or not a.due],
                     [("sku", "sku"), ("name", "good"), ("freeOwnStock", "own"), ("openRestockQuantity", "on order"),
                      ("point", "point"), ("target", "target"), ("hafo", "hafo has"), ("due", ""),
                      ("suggestedQuantity", "suggest"), ("flag", "flag")])
    return 0


def _list_table(lst):
    print(f"reorder list {lst['id']}  {lst['status']}  refreshed {lst['refreshedAt']}"
          + (f"  order {lst['purchaseOrderNumber']}" if lst.get("purchaseOrderNumber") else ""))
    output.table([{**l, "name": f"{l.get('productName')} {l.get('label') or ''}".strip(),
                   "dropped": "dropped" if l.get("dropped") else "", "edited": "edited" if l.get("edited") else ""}
                  for l in lst["lines"]],
                 [("id", "line"), ("sku", "sku"), ("name", "good"), ("freeOwnStock", "own"), ("hafoQuantity", "hafo has"),
                  ("suggestedQuantity", "suggest"), ("quantity", "order"), ("dropped", ""), ("edited", ""), ("flag", "flag")])


def cmd_reorder_list(a):
    r = _get(a, "/hafo/reorder/list") or {}
    if not a.json:
        if r.get("list"):
            _list_table(r["list"])
        else:
            print("no pending reorder list (`siruk ops reorder build` makes one)")
        print(f"daily run: {'on' if r.get('dailyRunEnabled') else 'off'}")
    return 0


def cmd_reorder_build(a):
    r = _ops.default().get("/hafo/reorder/list") or {}
    state = P.list_state(r["list"]) if r.get("list") else None
    return _write(a, [guard.Step("POST", "/hafo/reorder/list/build", None, "build or refresh the pending list")],
                  "build or refresh the pending reorder list (staff are told on Telegram when the list is new or its goods change)",
                  "draft", state, "siruk ops reorder list")


def cmd_reorder_lines(a):
    lst = P.current_list()
    body = P.reorder_edit(lst, a.set, a.drop, a.keep)
    return _write(a, [guard.Step("PUT", f"/hafo/reorder/list/{lst['id']}/lines", body, "edit lines")],
                  f"edit {len(body['lines'])} line(s) of the reorder list", "draft", P.list_state(lst),
                  "siruk ops reorder list")


def _decide(action, summary):
    def cmd(a):
        lst = P.current_list()
        if lst.get("status") != "pending":
            raise PayloadError(f"the reorder list is {lst.get('status')}: only a pending list can be {action}ed")
        state = P.list_state(lst)
        if action == "accept":
            if P.auto_place_on():
                raise PayloadError("reorder.autoPlace is on: accepting would place a real hafo order; "
                                   "accept it in the Ops app")
            state["reorder.autoPlace"] = False
        return _write(a, [guard.Step("POST", f"/hafo/reorder/list/{lst['id']}/{action}", None, action)],
                      summary, "draft", state, "siruk ops reorder list")
    return cmd


def cmd_hafo_stock(a):
    params = {k: v for k, v in (("q", a.q), ("limit", a.limit)) if v}
    r = _get(a, "/hafo/stock", params or None) or {}
    if not a.json:
        print(f"hafo readings last changed {r.get('lastApplied') or '-'}")
        output.table([{**i, "name": f"{i.get('productName')} {i.get('label') or ''}".strip(),
                       "has": i.get("quantity"), "in": "yes" if i.get("inStock") else "no"}
                      for i in r.get("items") or []],
                     [("sku", "sku"), ("name", "good"), ("hafoSku", "hafo sku"), ("has", "hafo has"), ("in", "in stock"),
                      ("observedAt", "seen")])
    return 0


def register(reg):
    def sup(name, fn, help, **kw):
        p = reg.command(("ops", "suppliers", name), fn, help, **kw)
        if name != "list" and name != "create":
            p.add_argument("supplier", help="id, TIN or exact name")
        return p

    sup("list", cmd_suppliers_list, "suppliers and what we owe each", api=["GET /suppliers"],
        roles="manager, warehouse", example="siruk ops suppliers list")
    sup("show", cmd_suppliers_show, "one supplier: balance and received-not-invoiced",
        api=["GET /suppliers", "GET /suppliers/:id"], roles="manager", example="siruk ops suppliers show 'Pet House'")
    p = sup("create", cmd_suppliers_create, "add a supplier", api=["POST /suppliers"], tier="draft", roles="manager",
            example="siruk ops suppliers create 'Pet House' --tin 00000000")
    p.add_argument("name")
    p.add_argument("--tin")
    p.add_argument("--armsoft-code")
    p.add_argument("--connector", help="'hafo' for hafo's")
    p = sup("set", cmd_suppliers_set, "rename, change codes, switch a supplier on or off",
            api=["GET /suppliers", "PATCH /suppliers/:id"], tier="draft", roles="manager",
            example="siruk ops suppliers set 'Pet House' --inactive")
    p.add_argument("--name")
    p.add_argument("--tin")
    p.add_argument("--armsoft-code")
    p.add_argument("--connector")
    p.add_argument("--clear", action="append", default=[], choices=["tin", "armsoft-code", "connector"],
                   help="empty that field; repeat for more")
    g = p.add_mutually_exclusive_group()
    g.add_argument("--active", action="store_true")
    g.add_argument("--inactive", action="store_true")
    p = sup("ledger", cmd_suppliers_ledger, "invoices, payments and the running balance",
            api=["GET /suppliers", "GET /suppliers/:id/ledger"], roles="manager",
            example="siruk ops suppliers ledger 'Pet House' --from 2026-11-01")
    p.add_argument("--from", dest="date_from", metavar="DATE", help="YYYY-MM-DD, a day in Armenia")
    p.add_argument("--to", metavar="DATE", help="YYYY-MM-DD, that day included")
    p = sup("pay", cmd_suppliers_pay, "record a payment to a supplier (takes the balance down)",
            api=["GET /suppliers", "POST /suppliers/:id/payments"], tier="irreversible", roles="manager",
            example="siruk ops suppliers pay 'Pet House' --amount-amd 1300 --method bank")
    p.add_argument("--amount-amd", required=True, metavar="AMD", help="positive; two identical payments on one "
                   "day need a different --note, or the second is taken as a resend")
    p.add_argument("--method", required=True, choices=P.METHODS)
    p.add_argument("--date", metavar="DATE", help="YYYY-MM-DD (default: today in Armenia)")
    p.add_argument("--note")
    p = sup("adjust", cmd_suppliers_adjust, "put a balance right with a signed entry (+ we owe more, - less)",
            api=["GET /suppliers", "POST /suppliers/:id/adjustments"], tier="irreversible", roles="manager",
            example="siruk ops suppliers adjust 'Pet House' --amount-amd=-500 --note 'credit note 17'")
    p.add_argument("--amount-amd", required=True, metavar="AMD", help="signed, never zero (write --amount-amd=-500)")
    p.add_argument("--note", required=True, help="why (3 characters or more)")
    p.add_argument("--date", metavar="DATE", help="YYYY-MM-DD (default: today in Armenia)")
    p = sup("statement-check", cmd_suppliers_statement_check, "compare a month's invoices with the supplier's statement",
            api=["GET /suppliers", "POST /suppliers/:id/statement-check"], roles="manager",
            example="siruk ops suppliers statement-check hafo --month 2026-10 --statement-amd 1250000")
    p.add_argument("--month", required=True, metavar="YYYY-MM")
    p.add_argument("--statement-amd", required=True, metavar="AMD", help="the total on the supplier's statement")

    def po(name, fn, help, **kw):
        p = reg.command(("ops", "po", name), fn, help, **kw)
        if name not in ("list", "create", "from-web-order"):
            p.add_argument("po", help="order id or number (PO-…)")
        return p

    who = "manager, warehouse"
    everyone = "manager, warehouse, cashier"
    p = po("list", cmd_po_list, "purchase orders", api=["GET /suppliers", "GET /purchase-orders"], roles=everyone,
           example="siruk ops po list --status placed")
    p.add_argument("--status", choices=["draft", "placed", "delivered", "invoiced", "cancelled"])
    p.add_argument("--kind", choices=["restock", "web_order"])
    p.add_argument("--supplier", help="id, TIN or exact name")
    p.add_argument("--q", help="search text")
    po("show", cmd_po_show, "one order: lines, what is received and still open, receipts",
       api=["GET /purchase-orders", "GET /purchase-orders/:id"], roles=everyone, example="siruk ops po show PO-0042")
    p = po("create", cmd_po_create, "a draft order (hafo unless --supplier)", api=["GET /suppliers", "GET /goods",
           "POST /purchase-orders"], tier="draft", roles=who,
           example="siruk ops po create --line 8009470387958=6 --line 387967=12@1300")
    p.add_argument("--supplier", help="id, TIN or exact name (default: hafo)")
    p.add_argument("--note")
    _line_arg(p)
    p = po("lines", cmd_po_lines, "replace every line of a draft order",
           api=["GET /purchase-orders", "GET /purchase-orders/:id", "GET /goods", "PUT /purchase-orders/:id/lines"], tier="draft", roles=who,
           example="siruk ops po lines PO-0042 --line 387957=6 --line 387967=12")
    _line_arg(p, "a line REF=QUANTITY[@UNIT_COST_AMD]; the whole new set")
    p = po("sent", cmd_po_sent, "record that the order was sent to the supplier (hafo's number is required)",
           api=["GET /purchase-orders", "GET /purchase-orders/:id", "POST /purchase-orders/:id/placed"], tier="irreversible", roles=who,
           example="siruk ops po sent PO-0042 --ref 2026-1187")
    p.add_argument("--ref", help="the supplier's own order number")
    p = po("receive", cmd_po_receive, "book goods into stock from a placed order: one receipt per press",
           api=["GET /purchase-orders", "GET /purchase-orders/:id", "GET /locations", "POST /purchase-orders/:id/receive"],
           tier="irreversible", roles=everyone, example="siruk ops po receive PO-0042 --line 387957=4")
    _line_arg(p, "a line REF=QUANTITY[@UNIT_COST_AMD] (the cost only for a line with none)")
    p.add_argument("--all", action="store_true", help="every line, all of what is still open")
    p.add_argument("--location", help="location code or id (default: the first active shop; a web_order order uses its own location)")
    for name, path, help in (("not-received", "not-received", "mark lines the supplier did not bring"),
                             ("reopen", "reopen", "put lines marked not received back on the order")):
        p = po(name, _close(name, path), help,
               api=["GET /purchase-orders", "GET /purchase-orders/:id", f"POST /purchase-orders/:id/{path}"], tier="draft", roles=everyone,
               example=f"siruk ops po {name} PO-0042 --line 387957")
        p.add_argument("--line", action="append", default=[], metavar="REF", help="sku, barcode or line id; repeat")
        p.add_argument("--all", action="store_true")
    po("delivered", _move("delivered", ("placed",), "marked delivered", "mark delivered"),
       "close a placed order as delivered", api=["GET /purchase-orders", "GET /purchase-orders/:id", "POST /purchase-orders/:id/delivered"],
       tier="irreversible", roles=who, example="siruk ops po delivered PO-0042")
    po("cancel", _move("cancel", ("draft", "placed"), "cancelled", "cancel"),
       "cancel an order with nothing received", api=["GET /purchase-orders", "GET /purchase-orders/:id", "POST /purchase-orders/:id/cancel"],
       tier="irreversible", roles=who, example="siruk ops po cancel PO-0042")
    po("from-web-order", cmd_po_from_web_order, "the draft order for one web order (the one there is, or a new one)",
       api=["POST /purchase-orders/from-web-order/:webOrderId"], tier="draft", roles=who,
       example="siruk ops po from-web-order 0b9c3a52-7c1d-4e0a-9d52-3f1d6c1f0a11").add_argument(
        "web_order", help="the web order's Ops id")

    def rd(name, fn, help, **kw):
        kw.setdefault("roles", who)
        return reg.command(("ops", "reorder", name), fn, help, **kw)

    p = rd("show", cmd_reorder_show, "every variant as the reorder rule sees it now", api=["GET /hafo/reorder"],
           example="siruk ops reorder show --due")
    p.add_argument("--due", action="store_true", help="only those at or below their point")
    rd("list", cmd_reorder_list, "the pending reorder list", api=["GET /hafo/reorder/list"],
       example="siruk ops reorder list")
    rd("build", cmd_reorder_build, "build or refresh the pending list", tier="draft",
       api=["GET /hafo/reorder/list", "POST /hafo/reorder/list/build"], example="siruk ops reorder build")
    p = rd("lines", cmd_reorder_lines, "change quantities, drop or keep lines of the pending list", tier="draft",
           api=["GET /hafo/reorder/list", "PUT /hafo/reorder/list/:id/lines"],
           example="siruk ops reorder lines --set 387957=6 --drop 387967")
    p.add_argument("--set", action="append", default=[], metavar="REF=QUANTITY", help="pieces to order (0 allowed)")
    p.add_argument("--drop", action="append", default=[], metavar="REF")
    p.add_argument("--keep", action="append", default=[], metavar="REF", help="take a dropped line back")
    rd("accept", _decide("accept", "accept the reorder list as a draft order"),
       "turn the pending list into a draft purchase order", tier="draft", roles="manager",
       api=["GET /hafo/reorder/list", "GET /settings", "POST /hafo/reorder/list/:id/accept"], example="siruk ops reorder accept")
    rd("reject", _decide("reject", "reject the reorder list"), "discard the pending list", tier="draft",
       api=["GET /hafo/reorder/list", "POST /hafo/reorder/list/:id/reject"], example="siruk ops reorder reject")

    p = reg.command(("ops", "hafo", "stock"), cmd_hafo_stock, "what hafo has, as the watch tower last read it",
                    api=["GET /hafo/stock"], roles="any role", example="siruk ops hafo stock royal")
    p.add_argument("q", nargs="?", help="search text")
    p.add_argument("--limit", type=int, help="at most this many rows (1-500)")
