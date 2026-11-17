"""`siruk ops stock | history | sales | report | orders | receipts | incidents | outbox | catalog |
settings | services | promotions` — what the office reads from Ops, and the two things it may start.

Every command here is a GET except `catalog sync` (pulls siruk's catalogue into Ops, never writes siruk) and
`outbox resend` (sends a failed message to siruk or Telegram again); both are dry runs until `--apply <code>`.
`--json` prints the API's answer unmodified.
"""
import os, urllib.parse

from siruk import output
from siruk.ops import client as _ops, guard, office, resolve
from siruk.payload import PayloadError

ROLE_TILL = "cashier, manager, warehouse"


def _get(path, **kw):
    return _ops.default().get(path, office.params(**kw) or None)


def _show(a, data, rows, cols, head=None, foot=None):
    """--json: the answer as it came; else an optional line above, the table, an optional line below."""
    if a.json:
        output.dump(data)
        return 0
    if head:
        print(head)
    if rows:
        output.table(rows, cols)
    else:
        print("nothing")
    if foot:
        print(foot)
    return 0


def _facts(pairs):
    for k, v in pairs:
        print(f"{k:<16} {'-' if v is None else v}")


# ---------------------------------------------------------------- stock ----
def cmd_stock(a):
    loc = resolve.location(a.location) if a.location else None
    r = _get("/reports/stock", locationId=loc and loc["id"], at=a.at) or {}
    cols = [("sku", "sku"), ("product", "product"), ("label", "label"), ("location", "location"),
            ("qty", "qty"), ("reserved", "reserved"), ("value", "value AMD")]
    return _show(a, r, office.stock_rows(r), cols,
                 foot=f"as of {r.get('at')}   total value {office.amd(r.get('totalValueMinor'))} AMD")


def cmd_history(a):
    v = resolve.variant(a.good)
    loc = resolve.location(a.location) if a.location else None
    r = _get(f"/reports/variants/{urllib.parse.quote(v['variantId'], safe='')}/history",
             locationId=loc and loc["id"], **{"from": a.date_from}, to=a.to, limit=office.limit(a.limit, "history")) or {}
    cols = [("at", "at"), ("location", "location"), ("kind", "kind"), ("document", "document"), ("change", "change"),
            ("after", "after"), ("reserved", "reserved"), ("value", "value AMD"), ("value_after", "value after"),
            ("flag", "")]
    ref = r.get("variant") or {}
    return _show(a, r, office.history_rows(r), cols,
                 head=f"{ref.get('sku')}  {office.name(ref.get('productName'))} {ref.get('label') or ''}".rstrip(),
                 foot="older movements exist: narrow with --from or raise --limit" if r.get("hasMore") else None)


# ---------------------------------------------------------------- till sales ----
def cmd_sales_list(a):
    r = _get("/sales", number=a.number, shiftId=office.uuid(a.shift, "--shift"),
             limit=office.limit(a.limit, "sales")) or []
    cols = [("number", "number"), ("sold", "sold"), ("status", "status"), ("total", "total AMD"),
            ("paid", "paid"), ("flags", "flags")]
    return _show(a, r, office.sale_rows(r), cols)


def cmd_sales_show(a):
    ref = a.sale.strip()
    if not resolve.UUID.fullmatch(ref):
        hit = _ops.default().get("/sales", {"number": ref}) or []
        if len(hit) != 1:
            raise PayloadError(f"{len(hit)} sales have the number {ref!r}" if hit else f"no sale has the number {ref!r}")
        ref = hit[0]["id"]
    s = _ops.default().get(f"/sales/{urllib.parse.quote(ref, safe='')}") or {}
    if a.json:
        output.dump(s)
        return 0
    _facts([("number", s.get("number")), ("sold", s.get("soldAt")), ("status", s.get("status")),
            ("total AMD", office.amd(s.get("totalMinor"))), ("discount AMD", office.amd(s.get("discountMinor"))),
            ("change AMD", office.amd(s.get("changeMinor"))), ("paid", ", ".join(
                f"{p.get('method')} {office.amd(p.get('amountMinor'))}" for p in s.get("payments") or [])),
            ("flags", ", ".join(s.get("flags") or [])), ("fiscal receipt", s.get("fiscalReceiptId"))])
    output.table(office.sale_line_rows(s), [("name", "line"), ("qty", "qty"), ("price", "price"),
                                            ("discount", "discount"), ("total", "total"), ("returned", "returned"),
                                            ("price_type", "price type")])
    return 0


