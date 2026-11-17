"""Admin orders, payments, customers, subscribers. Request bodies use the field names the controllers validate
(siruk-web/backend/app/Http/Controllers/Admin/Customer/{OrderController,PaymentController,CustomerController}.php);
records use the Resources under Http/Resources/Admin/{Order,Customer}/; the status values are the enum cases in
app/Enums/{OrderStatus,PaymentStatus,PaymentType}.php (compared below when the sibling repo is present)."""
import json, os, re

import pytest

from siruk import cli
from siruk.admin import orders as O

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENUMS = os.path.join(os.path.dirname(ROOT), "siruk-web", "backend", "app", "Enums")


# SingleOrderResource::toArray: `allowed_next_statuses` = [{value, label}] from OrderStatus::canTransitionTo,
# `total` formatted by formatAdminPrice, `payment_method` the raw column,
# `gateway_payment_status` the Payment row's status
def order(i=5, status="accepted", payment_status="unpaid", method="cash_on_delivery", nxt=("delivered", "cancelled"),
          **kw):
    return {"data": {"id": i, "order_number": f"#10{i}", "status": status, "status_label": status.title(),
                     "payment_status": payment_status, "payment_method": method, "total": "12 500 AMD",
                     "gateway_payment_status": None,
                     "updated_at": "2026-11-16T10:00:00+00:00",
                     "allowed_next_statuses": [{"value": v, "label": v.title()} for v in nxt], **kw}}


# SinglePaymentResource::toArray (`can_check_status` is `(bool) payment_id`)
def payment(i=88, status="pending", can=True, **kw):
    return {"data": {"id": i, "order_id": 5, "order_number": "104", "order_status": "pending", "payment_id": "abc",
                     "amount": "12 500 AMD", "status": status, "type": "Card", "can_check_status": can,
                     "gateway_status": None, "gateway_details": {}, **kw}}


# SingleCustomerResource::toArray: `balance` is null for a customer without one, else `amount` as a float
def customer(i=42, amount=2000.0):
    return {"data": {"id": i, "name": "Anna Petrosyan", "email": "a@x.test",
                     "balance": None if amount is None else {"amount": amount, "formatted_amount": "x"}}}


def run(argv):
    with pytest.raises(SystemExit) as e:
        cli.main(["-q", *argv])
    return e.value.code


def writes(fc):
    return [c for c in fc.calls if c[0] != "GET"]


def dry_code(capsys, argv):
    assert run([*argv, "--json"]) == 0
    return json.loads(capsys.readouterr().out)["code"]


# --------------------------------------------------------------- the four writes + adjust-balance ----
def test_set_status_posts_status(admin_fake, capsys):
    # OrderController::updateStatus validates `status` (required string); route orders/{order}/update-status
    admin_fake.on("GET", "/orders/5", order())
    admin_fake.on("POST", "/orders/5/update-status", order(status="delivered"))
    code = dry_code(capsys, ["admin", "orders", "set-status", "5", "delivered"])
    assert writes(admin_fake) == []
    assert run(["admin", "orders", "set-status", "5", "delivered", "--apply", code]) == 0
    assert writes(admin_fake) == [("POST", "/orders/5/update-status", {"status": "delivered"})]


def test_set_status_takes_the_admin_label_and_sends_the_enum_value(admin_fake, capsys):
    admin_fake.on("GET", "/orders/5", order(status="pending", nxt=("accepted", "cancelled")))
    admin_fake.on("POST", "/orders/5/update-status", order(status="accepted"))
    code = dry_code(capsys, ["admin", "orders", "set-status", "5", "Received"])
    assert run(["admin", "orders", "set-status", "5", "received", "--apply", code]) == 0
    assert writes(admin_fake)[0][2] == {"status": "accepted"}


def test_set_payment_status_posts_payment_status(admin_fake, capsys):
    # OrderController::updatePaymentStatus validates `payment_status` (required, in PaymentStatus values)
    admin_fake.on("GET", "/orders/5", order())
    admin_fake.on("POST", "/orders/5/update-payment-status", order(payment_status="paid"))
    code = dry_code(capsys, ["admin", "orders", "set-payment-status", "5", "paid"])
    assert run(["admin", "orders", "set-payment-status", "5", "paid", "--apply", code]) == 0
    assert writes(admin_fake) == [("POST", "/orders/5/update-payment-status", {"payment_status": "paid"})]


