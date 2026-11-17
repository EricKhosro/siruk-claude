"""Ops purchasing commands: suppliers, purchase orders, the hafo reorder list. Fixture shapes and request bodies use
the field names of siruk-web/ops/packages/contracts/src/api/{backoffice,hafo}.ts and the DTOs under
siruk-web/ops/apps/api/src/modules/{suppliers,hafo}/dto (the path is above each fixture)."""
import copy, json, re

import pytest

from siruk import cli, commands
from siruk.ops import client as O, guard, policy
from siruk.ops import purchasing as P
from siruk.payload import PayloadError

SUP_ID = "5b1a7f0c-2d3e-4a5b-8c6d-7e8f90a1b2c3"
OTHER_SUP_ID = "6c2b8a1d-3e4f-4b6c-9d7e-8f90a1b2c3d4"
PO_ID = "0b9c3a52-7c1d-4e0a-9d52-3f1d6c1f0a11"
LINE_A = "11111111-1111-4111-8111-111111111111"
LINE_B = "22222222-2222-4222-8222-222222222222"
VAR_A = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
VAR_B = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
LOC_ID = "cccccccc-cccc-4ccc-8ccc-cccccccccccc"
WEB_ORDER = "dddddddd-dddd-4ddd-8ddd-dddddddddddd"
LIST_ID = "eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee"
RLINE_A = "f1111111-1111-4111-8111-111111111111"
RLINE_B = "f2222222-2222-4222-8222-222222222222"
UUID_V4 = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}")

# backoffice.ts SupplierRow
SUPPLIER = {"id": SUP_ID, "name": "Pet House", "tin": "00000001", "armsoftCode": "0001", "connector": "hafo",
            "isActive": True, "balanceMinor": "250000"}
OTHER = {"id": OTHER_SUP_ID, "name": "Zoo Trade", "tin": None, "armsoftCode": None, "connector": None,
         "isActive": True, "balanceMinor": "0"}
# backoffice.ts GoodsItem (the fields resolve.variant reads) and Paged
GOODS = {"387957": {"variantId": VAR_A, "sku": "387957", "barcode": "8009470387958", "accountingCode": "0352",
                    "extraBarcodes": [], "stockUnit": "pack", "label": "Salmon 1250 g", "productName": {"en": "Chunks"}},
         "387967": {"variantId": VAR_B, "sku": "387967", "barcode": "8009470387968", "accountingCode": "0353",
                    "extraBarcodes": [], "stockUnit": "pack", "label": "Veal 1250 g", "productName": {"en": "Chunks"}},
         "LOOSE": {"variantId": "99999999-9999-4999-8999-999999999999", "sku": "LOOSE", "barcode": None,
                   "accountingCode": None, "extraBarcodes": [], "stockUnit": "loose", "label": None,
                   "productName": {"en": "Loose"}}}


def line(i, var, sku, qty, got=0, closed=0, cost="130000"):
    # hafo.ts HafoPurchaseOrderLine
    return {"id": i, "variantId": var, "sku": sku, "label": None, "barcode": GOODS[sku]["barcode"], "productName": "Chunks",
            "quantity": qty, "unitCostMinor": cost, "hafoSku": None, "hafoUnits": 1, "hafoQuantity": None,
            "hafoInStock": None, "hafoObservedAt": None, "allocations": [], "receivedQuantity": got,
            "closedQuantity": closed, "openQuantity": qty - got - closed}


def order(status="placed", hafo=True, lines=None, ref="H-1187"):
    # hafo.ts HafoPurchaseOrder
    lines = lines if lines is not None else [line(LINE_A, VAR_A, "387957", 6), line(LINE_B, VAR_B, "387967", 4)]
    return {"id": PO_ID, "number": "PO-0042", "kind": "restock", "status": status, "supplierId": SUP_ID,
            "supplierName": "Pet House", "webOrderId": None, "webOrderNumber": None, "webOrders": [],
            "externalRef": ref if status != "draft" else None, "placedAt": None, "placedById": None, "placing": False,
            "note": None, "createdAt": "2026-11-15T09:00:00.000Z", "lineCount": len(lines),
            "knownCostMinor": "1300000", "allCostsKnown": True, "orderedQuantity": 10, "receivedQuantity": 0,
            "closedQuantity": 0, "isHafo": hafo, "lines": lines, "invoices": [], "receipts": []}


def rline(i, var, sku, qty, dropped=False):
    # hafo.ts ReorderListLine
    return {"id": i, "variantId": var, "sku": sku, "label": None, "barcode": GOODS[sku]["barcode"], "productName": "Chunks",
            "freeOwnStock": 1, "openRestockQuantity": 0, "position": 1, "point": 3, "target": 8, "hafoQuantity": 50,
            "suggestedQuantity": 6, "quantity": qty, "edited": False, "dropped": dropped, "flag": None}


