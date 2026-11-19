"""`siruk ops docs`: the POST /documents body field by field, the rules refused before a write, the post
review and its confirm code. Shapes are copied from siruk-web/ops/apps/api/src/modules/stock/dto/
{create-document,document-line,replace-lines}.dto.ts and packages/contracts/src/api/backoffice.ts."""
import json, re

import pytest

from siruk import cli
from siruk.ops import client as O, documents as D, guard

SHOP, STORE, SUP = ("5f0e1d8a-0000-4000-8000-00000000000%d" % i for i in (1, 2, 3))
PACK, LOOSE, DOC = ("7a1c2b3d-0000-4000-8000-00000000000%d" % i for i in (1, 2, 3))
INVOICE = "AB123456"


def run(argv):
    with pytest.raises(SystemExit) as e:
        cli.main(["-q", *argv])
    return e.value.code


# backoffice.ts StockLocationRow, SupplierRow
LOCATIONS = [{"id": SHOP, "code": "shop", "name": "Shop", "kind": "shop", "isActive": True,
              "sirukWarehouseCode": None, "armsoftStorage": None, "supplierId": None, "connector": None},
             {"id": STORE, "code": "store", "name": "Storeroom", "kind": "storeroom", "isActive": True,
              "sirukWarehouseCode": None, "armsoftStorage": None, "supplierId": None, "connector": None},
             {"id": "9c9c9c9c-0000-4000-8000-000000000009", "code": "hafo", "name": "Hafo", "kind": "supplier",
              "isActive": True, "sirukWarehouseCode": None, "armsoftStorage": None, "supplierId": SUP,
              "connector": "hafo"}]
SUPPLIERS = [{"id": SUP, "name": "Hafo", "tin": "01234567", "armsoftCode": None, "connector": "hafo",
              "isActive": True, "balanceMinor": "0"}]


def own_stock(loc_id, code, qty):
    # backoffice.ts GoodsOwnStock
    return {"kind": "shop" if code == "shop" else "storeroom", "locationId": loc_id, "locationCode": code,
            "locationName": code, "quantity": qty, "reserved": 0, "available": qty, "valueMinor": "0",
            "averageCostMinor": None}


def good(variant_id, sku, unit, shop, store, **extra):
    # backoffice.ts GoodsItem (GET /goods/:variantId adds movements)
    return {"variantId": variant_id, "productId": "p1", "sku": sku, "label": None, "barcode": None,
            "extraBarcodes": [], "accountingCode": None, "stockUnit": unit,
            "productName": {"en": "Royal Canin", "ru": None, "hy": None}, "contentMilli": 2000000,
            "packCount": 1, "stock": [own_stock(SHOP, "shop", shop), own_stock(STORE, "store", store)],
            "movements": [], **extra}


@pytest.fixture
def world(ops_fake):
    ops_fake.on("GET", "/locations", LOCATIONS).on("GET", "/suppliers", SUPPLIERS)
    ops_fake.on("GET", f"/goods/{PACK}", good(PACK, "RC-2KG", "pack", 5, 40))
    ops_fake.on("GET", f"/goods/{LOOSE}", good(LOOSE, "RC-2KG-KG", "loose", 2500, 0, contentMilli=1000000))
    return ops_fake


def writes(fake):
    return [c for c in fake.calls if c[0] != "GET"]


def plan(argv, capsys):
    capsys.readouterr()
    assert run([*argv, "--json"]) == 0
    return json.loads(capsys.readouterr().out)


def posted_body(fake, argv, capsys):
    """Dry run, then apply the code it printed; the body POST /documents received."""
    p = plan(argv, capsys)
    assert not writes(fake)
    assert run([*argv, "--apply", p["code"]]) == 0
    [(method, path, body)] = writes(fake)
    assert (method, path) == ("POST", "/documents") and body == p["requests"][0]["body"]
    return body


def new(type_, *extra, lines):
    return ["ops", "docs", "new", type_, *extra, "--lines", json.dumps(lines)]


KEY = re.compile(r"cli-[0-9a-f]{32}")