# ---------------------------------------------------------------- reports ----
def cmd_report_sales(a):
    r = _get("/reports/sales", **{"from": a.date_from}, to=a.to, groupBy=a.group_by,
             channels=office.channels(a.channels)) or {}
    kind, cols, rows = office.sales_report_rows(r)
    t = r.get("totals") or {}
    foot = (f"{r.get('from')} .. {r.get('to')}   till {office.amd(t.get('tillMinor'))}  web {office.amd(t.get('webMinor'))}  "
            f"total {office.amd(t.get('totalMinor'))}  returns {office.amd(t.get('returnsMinor'))}  "
            f"net {office.amd(t.get('netMinor'))} AMD")
    return _show(a, r, rows, cols, foot=foot)


def _margin_lines(m):
    return [("revenue AMD", office.amd(m.get("revenueMinor"))), ("cost AMD", office.amd(m.get("costMinor"))),
            ("margin AMD", office.amd(m.get("marginMinor")))]


def cmd_report_margin(a):
    r = _get("/reports/margin", **{"from": a.date_from}, to=a.to, channels=office.channels(a.channels)) or {}
    if a.json:
        output.dump(r)
        return 0
    _facts([("from", r.get("from")), ("to", r.get("to")), *_margin_lines(r),
            ("margin %", r.get("marginPercent")), ("refunds AMD", office.amd(r.get("refundsMinor"))),
            ("returned cost AMD", office.amd(r.get("returnedCostMinor"))),
            ("uncosted AMD", office.amd(r.get("uncostedRevenueMinor")))])
    rows = [{"channel": c.get("channel"), "revenue": office.amd(c.get("revenueMinor")),
             "cost": office.amd(c.get("costMinor")), "margin": office.amd(c.get("marginMinor")),
             "pct": c.get("marginPercent"), "uncosted": office.amd(c.get("uncostedRevenueMinor"))}
            for c in r.get("channels") or []]
    output.table(rows, [("channel", "channel"), ("revenue", "revenue"), ("cost", "cost"), ("margin", "margin"),
                        ("pct", "margin %"), ("uncosted", "uncosted")])
    return 0


def cmd_report_analytics(a):
    r = _get("/reports/analytics", **{"from": a.date_from}, to=a.to, channels=office.channels(a.channels)) or {}
    if a.json:
        output.dump(r)
        return 0
    row = lambda label, f: {"channel": label, "orders": f.get("orders"), "sales": office.amd(f.get("salesMinor")),
                            "avg": office.amd(f.get("averageOrderMinor")), "refunds": office.amd(f.get("refundsMinor")),
                            "net": office.amd(f.get("netMinor")), "margin": office.amd(f.get("marginMinor")),
                            "pct": f.get("marginPercent")}
    rows = [row("all", r.get("totals") or {}), *[row(c.get("channel"), c) for c in r.get("byChannel") or []]]
    print(f"{r.get('from')} .. {r.get('to')}   channels {', '.join(r.get('channels') or [])}   (AMD)")
    output.table(rows, [("channel", "channel"), ("orders", "orders"), ("sales", "sales"), ("avg", "average"),
                        ("refunds", "refunds"), ("net", "net"), ("margin", "margin"), ("pct", "margin %")])
    top = office.sales_report_rows({"groupBy": "variant", "rows": r.get("topByMargin")})
    if top[2]:
        print("\ntop by margin")
        output.table(top[2], top[1])
    return 0


def cmd_report_accountant(a):
    mon = office.month(a.month)
    raw, filename = _ops.default().download("/reports/accountant.xlsx", {"month": mon})
    path = office.accountant_path(a.out, mon, filename)
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "wb") as f:
        f.write(raw)
    print(path)
    return 0


# ---------------------------------------------------------------- web orders ----
def cmd_orders_list(a):
    r = _get("/web-orders", prepStatus=a.prep_status, status=a.status, channel=a.channel, q=a.q,
             limit=office.limit(a.limit, "orders"), offset=a.offset) or {}
    cols = [("number", "number"), ("channel", "channel"), ("status", "status"), ("prep", "prep"),
            ("received", "received"), ("total", "total AMD"), ("customer", "customer"), ("phone", "phone"),
            ("receipt", "receipt")]
    items = r.get("items") or []
    return _show(a, r, office.order_rows(items), cols, foot=f"{len(items)} of {r.get('total')}")