def test_set_payment_type_posts_order_id_and_payment_type(admin_fake, capsys):
    # OrderController::updateOrderPaymentType validates order_id (integer), payment_type (required string max 50),
    # payment_method (nullable); route `POST update-order-payment-type`, the order id is in the body
    admin_fake.on("GET", "/orders/5", order())
    admin_fake.on("POST", "/update-order-payment-type", order(method="idram"))
    code = dry_code(capsys, ["admin", "orders", "set-payment-type", "5", "idram"])
    assert run(["admin", "orders", "set-payment-type", "5", "idram", "--apply", code]) == 0
    assert writes(admin_fake) == [("POST", "/update-order-payment-type", {"order_id": 5, "payment_type": "idram"})]


def test_payment_check_posts_without_a_body(admin_fake, capsys):
    # PaymentController::checkStatus reads nothing from the request; route payments/{payment}/check-status
    admin_fake.on("GET", "/payments/88", payment())
    admin_fake.on("POST", "/payments/88/check-status", {"message": "Bank status: Pending. Nothing changed."})
    code = dry_code(capsys, ["admin", "payments", "check", "88"])
    assert run(["admin", "payments", "check", "88", "--apply", code]) == 0
    assert writes(admin_fake) == [("POST", "/payments/88/check-status", None)]


def test_payment_check_refuses_a_payment_without_a_bank_id(admin_fake):
    admin_fake.on("GET", "/payments/88", payment(can=False))
    assert run(["admin", "payments", "check", "88"]) == 1
    assert writes(admin_fake) == []


def test_adjust_balance_posts_action_amount_comment(admin_fake, capsys):
    # CustomerController::adjustBalance validates action_type (add|subtract), amount (numeric min:1),
    # comment (nullable string max 255); route customers/{customer}/adjust-balance
    admin_fake.on("GET", "/customers/42", customer())
    admin_fake.on("POST", "/customers/42/adjust-balance", customer(amount=3000.0))
    argv = ["admin", "customers", "adjust-balance", "42", "add", "1000", "--note", "refund of order 104"]
    code = dry_code(capsys, argv)
    assert run([*argv, "--apply", code]) == 0
    assert writes(admin_fake) == [("POST", "/customers/42/adjust-balance",
                                   {"action_type": "add", "amount": 1000, "comment": "refund of order 104"})]


# ------------------------------------------------------------------- refusals, before any call ----
@pytest.mark.parametrize("argv", [
    ["orders", "set-status", "5", "shipping"],
    ["orders", "set-status", "5", ""],
    ["orders", "set-payment-status", "5", "settled"],
    ["orders", "set-payment-status", "5", "completed"],
    ["orders", "set-payment-type", "5", "bitcoin"],
    ["orders", "set-status", "abc", "delivered"],
    ["customers", "adjust-balance", "42", "add", "1000"],
    ["customers", "adjust-balance", "42", "add", "1000", "--note", "   "],
    ["customers", "adjust-balance", "42", "give", "1000", "--note", "x"],
    ["customers", "adjust-balance", "42", "add", "1005", "--note", "x"],
    ["customers", "adjust-balance", "42", "add", "0", "--note", "x"],
    ["customers", "adjust-balance", "42", "add", "-10", "--note", "x"],
    ["customers", "adjust-balance", "42", "add", "1000", "--note", "x" * 256],
], ids=lambda a: " ".join(a))
def test_refused_before_any_call(admin_fake, argv, capsys):
    assert run(["admin", *argv]) == 1
    assert admin_fake.calls == [] and "refused" in capsys.readouterr().err


def test_a_bad_status_is_refused_even_with_apply(admin_fake):
    assert run(["admin", "orders", "set-status", "5", "shipping", "--apply", "deadbeef"]) == 1
    assert admin_fake.calls == []


