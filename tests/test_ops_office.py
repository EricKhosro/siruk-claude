"""Ops reads and the catalogue sync (`siruk ops stock | history | sales | report | orders | receipts | incidents |
outbox | catalog | settings | services | promotions`). Query parameters are the DTO field names and fixture bodies the
contract's, each with its path above it: siruk-web/ops/apps/api/src/modules/<module>/dto/*.ts and
siruk-web/ops/packages/contracts/src/api/{reports,web-orders,till,backoffice,promotions,auth}.ts."""
import json, os

import pytest

from siruk import cli, commands, config
from siruk.ops import guard, office
from siruk.ops import client as O

LOC = "11111111-1111-4111-8111-111111111111"
VAR = "22222222-2222-4222-8222-222222222222"
SALE = "33333333-3333-4333-8333-333333333333"
MSG = "44444444-4444-4444-8444-444444444444"
ORDER = "55555555-5555-4555-8555-555555555555"
OWN = {"sales", "history", "stock", "report", "orders", "receipts", "incidents", "outbox", "catalog", "settings",
       "services", "promotions"}
NAMES = ["ops stock", "ops history", "ops sales list", "ops sales show", "ops report sales", "ops report margin",
         "ops report analytics", "ops report accountant", "ops orders list", "ops orders show", "ops receipts list",
         "ops incidents", "ops outbox list", "ops outbox resend", "ops catalog status", "ops catalog sync",
         "ops settings list", "ops services list", "ops promotions list"]
FORBIDDEN = ("/sales", "/fiscal", "/web-orders", "/settings", "/services", "/shop-promotions")


@pytest.fixture(autouse=True)
def only_ops_office(monkeypatch):
    monkeypatch.setattr(commands, "GROUPS", ("ops_core", "ops_office"))


def run(argv):
    with pytest.raises(SystemExit) as e:
        cli.main(["-q", *argv])
    return e.value.code


def manifest():
    return [r for r in cli.build_parser().parse_args(["commands"]).manifest if r["name"].split()[1:2] and
            r["name"].split()[0] == "ops" and r["name"].split()[1] in OWN]


# ---------------------------------------------------------------- manifest ----
def test_every_command_exists_with_its_manifest_fields_and_only_two_write():
    rows = manifest()
    assert sorted(r["name"] for r in rows) == sorted(NAMES)
    for r in rows:
        assert r["backend"] == "ops" and r["api"] and r["roles"] and r["help"] and r["example"], r["name"]
        assert r["example"].startswith("siruk " + r["name"].split()[0]), r["name"]
    assert {r["name"]: r["tier"] for r in rows if r["tier"] != "read"} == \
        {"ops outbox resend": "real-world", "ops catalog sync": "draft"}


def test_no_registered_command_writes_to_sales_fiscal_web_orders_settings_services_or_promotions():
    for r in manifest():
        for entry in r["api"]:
            method, path = entry.split(" ", 1)
            if method != "GET":
                assert not path.startswith(FORBIDDEN), (r["name"], entry)


# ---------------------------------------------------------------- fixtures ----
# GET /locations: StockLocationRow (contracts/src/api/backoffice.ts)
LOCATIONS = [{"id": LOC, "code": "MAIN", "name": "Main shop", "kind": "shop", "isActive": True,
              "sirukWarehouseCode": None, "armsoftStorage": None, "supplierId": None, "connector": None}]
# GET /goods/:id: GoodsDetail extends GoodsItem (backoffice.ts); only the fields the resolver reads
GOOD = {"variantId": VAR, "sku": "RC-1", "barcode": "4820000000017", "accountingCode": None, "extraBarcodes": [],
        "productName": {"en": "Royal Canin", "ru": None, "hy": None}, "label": "2 kg", "stockUnit": "pack"}
# GET /reports/stock: StockReport / StockReportRow (contracts/src/api/reports.ts)
STOCK = {"at": "2026-10-31T19:59:59.999Z", "locationId": None, "totalValueMinor": "1250000", "rows": [
    {"variantId": VAR, "sku": "RC-1", "productName": "Royal Canin", "label": "2 kg", "barcode": None,
     "accountingCode": None, "locationId": LOC, "locationCode": "MAIN", "locationName": "Main shop",
     "quantity": 2500, "reserved": 3, "unit": "g", "valueMinor": "1250000"}]}