def cmd_orders_show(a):
    ref = a.order.strip()
    if not resolve.UUID.fullmatch(ref):
        hit = [o for o in (_ops.default().get("/web-orders", {"q": ref, "limit": 500}) or {}).get("items") or []
               if str(o.get("number")).lower() == ref.lower()]
        if len(hit) != 1:
            raise PayloadError(f"{len(hit)} web orders have the number {ref!r}" if hit else f"no web order has the number {ref!r}")
        ref = hit[0]["id"]
    d = _ops.default().get(f"/web-orders/{urllib.parse.quote(ref, safe='')}") or {}
    if a.json:
        output.dump(d)
        return 0
    o = d.get("order") or {}
    _facts([("number", o.get("number")), ("channel", o.get("channel")), ("status", o.get("status")),
            ("prep", o.get("prepStatus")), ("received", o.get("receivedAt")), ("packed", o.get("packedAt")),
            ("total AMD", office.amd(o.get("totalMinor"))), ("delivery AMD", office.amd(o.get("deliveryFeeMinor"))),
            ("customer", o.get("customerName")), ("phone", o.get("phone")), ("address", o.get("address")),
            ("note", o.get("note")), ("receipt", o.get("saleReceiptStatus"))])
    output.table(office.order_line_rows(d), [("sku", "sku"), ("name", "line"), ("qty", "qty"), ("price", "price"),
                                            ("total", "total"), ("gift", "")])
    return 0


# ---------------------------------------------------------------- fiscal ----
def cmd_receipts_list(a):
    r = _get("/fiscal/receipts", status=a.status, kind=a.kind, saleId=office.uuid(a.sale, "--sale"),
             limit=office.limit(a.limit, "receipts")) or []
    cols = [("id", "id"), ("kind", "kind"), ("status", "status"), ("total", "total AMD"), ("fiscal", "fiscal no."),
            ("issued", "issued"), ("attempts", "tries"), ("error", "error")]
    return _show(a, r, office.receipt_rows(r), cols)


def cmd_incidents(a):
    r = _get("/fiscal/incidents") or []
    return _show(a, r, office.incident_rows(r), [("at", "at"), ("kind", "kind"), ("receipt", "receipt"),
                                                   ("till", "till"), ("detail", "detail")])


# ---------------------------------------------------------------- outbox ----
def cmd_outbox_list(a):
    r = _get("/outbox/failed") or {}
    counts = ", ".join(f"{c.get('topic')} {c.get('count')}" for c in r.get("counts") or []) or "none"
    return _show(a, r, office.outbox_rows(r.get("items")),
                 [("id", "id"), ("topic", "topic"), ("attempts", "tries"), ("created", "created"), ("error", "last error")],
                 head=f"failed messages: {counts}")


def cmd_outbox_resend(a):
    want = a.id.strip().lower()
    hit = [m for m in (_get("/outbox/failed") or {}).get("items") or [] if str(m.get("id")).lower() == want]
    if not hit:
        raise PayloadError(f"{a.id!r} is not in the failed list (`siruk ops outbox list`)")
    m = hit[0]
    return guard.run(a, steps=[guard.Step("POST", f"/outbox/{urllib.parse.quote(m['id'], safe='')}/resend",
                                          label=f"{m.get('topic')}, {m.get('attempts')} tries")],
                     summary=f"send the failed {m.get('topic')} message to {office.outbox_target(m.get('topic'))} again", tier="real-world",
                     shown_state=m, verify="siruk ops outbox list")


# ---------------------------------------------------------------- catalogue ----
def cmd_catalog_status(a):
    r = _get("/catalog/status") or {}
    if a.json:
        output.dump(r)
        return 0
    _facts([("last sync", r.get("lastSyncAt")), ("auto sync", r.get("autoSync")),
            ("token from", r.get("tokenSource")), ("running", r.get("running"))])
    return 0