# ------------------------------------------- POST /documents, field by field ----
def test_receipt_body(world, capsys):
    world.on("POST", "/documents", lambda _: detail())
    body = posted_body(world, new("receipt", "--location", "shop", "--supplier", "01234567", "--invoice", INVOICE,
                                  "--note", "delivery", "--date", "2026-11-16",
                                  lines=[{"variant": PACK, "quantity": 12, "unit_cost_amd": 1300},
                                         {"variant": LOOSE, "quantity": "2.5kg", "amount_amd": "15600.5",
                                          "note": "bulk"}]), capsys)
    key = body.pop("idempotencyKey")
    assert KEY.fullmatch(key)
    assert body == {"type": "receipt", "locationId": SHOP, "supplierId": SUP, "invoiceSerial": INVOICE,
                    "note": "delivery", "documentDate": "2026-11-16",
                    "lines": [{"variantId": PACK, "quantity": 12, "unitCostMinor": "130000"},
                              {"variantId": LOOSE, "quantity": 2500, "amountMinor": "1560050", "note": "bulk"}]}
    assert type(body["lines"][0]["quantity"]) is int and type(body["lines"][0]["unitCostMinor"]) is str
    assert type(body["lines"][1]["amountMinor"]) is str


def test_write_off_body(world, capsys):
    world.on("POST", "/documents", lambda _: detail())
    body = posted_body(world, new("write_off", "--location", "store", "--reason", "damaged",
                                  lines=[{"variant": PACK, "quantity": 2}]), capsys)
    assert KEY.fullmatch(body.pop("idempotencyKey"))
    assert body == {"type": "write_off", "locationId": STORE, "reason": "damaged",
                    "lines": [{"variantId": PACK, "quantity": 2}]}


def test_count_body_uses_counted_quantity(world, capsys):
    world.on("POST", "/documents", lambda _: detail())
    body = posted_body(world, new("count", "--location", "shop",
                                  lines=[{"variant": PACK, "counted": 9}, {"variant": LOOSE, "counted": "500g"}]),
                       capsys)
    assert KEY.fullmatch(body.pop("idempotencyKey"))
    assert body == {"type": "count", "locationId": SHOP,
                    "lines": [{"variantId": PACK, "countedQuantity": 9},
                              {"variantId": LOOSE, "countedQuantity": 500}]}


def test_transfer_body(world, capsys):
    world.on("POST", "/documents", lambda _: detail())
    body = posted_body(world, new("transfer", "--location", "store", "--to-location", "shop",
                                  lines=[{"variant": PACK, "quantity": 6}]), capsys)
    assert KEY.fullmatch(body.pop("idempotencyKey"))
    assert body == {"type": "transfer", "locationId": STORE, "toLocationId": SHOP,
                    "lines": [{"variantId": PACK, "quantity": 6}]}


def test_supplier_return_and_bag_opening_bodies(world, capsys):
    world.on("POST", "/documents", lambda _: detail())
    body = posted_body(world, new("supplier_return", "--location", "shop", "--supplier", "Hafo", "--invoice", "R1",
                                  lines=[{"variant": PACK, "quantity": 1}]), capsys)
    assert body["supplierId"] == SUP and body["invoiceSerial"] == "R1" and "unitCostMinor" not in body["lines"][0]
    world.calls.clear()
    body = posted_body(world, new("bag_opening", "--location", "shop",
                                  lines=[{"variant": PACK, "quantity": 1, "target": LOOSE}]), capsys)
    assert body["lines"] == [{"variantId": PACK, "quantity": 1, "targetVariantId": LOOSE}]


def test_variant_found_by_sku_through_the_resolver(world, capsys):
    world.on("GET", "/goods", {"items": [good(PACK, "RC-2KG", "pack", 5, 40)], "total": 1, "page": 1,
                               "pageSize": 50, "locations": []})
    world.on("POST", "/documents", lambda _: detail())
    body = posted_body(world, new("write_off", "--location", "shop", "--reason", "lost",
                                  lines=[{"variant": "rc-2kg", "quantity": 1}]), capsys)
    assert body["lines"] == [{"variantId": PACK, "quantity": 1}]


