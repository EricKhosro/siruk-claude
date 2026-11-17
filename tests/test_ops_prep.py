"""Ops order prep, services and shop promotions. Paths and bodies follow the Ops sources: controllers
ops/apps/api/src/modules/{web-orders/web-orders.controller.ts, services/services.controller.ts,
shop-promotions/shop-promotions.controller.ts} and their dto/ (add-gift, mark-damaged, service, shop-promotion);
fixtures follow ops/packages/contracts/src/api/{web-orders,promotions}.ts, till.ts (ServiceRow), backoffice.ts (GoodsItem)."""
import copy, json, re

import pytest

from siruk import cli, commands
from siruk.ops import client as O, policy

ORDER = "55555555-5555-4555-8555-555555555555"
OWN = "aaaaaaa1-1111-4111-8111-111111111111"
OWN2 = "aaaaaaa2-2222-4222-8222-222222222222"
GIFT = "aaaaaaa3-3333-4333-8333-333333333333"
HAFO = "bbbbbbb1-1111-4111-8111-111111111111"
VAR = "22222222-2222-4222-8222-222222222222"
PRODUCT = "33333333-3333-4333-8333-333333333333"
SERVICE = "66666666-6666-4666-8666-666666666666"
PROMO = "77777777-7777-4777-8777-777777777777"


@pytest.fixture(autouse=True)
def only_ops_prep(monkeypatch):
    monkeypatch.setattr(commands, "GROUPS", ("ops_core", "ops_office", "ops_prep"))


def run(argv):
    with pytest.raises(SystemExit) as e:
        cli.main(["-q", *argv])
    return e.value.code


def writes(fake):
    return [c for c in fake.calls if c[0] != "GET"]


def code_of(out):
    return re.search(r"--apply ([0-9a-f]{8})", out).group(1)


def dry(argv, capsys):
    assert run(argv) == 0
    return code_of(capsys.readouterr().out)


# web-orders.ts WebOrderOwnLine / WebOrderHafoLine (the fields the commands read)
def own(lid, sku, qty, cost=None, gift=False, added=False):
    return {"id": lid, "sku": sku, "name": sku, "variantId": VAR, "quantity": qty, "unitPriceMinor": 0 if gift else 250000,
            "lineTotalMinor": 0, "isGift": gift, "addedInOps": added, "costMinor": cost, "priceTypeCode": "website",
            "stockUnit": "pack", "reserved": True, "onHand": 9, "reservedTotal": 2, "available": 7, "scaleCode": None}


def detail(prep="new", status="accepted", own_lines=None, hafo=True):
    # web-orders.ts WebOrderDetail { order: WebOrderHeader, ownLines, hafoLines, ... }
    return {"order": {"id": ORDER, "channel": "siruk", "sirukOrderId": 10452, "number": "10452", "status": status,
                      "prepStatus": prep, "paymentType": "idram", "totalMinor": 500000, "customerName": "Anna",
                      "phone": "+37400000000", "note": None, "channelStatus": None, "receivedAt": "2026-11-16T07:00:00.000Z",
                      "packedAt": None, "ownLineCount": 2, "hafoLineCount": 1, "saleReceiptStatus": None,
                      "deliveryFeeMinor": 0, "address": "Yerevan", "paidAt": None, "stockDocumentId": None},
            "ownLines": own_lines if own_lines is not None else [own(OWN, "RC-1", 2), own(OWN2, "RC-2", 1)],
            "hafoLines": [{"id": HAFO, "sku": "HF-1", "name": "Hafo thing", "variantId": VAR, "quantity": 1,
                           "unitPriceMinor": 100000, "lineTotalMinor": 100000, "isGift": False, "addedInOps": False,
                           "costMinor": None, "priceTypeCode": "website", "supplierStock": None}] if hafo else [],
            "purchaseOrders": [], "receipts": [], "channelUpdates": []}


class Shop:
    """The faked Ops with one order that can change between a dry run and its apply."""

    def __init__(self, fake, order=None):
        self.order = order or detail()
        fake.on("GET", f"/web-orders/{ORDER}", lambda p: copy.deepcopy(self.order))
        fake.on("GET", "/web-orders", {"items": [{"id": ORDER, "number": "10452"}], "total": 1})
        for method, tail in (("POST", "picking"), ("POST", "pack"), ("POST", "ship"), ("POST", "damaged"),
                             ("POST", "gifts")):
            fake.on(method, f"/web-orders/{ORDER}/{tail}", {})
        fake.on("DELETE", re.compile(rf"/web-orders/{ORDER}/gifts/.+"), {})
        self.fake = fake


