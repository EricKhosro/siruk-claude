"""Orders, payments and customers on the admin API: the values the Laravel enums allow, and the plans
for the five writes (order status, payment status, payment type, a bank check, a balance adjustment).

Rules: a status or payment type outside the enums is refused before any call; an order can only go to
a status its own record lists in `allowed_next_statuses`; a balance adjustment needs a note and an AMD
amount in whole tens. Shapes: siruk-web/backend/app/Http/Controllers/Admin/Customer/*.php.
"""
from siruk.admin import guard, resource
from siruk.payload import PayloadError

SRC = "Http/Controllers/Admin/Customer/"
ORDERS = resource.Resource("order", "/orders", label="order_number", source=SRC + "OrderController.php")
PAYMENTS = resource.Resource("payment", "/payments", label="order", source=SRC + "PaymentController.php")
CUSTOMERS = resource.Resource("customer", "/customers", source=SRC + "CustomerController.php")
SUBSCRIBERS = resource.Resource("subscriber", "/subscribers", label="email", source=SRC + "CustomerController.php")

# app/Enums/OrderStatus.php (`normalize` also takes the admin labels); PaymentStatus.php; PaymentType.php
ORDER_STATUSES = ("pending", "accepted", "delivered", "completed", "cancelled", "refunded", "payment_failed",
                  "processing", "shipped")
ORDER_ALIASES = {"received": "accepted", "ended": "completed", "canceled": "cancelled"}
ORDER_LISTS = ("current", "history")   # OrderStatus::adminLists()
PAYMENT_STATUSES = ("unpaid", "pending", "paid", "failed", "refunded", "partially_refunded")
PAYMENT_TYPES = ("credit_card", "pos_terminal", "cash_on_delivery", "idram")
PAYMENT_ALIASES = {"cod": "cash_on_delivery", "cash": "cash_on_delivery", "card": "credit_card",
                   "pos": "pos_terminal"}
BANK = {"completed": "captures", "cancelled": "cancels the authorization of", "refunded": "refunds"}
GATEWAY_PAID = ("paid", "approved")   # OrderService::settleGatewayPayment acts on a payment in one of these
ACCEPTED_AGAIN = "Ops hears order.accepted again only if the order is accepted and was already sent to it"
ABANDONED_MINUTES = 10   # CheckoutPaymentService::ABANDONED_AFTER_MINUTES
GIVE_BACK = "returns or releases the stock, refunds used balance, reverses cashback, rolls back promotion usage"


def _pick(value, allowed, aliases, what):
    v = str(value or "").strip().lower()
    v = aliases.get(v, v)
    if v not in allowed:
        raise PayloadError(f"{what} {value!r} is not one of {', '.join(allowed)}")
    return v


def order_status(value):
    return _pick(value, ORDER_STATUSES, ORDER_ALIASES, "order status")


def payment_status(value):
    return _pick(value, PAYMENT_STATUSES, {}, "payment status")


def payment_type(value):
    return _pick(value, PAYMENT_TYPES, PAYMENT_ALIASES, "payment type")


def csv(value, one):
    """A comma list of values, each through `one`; None stays None."""
    return None if not value else ",".join(one(v) for v in str(value).split(",") if v.strip())


def order_list(value):
    if value not in (None, *ORDER_LISTS):
        raise PayloadError(f"--list is one of {', '.join(ORDER_LISTS)}")
    return value


def _id(value, what):
    if not str(value).isdigit():
        raise PayloadError(f"{what} id must be a number, got {value!r}")
    return str(value)


def _state(rec, keys):
    return {k: rec.get(k) for k in keys}


def _who(rec, key):
    return f"{rec.get(key) or ''}".strip()


ORDER_STATE = ("status", "payment_status", "payment_method", "total", "gateway_payment_status")


def effects(o, now, status):
    """What moving the order from `now` to `status` does, from the branches of OrderService, OrderStatusListener,
    OpsOrderListener and NotificationService."""
    method = str(o.get("payment_method") or "").lower()
    method = PAYMENT_ALIASES.get(method, method)
    if now == "pending" and status == "accepted":
        return ["runs the order confirmation (balance, promotion usage, confirmation email)",
                "Ops hears order.accepted"]
    notice = {"accepted": "pushes the customer", "delivered": "pushes and emails the customer",
              "cancelled": "pushes and emails the customer"}
    out = [notice.get(status, "no customer notice")]
    ops = {"accepted": "order.accepted", "delivered": "order.delivered", "refunded": "order.refunded"}.get(status)
    if status == "cancelled" and now != "pending":
        ops = "order.cancelled"
    if status == "completed" and now != "delivered":
        ops = "order.delivered"
    out.append(f"Ops hears {ops}" if ops else "no Ops event")
    if status == "delivered" or (status == "completed" and now != "delivered"):
        out.append("ships the stock and credits cashback")
    elif status in ("cancelled", "refunded"):
        out.append(GIVE_BACK)
    else:
        out.append("no stock change")
    if status == "delivered" and method == "cash_on_delivery" and o.get("payment_status") != "paid":
        out.append("marks the payment paid")
    if method == "credit_card" and status in BANK and o.get("gateway_payment_status") in GATEWAY_PAID:
        out.append(f"{BANK[status]} the card payment at Ameria (order total {o.get('total')}; "
                   f"the bank moves the payment's own amount)"
                   + (" and sets the payment status refunded" if status == "refunded" else ""))
    return out