# --------------------------------------------------------- refused before a call ----
@pytest.mark.parametrize("argv,why", [
    (new("receipt", "--location", "shop", "--invoice", INVOICE, lines=[{"variant": PACK, "quantity": 1,
                                                                        "amount_amd": 1}]), "--supplier"),
    (new("receipt", "--location", "shop", "--supplier", "Hafo", lines=[{"variant": PACK, "quantity": 1,
                                                                        "amount_amd": 1}]), "--invoice"),
    (new("supplier_return", "--location", "shop", "--supplier", "Hafo",
         lines=[{"variant": PACK, "quantity": 1}]), "--invoice"),
    (new("transfer", "--location", "shop", lines=[{"variant": PACK, "quantity": 1}]), "--to-location"),
    (new("write_off", "--location", "shop", lines=[{"variant": PACK, "quantity": 1}]), "--reason"),
    (new("write_off", "--location", "shop", "--reason", "stolen", lines=[{"variant": PACK, "quantity": 1}]),
     "--reason must be one of"),
    (new("count", "--location", "shop", "--reason", "lost", lines=[{"variant": PACK, "counted": 1}]),
     "only a write_off"),
    (new("receipt", "--location", "shop", "--to-location", "store", "--supplier", "Hafo", "--invoice", "1",
         lines=[{"variant": PACK, "quantity": 1, "amount_amd": 1}]), "only a transfer"),
    (new("sale", "--location", "shop", lines=[{"variant": PACK, "quantity": 1}]), "unknown document type"),
    (new("write_off", "--location", "shop", "--reason", "lost", "--date", "yesterday",
         lines=[{"variant": PACK, "quantity": 1}]), "ISO date"),
    (new("receipt", "--location", "shop", "--supplier", "Hafo", "--invoice", INVOICE,
         lines=[{"variant": PACK, "quantity": 1}]), 'exactly one of "unit_cost_amd"'),
    (new("receipt", "--location", "shop", "--supplier", "Hafo", "--invoice", INVOICE,
         lines=[{"variant": PACK, "quantity": 1, "unit_cost_amd": 1, "amount_amd": 1}]), "exactly one of"),
    (new("write_off", "--location", "shop", "--reason", "lost",
         lines=[{"variant": PACK, "quantity": 1, "amount_amd": 1}]), "takes no cost"),
    (new("count", "--location", "shop", lines=[{"variant": PACK, "quantity": 1}]), '"counted"'),
    (new("write_off", "--location", "shop", "--reason", "lost", lines=[{"variant": PACK, "counted": 1}]),
     "belongs to a count"),
    (new("write_off", "--location", "shop", "--reason", "lost", lines=[{"variant": PACK}]), 'needs "quantity"'),
    (new("write_off", "--location", "shop", "--reason", "lost", lines=[{"variant": PACK, "quantity": 1, "qty": 1}]),
     "unknown key qty"),
    (new("write_off", "--location", "shop", "--reason", "lost", lines=[{"variant": PACK, "quantity": 1,
                                                                        "target": LOOSE}]), "only a bag_opening"),
    (new("write_off", "--location", "shop", "--reason", "lost", lines=[]), "non-empty"),
])
def test_rule_refused_before_any_call(world, argv, why, capsys):
    capsys.readouterr()
    assert run(argv) == 1
    assert why in capsys.readouterr().err
    assert not world.calls


@pytest.mark.parametrize("line,why", [
    ({"variant": PACK, "quantity": "2.5kg"}, "pack good is counted in pcs"),
    ({"variant": PACK, "quantity": 0}, "at least 1"),
    ({"variant": PACK, "quantity": -3}, "cannot be negative"),
    ({"variant": LOOSE, "quantity": "3pcs"}, "loose good is counted in"),
])
def test_quantity_refused_before_a_write(world, line, why, capsys):
    capsys.readouterr()
    assert run(new("write_off", "--location", "shop", "--reason", "lost", lines=[line])) == 1
    assert why in capsys.readouterr().err and not writes(world)


def test_cost_and_location_rules_refused_before_a_write(world, capsys):
    bad = [new("receipt", "--location", "shop", "--supplier", "Hafo", "--invoice", "1",
               lines=[{"variant": PACK, "quantity": 1, "amount_amd": "1.234"}]),
           new("receipt", "--location", "shop", "--supplier", "Hafo", "--invoice", "1",
               lines=[{"variant": PACK, "quantity": 1, "amount_amd": -5}]),
           new("count", "--location", "shop", lines=[{"variant": PACK, "counted": 1}, {"variant": PACK, "counted": 2}]),
           new("transfer", "--location", "shop", "--to-location", "shop", lines=[{"variant": PACK, "quantity": 1}]),
           new("write_off", "--location", "hafo", "--reason", "lost", lines=[{"variant": PACK, "quantity": 1}])]
    assert [run(a) for a in bad] == [1] * len(bad) and not writes(world)