# backoffice.ts GoodsItem + Paged
GOOD = {"variantId": VAR, "productId": PRODUCT, "sku": "RC-1", "barcode": "4820000000017", "accountingCode": None,
        "extraBarcodes": [], "stockUnit": "pack", "label": "2 kg", "productName": {"en": "Royal Canin"}, "brand": "Royal Canin"}
LOOSE = {**GOOD, "sku": "LOOSE-1", "stockUnit": "loose", "barcode": None}


def goods(fake, *items):
    fake.on("GET", "/goods", {"items": list(items), "total": len(items), "page": 1, "pageSize": 50})


# ---------------------------------------------------------------- manifest ----
NEW = {"ops orders accept": "draft", "ops orders gift add": "draft", "ops orders gift rm": "draft",
       "ops orders pack": "irreversible", "ops orders ship": "real-world", "ops orders damaged": "irreversible",
       "ops services add": "real-world", "ops services set": "real-world", "ops promotions add": "real-world",
       "ops promotions set": "real-world"}


def manifest():
    return cli.build_parser().parse_args(["commands"]).manifest


def test_the_commands_exist_with_their_tiers_and_manifest_fields():
    rows = {r["name"]: r for r in manifest()}
    for name, tier in NEW.items():
        r = rows[name]
        assert r["backend"] == "ops" and r["tier"] == tier and r["api"] and r["roles"] and r["help"], name
        assert r["example"].startswith("siruk " + name.split()[0] + " " + name.split()[1]), name
    assert "ops orders list" in rows and "ops orders show" in rows and rows["ops orders list"]["tier"] == "read"


def test_no_command_reaches_the_hdm_ready_for_pickup_or_the_goods_import():
    apis = [e for r in manifest() for e in r["api"]]
    assert not [e for e in apis if re.search(r"print-hdm|ready-for-pickup|armsoft-goods", e)]


# ------------------------------------------------------------------ policy ----
# office-api-keys.md route table: office:write / office:manage / office:admin routes and the closed ones
@pytest.mark.parametrize("method,path", [
    ("POST", "/web-orders/x/pack"), ("POST", "/web-orders/x/picking"), ("DELETE", "/web-orders/x/gifts/y"),
    ("PATCH", "/services/x"), ("POST", "/services"), ("PUT", "/shop-promotions/x"), ("POST", "/shop-promotions"),
    ("PUT", "/settings/k"), ("POST", "/users"), ("PATCH", "/users/x"), ("PATCH", "/tills/x"),
    ("PUT", "/catalog/auto-sync")])
def test_policy_passes_the_office_areas(method, path):
    assert policy.allowed(method, path) is None


@pytest.mark.parametrize("method,path", [
    ("POST", "/web-orders/x/print-hdm"), ("POST", "/tills"), ("POST", "/tills/x/rotate-key"),
    ("POST", "/purchase-orders/x/place"), ("POST", "/sales"), ("PUT", "/fiscal/device"),
    ("POST", "/catalog/armsoft-goods"), ("POST", "/glovo/orders/x/ready-for-pickup"), ("POST", "/api-keys"),
    ("POST", "/connectors/siruk"), ("PUT", "/WEB-ORDERS/x/Print-Hdm/")])
def test_policy_refuses_what_stays_in_the_app(method, path):
    assert "not from the CLI" in policy.allowed(method, path)


# ------------------------------------------------------------------- orders ----
def test_accept_is_a_dry_run_then_sends_one_post(ops_fake, capsys):
    Shop(ops_fake)
    code = dry(["ops", "orders", "accept", ORDER], capsys)
    assert writes(ops_fake) == []
    assert run(["ops", "orders", "accept", ORDER, "--apply", code]) == 0
    assert writes(ops_fake) == [("POST", f"/web-orders/{ORDER}/picking", None)]