def rlist(status="pending"):
    # hafo.ts ReorderList / ReorderListResponse
    return {"id": LIST_ID, "status": status, "createdAt": "2026-11-16T04:00:00.000Z",
            "refreshedAt": "2026-11-16T04:00:00.000Z", "decidedAt": None, "purchaseOrderId": None,
            "purchaseOrderNumber": None,
            "lines": [rline(RLINE_A, VAR_A, "387957", 6), rline(RLINE_B, VAR_B, "387967", 4)]}


def setting(on):
    # auth.ts SettingEntry
    return {"key": "reorder.autoPlace", "value": on, "default": False, "isDefault": not on,
            "description": "place accepted lists with hafo", "updatedAt": None}


def run(argv):
    with pytest.raises(SystemExit) as e:
        cli.main(["-q", *argv])
    return e.value.code


def writes(fake):
    return [c for c in fake.calls if c[0] != "GET"]


def plan(argv, capsys):
    capsys.readouterr()
    assert run([*argv, "--json"]) == 0
    return json.loads(capsys.readouterr().out)


def applied(fake, argv, capsys):
    """A dry run, then the same command with the code it printed; the writes the second one made."""
    code = plan(argv, capsys)["code"]
    assert not writes(fake)
    assert run([*argv, "--apply", code, "--json"]) == 0
    return writes(fake)


@pytest.fixture
def api(ops_fake):
    f = ops_fake
    for method in ("POST", "PUT", "PATCH"):
        f.on(method, re.compile(".*"), {"ok": True})
    f.on("GET", "/suppliers", [SUPPLIER, OTHER])
    f.on("GET", "/goods", lambda p: {"items": [g for k, g in GOODS.items() if p["q"].lower() in (k.lower(), g["barcode"] or "")],
                                      "total": 1, "page": 1, "pageSize": 50})
    f.on("GET", "/locations", [{"id": LOC_ID, "code": "SHOP", "name": "Shop", "kind": "shop", "isActive": True,
                                "sirukWarehouseCode": None, "armsoftStorage": None, "supplierId": None,
                                "connector": None}])
    f.on("GET", "/purchase-orders", [order()])
    f.on("GET", f"/purchase-orders/{PO_ID}", order())
    f.on("GET", "/hafo/reorder/list", {"list": rlist(), "dailyRunEnabled": True})
    f.on("GET", "/settings", [setting(False)])
    return f


P4 = ["ops suppliers list", "ops suppliers show", "ops suppliers create", "ops suppliers set", "ops suppliers ledger",
      "ops suppliers pay", "ops suppliers adjust", "ops suppliers statement-check", "ops po list", "ops po show",
      "ops po create", "ops po lines", "ops po sent", "ops po receive", "ops po not-received", "ops po reopen",
      "ops po delivered", "ops po cancel", "ops po from-web-order", "ops reorder show", "ops reorder list",
      "ops reorder build", "ops reorder lines", "ops reorder accept", "ops reorder reject", "ops hafo stock"]
NEVER = re.compile(r"^/purchase-orders/[^/]+/(place|release)$|^/hafo/(crawl|account-orders)")


def test_every_p4_command_is_in_the_manifest_and_none_reaches_a_refused_path(capsys):
    assert run(["commands", "--json"]) == 0
    rows = {r["name"]: r for r in json.loads(capsys.readouterr().out)}
    assert set(P4) <= set(rows)
    for name in P4:
        r = rows[name]
        assert r["backend"] == "ops" and r["api"] and r["help"] and r["example"] and r["roles"], name
        assert r["tier"] in ("read", "draft", "irreversible"), name
        for endpoint in r["api"]:
            method, path = endpoint.split(" ", 1)
            assert not NEVER.match(path), endpoint
            assert method == "GET" or not policy.allowed(method, path.replace(":id", PO_ID).replace(
                ":webOrderId", WEB_ORDER)), endpoint
    assert not [n for n, r in rows.items() for e in r["api"] if NEVER.match(e.split(" ", 1)[1])]
    for name in ("lines", "sent", "receive", "not-received", "reopen", "delivered", "cancel"):
        assert "GET /purchase-orders" in rows[f"ops po {name}"]["api"], name
    assert "GET /suppliers" in rows["ops po list"]["api"] and "GET /settings" in rows["ops reorder accept"]["api"]
    assert rows["ops po sent"]["tier"] == "irreversible"
    assert rows["ops po receive"]["tier"] == "irreversible" and rows["ops suppliers pay"]["tier"] == "irreversible"
    assert rows["ops reorder accept"]["tier"] == "draft" and rows["ops po create"]["tier"] == "draft"
    assert rows["ops po list"]["tier"] == rows["ops suppliers statement-check"]["tier"] == "read"