def test_count_accepts_zero(world, capsys):
    p = plan(new("count", "--location", "shop", lines=[{"variant": PACK, "counted": 0}]), capsys)
    assert p["requests"][0]["body"]["lines"] == [{"variantId": PACK, "countedQuantity": 0}]


# ------------------------------------------------------------ the idempotency key ----
def test_same_command_twice_same_key_and_key_option_changes_it(world, capsys):
    argv = new("write_off", "--location", "shop", "--reason", "lost", lines=[{"variant": PACK, "quantity": 2}])
    keys = lambda a: plan(a, capsys)["requests"][0]["body"]["idempotencyKey"]
    first = keys(argv)
    assert KEY.fullmatch(first) and keys(argv) == first
    other = keys([*argv, "--key", "second"])
    assert other != first and KEY.fullmatch(other) and keys([*argv, "--key", "second"]) == other
    assert keys([*argv, "--key", "third"]) != other
    changed = new("write_off", "--location", "shop", "--reason", "lost", lines=[{"variant": PACK, "quantity": 3}])
    assert keys(changed) != first


def test_a_new_day_is_a_new_key_and_the_same_day_the_same(world, capsys, monkeypatch):
    argv = new("write_off", "--location", "shop", "--reason", "lost", lines=[{"variant": PACK, "quantity": 1}])
    key = lambda: plan(argv, capsys)["requests"][0]["body"]["idempotencyKey"]
    monkeypatch.setattr(D, "today", lambda: "2026-11-16")
    monday = key()
    assert key() == monday
    monkeypatch.setattr(D, "today", lambda: "2026-11-23")
    assert key() != monday
    dated = [*argv, "--date", "2026-11-16"]
    first = plan(dated, capsys)["requests"][0]["body"]["idempotencyKey"]
    monkeypatch.setattr(D, "today", lambda: "2026-11-30")
    assert plan(dated, capsys)["requests"][0]["body"]["idempotencyKey"] == first
    assert "documentDate" not in plan(argv, capsys)["requests"][0]["body"]


def test_a_replayed_key_that_answers_with_a_posted_document_is_refused(world, capsys):
    # stock-documents.service.ts createDraftTx: a repeated key returns the existing document, any status
    world.on("POST", "/documents", lambda _: detail("posted", postedAt="2026-11-09T10:00:00.000Z"))
    argv = new("write_off", "--location", "shop", "--reason", "lost", lines=[{"variant": PACK, "quantity": 1}])
    code = plan(argv, capsys)["code"]
    capsys.readouterr()
    assert run([*argv, "--apply", code]) == 1
    err = capsys.readouterr().err
    assert ("Ops returned existing document RC-000001, posted since 2026-11-09T10:00:00.000Z; "
            "nothing new was made; --key makes a second one") in err
    assert [w[:2] for w in writes(world)] == [("POST", "/documents")]


@pytest.mark.parametrize("extra", [["--invoice", " "], ["--invoice", ""]])
def test_a_blank_invoice_is_refused_where_required(world, extra, capsys):
    capsys.readouterr()
    assert run(new("receipt", "--location", "shop", "--supplier", "Hafo", *extra,
                   lines=[{"variant": PACK, "quantity": 1, "amount_amd": 1}])) == 1
    assert "--invoice" in capsys.readouterr().err and not world.calls


def test_invoice_and_note_are_sent_stripped(world, capsys):
    body = plan(new("receipt", "--location", "shop", "--supplier", "Hafo", "--invoice", "  AB1 ", "--note", " hi ",
                    lines=[{"variant": PACK, "quantity": 1, "amount_amd": 1}]), capsys)["requests"][0]["body"]
    assert body["invoiceSerial"] == "AB1" and body["note"] == "hi"


@pytest.mark.parametrize("milli", [2500, None, 0])
def test_a_bag_that_cannot_pour_whole_grams_is_refused_in_the_dry_run(world, milli, capsys):
    # bag-opening gramsPerBag: `!bag.contentMilli || bag.contentMilli % 1000 !== 0` is refused
    world.on("GET", f"/goods/{PACK}", good(PACK, "RC-2KG", "pack", 5, 40, contentMilli=milli))
    doc = detail(type_="bag_opening", qty=1)
    doc["lines"][0]["targetVariantId"] = LOOSE
    world.on("GET", f"/documents/{DOC}", doc)
    capsys.readouterr()
    assert run(["ops", "docs", "post", DOC]) == 1
    assert "whole net content" in capsys.readouterr().err and not writes(world)