def cmd_catalog_sync(a):
    status = _get("/catalog/status") or {}
    if not a.json and not a.apply:
        print(f"last sync {status.get('lastSyncAt') or 'never'}   running {status.get('running')}   "
              f"{'whole catalogue' if a.full else 'only what changed'}\n")
    return guard.run(a, steps=[guard.Step("POST", "/catalog/sync", {"full": True} if a.full else {})],
                     summary="pull siruk's catalogue into Ops (siruk itself is not written)", tier="draft",
                     shown_state={"running": status.get("running")}, verify="siruk ops catalog status")


# ---------------------------------------------------------------- settings, services, promotions ----
def cmd_settings_list(a):
    r = _get("/settings") or []
    return _show(a, r, office.setting_rows(r), [("key", "key"), ("value", "value"), ("default", "default"),
                                                  ("set", "set"), ("description", "what")])


def cmd_services_list(a):
    r = _get("/services", active="1" if a.active else None) or []
    return _show(a, r, office.service_rows(r), [("code", "code"), ("name", "name"), ("price", "price AMD"),
                                                  ("fiscal", "fiscal name"), ("adg", "ADG"), ("active", "active")])


def cmd_promotions_list(a):
    r = _get("/shop-promotions") or []
    return _show(a, r, office.promotion_rows(r), [("name", "name"), ("on", "on"), ("off", "off"), ("from", "from"),
                                                    ("until", "until"), ("active", "active")])


# ---------------------------------------------------------------- registration ----
def _range(p):
    p.add_argument("--from", dest="date_from", required=True, metavar="DAY", help="first day YYYY-MM-DD (shop time) or ISO time")
    p.add_argument("--to", required=True, metavar="DAY", help="last day, included, or ISO time")


def _channels(p):
    p.add_argument("--channels", metavar="LIST", help=f"comma list of {', '.join(office.CHANNELS)}; default all")