# GET /reports/variants/:id/history: VariantHistory / VariantHistoryEntry (reports.ts)
HISTORY = {"variant": {"variantId": VAR, "sku": "RC-1", "productName": "Royal Canin", "label": "2 kg", "barcode": None,
                       "accountingCode": None, "unit": "pcs"},
           "hasMore": True, "movements": [
    {"id": "m1", "at": "2026-10-05T08:00:00.000Z", "locationId": LOC, "locationCode": "MAIN", "kind": "sale",
     "documentId": "d1", "documentNumber": "S-1", "documentType": "sale", "quantityDelta": -2, "reservedDelta": 0,
     "valueDeltaMinor": "-60000", "quantityAfter": -1, "reservedAfter": 0, "valueAfterMinor": "-30000",
     "wentNegative": True}]}
# GET /reports/sales: SalesReport by day / variant / payment / priceType (reports.ts)
TOTALS = {"tillSales": 2, "webOrders": 1, "tillMinor": "500000", "webMinor": "250000", "totalMinor": "750000",
          "cashMinor": "300000", "nonCashMinor": "450000", "returnsMinor": "0", "netMinor": "750000"}
SALES_DAY = {"from": "2026-10-01", "to": "2026-10-31", "groupBy": "day", "totals": TOTALS, "rows": [
    {"day": "2026-10-05", "tillSales": 2, "webOrders": 1, "tillMinor": "500000", "webMinor": "250000",
     "totalMinor": "750000", "cashMinor": "300000", "nonCashMinor": "450000", "returnsMinor": "0",
     "netMinor": "750000"}]}
SALES_VARIANT = {**SALES_DAY, "groupBy": "variant", "rows": [
    {"variantId": VAR, "sku": "RC-1", "productName": "Royal Canin", "label": "2 kg", "barcode": None,
     "accountingCode": None, "quantity": 3, "revenueMinor": "300000", "costMinor": "200000", "uncostedLines": 0}]}
SALES_PAYMENT = {**SALES_DAY, "groupBy": "payment", "rows": [{"method": "cash", "count": 2, "amountMinor": "300000"}]}
SALES_PRICE_TYPE = {**SALES_DAY, "groupBy": "priceType", "rows": [
    {"code": None, "lines": 1, "revenueMinor": "50000"}, {"code": "store", "lines": 4, "revenueMinor": "700000"}]}
# GET /reports/margin: MarginReport (reports.ts)
BREAK = {"revenueMinor": "300000", "costMinor": "200000", "marginMinor": "100000"}
MARGIN = {**BREAK, "from": "2026-10-01", "to": "2026-10-31", "marginPercent": 33.33, "till": BREAK, "web": BREAK,
          "channels": [{**BREAK, "channel": "till", "marginPercent": 33.33, "uncostedRevenueMinor": "0"}],
          "refundsMinor": "0", "returnedCostMinor": "0", "uncostedRevenueMinor": "0"}
FIGURES = {"orders": 3, "salesMinor": "750000", "averageOrderMinor": "250000", "refundsMinor": "0",
           "netMinor": "750000", **BREAK, "marginPercent": 33.33, "uncostedRevenueMinor": "0"}
# GET /reports/analytics: AnalyticsReport (reports.ts)
ANALYTICS = {"from": "2026-10-01", "to": "2026-10-31", "channels": ["till"], "totals": FIGURES,
             "byChannel": [{**FIGURES, "channel": "till"}], "topByMargin": SALES_VARIANT["rows"]}
# GET /sales: TillSale[] (contracts/src/api/till.ts)
TILL_SALE = {"id": SALE, "number": "000123", "clientSaleId": "c1", "status": "completed", "tillId": "t", "shiftId": "s",
             "locationId": LOC, "cashierId": "u", "subtotalMinor": "130000", "discountMinor": "0",
             "totalMinor": "130000", "discountName": None, "isTreat": False, "changeMinor": "0", "offline": False,
             "soldAt": "2026-10-05T08:00:00.000Z", "stockDocumentId": None, "flags": [], "fiscalReceiptId": None,
             "lines": [{"id": "l1", "variantId": VAR, "serviceId": None, "quantity": 2500, "unit": "կգ",
                        "unitPriceMinor": "52000", "discountMinor": "0", "lineTotalMinor": "130000",
                        "fiscalName": "Royal", "adgCode": "1", "scannedCode": None, "returnedQuantity": 0,
                        "promotionName": None, "priceTypeCode": "store"}],
             "payments": [{"method": "cash", "amountMinor": "130000"}]}