def test_bag_opening_review_shows_the_poured_grams(world, capsys):
    doc = detail(type_="bag_opening", qty=1)
    doc["lines"][0]["targetVariantId"] = LOOSE
    world.on("GET", f"/documents/{DOC}", doc)
    capsys.readouterr()
    assert run(["ops", "docs", "post", DOC]) == 0
    out = capsys.readouterr().out
    assert "4 pcs" in out and "2.5 kg" in out and "4.5 kg" in out


def test_dry_run_of_new_sends_nothing_and_a_wrong_code_is_refused(world, capsys):
    argv = new("write_off", "--location", "shop", "--reason", "lost", lines=[{"variant": PACK, "quantity": 2}])
    assert run(argv) == 0 and not writes(world)
    assert run([*argv, "--apply", "00000000"]) == 1 and not writes(world)


# ------------------------------------------------------------ docs post ----
def detail(status="draft", qty=12, type_="receipt", **extra):
    # backoffice.ts StockDocumentDetail / StockDocumentLineRow
    return {"id": DOC, "type": type_, "number": "RC-000001", "status": status, "locationId": SHOP,
            "locationName": "Shop", "toLocationId": None, "toLocationName": None, "supplierId": SUP,
            "supplierName": "Hafo", "invoiceSerial": INVOICE, "reason": None, "note": None,
            "documentDate": "2026-11-16T00:00:00.000Z", "createdAt": "2026-11-16T08:00:00.000Z",
            "postedAt": None, "lineCount": 1, "totalAmountMinor": "1560000", "createdById": None,
            "postedById": None,
            "lines": [{"id": "l1", "variantId": PACK, "sku": "RC-2KG", "label": None,
                       "productName": {"en": "Royal Canin", "ru": None, "hy": None}, "stockUnit": "pack",
                       "quantity": qty, "amountMinor": "1560000", "countedQuantity": None,
                       "targetVariantId": None, "targetSku": None, "postedValueMinor": None, "note": None}],
            **extra}


def test_post_dry_run_shows_stock_now_and_after_and_records_no_write(world, capsys):
    world.on("GET", f"/documents/{DOC}", detail())
    capsys.readouterr()
    assert run(["ops", "docs", "post", DOC]) == 0
    out = capsys.readouterr().out
    assert "5 pcs" in out and "+12 pcs" in out and "17 pcs" in out and "nothing sent" in out
    assert not writes(world)


def test_post_review_of_a_transfer_and_a_negative_after(world, capsys):
    doc = detail(type_="transfer", qty=50, toLocationId=STORE, toLocationName="Storeroom")
    world.on("GET", f"/documents/{DOC}", doc)
    capsys.readouterr()
    assert run(["ops", "docs", "post", DOC]) == 0
    out = capsys.readouterr().out
    assert "Shop" in out and "Storeroom" in out and "-45 pcs" in out and "NEGATIVE" in out and "90 pcs" in out
    assert not writes(world)


def test_a_line_edited_after_the_dry_run_makes_the_old_code_fail(world, capsys):
    current = {"doc": detail(qty=12)}
    world.on("GET", f"/documents/{DOC}", lambda _: current["doc"])
    world.on("POST", f"/documents/{DOC}/post", detail("posted"))
    code = plan(["ops", "docs", "post", DOC], capsys)["code"]
    current["doc"] = detail(qty=13)
    capsys.readouterr()
    assert run(["ops", "docs", "post", DOC, "--apply", code]) == 1
    assert "state that has since changed" in capsys.readouterr().err and not writes(world)
    new_code = plan(["ops", "docs", "post", DOC], capsys)["code"]
    assert new_code != code
    assert run(["ops", "docs", "post", DOC, "--apply", new_code]) == 0
    assert writes(world) == [("POST", f"/documents/{DOC}/post", None)]


def test_post_code_follows_the_document_and_the_target(world, capsys):
    world.on("GET", f"/documents/{DOC}", detail())
    code = plan(["ops", "docs", "post", DOC], capsys)["code"]
    step = guard.Step("POST", f"/documents/{DOC}/post", None, "post — final")
    assert code == guard.confirm_code([step], D.state(detail()), world.base)