def test_the_policy_still_refuses_place_and_release():
    assert policy.allowed("POST", f"/purchase-orders/{PO_ID}/place") and policy.allowed("POST", f"/purchase-orders/{PO_ID}/release")


# suppliers/dto/create-supplier.dto.ts
def test_supplier_create_posts_the_dto_fields(api, capsys):
    out = applied(api, ["ops", "suppliers", "create", "Zoo Trade 2", "--tin", "123", "--armsoft-code", "77",
                        "--connector", "other"], capsys)
    assert out == [("POST", "/suppliers", {"name": "Zoo Trade 2", "tin": "123", "armsoftCode": "77", "connector": "other"})]


def test_supplier_create_sends_only_what_was_given(api, capsys):
    assert applied(api, ["ops", "suppliers", "create", "Bare"], capsys) == [("POST", "/suppliers", {"name": "Bare"})]


# suppliers/dto/update-supplier.dto.ts
def test_supplier_set_patches_and_clears(api, capsys):
    out = applied(api, ["ops", "suppliers", "set", "Pet House", "--name", "Pet House LLC", "--inactive",
                        "--clear", "tin", "--clear", "connector"], capsys)
    assert out == [("PATCH", f"/suppliers/{SUP_ID}",
                    {"name": "Pet House LLC", "isActive": False, "tin": None, "connector": None})]
    assert run(["ops", "suppliers", "set", "Pet House"]) == 1
    assert run(["ops", "suppliers", "set", "Pet House", "--tin", "1", "--clear", "tin"]) == 1


def test_supplier_is_found_by_tin_and_an_unknown_one_is_refused(api, capsys):
    assert [c for c in applied(api, ["ops", "suppliers", "set", "00000001", "--name", "X"], capsys)][0][1] == f"/suppliers/{SUP_ID}"
    assert run(["ops", "suppliers", "show", "Nobody"]) == 1


# suppliers/dto/record-payment.dto.ts
def test_pay_sends_minor_units_a_uuid_and_a_stable_client_payment_id(api, capsys):
    argv = ["ops", "suppliers", "pay", "Pet House", "--amount-amd", "1300", "--method", "bank",
            "--date", "2026-11-16", "--note", "october"]
    first = plan(argv, capsys)
    body = first["requests"][0]["body"]
    assert first["tier"] == "irreversible" and first["requests"][0]["path"] == f"/suppliers/{SUP_ID}/payments"
    assert body["amountMinor"] == "130000"
    assert {k: v for k, v in body.items() if k != "clientPaymentId"} == {
        "amountMinor": "130000", "date": "2026-11-16", "method": "bank", "note": "october"}
    assert UUID_V4.fullmatch(body["clientPaymentId"])
    assert plan(argv, capsys) == first
    assert plan([*argv[:-1], "november"], capsys)["requests"][0]["body"]["clientPaymentId"] != body["clientPaymentId"]
    out = applied(api, argv, capsys)
    assert out == [("POST", f"/suppliers/{SUP_ID}/payments", body)]
    assert not [c for c in api.calls if c[2] and c[2].get("amountMinor") == 1300]


def test_pay_refuses_what_the_api_would(api):
    base = ["ops", "suppliers", "pay", "Pet House", "--method", "cash"]
    for amount in ("0", "-5", "12.345", "abc"):
        assert run([*base, "--amount-amd", amount]) == 1, amount
    assert run([*base, "--amount-amd", "5", "--date", "16.11.2026"]) == 1
    assert not writes(api)


# suppliers/dto/record-adjustment.dto.ts
def test_adjust_is_signed_needs_a_note_and_never_zero(api, capsys):
    argv = ["ops", "suppliers", "adjust", "Pet House", "--amount-amd=-500.5", "--note", "credit note 17",
            "--date", "2026-11-16"]
    out = applied(api, argv, capsys)
    path, body = out[0][1], out[0][2]
    assert path == f"/suppliers/{SUP_ID}/adjustments"
    assert {k: v for k, v in body.items() if k != "clientAdjustmentId"} == {
        "amountMinor": "-50050", "date": "2026-11-16", "note": "credit note 17"}
    assert UUID_V4.fullmatch(body["clientAdjustmentId"])
    api.calls.clear()
    assert run(["ops", "suppliers", "adjust", "Pet House", "--amount-amd", "0", "--note", "why not"]) == 1
    assert run(["ops", "suppliers", "adjust", "Pet House", "--amount-amd", "5", "--note", "ab"]) == 1
    assert not writes(api)
    assert plan(["ops", "suppliers", "adjust", "Pet House", "--amount-amd", "+5", "--note", "abc", "--date",
                 "2026-11-16"], capsys)["requests"][0]["body"]["amountMinor"] == "500"


