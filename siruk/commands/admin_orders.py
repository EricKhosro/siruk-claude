"""`siruk admin orders|payments|customers|subscribers`: read them, and change an order's status, payment
status or payment type, check a card payment with the bank, or adjust a customer's balance.

Every write is a dry run until `--apply <code>`; an order or payment change reaches the customer, Ops or
the bank (real-world), a balance adjustment is money (irreversible). Statuses are checked before any call.
"""
import json

from siruk import client as _client, output
from siruk.admin import guard, orders as O, resource
from siruk.payload import PayloadError

ROLES = "admin"


def _page_arg(s):
    if s == "all" or s.isdigit():
        return s
    raise PayloadError("--page is a number or 'all'")


def _lister(res, cols, extra=None):
    """A list command over `res`: a table of `cols`, or the API's JSON unmodified."""
    def cmd(a):
        params = extra(a) if extra else None
        if a.json and a.page != "all":
            output.dump(resource.list_page(res, search=a.search, page=a.page, params=params))
            return 0
        rows = resource.list_rows(res, search=a.search, page=a.page, params=params)
        if a.json:
            output.dump({"data": rows})
        else:
            output.table(rows, cols)
        return 0
    return cmd


def _list_args(p):
    p.add_argument("--search")
    p.add_argument("--page", type=_page_arg, help="a page number, or 'all'")


def _order_params(a):
    return {"list": O.order_list(a.list), "status": O.csv(a.status, O.order_status),
            "payment_status": O.csv(a.payment_status, O.payment_status),
            "payment_method": a.payment_method and O.payment_type(a.payment_method)}


def _status_params(a):
    return {"status": a.status}


def _write(a, plan, tier, verify):
    steps, summary, shown = plan
    return guard.run(a, steps=steps, summary=summary, tier=tier, shown_state=shown, verify=verify)


def _cell(v):
    return v if v is None or isinstance(v, (str, int, float, bool)) else json.dumps(v, ensure_ascii=False)[:40]


def cmd_payment_show(a):
    raw = _client.default().get(f"{O.PAYMENTS.path}/{_client.quote(a.id)}")
    if a.json:
        output.dump(raw)
        return 0
    rec = raw.get("data", raw) if isinstance(raw, dict) else {}
    output.table([{"field": k, "value": _cell(v)} for k, v in rec.items()], [("field", "field"), ("value", "value")])
    return 0


def cmd_set_status(a):
    plan = O.plan_set_status(a.id, a.status)
    return _write(a, plan, "real-world", f"siruk admin orders show {a.id}")


def cmd_set_payment_status(a):
    plan = O.plan_set_payment_status(a.id, a.payment_status)
    return _write(a, plan, "real-world", f"siruk admin orders show {a.id}")


def cmd_set_payment_type(a):
    plan = O.plan_set_payment_type(a.id, a.payment_type)
    return _write(a, plan, "real-world", f"siruk admin orders show {a.id}")


def cmd_check(a):
    return _write(a, O.plan_check(a.id), "real-world", f"siruk admin payments show {a.id}")


def cmd_adjust_balance(a):
    plan = O.plan_adjust_balance(a.id, a.action, a.amount, a.note)
    return _write(a, plan, "irreversible", f"siruk admin customers show {a.id}")