def test_a_status_the_order_cannot_reach_is_refused_after_the_read(admin_fake, capsys):
    admin_fake.on("GET", "/orders/5", order(status="completed", nxt=("refunded",)))
    assert run(["admin", "orders", "set-status", "5", "cancelled"]) == 1
    assert "can go to: refunded" in capsys.readouterr().err and writes(admin_fake) == []


@pytest.mark.parametrize("status", ["processing", "shipped"])
def test_legacy_statuses_are_in_the_enum_but_never_offered(admin_fake, status):
    # OrderController::updateStatus answers 422 for them; SingleOrderResource leaves them out of allowed_next_statuses
    admin_fake.on("GET", "/orders/5", order())
    assert run(["admin", "orders", "set-status", "5", status]) == 1
    assert writes(admin_fake) == []


def test_the_same_status_is_refused(admin_fake):
    admin_fake.on("GET", "/orders/5", order(status="delivered", nxt=("completed",)))
    assert run(["admin", "orders", "set-status", "5", "delivered"]) == 1
    admin_fake.on("GET", "/orders/6", order(6, payment_status="paid"))
    assert run(["admin", "orders", "set-payment-status", "6", "paid"]) == 1
    assert writes(admin_fake) == []


def test_subtracting_from_an_empty_balance_is_refused(admin_fake):
    admin_fake.on("GET", "/customers/42", customer(amount=None))
    assert run(["admin", "customers", "adjust-balance", "42", "subtract", "100", "--note", "x"]) == 1
    assert writes(admin_fake) == []


# --------------------------------------------------------- dry run vs. a record that moved on ----
CHANGES = [
    (["orders", "set-status", "5", "delivered"], "/orders/5", dict(), dict(payment_status="paid"),
     "/orders/5/update-status"),
    (["orders", "set-status", "5", "delivered"], "/orders/5", dict(), dict(status="pending", nxt=("delivered",)),
     "/orders/5/update-status"),
    (["orders", "set-payment-status", "5", "paid"], "/orders/5", dict(), dict(status="cancelled"),
     "/orders/5/update-payment-status"),
    (["orders", "set-payment-type", "5", "idram"], "/orders/5", dict(), dict(method="credit_card"),
     "/update-order-payment-type"),
]


@pytest.mark.parametrize("argv,get,before,after,post", CHANGES, ids=lambda x: x if isinstance(x, str) else "")
def test_an_order_that_changed_since_the_dry_run_voids_the_code(admin_fake, capsys, argv, get, before, after, post):
    admin_fake.on("GET", get, order(**before))
    admin_fake.on("POST", post, order())
    code = dry_code(capsys, ["admin", *argv])
    admin_fake.on("GET", get, order(**after))
    assert run(["admin", *argv, "--apply", code]) == 1
    assert writes(admin_fake) == []
    assert "different plan" in capsys.readouterr().err


def test_a_payment_that_changed_since_the_dry_run_voids_the_code(admin_fake, capsys):
    admin_fake.on("GET", "/payments/88", payment())
    admin_fake.on("POST", "/payments/88/check-status", {})
    code = dry_code(capsys, ["admin", "payments", "check", "88"])
    admin_fake.on("GET", "/payments/88", payment(status="paid"))
    assert run(["admin", "payments", "check", "88", "--apply", code]) == 1
    assert writes(admin_fake) == []


def test_a_balance_that_moved_voids_the_code_so_a_repeat_cannot_double_it(admin_fake, capsys):
    argv = ["admin", "customers", "adjust-balance", "42", "add", "1000", "--note", "gift"]
    admin_fake.on("GET", "/customers/42", customer())
    admin_fake.on("POST", "/customers/42/adjust-balance", customer(amount=3000.0))
    code = dry_code(capsys, argv)
    admin_fake.on("GET", "/customers/42", customer(amount=3000.0))
    assert run([*argv, "--apply", code]) == 1
    assert writes(admin_fake) == []