# GET /web-orders: WebOrderList / WebOrderSummary (contracts/src/api/web-orders.ts); money is a JSON number
SUMMARY = {"id": ORDER, "channel": "siruk", "sirukOrderId": 10452, "number": "10452", "status": "accepted",
           "prepStatus": "new", "paymentType": "cash_on_delivery", "totalMinor": 1300000, "customerName": "Ani",
           "phone": "+37400000000", "note": None, "channelStatus": None, "receivedAt": "2026-10-05T08:00:00.000Z",
           "packedAt": None, "ownLineCount": 1, "hafoLineCount": 0, "saleReceiptStatus": None}
ORDERS = {"items": [SUMMARY], "total": 1}
# GET /web-orders/:id: WebOrderDetail (web-orders.ts)
ORDER_DETAIL = {"order": {**SUMMARY, "deliveryFeeMinor": 100000, "address": "Yerevan", "paidAt": None,
                          "stockDocumentId": None},
                "ownLines": [{"id": "l1", "sku": "RC-1", "name": "Royal Canin", "variantId": VAR, "quantity": 1,
                              "unitPriceMinor": 1200000, "lineTotalMinor": 1200000, "isGift": False,
                              "addedInOps": False, "costMinor": None, "priceTypeCode": "website"}],
                "hafoLines": [], "purchaseOrders": [], "receipts": [], "channelUpdates": []}
# GET /fiscal/receipts: TillFiscalReceipt[]; GET /fiscal/incidents: TillFiscalIncident[] (till.ts)
RECEIPTS = [{"id": "r1", "kind": "sale", "status": "failed", "saleId": SALE, "saleReturnId": None, "webOrderId": None,
             "originalReceiptId": None, "cashMinor": "130000", "cardMinor": "0", "totalMinor": "130000", "crn": None,
             "rseq": None, "fiscalNumber": None, "lotteryNumber": None, "qr": None, "issuedAt": None,
             "errorCode": "E1", "errorMessage": "HDM refused", "attempts": 2, "environment": "live",
             "claimedByTillId": None, "claimedAt": None, "createdAt": "2026-10-05T08:00:00.000Z", "claimable": True}]
INCIDENTS = [{"id": "i1", "receiptId": "r1", "tillId": "t", "kind": "second_fiscal_document",
              "detail": {"why": "x"}, "createdAt": "2026-10-05T08:00:00.000Z"}]
# GET /outbox/failed: FailedOutboxList (backoffice.ts)
FAILED = {"counts": [{"topic": "order.fiscal-receipt", "count": 1}], "items": [
    {"id": MSG, "topic": "order.fiscal-receipt", "attempts": 8, "lastError": "HTTP 500",
     "createdAt": "2026-10-05T08:00:00.000Z"}]}
# GET /catalog/status: CatalogStatus (backoffice.ts)
STATUS = {"lastSyncAt": "2026-11-15T20:00:00.000Z", "autoSync": True, "tokenSource": "stored", "running": False}
# GET /settings: SettingEntry[] (contracts/src/api/auth.ts)
SETTINGS = [{"key": "telegram.notifyTillSales", "value": True, "default": False, "isDefault": False,
             "description": "Tell the manager chat about each sale", "updatedAt": "2026-10-01T00:00:00.000Z"}]
# GET /services: ServiceRow[] (till.ts)
SERVICES = [{"id": "s1", "code": "DELIVERY", "name": {"en": "Delivery", "hy": "Առաքում", "ru": "Доставка"},
             "fiscalName": None, "adgCode": "9", "priceMinor": None, "isActive": True}]
# GET /shop-promotions: ShopPromotionRow[] (promotions.ts)
PROMOS = [{"id": "p1", "name": "Autumn", "target": "brand", "variantId": None, "productId": None, "brand": "Royal",
           "targetLabel": "Royal", "percent": 10, "amountMinor": None, "startsAt": "2026-10-01T00:00:00.000Z",
           "endsAt": None, "isActive": True, "createdAt": "2026-09-30T00:00:00.000Z"}]