def test_stacked_signs_on_an_amount_are_refused(api):
    for amount in ("+-5", "--5", "-+5", "++5", "-", "+"):
        assert run(["ops", "suppliers", "adjust", "Pet House", f"--amount-amd={amount}", "--note", "abc"]) == 1, amount
        assert run(["ops", "suppliers", "pay", "Pet House", f"--amount-amd={amount}", "--method", "cash"]) == 1, amount
    assert not writes(api)


# suppliers/dto/statement-check.dto.ts: a POST that only compares
def test_statement_check_posts_the_month_and_total(api, capsys):
    result = {"month": "2026-10", "from": "2026-09-30T20:00:00.000Z", "to": "2026-10-31T20:00:00.000Z",
              "ourInvoicesMinor": "100000", "statementTotalMinor": "120000", "differenceMinor": "20000",
              "matches": False, "invoices": [{"id": "i1", "invoiceSerial": "A-1", "amountMinor": "100000",
                                              "entryDate": "2026-10-05T00:00:00.000Z"}]}
    api.on("POST", f"/suppliers/{SUP_ID}/statement-check", result)
    capsys.readouterr()
    assert run(["ops", "suppliers", "statement-check", "Pet House", "--month", "2026-10", "--statement-amd", "1200"]) == 0
    assert api.calls[-1] == ("POST", f"/suppliers/{SUP_ID}/statement-check",
                             {"month": "2026-10", "statementTotalMinor": "120000"})
    assert "DOES NOT MATCH" in capsys.readouterr().out
    assert run(["ops", "suppliers", "statement-check", "Pet House", "--month", "2026-13", "--statement-amd", "1"]) == 1


def test_supplier_reads(api, capsys):
    capsys.readouterr()
    assert run(["ops", "suppliers", "list"]) == 0
    out = capsys.readouterr().out
    assert "Pet House" in out and "2500" in out and "250000" not in out
    assert run(["ops", "suppliers", "list", "--json"]) == 0
    assert json.loads(capsys.readouterr().out) == [SUPPLIER, OTHER]
    ledger = {"supplier": {"id": SUP_ID, "name": "Pet House"}, "from": None, "to": None, "openingBalanceMinor": "0",
              "entries": [{"id": "e1", "kind": "invoice", "amountMinor": "250000", "entryDate": "2026-11-02T00:00:00.000Z",
                           "invoiceSerial": "A-1", "method": None, "note": None, "runningBalanceMinor": "250000"}],
              "closingBalanceMinor": "250000", "invoicedMinor": "250000", "paidMinor": "0", "currentBalanceMinor": "250000"}
    api.on("GET", f"/suppliers/{SUP_ID}/ledger", ledger)
    assert run(["ops", "suppliers", "ledger", "Pet House", "--from", "2026-11-01", "--to", "2026-11-30"]) == 0
    assert api.calls[-1] == ("GET", f"/suppliers/{SUP_ID}/ledger", {"from": "2026-11-01", "to": "2026-11-30"})
    assert "A-1" in capsys.readouterr().out


# hafo/dto/create-purchase-order.dto.ts + purchase-line.dto.ts
def test_po_create_resolves_goods_and_sends_the_dto(api, capsys):
    out = applied(api, ["ops", "po", "create", "--supplier", "Zoo Trade", "--note", "friday",
                        "--line", "387957=6", "--line", "8009470387968=12@1300"], capsys)
    assert out == [("POST", "/purchase-orders", {"supplierId": OTHER_SUP_ID, "note": "friday", "lines": [
        {"variantId": VAR_A, "quantity": 6}, {"variantId": VAR_B, "quantity": 12, "unitCostMinor": "130000"}]})]


def test_po_create_without_supplier_or_lines_is_an_empty_hafo_draft(api, capsys):
    assert applied(api, ["ops", "po", "create"], capsys) == [("POST", "/purchase-orders", {})]


def test_po_create_refuses_loose_goods_duplicates_and_bad_lines(api):
    for lines in (["LOOSE=1"], ["387957=1", "387957=2"], ["387957"], ["387957=0"], ["387957=1kg"], ["387957=2@1.234"]):
        assert run(["ops", "po", "create", *[x for l in lines for x in ("--line", l)]]) == 1, lines
    assert not writes(api)