def test_an_order_is_found_by_its_number(ops_fake, capsys):
    Shop(ops_fake)
    code = dry(["ops", "orders", "accept", "10452"], capsys)
    assert run(["ops", "orders", "accept", "10452", "--apply", code]) == 0
    assert ("GET", "/web-orders", {"q": "10452", "limit": 500}) in ops_fake.calls
    assert writes(ops_fake) == [("POST", f"/web-orders/{ORDER}/picking", None)]


@pytest.mark.parametrize("verb,state,words", [
    ("accept", {"prep": "packed"}, "already packed"), ("accept", {"prep": "picking"}, "already being picked"),
    ("accept", {"status": "cancelled"}, "cancelled"), ("ship", {"prep": "picking"}, "pack it before shipping"),
    ("ship", {"prep": "shipped"}, "already shipped"), ("pack", {"status": "refunded"}, "refunded"),
    ("pack", {"prep": "packed", "own": [own(OWN, "RC-1", 2, cost=100000)]}, "already packed")])
def test_a_step_the_server_would_refuse_sends_nothing(ops_fake, capsys, verb, state, words):
    Shop(ops_fake, detail(prep=state.get("prep", "new"), status=state.get("status", "accepted"),
                          own_lines=state.get("own")))
    assert run(["ops", "orders", verb, ORDER]) == 1
    assert words in capsys.readouterr().err and writes(ops_fake) == []


def test_gift_add_sends_variant_id_and_quantity_in_base_units(ops_fake, capsys):
    Shop(ops_fake)
    goods(ops_fake, GOOD)
    code = dry(["ops", "orders", "gift", "add", ORDER, "RC-1", "2"], capsys)
    assert writes(ops_fake) == []
    assert run(["ops", "orders", "gift", "add", ORDER, "RC-1", "2", "--apply", code]) == 0
    assert writes(ops_fake) == [("POST", f"/web-orders/{ORDER}/gifts", {"variantId": VAR, "quantity": 2})]


def test_gift_add_of_a_loose_good_takes_grams_or_kilograms(ops_fake, capsys):
    Shop(ops_fake)
    goods(ops_fake, LOOSE)
    code = dry(["ops", "orders", "gift", "add", ORDER, "LOOSE-1", "1.5kg"], capsys)
    assert run(["ops", "orders", "gift", "add", ORDER, "LOOSE-1", "1.5kg", "--apply", code]) == 0
    assert writes(ops_fake) == [("POST", f"/web-orders/{ORDER}/gifts", {"variantId": VAR, "quantity": 1500})]


@pytest.mark.parametrize("qty,words", [("0", "1 to 1000000"), ("1000001", "1 to 1000000"), ("2kg", "counted in pcs")])
def test_gift_add_refuses_a_quantity_the_dto_would_refuse(ops_fake, capsys, qty, words):
    Shop(ops_fake)
    goods(ops_fake, GOOD)
    assert run(["ops", "orders", "gift", "add", ORDER, "RC-1", qty]) == 1
    assert words in capsys.readouterr().err and writes(ops_fake) == []


def test_gifts_change_only_before_packing(ops_fake, capsys):
    Shop(ops_fake, detail(prep="packed"))
    goods(ops_fake, GOOD)
    assert run(["ops", "orders", "gift", "add", ORDER, "RC-1", "1"]) == 1
    assert "only before packing" in capsys.readouterr().err and writes(ops_fake) == []


def test_gift_rm_deletes_the_gift_line_and_only_a_gift_added_in_ops(ops_fake, capsys):
    Shop(ops_fake, detail(own_lines=[own(OWN, "RC-1", 2), own(GIFT, "TOY-1", 1, gift=True, added=True)]))
    code = dry(["ops", "orders", "gift", "rm", ORDER, "TOY-1"], capsys)
    assert run(["ops", "orders", "gift", "rm", ORDER, "TOY-1", "--apply", code]) == 0
    assert writes(ops_fake) == [("DELETE", f"/web-orders/{ORDER}/gifts/{GIFT}", None)]
    assert run(["ops", "orders", "gift", "rm", ORDER, "RC-1"]) == 1
    assert "no own line matches 'RC-1'" in capsys.readouterr().err and len(writes(ops_fake)) == 1


def test_gift_rm_refuses_a_packed_gift(ops_fake, capsys):
    Shop(ops_fake, detail(own_lines=[own(GIFT, "TOY-1", 1, cost=0, gift=True, added=True)]))
    assert run(["ops", "orders", "gift", "rm", ORDER, GIFT]) == 1
    assert "already packed" in capsys.readouterr().err and writes(ops_fake) == []