def test_a_second_order_field_that_does_not_matter_keeps_the_code(admin_fake, capsys):
    argv = ["admin", "orders", "set-status", "5", "delivered"]
    admin_fake.on("GET", "/orders/5", order())
    admin_fake.on("POST", "/orders/5/update-status", order())
    code = dry_code(capsys, argv)
    admin_fake.on("GET", "/orders/5", order(updated_at="2026-11-16T11:00:00+00:00", note="called"))
    assert run([*argv, "--apply", code]) == 0 and len(writes(admin_fake)) == 1


# ----------------------------------------------------------------------------- summaries ----
def summary_of(fc, capsys, id, now, to, *, method="cash_on_delivery", nxt=None, **kw):
    fc.on("GET", f"/orders/{id}", order(id, status=now, method=method, nxt=nxt or (to,), **kw))
    assert run(["admin", "orders", "set-status", str(id), to, "--json"]) == 0
    d = json.loads(capsys.readouterr().out)
    assert d["tier"] == "real-world" and f"{now} → {to}" in d["summary"]
    return d["summary"]


# Effects below: OrderStatus::canTransitionTo for the moves; NotificationService::sendOrderStatusPush / Email
# (accepted, delivered, cancelled), OpsOrderListener::handle, OrderStatusListener::handle, OrderService::updateStatus
def test_pending_to_accepted_runs_the_confirmation_only(admin_fake, capsys):
    s = summary_of(admin_fake, capsys, 5, "pending", "accepted", method="credit_card", gateway_payment_status="paid")
    assert "confirmation" in s and "Ops hears order.accepted" in s
    assert "captures" not in s and "ships" not in s and "pushes" not in s


def test_legacy_processing_to_accepted_pushes_without_email_and_tells_ops(admin_fake, capsys):
    s = summary_of(admin_fake, capsys, 5, "processing", "accepted", nxt=("accepted",))
    assert "pushes the customer" in s and "emails" not in s and "Ops hears order.accepted" in s
    assert "no stock change" in s and "confirmation" not in s


def test_delivered_on_a_cash_order_ships_credits_cashback_and_marks_it_paid(admin_fake, capsys):
    s = summary_of(admin_fake, capsys, 5, "accepted", "delivered")
    assert "pushes and emails the customer" in s and "Ops hears order.delivered" in s
    assert "ships the stock and credits cashback" in s and "marks the payment paid" in s


def test_delivered_on_a_paid_cash_order_does_not_mark_it_paid_again(admin_fake, capsys):
    assert "marks the payment paid" not in summary_of(admin_fake, capsys, 5, "accepted", "delivered",
                                                      payment_status="paid")


def test_delivered_to_completed_is_quiet_and_captures_a_paid_card(admin_fake, capsys):
    s = summary_of(admin_fake, capsys, 5, "delivered", "completed", method="credit_card",
                   gateway_payment_status="approved")
    assert "no customer notice" in s and "no Ops event" in s and "no stock change" in s
    assert "captures the card payment at Ameria (order total 12 500 AMD; the bank moves the payment's own amount)" in s


def test_the_bank_is_named_only_for_a_card_payment_the_bank_holds(admin_fake, capsys):
    assert "Ameria" not in summary_of(admin_fake, capsys, 5, "delivered", "completed", method="credit_card",
                                      gateway_payment_status="pending")
    assert "Ameria" not in summary_of(admin_fake, capsys, 6, "delivered", "completed", method="idram",
                                      gateway_payment_status="paid")


def test_cancelling_an_accepted_card_order_cancels_the_authorization_and_gives_back(admin_fake, capsys):
    s = summary_of(admin_fake, capsys, 5, "accepted", "cancelled", method="card", nxt=("delivered", "cancelled"),
                   gateway_payment_status="paid")
    assert "pushes and emails the customer" in s and "Ops hears order.cancelled" in s
    assert "refunds used balance, reverses cashback, rolls back promotion usage" in s
    assert "cancels the authorization of the card payment at Ameria" in s


def test_cancelling_a_pending_order_tells_ops_nothing(admin_fake, capsys):
    s = summary_of(admin_fake, capsys, 5, "pending", "cancelled", nxt=("accepted", "cancelled"))
    assert "no Ops event" in s and "pushes and emails the customer" in s