# ---------------------------------------------------------------- query parameters ----
# reports/dto/stock-report-query.dto.ts: locationId, at
def test_stock_sends_location_id_and_at(ops_fake, capsys):
    ops_fake.on("GET", "/locations", LOCATIONS).on("GET", "/reports/stock", STOCK)
    assert run(["ops", "stock", "--location", "main", "--at", "2026-10-31"]) == 0
    assert ops_fake.calls[-1] == ("GET", "/reports/stock", {"locationId": LOC, "at": "2026-10-31"})
    out = capsys.readouterr().out
    assert "2.5 kg" in out and "12500" in out and "MAIN" in out


def test_stock_without_options_sends_no_parameters(ops_fake):
    ops_fake.on("GET", "/reports/stock", STOCK)
    assert run(["ops", "stock"]) == 0
    assert ops_fake.calls == [("GET", "/reports/stock", None)]


# reports/dto/history-query.dto.ts: locationId, from, to, limit (1..1000)
def test_history_resolves_the_good_and_sends_the_dto_fields(ops_fake, capsys):
    ops_fake.on("GET", f"/goods/{VAR}", GOOD).on("GET", "/locations", LOCATIONS)
    ops_fake.on("GET", f"/reports/variants/{VAR}/history", HISTORY)
    assert run(["ops", "history", VAR, "--location", "MAIN", "--from", "2026-10-01", "--to", "2026-10-31",
                "--limit", "50"]) == 0
    assert ops_fake.calls[-1] == ("GET", f"/reports/variants/{VAR}/history",
                                  {"locationId": LOC, "from": "2026-10-01", "to": "2026-10-31", "limit": 50})
    out = capsys.readouterr().out
    assert "RC-1" in out and "-2 pcs" in out and "NEGATIVE" in out and "-600" in out and "older movements" in out


def test_history_takes_a_sku_through_the_resolver(ops_fake):
    ops_fake.on("GET", "/goods", {"items": [GOOD], "total": 1, "page": 1, "pageSize": 50})
    ops_fake.on("GET", f"/reports/variants/{VAR}/history", HISTORY)
    assert run(["ops", "history", "rc-1"]) == 0
    assert ops_fake.calls[0] == ("GET", "/goods", {"q": "rc-1", "page": 1})
    assert ops_fake.calls[-1] == ("GET", f"/reports/variants/{VAR}/history", None)


def test_history_refuses_a_limit_the_dto_would_refuse(ops_fake, capsys):
    ops_fake.on("GET", f"/goods/{VAR}", GOOD)
    assert run(["ops", "history", VAR, "--limit", "1001"]) == 1
    assert "--limit" in capsys.readouterr().err and ops_fake.calls == [("GET", f"/goods/{VAR}", None)]


# reports/dto/sales-query.dto.ts: from, to, groupBy (day|variant|payment|priceType), channels (comma list)
@pytest.mark.parametrize("group,body,shown", [("day", SALES_DAY, "2026-10-05"), ("variant", SALES_VARIANT, "Royal Canin"),
                                              ("payment", SALES_PAYMENT, "cash"), ("priceType", SALES_PRICE_TYPE, "store")])
def test_report_sales_sends_the_dto_fields_for_every_grouping(ops_fake, capsys, group, body, shown):
    ops_fake.on("GET", "/reports/sales", body)
    assert run(["ops", "report", "sales", "--from", "2026-10-01", "--to", "2026-10-31", "--group-by", group,
                "--channels", "till,glovo"]) == 0
    assert ops_fake.calls == [("GET", "/reports/sales", {"from": "2026-10-01", "to": "2026-10-31", "groupBy": group,
                                                          "channels": "till,glovo"})]
    out = capsys.readouterr().out
    assert shown in out and ("base units" in out) == (group == "variant")


def test_report_sales_defaults_group_and_channels_to_the_servers(ops_fake):
    ops_fake.on("GET", "/reports/sales", SALES_DAY)
    assert run(["ops", "report", "sales", "--from", "2026-10-01", "--to", "2026-10-31"]) == 0
    assert ops_fake.calls == [("GET", "/reports/sales", {"from": "2026-10-01", "to": "2026-10-31"})]


@pytest.mark.parametrize("argv,code", [(["--channels", "till,yandex"], 1), (["--group-by", "week"], 2)])
def test_report_sales_refuses_what_the_dto_would_refuse(ops_fake, argv, code):
    assert run(["ops", "report", "sales", "--from", "2026-10-01", "--to", "2026-10-31", *argv]) == code
    assert not ops_fake.calls