# hafo/dto/replace-lines.dto.ts
def test_po_lines_replaces_every_line_of_a_draft(api, capsys):
    api.on("GET", f"/purchase-orders/{PO_ID}", order("draft", lines=[line(LINE_A, VAR_A, "387957", 6)]))
    out = applied(api, ["ops", "po", "lines", "PO-0042", "--line", "387967=3@1300"], capsys)
    assert out == [("PUT", f"/purchase-orders/{PO_ID}/lines",
                    {"lines": [{"variantId": VAR_B, "quantity": 3, "unitCostMinor": "130000"}]})]


def test_po_lines_refuses_a_placed_order_and_no_lines(api):
    assert run(["ops", "po", "lines", "PO-0042", "--line", "387957=1"]) == 1
    api.on("GET", f"/purchase-orders/{PO_ID}", order("draft"))
    assert run(["ops", "po", "lines", "PO-0042"]) == 1
    assert not writes(api)


def test_a_changed_draft_invalidates_the_lines_code(api, capsys):
    api.on("GET", f"/purchase-orders/{PO_ID}", order("draft"))
    argv = ["ops", "po", "lines", PO_ID, "--line", "387957=1"]
    code = plan(argv, capsys)["code"]
    api.on("GET", f"/purchase-orders/{PO_ID}", order("draft", lines=[line(LINE_A, VAR_A, "387957", 9)]))
    assert run([*argv, "--apply", code]) == 1 and not writes(api)


# hafo/dto/mark-placed.dto.ts
def test_sent_records_the_suppliers_number(api, capsys):
    api.on("GET", f"/purchase-orders/{PO_ID}", order("draft"))
    assert applied(api, ["ops", "po", "sent", "PO-0042", "--ref", " H-1187 "], capsys) == [
        ("POST", f"/purchase-orders/{PO_ID}/placed", {"externalRef": "H-1187"})]


def test_sent_is_irreversible_and_a_line_edit_after_the_dry_run_invalidates_the_code(api, capsys):
    api.on("GET", f"/purchase-orders/{PO_ID}", order("draft"))
    argv = ["ops", "po", "sent", "PO-0042", "--ref", "H-1187"]
    first = plan(argv, capsys)
    assert first["tier"] == "irreversible"
    api.on("GET", f"/purchase-orders/{PO_ID}", order("draft", lines=[line(LINE_A, VAR_A, "387957", 7),
                                                                     line(LINE_B, VAR_B, "387967", 4)]))
    assert run([*argv, "--apply", first["code"]]) == 1 and not writes(api)
    api.on("GET", f"/purchase-orders/{PO_ID}", order("draft", lines=[line(LINE_A, VAR_A, "387957", 6, cost="140000"),
                                                                     line(LINE_B, VAR_B, "387967", 4)]))
    assert run([*argv, "--apply", first["code"]]) == 1 and not writes(api)


def test_sent_needs_hafos_number_but_another_supplier_may_have_none(api, capsys):
    api.on("GET", f"/purchase-orders/{PO_ID}", order("draft"))
    assert run(["ops", "po", "sent", "PO-0042"]) == 1 and not writes(api)
    api.on("GET", f"/purchase-orders/{PO_ID}", order("draft", hafo=False))
    assert applied(api, ["ops", "po", "sent", "PO-0042"], capsys) == [("POST", f"/purchase-orders/{PO_ID}/placed", {})]
    api.on("GET", f"/purchase-orders/{PO_ID}", order("placed"))
    api.calls.clear()
    assert run(["ops", "po", "sent", "PO-0042", "--ref", "x"]) == 1


# hafo/dto/receive-purchase-order.dto.ts
def test_receive_sends_a_request_id_lines_and_the_location(api, capsys):
    argv = ["ops", "po", "receive", "PO-0042", "--line", "387957=4", "--line", "8009470387968=1@1300",
            "--location", "shop"]
    first = plan(argv, capsys)
    step = first["requests"][0]
    assert first["tier"] == "irreversible" and step["path"] == f"/purchase-orders/{PO_ID}/receive"
    body = step["body"]
    assert set(body) == {"requestId", "locationId", "lines"} and body["locationId"] == LOC_ID
    assert body["lines"] == [{"lineId": LINE_A, "quantity": 4},
                             {"lineId": LINE_B, "quantity": 1, "unitCostMinor": "130000"}]
    assert UUID_V4.fullmatch(body["requestId"])
    assert applied(api, argv, capsys) == [("POST", f"/purchase-orders/{PO_ID}/receive", body)]