def test_network_failure_on_post_apply_exits_3_and_names_the_check(world, capsys):
    world.on("GET", f"/documents/{DOC}", detail())
    world.on("POST", f"/documents/{DOC}/post", O.UnknownOutcome(0, "POST", f"/documents/{DOC}/post",
                                                                "network error: reset"))
    code = plan(["ops", "docs", "post", DOC], capsys)["code"]
    capsys.readouterr()
    assert run(["ops", "docs", "post", DOC, "--apply", code]) == 3
    assert f"`siruk ops docs show {DOC}`" in capsys.readouterr().err


@pytest.mark.parametrize("argv", [["post"], ["delete"], ["lines", "--lines", '[{"variant": "x", "quantity": 1}]']])
def test_a_posted_document_cannot_be_posted_edited_or_deleted(world, argv, capsys):
    world.on("GET", f"/documents/{DOC}", detail("posted"))
    capsys.readouterr()
    assert run(["ops", "docs", argv[0], DOC, *argv[1:]]) == 1
    assert "never changes" in capsys.readouterr().err and not writes(world)


def test_a_document_id_must_be_a_uuid(world, capsys):
    assert run(["ops", "docs", "post", "RC-000001"]) == 1 and not world.calls


# ------------------------------------------------------- docs lines / delete ----
def test_lines_replaces_a_drafts_lines_and_the_code_follows_the_current_ones(world, capsys):
    current = {"doc": detail(type_="write_off", qty=1, supplierId=None)}
    world.on("GET", f"/documents/{DOC}", lambda _: current["doc"])
    world.on("PUT", f"/documents/{DOC}/lines", {"id": DOC})
    argv = ["ops", "docs", "lines", DOC, "--lines", json.dumps([{"variant": PACK, "quantity": 4, "note": "x"}])]
    p = plan(argv, capsys)
    assert p["requests"][0] == {"method": "PUT", "path": f"/documents/{DOC}/lines", "label": "replace lines",
                                "body": {"lines": [{"variantId": PACK, "quantity": 4, "note": "x"}]}}
    current["doc"] = detail(type_="write_off", qty=2, supplierId=None)
    assert run([*argv, "--apply", p["code"]]) == 1 and not writes(world)
    assert run([*argv, "--apply", plan(argv, capsys)["code"]]) == 0
    assert writes(world) == [("PUT", f"/documents/{DOC}/lines", {"lines": [{"variantId": PACK, "quantity": 4,
                                                                           "note": "x"}]})]


def test_lines_follow_the_documents_own_type(world, capsys):
    world.on("GET", f"/documents/{DOC}", detail(type_="count"))
    capsys.readouterr()
    assert run(["ops", "docs", "lines", DOC, "--lines", '[{"variant": "%s", "quantity": 4}]' % PACK]) == 1
    assert '"counted"' in capsys.readouterr().err and not writes(world)


def test_delete_a_draft(world, capsys):
    world.on("GET", f"/documents/{DOC}", detail())
    world.on("DELETE", f"/documents/{DOC}", None)
    code = plan(["ops", "docs", "delete", DOC], capsys)["code"]
    assert not writes(world)
    assert run(["ops", "docs", "delete", DOC, "--apply", code]) == 0
    assert writes(world) == [("DELETE", f"/documents/{DOC}", None)]


# ------------------------------------------------------------------ reads ----
def test_list_passes_filters_and_json_is_unmodified(world, capsys):
    page = {"items": [detail()], "total": 1, "page": 1, "pageSize": 50}
    world.on("GET", "/documents", page)
    capsys.readouterr()
    assert run(["ops", "docs", "list", "--type", "receipt", "--status", "draft", "--location", "shop",
                "--from", "2026-11-01", "--to", "2026-11-30", "--json"]) == 0
    assert json.loads(capsys.readouterr().out) == page
    assert world.calls[-1] == ("GET", "/documents", {"type": "receipt", "status": "draft", "from": "2026-11-01",
                                                     "to": "2026-11-30", "locationId": SHOP})
    assert run(["ops", "docs", "list"]) == 0
    assert "RC-000001" in capsys.readouterr().out


def test_show_prints_a_table_in_amd_and_json_unmodified(world, capsys):
    world.on("GET", f"/documents/{DOC}", detail())
    capsys.readouterr()
    assert run(["ops", "docs", "show", DOC]) == 0
    out = capsys.readouterr().out
    assert "15600 AMD" in out and "RC-2KG" in out and "Hafo" in out
    assert run(["ops", "docs", "show", DOC, "--json"]) == 0
    assert json.loads(capsys.readouterr().out) == detail()