def test_pack_is_irreversible_and_sends_one_post(ops_fake, capsys):
    Shop(ops_fake, detail(prep="picking"))
    assert run(["ops", "orders", "pack", ORDER]) == 0
    out = capsys.readouterr().out
    assert "irreversible" in out and "2 own line(s) leave stock" in out and writes(ops_fake) == []
    assert run(["ops", "orders", "pack", ORDER, "--apply", code_of(out)]) == 0
    assert writes(ops_fake) == [("POST", f"/web-orders/{ORDER}/pack", None)]


def test_ship_is_real_world_and_sends_one_post(ops_fake, capsys):
    Shop(ops_fake, detail(prep="packed", own_lines=[own(OWN, "RC-1", 2, cost=100000)]))
    assert run(["ops", "orders", "ship", ORDER]) == 0
    out = capsys.readouterr().out
    assert "real-world" in out and writes(ops_fake) == []
    assert run(["ops", "orders", "ship", ORDER, "--apply", code_of(out)]) == 0
    assert writes(ops_fake) == [("POST", f"/web-orders/{ORDER}/ship", None)]


def test_damaged_sends_the_line_ids_once_each(ops_fake, capsys):
    Shop(ops_fake, detail(prep="packed", own_lines=[own(OWN, "RC-1", 2, cost=100000), own(OWN2, "RC-2", 1, cost=50000)]))
    argv = ["ops", "orders", "damaged", ORDER, "--lines", "RC-1,rc-2", OWN]
    code = dry(argv, capsys)
    assert writes(ops_fake) == []
    assert run([*argv, "--apply", code]) == 0
    assert writes(ops_fake) == [("POST", f"/web-orders/{ORDER}/damaged", {"lineIds": [OWN, OWN2]})]


@pytest.mark.parametrize("lines,words", [
    (["RC-2"], "never packed"), (["HF-1"], "hafo line"), (["NOPE"], "no own line matches")])
def test_damaged_refuses_what_the_server_would(ops_fake, capsys, lines, words):
    Shop(ops_fake, detail(prep="packed", own_lines=[own(OWN, "RC-1", 2, cost=100000), own(OWN2, "RC-2", 1)]))
    assert run(["ops", "orders", "damaged", ORDER, "--lines", *lines]) == 1
    assert words in capsys.readouterr().err and writes(ops_fake) == []


def test_damaged_on_a_refunded_order_is_sent_because_the_server_writes_the_goods_off_now(ops_fake, capsys):
    Shop(ops_fake, detail(prep="shipped", status="refunded", own_lines=[own(OWN, "RC-1", 2, cost=100000)]))
    assert run(["ops", "orders", "damaged", ORDER, "--lines", "RC-1"]) == 0
    out = capsys.readouterr().out
    assert "written off now" in out
    assert run(["ops", "orders", "damaged", ORDER, "--lines", "RC-1", "--apply", code_of(out)]) == 0
    assert writes(ops_fake) == [("POST", f"/web-orders/{ORDER}/damaged", {"lineIds": [OWN]})]


def test_ship_refuses_a_glovo_order(ops_fake, capsys):
    d = detail(prep="packed", own_lines=[own(OWN, "RC-1", 2, cost=1)])
    d["order"]["channel"] = "glovo"
    Shop(ops_fake, d)
    assert run(["ops", "orders", "ship", ORDER]) == 1
    assert "Glovo order" in capsys.readouterr().err and writes(ops_fake) == []


def test_gift_rm_by_sku_finds_the_gift_when_the_customer_bought_the_same_sku(ops_fake, capsys):
    Shop(ops_fake, detail(own_lines=[own(OWN, "RC-1", 2), own(GIFT, "RC-1", 1, gift=True, added=True)]))
    code = dry(["ops", "orders", "gift", "rm", ORDER, "RC-1"], capsys)
    assert run(["ops", "orders", "gift", "rm", ORDER, "RC-1", "--apply", code]) == 0
    assert writes(ops_fake) == [("DELETE", f"/web-orders/{ORDER}/gifts/{GIFT}", None)]