def test_receive_request_id_comes_from_idem_key_and_is_stable_across_a_repeat(api, capsys):
    argv = ["ops", "po", "receive", PO_ID, "--all"]
    a, b = plan(argv, capsys), plan(argv, capsys)
    assert a == b
    rid = a["requests"][0]["body"]["requestId"]
    state = [{"lineId": LINE_A, "sku": "387957", "open": 6}, {"lineId": LINE_B, "sku": "387967", "open": 4}]
    lines = [{"lineId": LINE_A, "quantity": 6}, {"lineId": LINE_B, "quantity": 4}]
    key = guard.idem_key("po-receive", PO_ID, None, lines, state)
    assert rid == guard.idem_uuid("po-receive", PO_ID, None, lines, state)
    assert rid.replace("-", "")[:12] == key[4:16] and rid.replace("-", "")[13:16] == key[17:20]
    assert plan([*argv[:-1], "--line", "387957=6", "--line", "387967=4"], capsys)["requests"][0]["body"]["requestId"] == rid


def test_a_changed_open_line_state_invalidates_the_code_and_the_request_id(api, capsys):
    argv = ["ops", "po", "receive", PO_ID, "--line", "387957=2"]
    before = plan(argv, capsys)
    moved = order(lines=[line(LINE_A, VAR_A, "387957", 6, got=2), line(LINE_B, VAR_B, "387967", 4)])
    api.on("GET", f"/purchase-orders/{PO_ID}", moved)
    capsys.readouterr()
    assert run([*argv, "--apply", before["code"]]) == 1
    assert not writes(api)
    after = plan(argv, capsys)
    assert after["code"] != before["code"]
    assert after["requests"][0]["body"]["requestId"] != before["requests"][0]["body"]["requestId"]


def test_receive_all_takes_only_what_is_open(api, capsys):
    api.on("GET", f"/purchase-orders/{PO_ID}", order(lines=[line(LINE_A, VAR_A, "387957", 6, got=6),
                                                            line(LINE_B, VAR_B, "387967", 4, got=1, closed=1)]))
    body = applied(api, ["ops", "po", "receive", "PO-0042", "--all"], capsys)[0][2]
    assert body["lines"] == [{"lineId": LINE_B, "quantity": 2}] and "locationId" not in body


def test_receive_refuses_what_the_api_would(api):
    base = ["ops", "po", "receive", "PO-0042"]
    for extra in (["--line", "387957=7"], ["--line", "387957=1", "--line", "387957=2"], ["--line", "nothing=1"],
                  ["--line", "387957=0"], ["--line", "387957=1kg"], [], ["--all", "--line", "387957=1"],
                  ["--all", "--location", "nowhere"]):
        assert run([*base, *extra]) == 1, extra
    api.on("GET", f"/purchase-orders/{PO_ID}", order("draft"))
    assert run([*base, "--all"]) == 1
    api.on("GET", f"/purchase-orders/{PO_ID}", order(lines=[line(LINE_A, VAR_A, "387957", 6, got=6)]))
    assert run([*base, "--all"]) == 1
    assert not writes(api)


def test_receive_with_an_unknown_outcome_exits_3(api, capsys):
    argv = ["ops", "po", "receive", PO_ID, "--all"]
    code = plan(argv, capsys)["code"]
    api.on("POST", f"/purchase-orders/{PO_ID}/receive", O.UnknownOutcome(0, "POST", "/x", "network error: reset"))
    assert run([*argv, "--apply", code]) == 3
    err = capsys.readouterr().err
    assert "siruk ops po show PO-0042" in err and "plan again from the open quantities" in err
    assert len(writes(api)) == 1


# hafo/dto/receive-purchase-order.dto.ts PurchaseOrderLinesDto
def test_not_received_and_reopen_send_line_ids(api, capsys):
    assert applied(api, ["ops", "po", "not-received", "PO-0042", "--line", "387957"], capsys) == [
        ("POST", f"/purchase-orders/{PO_ID}/not-received", {"lineIds": [LINE_A]})]
    api.calls.clear()
    api.on("GET", f"/purchase-orders/{PO_ID}", order(lines=[line(LINE_A, VAR_A, "387957", 6, closed=2),
                                                            line(LINE_B, VAR_B, "387967", 4)]))
    assert applied(api, ["ops", "po", "reopen", PO_ID, "--all"], capsys) == [
        ("POST", f"/purchase-orders/{PO_ID}/reopen", {"lineIds": [LINE_A]})]
    assert run(["ops", "po", "reopen", PO_ID, "--line", "387967"]) == 1
    assert run(["ops", "po", "not-received", PO_ID]) == 1


def test_cancel_and_delivered_post_to_the_order(api, capsys):
    assert applied(api, ["ops", "po", "cancel", "PO-0042"], capsys) == [("POST", f"/purchase-orders/{PO_ID}/cancel", None)]
    api.calls.clear()
    assert applied(api, ["ops", "po", "delivered", "PO-0042"], capsys) == [
        ("POST", f"/purchase-orders/{PO_ID}/delivered", None)]
    api.on("GET", f"/purchase-orders/{PO_ID}", order("delivered"))
    assert run(["ops", "po", "cancel", "PO-0042"]) == 1
    assert run(["ops", "po", "delivered", "PO-0042"]) == 1