# ---------------------------------------------------------------- manifest ----
def test_the_six_commands_are_in_the_manifest_with_every_field_filled(capsys):
    assert run(["commands", "--json"]) == 0
    rows = {r["name"]: r for r in json.loads(capsys.readouterr().out) if r["name"].startswith("ops docs")}
    assert sorted(rows) == [f"ops docs {n}" for n in ("delete", "lines", "list", "new", "post", "show")]
    assert {n: rows[f"ops docs {n}"]["tier"] for n in ("list", "show", "new", "lines", "post", "delete")} == \
        {"list": "read", "show": "read", "new": "draft", "lines": "draft", "post": "irreversible",
         "delete": "draft"}
    assert {"GET /goods", "GET /goods/:variantId", "GET /locations", "GET /suppliers"} <= set(rows["ops docs new"]["api"])
    assert {"GET /goods", "GET /goods/:variantId"} <= set(rows["ops docs lines"]["api"])
    for r in rows.values():
        assert r["backend"] == "ops" and r["api"] and r["roles"] == "manager, warehouse" and r["help"] and r["example"]


# ------------------------------------------------- many lines: one list read ----
def many_goods(n):
    ids = ["7a1c2b3d-0000-4000-8000-%012d" % (100 + i) for i in range(n)]
    return ids, [good(v, f"SKU-{i}", "pack", i, 0) for i, v in enumerate(ids)]


def paged_list(goods, size):
    def answer(p):
        page = int(p["page"])
        return {"items": goods[(page - 1) * size: page * size], "total": len(goods), "page": page,
                "pageSize": size}
    return answer


def test_a_big_document_reads_the_goods_list_once_not_each_line(world, capsys):
    ids, goods = many_goods(250)
    world.on("GET", "/goods", paged_list(goods, 200)).on("POST", "/documents", lambda _: detail())
    lines = [{"variant": v, "quantity": 1, "amount_amd": 100} for v in ids[:240]] + \
            [{"variant": f"SKU-{i}", "quantity": 2, "amount_amd": 200} for i in range(240, 250)]
    body = posted_body(world, new("opening_balance", "--location", "shop", lines=lines), capsys)
    assert [l["variantId"] for l in body["lines"]] == ids
    gets = [c for c in world.calls if c[0] == "GET" and c[1].startswith("/goods")]
    assert all(c[1] == "/goods" for c in gets) and len(gets) == 4   # 2 pages, dry run and apply


def test_a_small_document_still_reads_each_line(world, capsys):
    plan(new("receipt", "--location", "shop", "--supplier", "Hafo", "--invoice", INVOICE,
             lines=[{"variant": PACK, "quantity": 1, "unit_cost_amd": 1300}]), capsys)
    assert ("GET", f"/goods/{PACK}", None) in world.calls
    assert not [c for c in world.calls if c[1] == "/goods"]


def test_a_ref_the_list_does_not_settle_falls_back_to_one_lookup(world, capsys):
    ids, goods = many_goods(25)
    world.on("GET", "/goods", lambda p: paged_list(goods, 200)(p) if "q" not in p else
             {"items": [], "total": 0, "page": 1, "pageSize": 50})
    lines = [{"variant": v, "quantity": 1, "amount_amd": 1} for v in ids[:24]] +             [{"variant": "NOT-THERE", "quantity": 1, "amount_amd": 1}]
    capsys.readouterr()
    assert run(new("opening_balance", "--location", "shop", lines=lines)) == 1   # refused as before
    assert "no good matches 'NOT-THERE'" in capsys.readouterr().err
    assert ("GET", "/goods", {"q": "NOT-THERE", "page": 1}) in world.calls


def test_post_review_of_a_big_document_reads_the_list(world, capsys):
    ids, goods = many_goods(30)
    world.on("GET", "/goods", paged_list(goods, 200))
    doc = detail(type_="opening_balance", supplierId=None, supplierName=None, invoiceSerial=None)
    doc["lines"] = [{**doc["lines"][0], "id": f"l{i}", "variantId": v, "sku": f"SKU-{i}", "quantity": 1}
                    for i, v in enumerate(ids)]
    world.on("GET", f"/documents/{DOC}", doc)
    capsys.readouterr()
    assert run(["ops", "docs", "post", DOC]) == 0
    assert "SKU-29" in capsys.readouterr().out
    assert not [c for c in world.calls if c[1].startswith("/goods/")]