def register(reg):
    p = reg.command(("ops", "stock"), cmd_stock, "stock and its value at a date, per location",
                    api=["GET /reports/stock", "GET /locations"], roles="manager",
                    example="siruk ops stock --at 2026-10-31 --location MAIN")
    p.add_argument("--location", metavar="REF", help="location code or id; default every location")
    p.add_argument("--at", metavar="DATE", help="a day (end of that day, shop time) or ISO time; default now")

    p = reg.command(("ops", "history"), cmd_history, "every stock movement of one good",
                    api=["GET /goods/:id", "GET /goods", "GET /locations", "GET /reports/variants/:id/history"],
                    roles="manager", example="siruk ops history 4820000000017 --from 2026-10-01")
    p.add_argument("good", metavar="GOOD", help="id, SKU, barcode or accounting code")
    p.add_argument("--location", metavar="REF", help="location code or id")
    p.add_argument("--from", dest="date_from", metavar="DAY")
    p.add_argument("--to", metavar="DAY")
    p.add_argument("--limit", type=int, metavar="N", help=f"1 to {office.LIMITS['history']}")

    p = reg.command(("ops", "sales", "list"), cmd_sales_list, "till sales, newest first",
                    api=["GET /sales"], roles=ROLE_TILL, example="siruk ops sales list --limit 20")
    p.add_argument("--number", help="one sale by its number")
    p.add_argument("--shift", metavar="ID", help="the sales of one shift")
    p.add_argument("--limit", type=int, metavar="N", help=f"1 to {office.LIMITS['sales']}")
    p = reg.command(("ops", "sales", "show"), cmd_sales_show, "one till sale with its lines and payments",
                    api=["GET /sales/:id", "GET /sales"], roles=ROLE_TILL, example="siruk ops sales show 000123")
    p.add_argument("sale", metavar="SALE", help="id or sale number")

    p = reg.command(("ops", "report", "sales"), cmd_report_sales, "sales by day, good, payment or price type",
                    api=["GET /reports/sales"], roles="manager",
                    example="siruk ops report sales --from 2026-10-01 --to 2026-10-31 --group-by variant")
    _range(p)
    p.add_argument("--group-by", choices=office.GROUPINGS, help="default day")
    _channels(p)
    p = reg.command(("ops", "report", "margin"), cmd_report_margin, "revenue, cost and margin of a period",
                    api=["GET /reports/margin"], roles="manager",
                    example="siruk ops report margin --from 2026-10-01 --to 2026-10-31 --channels till")
    _range(p)
    _channels(p)
    p = reg.command(("ops", "report", "analytics"), cmd_report_analytics, "sales and margin by channel, top goods",
                    api=["GET /reports/analytics"], roles="manager",
                    example="siruk ops report analytics --from 2026-10-01 --to 2026-10-31")
    _range(p)
    _channels(p)
    p = reg.command(("ops", "report", "accountant"), cmd_report_accountant, "download the accountant's month file (xlsx)",
                    api=["GET /reports/accountant.xlsx"], roles="manager",
                    example="siruk ops report accountant --month 2026-10 -o runs/2026-11-16/oct.xlsx")
    p.add_argument("--month", required=True, metavar="YYYY-MM")
    p.add_argument("-o", "--out", metavar="FILE", help="file or folder; default runs/<today>/")

    p = reg.command(("ops", "orders", "list"), cmd_orders_list, "web orders (siruk, Glovo), newest first",
                    api=["GET /web-orders"], roles="any signed-in user",
                    example="siruk ops orders list --prep-status new --channel glovo")
    p.add_argument("--status", choices=office.WEB_STATUSES)
    p.add_argument("--prep-status", choices=office.PREP_STATUSES)
    p.add_argument("--channel", choices=office.WEB_CHANNELS)
    p.add_argument("--search", dest="q", metavar="TEXT", help="number, customer, phone, SKU or name")
    p.add_argument("--limit", type=int, metavar="N", help=f"1 to {office.LIMITS['orders']}; default 100")
    p.add_argument("--offset", type=int, metavar="N")
    p = reg.command(("ops", "orders", "show"), cmd_orders_show, "one web order with its lines",
                    api=["GET /web-orders/:id", "GET /web-orders"], roles="any signed-in user",
                    example="siruk ops orders show 10452")
    p.add_argument("order", metavar="ORDER", help="id or order number")

    p = reg.command(("ops", "receipts", "list"), cmd_receipts_list, "fiscal (HDM) receipts",
                    api=["GET /fiscal/receipts"], roles=ROLE_TILL, example="siruk ops receipts list --status failed")
    p.add_argument("--status", choices=office.FISCAL_STATUSES)
    p.add_argument("--kind", choices=office.FISCAL_KINDS)
    p.add_argument("--sale", metavar="ID", help="the receipts of one sale")
    p.add_argument("--limit", type=int, metavar="N", help=f"1 to {office.LIMITS['receipts']}")
    reg.command(("ops", "incidents"), cmd_incidents, "fiscal incidents the office should look at",
                api=["GET /fiscal/incidents"], roles="manager", example="siruk ops incidents")

    reg.command(("ops", "outbox", "list"), cmd_outbox_list, "messages to siruk or Telegram the outbox gave up on",
                api=["GET /outbox/failed"], roles="manager", example="siruk ops outbox list")
    p = reg.command(("ops", "outbox", "resend"), cmd_outbox_resend, "send one failed message to its target (siruk or Telegram) again",
                    api=["GET /outbox/failed", "POST /outbox/:id/resend"], tier="real-world", roles="manager",
                    example="siruk ops outbox resend 0b9c3a52-7c1d-4e0a-9d52-3f1d6c1f0a11")
    p.add_argument("id", metavar="ID", help="a message id from `ops outbox list`")

    reg.command(("ops", "catalog", "status"), cmd_catalog_status, "last catalogue sync and whether one is running",
                api=["GET /catalog/status"], roles="manager", example="siruk ops catalog status")
    p = reg.command(("ops", "catalog", "sync"), cmd_catalog_sync, "pull siruk's catalogue into Ops",
                    api=["GET /catalog/status", "POST /catalog/sync"], tier="draft", roles="manager",
                    example="siruk ops catalog sync --full")
    p.add_argument("--full", action="store_true", help="re-read everything and deactivate what siruk dropped")

    reg.command(("ops", "settings", "list"), cmd_settings_list, "the shop settings and their defaults",
                api=["GET /settings"], roles="manager", example="siruk ops settings list")
    p = reg.command(("ops", "services", "list"), cmd_services_list, "services sold at the till (delivery…)",
                    api=["GET /services"], roles=ROLE_TILL, example="siruk ops services list --active")
    p.add_argument("--active", action="store_true", help="only what the till can sell")
    reg.command(("ops", "promotions", "list"), cmd_promotions_list, "the shop's own till promotions",
                api=["GET /shop-promotions"], roles="manager", example="siruk ops promotions list")