# reports/dto/margin-query.dto.ts: from, to, channels — also what /reports/analytics takes
@pytest.mark.parametrize("cmd,path,body", [("margin", "/reports/margin", MARGIN), ("analytics", "/reports/analytics", ANALYTICS)])
def test_report_margin_and_analytics_send_from_to_channels(ops_fake, capsys, cmd, path, body):
    ops_fake.on("GET", path, body)
    assert run(["ops", "report", cmd, "--from", "2026-10-01", "--to", "2026-10-31", "--channels", "siruk"]) == 0
    assert ops_fake.calls == [("GET", path, {"from": "2026-10-01", "to": "2026-10-31", "channels": "siruk"})]
    assert "33.33" in capsys.readouterr().out


def test_report_margin_needs_a_range(ops_fake):
    assert run(["ops", "report", "margin", "--from", "2026-10-01"]) == 2 and not ops_fake.calls


# web-orders/dto/list-web-orders.dto.ts: prepStatus, status, channel, q, limit (1..500), offset
def test_orders_list_sends_the_dto_fields(ops_fake, capsys):
    ops_fake.on("GET", "/web-orders", ORDERS)
    assert run(["ops", "orders", "list", "--prep-status", "new", "--status", "accepted", "--channel", "siruk",
                "--search", "royal", "--limit", "25", "--offset", "50"]) == 0
    assert ops_fake.calls == [("GET", "/web-orders", {"prepStatus": "new", "status": "accepted", "channel": "siruk",
                                                      "q": "royal", "limit": 25, "offset": 50})]
    out = capsys.readouterr().out
    assert "10452" in out and "13000" in out and "1 of 1" in out


def test_orders_list_offset_zero_is_sent(ops_fake):
    ops_fake.on("GET", "/web-orders", ORDERS)
    assert run(["ops", "orders", "list", "--offset", "0"]) == 0
    assert ops_fake.calls == [("GET", "/web-orders", {"offset": 0})]


def test_orders_show_by_number_finds_the_one_order(ops_fake, capsys):
    own = {**ORDER_DETAIL["ownLines"][0], "quantity": 1500, "stockUnit": "loose"}
    ops_fake.on("GET", "/web-orders", ORDERS).on("GET", f"/web-orders/{ORDER}", {**ORDER_DETAIL, "ownLines": [own]})
    assert run(["ops", "orders", "show", "10452"]) == 0
    assert ops_fake.calls[0] == ("GET", "/web-orders", {"q": "10452", "limit": 500})
    assert ops_fake.calls[-1] == ("GET", f"/web-orders/{ORDER}", None)
    out = capsys.readouterr().out
    assert "Royal Canin" in out and "1.5 kg" in out


# sales/dto/list-sales-query.dto.ts: number, shiftId, limit; fiscal/dto/list-fiscal-receipts-query.dto.ts: status, kind, saleId, limit
def test_sales_list_and_receipts_list_send_the_dto_fields(ops_fake):
    ops_fake.on("GET", "/sales", [TILL_SALE]).on("GET", "/fiscal/receipts", RECEIPTS)
    assert run(["ops", "sales", "list", "--number", "000123", "--shift", SALE, "--limit", "5"]) == 0
    assert run(["ops", "receipts", "list", "--status", "failed", "--kind", "sale", "--sale", SALE, "--limit", "5"]) == 0
    assert ops_fake.calls == [("GET", "/sales", {"number": "000123", "shiftId": SALE, "limit": 5}),
                              ("GET", "/fiscal/receipts", {"status": "failed", "kind": "sale", "saleId": SALE,
                                                           "limit": 5})]


def test_sales_show_by_number_prints_lines_in_kilograms(ops_fake, capsys):
    sale = {**TILL_SALE, "lines": [{**TILL_SALE["lines"][0], "returnedQuantity": 500}]}
    ops_fake.on("GET", "/sales", [TILL_SALE]).on("GET", f"/sales/{SALE}", sale)
    assert run(["ops", "sales", "show", "000123"]) == 0
    assert ops_fake.calls[0] == ("GET", "/sales", {"number": "000123"})
    out = capsys.readouterr().out
    assert "2.5 kg" in out and "1300" in out and "cash 1300" in out and "500 g" in out


# services/dto/service.dto.ts ListServicesQueryDto: active "1" (a boolean would go out as "true")
def test_services_list_active_sends_the_string_one(ops_fake):
    ops_fake.on("GET", "/services", SERVICES)
    assert run(["ops", "services", "list", "--active"]) == 0
    assert ops_fake.calls == [("GET", "/services", {"active": "1"})]