def test_from_web_order_needs_the_ops_id(api, capsys):
    assert applied(api, ["ops", "po", "from-web-order", WEB_ORDER], capsys) == [
        ("POST", f"/purchase-orders/from-web-order/{WEB_ORDER}", None)]
    assert run(["ops", "po", "from-web-order", "W-1001"]) == 1


def test_an_order_is_found_by_its_number_and_a_wrong_one_is_refused(api):
    assert run(["ops", "po", "show", "PO-0042"]) == 0
    assert api.calls[-2:] == [("GET", "/purchase-orders", {"q": "PO-0042"}), ("GET", f"/purchase-orders/{PO_ID}", None)]
    assert run(["ops", "po", "show", "PO-9999"]) == 1


def test_po_reads(api, capsys):
    capsys.readouterr()
    assert run(["ops", "po", "list", "--status", "placed", "--supplier", "Pet House", "--q", "42"]) == 0
    assert api.calls[-1] == ("GET", "/purchase-orders", {"status": "placed", "q": "42", "supplierId": SUP_ID})
    assert "PO-0042" in capsys.readouterr().out
    assert run(["ops", "po", "show", PO_ID]) == 0
    out = capsys.readouterr().out
    assert "387957" in out and "1300" in out and "130000" not in out
    assert run(["ops", "po", "show", PO_ID, "--json"]) == 0
    assert json.loads(capsys.readouterr().out) == order()


# hafo/dto/update-reorder-lines.dto.ts
def test_reorder_lines_edit_puts_line_ids_with_quantity_and_dropped(api, capsys):
    out = applied(api, ["ops", "reorder", "lines", "--set", "387957=9", "--drop", "8009470387968", "--set", "387967=0"],
                  capsys)
    assert out == [("PUT", f"/hafo/reorder/list/{LIST_ID}/lines",
                    {"lines": [{"lineId": RLINE_A, "quantity": 9}, {"lineId": RLINE_B, "quantity": 0, "dropped": True}]})]


def test_reorder_lines_keep_and_refusals(api, capsys):
    assert applied(api, ["ops", "reorder", "lines", "--keep", "387957"], capsys)[0][2] == {
        "lines": [{"lineId": RLINE_A, "dropped": False}]}
    api.calls.clear()
    assert run(["ops", "reorder", "lines"]) == 1
    assert run(["ops", "reorder", "lines", "--set", "387957=2@5"]) == 1
    assert run(["ops", "reorder", "lines", "--set", "nothing=2"]) == 1
    api.on("GET", "/hafo/reorder/list", {"list": rlist("accepted"), "dailyRunEnabled": True})
    assert run(["ops", "reorder", "lines", "--set", "387957=2"]) == 1
    api.on("GET", "/hafo/reorder/list", {"list": None, "dailyRunEnabled": True})
    assert run(["ops", "reorder", "accept"]) == 1
    assert not writes(api)


def test_reorder_accept_is_a_draft_and_a_changed_list_invalidates_the_code(api, capsys):
    first = plan(["ops", "reorder", "accept"], capsys)
    assert first["tier"] == "draft" and first["requests"][0]["path"] == f"/hafo/reorder/list/{LIST_ID}/accept"
    code = first["code"]
    edited = rlist()
    edited["lines"][0]["quantity"] = 7
    api.on("GET", "/hafo/reorder/list", {"list": edited, "dailyRunEnabled": True})
    assert run(["ops", "reorder", "accept", "--apply", code]) == 1 and not writes(api)
    api.on("GET", "/hafo/reorder/list", {"list": rlist(), "dailyRunEnabled": True})
    assert applied(api, ["ops", "reorder", "accept"], capsys) == [("POST", f"/hafo/reorder/list/{LIST_ID}/accept", None)]


def test_reorder_accept_refuses_while_auto_place_is_on_and_binds_the_setting(api, capsys):
    api.on("GET", "/settings", [{**setting(False), "key": "reorder.enabled"}, setting(True)])
    capsys.readouterr()
    assert run(["ops", "reorder", "accept"]) == 1
    assert "reorder.autoPlace is on: accepting would place a real hafo order; accept it in the Ops app" in capsys.readouterr().err
    assert run(["ops", "reorder", "accept", "--apply", "deadbeef"]) == 1
    api.on("GET", "/settings", [])
    assert run(["ops", "reorder", "accept"]) == 1
    assert not writes(api)
    api.on("GET", "/settings", [setting(False)])
    code = plan(["ops", "reorder", "accept"], capsys)["code"]
    api.on("GET", "/settings", [setting(True)])
    assert run(["ops", "reorder", "accept", "--apply", code]) == 1 and not writes(api)
    api.on("GET", "/settings", [setting(False)])
    assert run(["ops", "reorder", "accept", "--apply", code, "--json"]) == 0
    assert writes(api) == [("POST", f"/hafo/reorder/list/{LIST_ID}/accept", None)]