def test_refunding_tells_ops_gives_back_and_refunds_the_card(admin_fake, capsys):
    s = summary_of(admin_fake, capsys, 5, "delivered", "refunded", method="credit_card",
                   nxt=("completed", "refunded"), gateway_payment_status="approved")
    assert "no customer notice" in s and "Ops hears order.refunded" in s and "returns or releases the stock" in s
    assert "refunds the card payment at Ameria" in s and "sets the payment status refunded" in s


def test_a_card_payment_that_changes_at_the_bank_voids_the_code(admin_fake, capsys):
    argv = ["admin", "orders", "set-status", "5", "completed"]
    kw = dict(status="delivered", method="credit_card", nxt=("completed",))
    admin_fake.on("GET", "/orders/5", order(gateway_payment_status="pending", **kw))
    admin_fake.on("POST", "/orders/5/update-status", order())
    code = dry_code(capsys, argv)
    admin_fake.on("GET", "/orders/5", order(gateway_payment_status="approved", **kw))
    assert run([*argv, "--apply", code]) == 1
    assert writes(admin_fake) == []


def test_payment_status_and_type_summaries_say_when_ops_hears_it(admin_fake, capsys):
    admin_fake.on("GET", "/orders/5", order())
    for argv in (["set-payment-status", "5", "paid"], ["set-payment-type", "5", "idram"]):
        assert run(["admin", "orders", *argv, "--json"]) == 0
        assert "only if the order is accepted and was already sent" in json.loads(capsys.readouterr().out)["summary"]


def test_payment_check_says_the_bank_was_already_asked_and_the_young_order_rule(admin_fake, capsys):
    admin_fake.on("GET", "/payments/88", payment(gateway_status="Pending"))
    assert run(["admin", "payments", "check", "88", "--json"]) == 0
    s = json.loads(capsys.readouterr().out)["summary"]
    assert "already queried the bank" in s and "under 10 minutes old" in s and "bank Pending" in s


def test_payments_show_is_a_read_that_prints_the_record(admin_fake, capsys):
    admin_fake.on("GET", "/payments/88", payment())
    assert run(["admin", "payments", "show", "88"]) == 0
    assert "can_check_status" in capsys.readouterr().out and writes(admin_fake) == []
    assert run(["admin", "payments", "show", "88", "--json"]) == 0
    assert json.loads(capsys.readouterr().out) == payment()


def test_subtract_shows_the_clamped_balance(admin_fake, capsys):
    admin_fake.on("GET", "/customers/42", customer(amount=500.0))
    assert run(["admin", "customers", "adjust-balance", "42", "subtract", "1000", "--note", "x", "--json"]) == 0
    d = json.loads(capsys.readouterr().out)
    assert d["tier"] == "irreversible" and "500 → 0" in d["summary"] and "cannot go below 0" in d["summary"]


# ------------------------------------------------------------------------------------ reads ----
def test_orders_list_passes_the_filters_and_prints_status_and_total(admin_fake, capsys):
    # OrderController::index reads list, status, payment_status, payment_method, search, page; OrderResource::toArray
    row = {"id": 5, "order_number": "#105", "customer_name": "Anna", "payment_type": "Cash",
           "payment_status": "unpaid", "status": "accepted", "total": "12 500 AMD", "date": "Nov 16, 2026 10:00"}
    admin_fake.on("GET", "/orders", {"data": [row], "meta": {"last_page": 1}})
    assert run(["admin", "orders", "list", "--list", "current", "--status", "received,pending",
                "--payment-status", "unpaid", "--payment-method", "cod", "--search", "anna"]) == 0
    out = capsys.readouterr().out
    assert "accepted" in out and "12 500 AMD" in out and "#105" in out
    (_, _, q), = admin_fake.calls
    assert q == {"list": "current", "status": "accepted,pending", "payment_status": "unpaid",
                 "payment_method": "cash_on_delivery", "search": "anna"}