def test_damaged_refuses_more_lines_than_the_dto_takes(ops_fake, capsys):
    many = [own(f"{i:08x}-0000-4000-8000-000000000000", f"S{i}", 1, cost=1) for i in range(201)]
    Shop(ops_fake, detail(prep="packed", own_lines=many))
    assert run(["ops", "orders", "damaged", ORDER, "--lines", *[f"S{i}" for i in range(201)]]) == 1
    assert "at most 200" in capsys.readouterr().err and writes(ops_fake) == []


def test_a_prep_status_that_changed_since_the_dry_run_invalidates_the_code(ops_fake, capsys):
    shop = Shop(ops_fake, detail(prep="new"))
    code = dry(["ops", "orders", "accept", ORDER], capsys)
    shop.order = detail(prep="waiting_hafo")
    assert run(["ops", "orders", "accept", ORDER, "--apply", code]) == 1
    assert "state that has since changed" in capsys.readouterr().err and writes(ops_fake) == []
    shop.order = detail(prep="new")
    assert run(["ops", "orders", "accept", ORDER, "--apply", code]) == 0


def test_a_line_added_since_the_dry_run_invalidates_the_pack_code(ops_fake, capsys):
    shop = Shop(ops_fake, detail(prep="picking"))
    code = dry(["ops", "orders", "pack", ORDER], capsys)
    shop.order["ownLines"].append(own(GIFT, "TOY-1", 1, gift=True, added=True))
    assert run(["ops", "orders", "pack", ORDER, "--apply", code]) == 1 and writes(ops_fake) == []


def test_an_unknown_outcome_exits_3_and_a_repeat_after_it_gets_a_new_code(ops_fake, capsys):
    shop = Shop(ops_fake, detail(prep="picking"))
    code = dry(["ops", "orders", "pack", ORDER], capsys)
    ops_fake.on("POST", f"/web-orders/{ORDER}/pack", O.UnknownOutcome(0, "POST", f"/web-orders/{ORDER}/pack", "timed out"))
    assert run(["ops", "orders", "pack", ORDER, "--apply", code]) == 3
    assert "siruk ops orders show 10452" in capsys.readouterr().err
    shop.order = detail(prep="packed", own_lines=[own(OWN, "RC-1", 2, cost=1), own(OWN2, "RC-2", 1, cost=1)])
    assert run(["ops", "orders", "pack", ORDER, "--apply", code]) == 1


# ----------------------------------------------------------------- services ----
# till.ts ServiceRow: priceMinor is a string in the answer; services.dto CreateServiceDto/UpdateServiceDto: an int
def service(**over):
    return {"id": SERVICE, "code": "DELIVERY", "name": {"hy": "Առաքում", "en": "Delivery", "ru": None},
            "fiscalName": None, "adgCode": "5310", "priceMinor": None, "isActive": True, **over}


def test_service_add_sends_the_dto_fields_with_an_integer_price(ops_fake, capsys):
    ops_fake.on("GET", "/services", [service()]).on("POST", "/services", service())
    argv = ["ops", "services", "add", "NAIL_TRIM", "--name-en", "Nail trim", "--name-hy", "Եղունգ", "--price", "3000.50",
            "--fiscal-name", "Nail trim", "--adg-code", "9609", "--inactive"]
    code = dry(argv, capsys)
    assert writes(ops_fake) == []
    assert run([*argv, "--apply", code]) == 0
    assert writes(ops_fake) == [("POST", "/services", {
        "code": "NAIL_TRIM", "name": {"hy": "Եղունգ", "en": "Nail trim"}, "priceMinor": 300050,
        "fiscalName": "Nail trim", "adgCode": "9609", "isActive": False})]


@pytest.mark.parametrize("argv,words", [
    (["nail", "--name-en", "x"], "2-32 capitals"), (["DELIVERY", "--name-en", "x"], "exists"),
    (["NAIL_TRIM"], "at least one language"), (["NAIL_TRIM", "--name-en", "x", "--price", "0"], "at least 0.01"),
    (["NAIL_TRIM", "--name-en", "x" * 121], "at most 120"), (["NAIL_TRIM", "--name-en", "x", "--adg-code", "1" * 17], "at most 16")])
def test_service_add_refuses_what_the_dto_would(ops_fake, capsys, argv, words):
    ops_fake.on("GET", "/services", [service()])
    assert run(["ops", "services", "add", *argv]) == 1
    assert words in capsys.readouterr().err and writes(ops_fake) == []