def test_reorder_build_says_it_tells_staff(api, capsys):
    capsys.readouterr()
    assert run(["ops", "reorder", "build"]) == 0
    assert "Telegram" in capsys.readouterr().out


def test_reorder_reject_and_build(api, capsys):
    assert applied(api, ["ops", "reorder", "reject"], capsys) == [("POST", f"/hafo/reorder/list/{LIST_ID}/reject", None)]
    api.calls.clear()
    assert applied(api, ["ops", "reorder", "build"], capsys) == [("POST", "/hafo/reorder/list/build", None)]


def test_reorder_and_hafo_reads(api, capsys):
    api.on("GET", "/hafo/reorder", [{"variantId": VAR_A, "sku": "387957", "label": None, "barcode": None,
                                     "productName": "Chunks", "hafoSku": "H1", "mode": "global", "point": 3,
                                     "target": 8, "freeOwnStock": 1, "openRestockQuantity": 0, "position": 1,
                                     "hafoQuantity": 50, "hafoInStock": True, "hafoObservedAt": None,
                                     "hafoUnits": 1, "due": True, "suggestedQuantity": 6, "flag": None},
                                    {"variantId": VAR_B, "sku": "387967", "label": None, "barcode": None,
                                     "productName": "Veal", "hafoSku": "H2", "mode": "global", "point": 3,
                                     "target": 8, "freeOwnStock": 9, "openRestockQuantity": 0, "position": 2,
                                     "hafoQuantity": 50, "hafoInStock": True, "hafoObservedAt": None,
                                     "hafoUnits": 1, "due": False, "suggestedQuantity": 0, "flag": None}])
    api.on("GET", "/hafo/stock", {"lastCrawl": None, "lastApplied": "2026-11-16T05:00:00.000Z", "items": [
        {"variantId": VAR_A, "sku": "387957", "label": None, "barcode": None, "productName": "Chunks",
         "hafoSku": "H1", "quantity": 50, "inStock": True, "observedAt": "2026-11-16T05:00:00.000Z"}]})
    capsys.readouterr()
    assert run(["ops", "reorder", "show", "--due"]) == 0
    out = capsys.readouterr().out
    assert "387957" in out and "387967" not in out
    assert run(["ops", "reorder", "list"]) == 0 and "387967" in capsys.readouterr().out
    assert run(["ops", "hafo", "stock", "royal", "--limit", "20"]) == 0
    assert api.calls[-1] == ("GET", "/hafo/stock", {"q": "royal", "limit": 20})
    assert "H1" in capsys.readouterr().out


def test_no_dry_run_records_a_write(api, capsys):
    dry = [["ops", "suppliers", "create", "X"], ["ops", "suppliers", "set", "Pet House", "--inactive"],
           ["ops", "suppliers", "pay", "Pet House", "--amount-amd", "1", "--method", "cash"],
           ["ops", "suppliers", "adjust", "Pet House", "--amount-amd", "1", "--note", "abc"],
           ["ops", "po", "create", "--line", "387957=1"], ["ops", "po", "receive", "PO-0042", "--all"],
           ["ops", "po", "not-received", "PO-0042", "--all"], ["ops", "po", "cancel", "PO-0042"],
           ["ops", "po", "delivered", "PO-0042"], ["ops", "po", "from-web-order", WEB_ORDER],
           ["ops", "reorder", "build"], ["ops", "reorder", "accept"], ["ops", "reorder", "reject"],
           ["ops", "reorder", "lines", "--drop", "387957"]]
    for argv in dry:
        capsys.readouterr()
        assert run(argv) == 0, argv
        assert "nothing sent; re-run with --apply" in capsys.readouterr().out
    assert not writes(api)


def test_a_wrong_code_writes_nothing(api, capsys):
    assert run(["ops", "po", "receive", "PO-0042", "--all", "--apply", "deadbeef"]) == 1
    assert run(["ops", "suppliers", "pay", "Pet House", "--amount-amd", "1", "--method", "cash", "--apply", "deadbeef"]) == 1
    assert not writes(api)


def test_the_module_never_builds_a_refused_path():
    src = open(P.__file__, encoding="utf-8").read() + open(commands.__file__.replace("__init__", "ops_purchasing"),
                                                          encoding="utf-8").read()
    assert not re.search(r"/(place|release)\b|hafo/crawl|account-orders", src.replace("`place` and `release`", ""))