def plan_set_status(id, status):
    status = order_status(status)
    id = _id(id, "order")
    o = resource.get(ORDERS, id)
    now = o.get("status")
    if now == status:
        raise PayloadError(f"order {id} is already {status}")
    if "allowed_next_statuses" in o:
        nxt = [n.get("value") for n in o["allowed_next_statuses"] or []]
        if status not in nxt:
            raise PayloadError(f"order {id} is {now}; it can go to: {', '.join(nxt) or 'nowhere'}")
    summary = (f"order {id} {_who(o, 'order_number')}: {now} → {status} (payment {o.get('payment_method')}, "
               f"{o.get('payment_status')}, total {o.get('total')}); " + "; ".join(effects(o, now, status)))
    return ([guard.Step("POST", f"/orders/{id}/update-status", {"status": status}, f"order {id} → {status}")],
            summary, _state(o, ORDER_STATE))


def plan_set_payment_status(id, value):
    value = payment_status(value)
    id = _id(id, "order")
    o = resource.get(ORDERS, id)
    if o.get("payment_status") == value:
        raise PayloadError(f"order {id} payment is already {value}")
    summary = (f"order {id} {_who(o, 'order_number')}: payment status {o.get('payment_status')} → {value} "
               f"(order {o.get('status')}, total {o.get('total')}); {ACCEPTED_AGAIN}; "
               f"paid also refreshes the customer's balance tier; no bank call")
    return ([guard.Step("POST", f"/orders/{id}/update-payment-status", {"payment_status": value},
                        f"order {id} payment → {value}")],
            summary, _state(o, ORDER_STATE))


def plan_set_payment_type(id, value):
    value = payment_type(value)
    id = _id(id, "order")
    o = resource.get(ORDERS, id)
    if o.get("payment_method") == value:
        raise PayloadError(f"order {id} already pays by {value}")
    summary = (f"order {id} {_who(o, 'order_number')}: payment type {o.get('payment_method')} → {value} "
               f"(order {o.get('status')}, payment {o.get('payment_status')}); {ACCEPTED_AGAIN}; no gateway capture")
    return ([guard.Step("POST", "/update-order-payment-type", {"order_id": int(id), "payment_type": value},
                        f"order {id} pays by {value}")],
            summary, _state(o, ORDER_STATE))


def plan_check(id):
    id = _id(id, "payment")
    p = resource.get(PAYMENTS, id)
    if not p.get("can_check_status"):
        raise PayloadError(f"payment {id} has no bank id: only card payments can be checked (Idram has no lookup)")
    summary = (f"payment {id} (order {p.get('order_number')}, {p.get('amount')}, {p.get('status')}, bank "
               f"{p.get('gateway_status') or 'unknown'}; reading it already queried the bank): asks the bank again; a "
               f"pending order is confirmed or failed as checkout would, unless it is under {ABANDONED_MINUTES} "
               f"minutes old, then nothing changes")
    return ([guard.Step("POST", f"/payments/{id}/check-status", None, f"check payment {id}")],
            summary, _state(p, ("status", "order_status", "amount", "gateway_status")))


def _amount(value):
    s = str(value).strip()
    if not s.isdigit() or int(s) < 10 or int(s) % 10:
        raise PayloadError(f"the amount is whole AMD in multiples of 10 (at least 10), got {value!r}")
    return int(s)


def plan_adjust_balance(id, action, amount, note):
    id = _id(id, "customer")
    if action not in ("add", "subtract"):
        raise PayloadError("the action is add or subtract")
    amount = _amount(amount)
    note = (note or "").strip()
    if not note:
        raise PayloadError("adjust-balance needs --note: why the balance changes")
    if len(note) > 255:
        raise PayloadError("--note is at most 255 characters")
    c = resource.get(CUSTOMERS, id)
    have = float((c.get("balance") or {}).get("amount") or 0)
    if action == "subtract" and have <= 0:
        raise PayloadError(f"customer {id} has no balance to subtract from")
    moved = amount if action == "add" else min(amount, have)
    after = have + moved if action == "add" else have - moved
    clamp = " (the balance cannot go below 0, so only that much is taken)" if moved < amount else ""
    summary = (f"customer {id} {_who(c, 'name')}: {action} {amount} AMD, balance {have:g} → {after:g}{clamp}; "
               f"note {note!r}")
    body = {"action_type": action, "amount": amount, "comment": note}
    return ([guard.Step("POST", f"/customers/{id}/adjust-balance", body, f"customer {id} {action} {amount}")],
            summary, {"balance": have})