def test_service_set_sends_the_whole_name_because_the_server_replaces_it(ops_fake, capsys):
    ops_fake.on("GET", "/services", [service()]).on("PATCH", f"/services/{SERVICE}", service())
    argv = ["ops", "services", "set", "delivery", "--name-ru", "Доставка", "--price", "1500"]
    code = dry(argv, capsys)
    assert run([*argv, "--apply", code]) == 0
    assert writes(ops_fake) == [("PATCH", f"/services/{SERVICE}", {
        "name": {"hy": "Առաքում", "en": "Delivery", "ru": "Доставка"}, "priceMinor": 150000})]


def test_service_set_can_clear_the_price_and_refuses_an_empty_change(ops_fake, capsys):
    ops_fake.on("GET", "/services", [service(priceMinor="150000")]).on("PATCH", f"/services/{SERVICE}", service())
    code = dry(["ops", "services", "set", SERVICE, "--ask-price", "--adg-code", ""], capsys)
    assert run(["ops", "services", "set", SERVICE, "--ask-price", "--adg-code", "", "--apply", code]) == 0
    assert writes(ops_fake) == [("PATCH", f"/services/{SERVICE}", {"priceMinor": None, "adgCode": None})]
    assert run(["ops", "services", "set", SERVICE]) == 1 and "nothing to change" in capsys.readouterr().err


def test_a_service_change_since_the_dry_run_invalidates_the_code(ops_fake, capsys):
    ops_fake.on("GET", "/services", [service()]).on("PATCH", f"/services/{SERVICE}", service())
    code = dry(["ops", "services", "set", "DELIVERY", "--price", "1000"], capsys)
    ops_fake.on("GET", "/services", [service(priceMinor="50000")])
    assert run(["ops", "services", "set", "DELIVERY", "--price", "1000", "--apply", code]) == 1
    assert writes(ops_fake) == []


# --------------------------------------------------------------- promotions ----
# promotions.ts ShopPromotionRow / ShopPromotionBody; shop-promotion.dto.ts: amountMinor is a string, percent an int
def promo(**over):
    return {"id": PROMO, "name": "Autumn", "target": "brand", "variantId": None, "productId": None, "brand": "Monge",
            "targetLabel": "Monge", "percent": 10, "amountMinor": None, "startsAt": "2026-11-19T20:00:00.000Z",
            "endsAt": "2026-11-30T20:00:00.000Z", "isActive": True, "createdAt": "2026-11-16T08:00:00.000Z", **over}


def test_promotion_add_by_brand_sends_percent_and_shop_time_days(ops_fake, capsys):
    ops_fake.on("GET", "/shop-promotions", [promo()]).on("POST", "/shop-promotions", promo())
    argv = ["ops", "promotions", "add", "--name", "Winter", "--brand", "Royal Canin", "--percent", "15",
            "--from", "2026-12-01", "--to", "2026-12-31"]
    code = dry(argv, capsys)
    assert writes(ops_fake) == []
    assert run([*argv, "--apply", code]) == 0
    assert writes(ops_fake) == [("POST", "/shop-promotions", {
        "name": "Winter", "target": "brand", "brand": "Royal Canin", "percent": 15,
        "startsAt": "2026-12-01T00:00:00+04:00", "endsAt": "2027-01-01T00:00:00+04:00"})]


def test_promotion_add_by_good_resolves_the_variant_and_sends_the_amount_as_a_string(ops_fake, capsys):
    ops_fake.on("GET", "/shop-promotions", []).on("POST", "/shop-promotions", promo())
    goods(ops_fake, GOOD)
    argv = ["ops", "promotions", "add", "--name", "Kibble", "--variant", "RC-1", "--amount", "500",
            "--from", "2026-12-01T09:00:00+04:00"]
    code = dry(argv, capsys)
    assert run([*argv, "--apply", code]) == 0
    assert writes(ops_fake) == [("POST", "/shop-promotions", {
        "name": "Kibble", "target": "variant", "variantId": VAR, "amountMinor": "50000",
        "startsAt": "2026-12-01T09:00:00+04:00"})]