def test_orders_list_refuses_an_unknown_filter_value(admin_fake):
    assert run(["admin", "orders", "list", "--status", "shipping"]) == 1
    assert run(["admin", "orders", "list", "--list", "all"]) == 1
    assert run(["admin", "orders", "list", "--payment-method", "cash,idram"]) == 1
    assert admin_fake.calls == []


def test_list_json_is_the_raw_page_and_all_pages_are_walked(admin_fake, capsys):
    page = {"data": [{"id": 88}], "meta": {"last_page": 2}, "links": {"next": "x"}}
    admin_fake.on("GET", "/payments", page)
    assert run(["admin", "payments", "list", "--json", "--status", "pending"]) == 0
    assert json.loads(capsys.readouterr().out) == page
    assert run(["admin", "payments", "list", "--json", "--page", "all"]) == 0
    assert json.loads(capsys.readouterr().out) == {"data": [{"id": 88}, {"id": 88}]}


def test_customers_and_subscribers_list(admin_fake, capsys):
    # CustomerResource::toArray (completed_orders_*) and SubscriberResource::toArray (no id)
    admin_fake.on("GET", "/customers", {"data": [{"id": 42, "name": "Anna", "email": "a@x.test", "phone": "077",
                                                  "completed_orders_count": 3, "completed_orders_sum": "30 000"}]})
    admin_fake.on("GET", "/subscribers", {"data": [{"email": "s@x.test", "receive_email": True, "phone": None,
                                                    "receive_phone_sms": False, "subscribe_date": "Nov 01, 2026"}]})
    assert run(["admin", "customers", "list"]) == 0 and "30 000" in capsys.readouterr().out
    assert run(["admin", "subscribers", "list"]) == 0 and "s@x.test" in capsys.readouterr().out


def test_show_prints_the_record(admin_fake, capsys):
    admin_fake.on("GET", "/orders/5", order())
    assert run(["admin", "orders", "show", "5"]) == 0
    assert "payment_status" in capsys.readouterr().out


# --------------------------------------------------------------------------- the manifest ----
def manifest(capsys):
    assert run(["commands", "--json"]) == 0
    return {r["name"]: r for r in json.loads(capsys.readouterr().out)}


NAMES = {"admin orders list": "read", "admin orders show": "read", "admin orders set-status": "real-world",
         "admin orders set-payment-status": "real-world", "admin orders set-payment-type": "real-world",
         "admin payments list": "read", "admin payments show": "read", "admin payments check": "real-world",
         "admin customers list": "read", "admin customers show": "read",
         "admin customers adjust-balance": "irreversible", "admin subscribers list": "read"}


def test_the_commands_are_registered_with_tier_roles_api_and_example(capsys):
    by = manifest(capsys)
    for name, tier in NAMES.items():
        r = by[name]
        assert r["tier"] == tier and r["roles"] and r["api"] and r["example"].startswith("siruk admin"), name
        assert r["backend"] == "admin"


def test_no_command_deletes_a_customer(capsys):
    by = manifest(capsys)
    assert not [n for n, r in by.items() if any(re.match(r"DELETE\s+/customers", a) for a in r["api"])]
    assert "admin customers delete" not in by


# ------------------------------------------------------------------------- the enum files ----
def cases(name):
    with open(os.path.join(ENUMS, name + ".php"), encoding="utf-8") as f:
        return re.findall(r"^\s*case \w+ = '([^']+)';", f.read(), re.M)


@pytest.mark.skipif(not os.path.isdir(ENUMS), reason="the siruk-web sibling repo is not next to this one")
@pytest.mark.parametrize("enum,ours", [("OrderStatus", O.ORDER_STATUSES), ("PaymentStatus", O.PAYMENT_STATUSES),
                                       ("PaymentType", O.PAYMENT_TYPES)])
def test_our_values_are_the_enum_cases(enum, ours):
    assert list(ours) == cases(enum)


def test_the_helpers_canonicalise():
    assert O.order_status(" Ended ") == "completed" and O.order_status("canceled") == "cancelled"
    assert O.payment_type("COD") == "cash_on_delivery" and O.payment_type("card") == "credit_card"
    assert O.csv("received, pending", O.order_status) == "accepted,pending"