# ---------------------------------------------------------------- accountant ----
# reports/dto/accountant-query.dto.ts: month "YYYY-MM"
def test_accountant_writes_the_downloaded_bytes_and_prints_the_path(ops_fake, tmp_path, capsys):
    ops_fake.on("GET", "/reports/accountant.xlsx", (b"PK\x03\x04bytes", "siruk-accountant-2026-10.xlsx"))
    out = tmp_path / "nested" / "oct.xlsx"
    assert run(["ops", "report", "accountant", "--month", "2026-10", "-o", str(out)]) == 0
    assert out.read_bytes() == b"PK\x03\x04bytes"
    assert capsys.readouterr().out.strip() == str(out)
    assert ops_fake.calls == [("GET", "/reports/accountant.xlsx", {"month": "2026-10"})]


def test_accountant_default_is_runs_today_with_the_servers_file_name(ops_fake, tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(config, "ROOT", str(tmp_path))
    ops_fake.on("GET", "/reports/accountant.xlsx", (b"x", "../../evil/siruk-accountant-2026-10.xlsx"))
    assert run(["ops", "report", "accountant", "--month", "2026-10"]) == 0
    printed = capsys.readouterr().out.strip()
    assert os.path.dirname(printed).startswith(str(tmp_path / "runs")) and os.path.basename(printed) == "siruk-accountant-2026-10.xlsx"
    assert open(printed, "rb").read() == b"x"


def test_accountant_into_a_folder_and_without_a_server_file_name(tmp_path):
    assert office.accountant_path(str(tmp_path), "2026-10", "a.xlsx") == str(tmp_path / "a.xlsx")
    assert office.accountant_path(None, "2026-10", None, today="2026-11-16") == \
        os.path.join(config.ROOT, "runs", "2026-11-16", "siruk-accountant-2026-10.xlsx")


@pytest.mark.parametrize("filename", ["", ".", "..", "x/..", "../", None])
def test_accountant_falls_back_to_the_default_name_when_the_servers_is_unusable(tmp_path, filename):
    assert office.accountant_path(str(tmp_path), "2026-10", filename) == str(tmp_path / "siruk-accountant-2026-10.xlsx")


def test_accountant_o_ending_in_a_slash_is_a_folder_and_is_created(ops_fake, tmp_path, capsys):
    ops_fake.on("GET", "/reports/accountant.xlsx", (b"x", "siruk-accountant-2026-10.xlsx"))
    folder = tmp_path / "new" / "dir"
    assert run(["ops", "report", "accountant", "--month", "2026-10", "-o", str(folder) + "/"]) == 0
    assert (folder / "siruk-accountant-2026-10.xlsx").read_bytes() == b"x"
    assert capsys.readouterr().out.strip() == os.path.join(str(folder) + "/", "siruk-accountant-2026-10.xlsx")


def test_accountant_o_an_existing_folder_gets_the_servers_file_name(ops_fake, tmp_path):
    ops_fake.on("GET", "/reports/accountant.xlsx", (b"x", None))
    assert run(["ops", "report", "accountant", "--month", "2026-10", "-o", str(tmp_path)]) == 0
    assert (tmp_path / "siruk-accountant-2026-10.xlsx").exists()


@pytest.mark.parametrize("month", ["2026-13", "202610", "2026-1", "October"])
def test_accountant_refuses_a_bad_month_before_asking(ops_fake, tmp_path, month):
    assert run(["ops", "report", "accountant", "--month", month, "-o", str(tmp_path / "x.xlsx")]) == 1
    assert not ops_fake.calls and not (tmp_path / "x.xlsx").exists()


# ---------------------------------------------------------------- the two writes ----
RUNNING_NO = {"running": False}
# catalog/dto/sync-catalog.dto.ts: full?: boolean; outbox.controller.ts: POST /outbox/:id/resend → 204
def test_catalog_sync_is_a_dry_run_without_apply(ops_fake, capsys):
    ops_fake.on("GET", "/catalog/status", STATUS).on("POST", "/catalog/sync", {})
    assert run(["ops", "catalog", "sync", "--full"]) == 0
    out = capsys.readouterr().out
    assert [c for c in ops_fake.calls if c[0] != "GET"] == []
    code = guard.confirm_code([guard.Step("POST", "/catalog/sync", {"full": True})], RUNNING_NO, ops_fake.base)
    assert f"--apply {code}" in out and "nothing sent" in out and "draft" in out
    assert "last sync 2026-11-15T20:00:00.000Z" in out


def test_catalog_sync_code_survives_an_auto_sync_but_not_a_running_one(ops_fake, capsys):
    ops_fake.on("GET", "/catalog/status", STATUS).on("POST", "/catalog/sync", {})
    steps = [guard.Step("POST", "/catalog/sync", {})]
    ops_fake.on("GET", "/catalog/status", {**STATUS, "lastSyncAt": "2026-11-15T20:10:00.000Z"})
    code = guard.confirm_code(steps, RUNNING_NO, ops_fake.base)
    assert run(["ops", "catalog", "sync", "--apply", code]) == 0
    ops_fake.on("GET", "/catalog/status", {**STATUS, "running": True})
    assert run(["ops", "catalog", "sync", "--apply", code]) == 1
    assert [c for c in ops_fake.calls if c[0] == "POST"] == [("POST", "/catalog/sync", {})]


def test_catalog_sync_apply_sends_one_post_with_the_right_code(ops_fake, capsys):
    result = {"full": True, "since": None, "syncedAt": "2026-11-16T10:00:00.000Z", "products": 1, "variants": 2,
              "created": 0, "deactivated": 0, "priceCodesSkipped": 0}
    ops_fake.on("GET", "/catalog/status", STATUS).on("POST", "/catalog/sync", result)
    code = guard.confirm_code([guard.Step("POST", "/catalog/sync", {"full": True})], RUNNING_NO, ops_fake.base)
    assert run(["ops", "catalog", "sync", "--full", "--apply", code]) == 0
    assert [c for c in ops_fake.calls if c[0] != "GET"] == [("POST", "/catalog/sync", {"full": True})]


def test_catalog_sync_without_full_sends_an_empty_body_and_a_wrong_code_sends_nothing(ops_fake):
    ops_fake.on("GET", "/catalog/status", STATUS).on("POST", "/catalog/sync", {})
    assert run(["ops", "catalog", "sync", "--apply", "deadbeef"]) == 1
    assert [c for c in ops_fake.calls if c[0] != "GET"] == []
    code = guard.confirm_code([guard.Step("POST", "/catalog/sync", {})], RUNNING_NO, ops_fake.base)
    assert run(["ops", "catalog", "sync", "--apply", code]) == 0
    assert ops_fake.calls[-1] == ("POST", "/catalog/sync", {})


def test_outbox_resend_is_a_dry_run_without_apply(ops_fake, capsys):
    ops_fake.on("GET", "/outbox/failed", FAILED)
    assert run(["ops", "outbox", "resend", MSG]) == 0
    out = capsys.readouterr().out
    assert [c for c in ops_fake.calls if c[0] != "GET"] == []
    step = guard.Step("POST", f"/outbox/{MSG}/resend", None, "order.fiscal-receipt, 8 tries")
    assert f"--apply {guard.confirm_code([step], FAILED['items'][0], ops_fake.base)}" in out and "real-world" in out


# order-ping.queue.ts: ORDER_PING_TOPIC = 'telegram.order' (posted to Telegram, not siruk)
def test_outbox_resend_names_telegram_for_a_telegram_topic_and_siruk_otherwise(ops_fake, capsys):
    tg = {"id": ORDER, "topic": "telegram.order", "attempts": 3, "lastError": "HTTP 502",
          "createdAt": "2026-10-05T09:00:00.000Z"}
    ops_fake.on("GET", "/outbox/failed", {"counts": [{"topic": "telegram.order", "count": 1}], "items": [tg, *FAILED["items"]]})
    assert run(["ops", "outbox", "resend", ORDER]) == 0
    assert "to Telegram again" in capsys.readouterr().out
    assert run(["ops", "outbox", "resend", MSG]) == 0
    assert "to siruk again" in capsys.readouterr().out


def test_outbox_resend_apply_posts_once_and_handles_the_204(ops_fake, capsys):
    ops_fake.on("GET", "/outbox/failed", FAILED).on("POST", f"/outbox/{MSG}/resend", None)
    step = guard.Step("POST", f"/outbox/{MSG}/resend", None, "order.fiscal-receipt, 8 tries")
    code = guard.confirm_code([step], FAILED["items"][0], ops_fake.base)
    assert run(["ops", "outbox", "resend", MSG, "--apply", code]) == 0
    assert [c for c in ops_fake.calls if c[0] != "GET"] == [("POST", f"/outbox/{MSG}/resend", None)]


def test_outbox_resend_refuses_a_message_that_is_not_in_the_failed_list(ops_fake, capsys):
    ops_fake.on("GET", "/outbox/failed", FAILED)
    assert run(["ops", "outbox", "resend", ORDER]) == 1
    assert "not in the failed list" in capsys.readouterr().err
    assert [c for c in ops_fake.calls if c[0] != "GET"] == []


def test_outbox_resend_with_an_unknown_outcome_exits_3(ops_fake, capsys):
    ops_fake.on("GET", "/outbox/failed", FAILED)
    ops_fake.on("POST", f"/outbox/{MSG}/resend", O.UnknownOutcome(0, "POST", f"/outbox/{MSG}/resend", "timeout"))
    step = guard.Step("POST", f"/outbox/{MSG}/resend", None, "order.fiscal-receipt, 8 tries")
    code = guard.confirm_code([step], FAILED["items"][0], ops_fake.base)
    assert run(["ops", "outbox", "resend", MSG, "--apply", code]) == 3
    assert "siruk ops outbox list" in capsys.readouterr().err


# ---------------------------------------------------------------- reads print the answer unmodified ----
READS = [
    (["ops", "stock"], "/reports/stock", STOCK), (["ops", "history", VAR], f"/reports/variants/{VAR}/history", HISTORY),
    (["ops", "sales", "list"], "/sales", [TILL_SALE]), (["ops", "sales", "show", SALE], f"/sales/{SALE}", TILL_SALE),
    (["ops", "report", "sales", "--from", "a", "--to", "b"], "/reports/sales", SALES_DAY),
    (["ops", "report", "sales", "--from", "a", "--to", "b", "--group-by", "priceType"], "/reports/sales",
     SALES_PRICE_TYPE),
    (["ops", "report", "margin", "--from", "a", "--to", "b"], "/reports/margin", MARGIN),
    (["ops", "report", "analytics", "--from", "a", "--to", "b"], "/reports/analytics", ANALYTICS),
    (["ops", "orders", "list"], "/web-orders", ORDERS), (["ops", "orders", "show", ORDER], f"/web-orders/{ORDER}", ORDER_DETAIL),
    (["ops", "receipts", "list"], "/fiscal/receipts", RECEIPTS), (["ops", "incidents"], "/fiscal/incidents", INCIDENTS),
    (["ops", "outbox", "list"], "/outbox/failed", FAILED), (["ops", "catalog", "status"], "/catalog/status", STATUS),
    (["ops", "settings", "list"], "/settings", SETTINGS), (["ops", "services", "list"], "/services", SERVICES),
    (["ops", "promotions", "list"], "/shop-promotions", PROMOS)]


@pytest.mark.parametrize("argv,path,body", READS, ids=[" ".join(r[0][1:]) for r in READS])
def test_reads_print_the_api_json_unmodified_and_a_table_otherwise(ops_fake, capsys, argv, path, body):
    ops_fake.on("GET", f"/goods/{VAR}", GOOD).on("GET", path, body)
    assert run(["--json", *argv]) == 0
    assert json.loads(capsys.readouterr().out) == body
    assert run(argv) == 0
    assert capsys.readouterr().out.strip()
    assert {c[0] for c in ops_fake.calls} == {"GET"}


def test_a_failing_read_is_exit_2(ops_fake, capsys):
    ops_fake.on("GET", "/settings", O.OpsError(403, "GET", "/settings", '{"message":"Forbidden","error":"FORBIDDEN"}'))
    assert run(["ops", "settings", "list"]) == 2
    assert "403" in capsys.readouterr().err


def test_money_and_quantities_in_tables_are_amd_and_humanised():
    assert office.amd("130050") == "1300.50" and office.amd(1300000) == "13000" and office.amd(None) == "-"
    assert office.qty(2500, "g") == "2.5 kg" and office.qty(250, "ml") == "250 ml" and office.qty(3, "pcs") == "3 pcs"
    assert office.qty(1500, "ml") == "1.5 l" and office.qty(2500, "կգ") == "2.5 kg" and office.qty(4, None) == "4"