def test_promotion_add_by_product_uses_the_goods_product_id(ops_fake, capsys):
    ops_fake.on("GET", "/shop-promotions", []).on("POST", "/shop-promotions", promo())
    goods(ops_fake, GOOD)
    argv = ["ops", "promotions", "add", "--name", "P", "--product", "RC-1", "--percent", "5", "--from", "2026-12-01"]
    assert run([*argv, "--apply", dry(argv, capsys)]) == 0
    body = writes(ops_fake)[0][2]
    assert body["target"] == "product" and body["productId"] == PRODUCT and "variantId" not in body


@pytest.mark.parametrize("argv,words", [
    (["--brand", "M", "--from", "2026-12-01"], "give the discount"),
    (["--brand", "M", "--amount", "5", "--percent", "5", "--from", "2026-12-01"], "not allowed with argument"),
    (["--percent", "5", "--from", "2026-12-01"], "needs its target"),
    (["--brand", "M", "--variant", "RC-1", "--percent", "5", "--from", "2026-12-01"], "one target"),
    (["--brand", "M", "--percent", "101", "--from", "2026-12-01"], "1 to 100"),
    (["--brand", "M", "--amount", "0", "--from", "2026-12-01"], "at least 0.01"),
    (["--brand", "M", "--percent", "5"], "first day"),
    (["--brand", "M", "--percent", "5", "--from", "2026-12-01T09:00:00"], "UTC offset"),
    (["--brand", "M", "--percent", "5", "--from", "2026-12-05", "--to", "2026-12-01"], "ends after it starts"),
    (["--brand", "M", "--percent", "5", "--from", "tomorrow"], "looks like")])
def test_promotion_add_refuses_what_the_server_would(ops_fake, capsys, argv, words):
    ops_fake.on("GET", "/shop-promotions", [])
    goods(ops_fake, GOOD)
    assert run(["ops", "promotions", "add", "--name", "X", *argv]) in (1, 2)
    assert words in capsys.readouterr().err and writes(ops_fake) == []


def test_promotion_set_replaces_the_whole_promotion(ops_fake, capsys):
    ops_fake.on("GET", "/shop-promotions", [promo()]).on("PUT", f"/shop-promotions/{PROMO}", promo())
    argv = ["ops", "promotions", "set", "autumn", "--amount", "250", "--inactive"]
    code = dry(argv, capsys)
    assert writes(ops_fake) == []
    assert run([*argv, "--apply", code]) == 0
    assert writes(ops_fake) == [("PUT", f"/shop-promotions/{PROMO}", {
        "name": "Autumn", "target": "brand", "brand": "Monge", "amountMinor": "25000",
        "startsAt": "2026-11-19T20:00:00+00:00", "endsAt": "2026-11-30T20:00:00+00:00", "isActive": False})]


def test_promotion_set_can_drop_the_end_and_move_to_another_target(ops_fake, capsys):
    ops_fake.on("GET", "/shop-promotions", [promo()]).on("PUT", f"/shop-promotions/{PROMO}", promo())
    goods(ops_fake, GOOD)
    argv = ["ops", "promotions", "set", PROMO, "--variant", "RC-1", "--no-end"]
    assert run([*argv, "--apply", dry(argv, capsys)]) == 0
    assert writes(ops_fake) == [("PUT", f"/shop-promotions/{PROMO}", {
        "name": "Autumn", "target": "variant", "variantId": VAR, "percent": 10,
        "startsAt": "2026-11-19T20:00:00+00:00"})]


def test_a_promotion_change_since_the_dry_run_invalidates_the_code(ops_fake, capsys):
    ops_fake.on("GET", "/shop-promotions", [promo()]).on("PUT", f"/shop-promotions/{PROMO}", promo())
    code = dry(["ops", "promotions", "set", "Autumn", "--percent", "20"], capsys)
    ops_fake.on("GET", "/shop-promotions", [promo(isActive=False)])
    assert run(["ops", "promotions", "set", "Autumn", "--percent", "20", "--apply", code]) == 1
    assert writes(ops_fake) == []


def test_two_promotions_with_the_same_name_must_be_named_by_id(ops_fake, capsys):
    ops_fake.on("GET", "/shop-promotions", [promo(), promo(id=ORDER)])
    assert run(["ops", "promotions", "set", "Autumn", "--percent", "20"]) == 1
    assert "2 promotions match" in capsys.readouterr().err and writes(ops_fake) == []