def register(reg):
    p = reg.command(("admin", "orders", "list"),
                    _lister(O.ORDERS, [("id", "id"), ("order_number", "order"), ("customer_name", "customer"),
                                       ("status", "status"), ("payment_status", "payment"),
                                       ("payment_type", "type"), ("total", "total"), ("date", "date")],
                            _order_params),
                    "list orders, newest first (one page, or --page all)", api=["GET /orders"], roles=ROLES,
                    example="siruk admin orders list --list current --payment-status unpaid")
    _list_args(p)
    p.add_argument("--list", help="current or history")
    p.add_argument("--status", help="order status, or a comma list")
    p.add_argument("--payment-status", help="payment status, or a comma list")
    p.add_argument("--payment-method", help="one payment type")
    resource.register_crud(reg, "orders", O.ORDERS, verbs=("show",), roles=ROLES)

    p = reg.command(("admin", "orders", "set-status"), cmd_set_status,
                    "move an order to another status (what it does depends on the move; the dry run lists it)",
                    api=["GET /orders/:id", "POST /orders/:id/update-status"], tier="real-world", roles=ROLES,
                    example="siruk admin orders set-status 1234 delivered")
    p.add_argument("id")
    p.add_argument("status", help="the status to move to (" + ", ".join(O.ORDER_STATUSES) + ")")
    p = reg.command(("admin", "orders", "set-payment-status"), cmd_set_payment_status,
                    "set an order's payment status (Ops hears it only if accepted and already sent; no bank call)",
                    api=["GET /orders/:id", "POST /orders/:id/update-payment-status"], tier="real-world",
                    roles=ROLES, example="siruk admin orders set-payment-status 1234 paid")
    p.add_argument("id")
    p.add_argument("payment_status", help=", ".join(O.PAYMENT_STATUSES))
    p = reg.command(("admin", "orders", "set-payment-type"), cmd_set_payment_type,
                    "correct how an order is paid (Ops hears it only if accepted and already sent; no capture)",
                    api=["GET /orders/:id", "POST /update-order-payment-type"], tier="real-world", roles=ROLES,
                    example="siruk admin orders set-payment-type 1234 cash_on_delivery")
    p.add_argument("id")
    p.add_argument("payment_type", help=", ".join(O.PAYMENT_TYPES))

    p = reg.command(("admin", "payments", "list"),
                    _lister(O.PAYMENTS, [("id", "id"), ("order", "order"), ("customer", "customer"),
                                         ("amount", "amount"), ("status", "status"), ("type", "type")],
                            _status_params),
                    "list payments, newest first (one page, or --page all)", api=["GET /payments"], roles=ROLES,
                    example="siruk admin payments list --status pending")
    _list_args(p)
    p.add_argument("--status", help="payment status or a comma list (paid, approved, disapproved, refunded, …)")
    p = reg.command(("admin", "payments", "show"), cmd_payment_show,
                    "one payment, with its live details from the bank (nothing changes)",
                    api=["GET /payments/:id"], roles=ROLES, example="siruk admin payments show 88")
    p.add_argument("id")
    p = reg.command(("admin", "payments", "check"), cmd_check,
                    "ask the bank for a card payment's status; a pending order is confirmed or failed",
                    api=["GET /payments/:id", "POST /payments/:id/check-status"], tier="real-world", roles=ROLES,
                    example="siruk admin payments check 88")
    p.add_argument("id")

    p = reg.command(("admin", "customers", "list"),
                    _lister(O.CUSTOMERS, [("id", "id"), ("name", "name"), ("email", "email"), ("phone", "phone"),
                                          ("completed_orders_count", "orders"),
                                          ("completed_orders_sum", "spent")]),
                    "list customers (one page, or --page all)", api=["GET /customers"], roles=ROLES,
                    example="siruk admin customers list --search anna")
    _list_args(p)
    resource.register_crud(reg, "customers", O.CUSTOMERS, verbs=("show",), roles=ROLES)
    p = reg.command(("admin", "customers", "adjust-balance"), cmd_adjust_balance,
                    "add to or subtract from a customer's balance, in AMD (multiples of 10), with a note",
                    api=["GET /customers/:id", "POST /customers/:id/adjust-balance"], tier="irreversible",
                    roles=ROLES, example="siruk admin customers adjust-balance 42 add 1000 --note 'refund 1234'")
    p.add_argument("id")
    p.add_argument("action", help="add or subtract")
    p.add_argument("amount", help="AMD, a multiple of 10")
    p.add_argument("--note", help="why: required, at most 255 characters")

    p = reg.command(("admin", "subscribers", "list"),
                    _lister(O.SUBSCRIBERS, [("email", "email"), ("phone", "phone"), ("receive_email", "email?"),
                                            ("receive_phone_sms", "sms?"), ("subscribe_date", "since")]),
                    "list newsletter subscribers (one page, or --page all)", api=["GET /subscribers"],
                    roles=ROLES, example="siruk admin subscribers list --page all")
    _list_args(p)
