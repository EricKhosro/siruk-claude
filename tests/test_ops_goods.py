"""Ops goods, locations and open-bag. Fixture shapes are copied from
siruk-web/ops/packages/contracts/src/api/backoffice.ts (GoodsItem, GoodsDetail, GoodsListResponse,
StockLocationRow, OpenBagResult) and the request bodies from apps/api/src/modules/stock/dto/*.dto.ts."""
import json, re

import pytest

from siruk import cli
from siruk.ops import client as O, guard
from siruk.ops.guard import confirm_code

ID = "5c1d8a0e-2b7f-4f43-9a55-0d6e3b1c7a01"
ID2 = "6d2e9b1f-3c80-4a54-8b66-1e7f4c2d8b02"
LOOSE = "7e3fac20-4d91-4b65-9c77-2f805d3e9c03"
SHOP = "8f40bd31-5ea2-4c76-8d88-30916e4fad04"
STORE = "9051ce42-6fb3-4d87-9e99-41a27f50be05"
HAFO = "a162df53-70c4-4e98-8faa-52b38061cf06"


def run(argv):
    with pytest.raises(SystemExit) as e:
        cli.main(["-q", *argv])
    return e.value.code


# siruk-web/ops/packages/contracts/src/api/backoffice.ts: GoodsItem (GoodsDetail adds `movements`)
def good(**kw):
    """A 2 kg pack; the loose twin below is its by-weight good."""
    g = {"variantId": ID, "productId": "p-1", "sirukProductId": 874, "sirukVariantId": 3871,
         "productName": {"en": "Royal Canin Mini", "ru": None, "hy": None}, "brand": "Royal Canin",
         "sku": "387957", "label": "2 kg", "barcode": "3182550402323", "extraBarcodes": [
             {"code": "9000000000017", "units": 6, "sellable": False}],
         "accountingCode": None, "measureType": "mass", "contentMilli": 2000000, "packCount": 1,
         "stockUnit": "pack", "bag": None, "salePriceMinor": "1300000", "prices": [], "promotion": None,
         "isActive": True, "isDiscontinued": False, "fiscalName": "Royal Canin Mini", "adgCode": "2309.10",
         "lowStockAt": 2, "reorderMode": "global", "reorderPoint": None, "reorderTarget": None,
         "reorderSource": "manual", "costPerQuantity": 1, "totalAvailable": 7, "isLow": False,
         "stock": [{"kind": "shop", "locationId": SHOP, "locationCode": "SHOP", "locationName": "Shop",
                    "quantity": 7, "reserved": 0, "available": 7, "valueMinor": "700000",
                    "averageCostMinor": "100000"},
                   {"kind": "supplier", "locationId": HAFO, "locationCode": "HAFO", "locationName": "Hafo",
                    "quantity": None, "inStock": None, "observedAt": None}]}
    return {**g, **kw}


def loose(**kw):
    return good(**{"variantId": LOOSE, "sku": "387957-KG", "label": None, "stockUnit": "loose",
                   "barcode": "4048422122074", "extraBarcodes": [], **kw})


def paged(*items):
    return {"items": list(items), "total": len(items), "page": 1, "pageSize": 50, "locations": []}


# siruk-web/ops/apps/api/src/modules/stock/locations.controller.ts → StockLocationRow[] (backoffice.ts)
LOCATIONS = [
    {"id": SHOP, "code": "SHOP", "name": "Shop", "kind": "shop", "isActive": True, "sirukWarehouseCode": "main",
     "armsoftStorage": "01", "supplierId": None, "connector": None},
    {"id": STORE, "code": "BACK", "name": "Storeroom", "kind": "storeroom", "isActive": True,
     "sirukWarehouseCode": None, "armsoftStorage": None, "supplierId": None, "connector": None},
    {"id": HAFO, "code": "HAFO", "name": "Hafo", "kind": "supplier", "isActive": True,
     "sirukWarehouseCode": None, "armsoftStorage": None, "supplierId": "s-1", "connector": "hafo"}]


@pytest.fixture
def ops(ops_fake):
    ops_fake.state = {ID: good(), LOOSE: loose()}
    ops_fake.on("GET", re.compile(r"/goods/([0-9a-f-]{36})"),
                lambda _: {**ops_fake.state[ops_fake.calls[-1][1].rsplit("/", 1)[1]], "movements": []})
    ops_fake.on("GET", "/goods", lambda p: paged(*[g for g in ops_fake.state.values()
                                                  if p["q"].lower() in (g["sku"].lower(), g["barcode"])]))
    ops_fake.on("GET", "/locations", LOCATIONS)
    return ops_fake


def writes(c):
    return [x for x in c.calls if x[0] != "GET"]


def dry(argv, capsys):
    capsys.readouterr()
    assert run([*argv, "--json"]) == 0
    return json.loads(capsys.readouterr().out)


def apply(argv, capsys):
    code = dry(argv, capsys)["code"]
    return run([*argv, "--apply", code])


# ------------------------------------------------------------ the manifest ----
def test_every_p2_command_is_registered_with_its_facts(capsys):
    assert run(["commands", "--json"]) == 0
    by = {r["name"]: r for r in json.loads(capsys.readouterr().out)}
    want = {"ops goods list": "read", "ops goods show": "read", "ops goods set": "draft",
            "ops goods set-many": "draft", "ops goods barcode add": "draft", "ops goods barcode rm": "draft",
            "ops goods plu": "irreversible", "ops locations list": "read", "ops locations create": "draft",
            "ops locations set": "draft", "ops open-bag": "irreversible"}
    for name, tier in want.items():
        r = by[name]
        assert r["backend"] == "ops" and r["tier"] == tier, name
        assert r["api"] and r["roles"] and r["example"].startswith("siruk "), name
    assert by["ops goods set"]["roles"] == "manager, warehouse" and by["ops locations set"]["roles"] == "manager"


# ------------------------------------------------------------------- reads ----
def test_list_sends_filters_and_prints_a_table(ops, capsys):
    ops.on("GET", "/goods", paged(good(), loose(isLow=True, totalAvailable=900)))
    assert run(["ops", "goods", "list", "royal", "--location", "SHOP", "--low", "--unit", "pack"]) == 0
    assert ops.calls[-1] == ("GET", "/goods", {"q": "royal", "stockUnit": "pack", "page": None,
                                               "pageSize": None, "locationId": SHOP, "lowStock": True})
    out = capsys.readouterr().out
    assert "387957-KG" in out and "900 g" in out and "LOW" in out


def test_list_json_is_the_api_answer_unchanged(ops, capsys):
    r = paged(good())
    ops.on("GET", "/goods", r)
    assert run(["ops", "goods", "list", "--json"]) == 0
    assert json.loads(capsys.readouterr().out) == r


def test_show_prints_every_warehouse_including_a_supplier_never_observed(ops, capsys):
    assert run(["ops", "goods", "show", "387957"]) == 0
    out = capsys.readouterr().out
    assert "Royal Canin Mini 2 kg (SKU 387957)" in out and "2309.10" in out
    assert "SHOP" in out and "HAFO" in out and "supplier" in out
    assert "9000000000017 (x6, receiving only)" in out


def test_show_by_id_does_not_fetch_twice(ops, capsys):
    assert run(["ops", "goods", "show", ID, "--json"]) == 0
    assert [c[1] for c in ops.calls] == [f"/goods/{ID}"]
    assert json.loads(capsys.readouterr().out)["movements"] == []


# ------------------------------------------------------------- goods set ----
def test_set_dry_run_shows_the_good_and_before_after_and_writes_nothing(ops, capsys):
    assert run(["ops", "goods", "set", "387957", "--fiscal-name", "RC Mini 2kg", "--adg", "2309.90"]) == 0
    out = capsys.readouterr().out
    assert "Royal Canin Mini 2 kg (SKU 387957)" in out
    assert "fiscalName: 'Royal Canin Mini' → 'RC Mini 2kg'" in out and "adgCode: '2309.10' → '2309.90'" in out
    assert "tier       draft" in out and writes(ops) == []


def test_set_sends_exactly_the_changed_dto_fields(ops, capsys):
    # siruk-web/ops/apps/api/src/modules/stock/dto/update-goods.dto.ts: fiscalName, adgCode, lowStockAt, reorderMode, reorderPoint, reorderTarget
    ops.on("PATCH", f"/goods/{ID}", good())
    argv = ["ops", "goods", "set", "387957", "--fiscal-name", "RC Mini 2kg", "--adg", "2309.10",
            "--reorder-mode", "custom", "--reorder-point", "3", "--reorder-target", "12", "--clear", "low-stock-at"]
    assert apply(argv, capsys) == 0
    # adgCode is unchanged, so it is not sent
    assert writes(ops) == [("PATCH", f"/goods/{ID}", {"fiscalName": "RC Mini 2kg", "lowStockAt": None,
                                                      "reorderMode": "custom", "reorderPoint": 3,
                                                      "reorderTarget": 12})]


def test_set_converts_a_low_stock_level_by_the_goods_own_unit(ops, capsys):
    ops.on("PATCH", f"/goods/{LOOSE}", loose())
    assert apply(["ops", "goods", "set", "387957-KG", "--low-stock-at", "2.5kg"], capsys) == 0
    assert writes(ops) == [("PATCH", f"/goods/{LOOSE}", {"lowStockAt": 2500})]
    assert run(["ops", "goods", "set", "387957", "--low-stock-at", "2kg"]) == 1   # kg on a pack


def test_set_dry_run_says_what_a_low_stock_or_reorder_change_sets_off(ops, capsys):
    assert run(["ops", "goods", "set", "387957", "--low-stock-at", "5"]) == 0
    out = capsys.readouterr().out
    assert "queues the good to siruk (stock push, when that setting is on)" in out and "reorderSource" not in out
    assert run(["ops", "goods", "set", "387957", "--reorder-point", "3"]) == 0
    out = capsys.readouterr().out
    assert "reorderSource becomes manual" in out and "queues" not in out
    assert run(["ops", "goods", "set", "387957", "--adg", "1"]) == 0
    out = capsys.readouterr().out
    assert "reorderSource" not in out and "queues" not in out


def test_set_many_summary_carries_the_same_lines(ops, tmp_path, capsys):
    f = many(tmp_path, [{"ref": "387957", "low_stock_at": 5, "reorder_mode": "never"}])
    s = dry(["ops", "goods", "set-many", f], capsys)["summary"]
    assert "queues the good to siruk" in s and "reorderSource becomes manual" in s


def test_set_with_nothing_different_writes_nothing(ops, capsys):
    assert run(["ops", "goods", "set", "387957", "--adg", "2309.10"]) == 0
    assert "nothing to change" in capsys.readouterr().out and writes(ops) == []


@pytest.mark.parametrize("flags", [["--fiscal-name", "x" * 51], ["--adg", "23O9"], ["--adg", "12-3"],
                                   ["--fiscal-name", " "], ["--reorder-point", "-1"], ["--reorder-target", "1.5"],
                                   ["--fiscal-name", "a", "--clear", "fiscal-name"]])
def test_set_refuses_a_bad_value_before_any_call(ops, flags):
    assert run(["ops", "goods", "set", "387957", *flags]) == 1
    assert ops.calls == []


def test_set_accepts_exactly_50_characters(ops, capsys):
    assert run(["ops", "goods", "set", "387957", "--fiscal-name", "x" * 50]) == 0
    assert "x" * 50 in capsys.readouterr().out


def test_a_stale_code_is_refused_and_writes_nothing(ops, capsys):
    argv = ["ops", "goods", "set", "387957", "--fiscal-name", "RC Mini 2kg"]
    code = dry(argv, capsys)["code"]
    ops.state[ID] = good(fiscalName="Someone else's edit")
    assert run([*argv, "--apply", code]) == 1
    assert "changed" in capsys.readouterr().err and writes(ops) == []


def test_a_code_from_another_plan_is_refused(ops, capsys):
    code = dry(["ops", "goods", "set", "387957", "--fiscal-name", "A"], capsys)["code"]
    assert run(["ops", "goods", "set", "387957", "--fiscal-name", "B", "--apply", code]) == 1
    assert writes(ops) == []


def test_apply_with_the_right_code_by_hand(ops):
    ops.on("PATCH", f"/goods/{ID}", good())
    steps = [guard.Step("PATCH", f"/goods/{ID}", {"fiscalName": "Z"}, label="387957")]
    state = {"variantId": ID, "before": {"fiscalName": "Royal Canin Mini"}}
    code = confirm_code(steps, state, ops.base)
    assert run(["ops", "goods", "set", ID, "--fiscal-name", "Z", "--apply", code]) == 0
    assert writes(ops) == [("PATCH", f"/goods/{ID}", {"fiscalName": "Z"})]


def test_an_ambiguous_ref_is_refused(ops):
    ops.state[ID2] = good(variantId=ID2)
    assert run(["ops", "goods", "set", "387957", "--adg", "1"]) == 1
    assert writes(ops) == []


# -------------------------------------------------------------- set-many ----
def many(tmp_path, rows):
    f = tmp_path / "rows.json"
    f.write_text(json.dumps(rows))
    return str(f)


def test_set_many_shows_every_row_in_one_dry_run_with_one_code(ops, tmp_path, capsys):
    f = many(tmp_path, [{"ref": "387957", "fiscal_name": "RC Mini"}, {"ref": "387957-KG", "adg": "2309.90"}])
    d = dry(["ops", "goods", "set-many", f], capsys)
    assert [r["method"] for r in d["requests"]] == ["PATCH", "PATCH"] and len(d["code"]) == 8
    assert "1. Royal Canin Mini 2 kg (SKU 387957)" in d["summary"] and "2. " in d["summary"]
    assert "fiscalName: 'Royal Canin Mini' → 'RC Mini'" in d["summary"] and "'2309.10' → '2309.90'" in d["summary"]
    assert writes(ops) == []


def test_set_many_sends_one_patch_per_good_in_order(ops, tmp_path, capsys):
    # siruk-web/ops/apps/api/src/modules/stock/goods.controller.ts PATCH :variantId, dto/update-goods.dto.ts (null clears)
    ops.on("PATCH", f"/goods/{ID}", good()).on("PATCH", f"/goods/{LOOSE}", loose())
    f = many(tmp_path, [{"ref": "387957", "fiscal_name": "RC Mini"}, {"ref": "387957-KG", "adg": None}])
    assert apply(["ops", "goods", "set-many", f], capsys) == 0
    assert writes(ops) == [("PATCH", f"/goods/{ID}", {"fiscalName": "RC Mini"}),
                           ("PATCH", f"/goods/{LOOSE}", {"adgCode": None})]


def test_set_many_stops_at_the_first_failing_row_and_says_what_was_written(ops, tmp_path, capsys):
    # siruk-web/ops/apps/api/src/modules/stock/goods.controller.ts PATCH :variantId, dto/update-goods.dto.ts
    ops.state[ID2] = good(variantId=ID2, sku="500100", barcode="111111111111", extraBarcodes=[])
    third = loose(variantId="b273e064-81d5-4fa9-9fbb-63c49172d007", sku="500200", barcode="222222222222")
    ops.state[third["variantId"]] = third
    ops.on("PATCH", f"/goods/{ID}", good())
    ops.on("PATCH", f"/goods/{ID2}", O.OpsError(409, "PATCH", f"/goods/{ID2}", '{"message":"no","error":"X"}'))
    f = many(tmp_path, [{"ref": "387957", "adg": "1"}, {"ref": "500100", "adg": "2"}, {"ref": "500200", "adg": "3"}])
    argv = ["ops", "goods", "set-many", f]
    assert apply(argv, capsys) == 2
    assert [w[1] for w in writes(ops)] == [f"/goods/{ID}", f"/goods/{ID2}"]   # the third is never sent
    err = capsys.readouterr().err
    assert "step 2 of 3" in err and "1 before it were applied" in err
    code = dry(argv, capsys)["code"]
    assert run([*argv, "--apply", code, "--json"]) == 2
    out = json.loads(capsys.readouterr().out)
    assert [a["label"] for a in out["applied"]] == ["387957"] and out["failed"]["label"] == "500100"


@pytest.mark.parametrize("rows", [[{"ref": "387957", "fiscal_name": "x" * 51}],
                                  [{"ref": "387957", "adg": "1"}, {"ref": "387957-KG", "adg": "ab"}],
                                  [{"ref": "387957", "price": 5}], [{"fiscal_name": "x"}], [{"ref": "387957"}],
                                  [{"ref": "387957", "reorder_mode": "sometimes"}]])
def test_set_many_refuses_a_bad_row_before_any_call(ops, tmp_path, rows):
    assert run(["ops", "goods", "set-many", many(tmp_path, rows)]) == 1
    assert ops.calls == []


def test_set_many_refuses_two_rows_for_one_good(ops, tmp_path):
    f = many(tmp_path, [{"ref": "387957", "adg": "1"}, {"ref": ID, "adg": "2"}])
    assert run(["ops", "goods", "set-many", f]) == 1
    assert writes(ops) == []


def test_set_many_an_unknown_good_is_refused_with_its_row(ops, tmp_path, capsys):
    assert run(["ops", "goods", "set-many", many(tmp_path, [{"ref": "nope", "adg": "1"}])]) == 1
    assert "row 1 (nope)" in capsys.readouterr().err and writes(ops) == []


# -------------------------------------------------------------- barcodes ----
def test_barcode_add_posts_the_dto_fields(ops, capsys):
    # siruk-web/ops/apps/api/src/modules/stock/dto/add-barcode.dto.ts: code, units, sellable
    ops.on("POST", f"/goods/{ID}/barcodes", good())
    assert apply(["ops", "goods", "barcode", "add", "387957", "4048422122074", "--units", "26",
                  "--receiving-only"], capsys) == 0
    assert writes(ops) == [("POST", f"/goods/{ID}/barcodes",
                            {"code": "4048422122074", "units": 26, "sellable": False})]


def test_barcode_add_with_only_a_code_sends_only_the_code(ops, capsys):
    ops.on("POST", f"/goods/{ID}/barcodes", good())
    assert apply(["ops", "goods", "barcode", "add", "387957", "ABCD-1234"], capsys) == 0
    assert writes(ops)[0][2] == {"code": "ABCD-1234"}


@pytest.mark.parametrize("args", [["abc"], ["x" * 33], ["12 34 56"], ["9000000000017"], ["3182550402323"],
                                  ["1234567", "--units", "0"], ["1234567", "--units", "10001"]])
def test_barcode_add_refuses_a_bad_or_held_code(ops, args):
    assert run(["ops", "goods", "barcode", "add", "387957", *args]) == 1
    assert writes(ops) == []


def test_barcode_add_dry_run_shows_the_barcodes_now(ops, capsys):
    assert run(["ops", "goods", "barcode", "add", "387957", "4048422122074"]) == 0
    assert "main 3182550402323; extra 9000000000017" in capsys.readouterr().out


def test_barcode_rm_deletes_the_extra_code(ops, capsys):
    # siruk-web/ops/apps/api/src/modules/stock/goods.controller.ts DELETE :variantId/barcodes/:code
    ops.on("DELETE", f"/goods/{ID}/barcodes/9000000000017", good())
    assert apply(["ops", "goods", "barcode", "rm", "387957", "9000000000017"], capsys) == 0
    assert writes(ops) == [("DELETE", f"/goods/{ID}/barcodes/9000000000017", None)]


def test_barcode_rm_refuses_the_main_barcode_and_a_stranger(ops):
    for code in ("3182550402323", "7777777777"):
        assert run(["ops", "goods", "barcode", "rm", "387957", code]) == 1
    assert writes(ops) == []


# ------------------------------------------------------------------- PLU ----
def test_plu_puts_the_number_and_the_dry_run_says_the_ean_moves(ops, capsys):
    # siruk-web/ops/apps/api/src/modules/stock/dto/set-plu.dto.ts: plu; goods.service.ts setPlu moves the EAN to the extra barcodes
    ops.on("PUT", f"/goods/{LOOSE}/plu", loose())
    argv = ["ops", "goods", "plu", "387957-KG", "121"]
    assert run(argv) == 0
    out = capsys.readouterr().out
    assert "tier       irreversible" in out and "4048422122074 moves to the extra barcodes" in out
    assert "main barcode: '4048422122074' → 121" in out and writes(ops) == []
    assert apply(argv, capsys) == 0
    assert writes(ops) == [("PUT", f"/goods/{LOOSE}/plu", {"plu": 121})]


def test_plu_without_an_ean_says_so(ops, capsys):
    ops.state[LOOSE] = loose(barcode=None, accountingCode="ACC1")
    assert run(["ops", "goods", "plu", "387957-KG", "121"]) == 0
    assert "no other main barcode" in capsys.readouterr().out


@pytest.mark.parametrize("plu", ["0", "100000", "-4"])
def test_plu_out_of_range_is_refused(ops, plu):
    assert run(["ops", "goods", "plu", "387957-KG", plu]) == 1
    assert writes(ops) == []


def test_plu_refuses_a_pack_and_a_good_that_has_one(ops):
    assert run(["ops", "goods", "plu", "387957", "121"]) == 1
    ops.state[LOOSE] = loose(barcode="121")
    assert run(["ops", "goods", "plu", "121", "122"]) == 1
    assert writes(ops) == []


# ------------------------------------------------------------- locations ----
def test_locations_list(ops, capsys):
    assert run(["ops", "locations", "list"]) == 0
    out = capsys.readouterr().out
    assert "BACK" in out and "HAFO" in out and "armsoft" in out
    assert run(["ops", "locations", "list", "--json"]) == 0
    assert json.loads(capsys.readouterr().out) == LOCATIONS


def test_locations_create_posts_the_dto_fields(ops, capsys):
    # siruk-web/ops/apps/api/src/modules/stock/dto/create-location.dto.ts: code, name, kind, sirukWarehouseCode, armsoftStorage
    ops.on("POST", "/locations", LOCATIONS[0])
    argv = ["ops", "locations", "create", "--code", "SH2", "--name", "Shop 2", "--kind", "shop",
            "--armsoft-storage", "02"]
    assert apply(argv, capsys) == 0
    assert writes(ops) == [("POST", "/locations", {"code": "SH2", "name": "Shop 2", "kind": "shop",
                                                   "armsoftStorage": "02"})]


def test_locations_create_goes_stale_when_the_list_changes(ops, capsys):
    argv = ["ops", "locations", "create", "--code", "SH2", "--name", "Shop 2", "--kind", "shop"]
    code = dry(argv, capsys)["code"]
    ops.on("GET", "/locations", [*LOCATIONS, {**LOCATIONS[1], "id": "x", "code": "OTHER"}])
    assert run([*argv, "--apply", code]) == 1
    assert writes(ops) == []


@pytest.mark.parametrize("flags", [["--code", "has space", "--name", "n", "--kind", "shop"],
                                   ["--code", "x" * 17, "--name", "n", "--kind", "shop"],
                                   ["--code", "OK", "--name", " ", "--kind", "shop"],
                                   ["--code", "OK", "--name", "n" * 101, "--kind", "storeroom"],
                                   ["--code", "OK", "--name", "n", "--kind", "shop", "--armsoft-storage", "x" * 17],
                                   ["--code", "OK", "--name", "n", "--kind", "shop", "--siruk-warehouse-code",
                                    "w" * 51]])
def test_locations_create_refuses_a_bad_value_before_any_call(ops, flags):
    assert run(["ops", "locations", "create", *flags]) == 1
    assert ops.calls == []


def test_locations_create_refuses_a_taken_code_and_a_supplier_kind(ops, capsys):
    assert run(["ops", "locations", "create", "--code", "shop", "--name", "n", "--kind", "shop"]) == 1
    assert run(["ops", "locations", "create", "--code", "S9", "--name", "n", "--kind", "supplier"]) == 2   # not a choice
    assert writes(ops) == []


def test_locations_set_patches_the_changed_fields_only(ops, capsys):
    # siruk-web/ops/apps/api/src/modules/stock/dto/update-location.dto.ts: name, isActive, sirukWarehouseCode, armsoftStorage
    ops.on("PATCH", f"/locations/{STORE}", LOCATIONS[1])
    argv = ["ops", "locations", "set", "BACK", "--name", "Storeroom", "--inactive", "--armsoft-storage", "09",
            "--clear", "siruk-warehouse-code"]
    assert apply(argv, capsys) == 0
    assert writes(ops) == [("PATCH", f"/locations/{STORE}", {"isActive": False, "armsoftStorage": "09"})]


def test_locations_set_clears_with_null_and_shows_before_after(ops, capsys):
    ops.on("PATCH", f"/locations/{SHOP}", LOCATIONS[0])
    argv = ["ops", "locations", "set", SHOP, "--clear", "armsoft-storage"]
    assert run(argv) == 0
    assert "armsoftStorage: '01' → (empty)" in capsys.readouterr().out
    assert apply(argv, capsys) == 0
    assert writes(ops) == [("PATCH", f"/locations/{SHOP}", {"armsoftStorage": None})]


def test_locations_set_refuses_a_supplier_warehouse_and_an_empty_command(ops):
    assert run(["ops", "locations", "set", "HAFO", "--name", "x"]) == 1
    assert run(["ops", "locations", "set", "SHOP"]) == 1
    assert run(["ops", "locations", "set", "SHOP", "--name", " "]) == 1
    assert writes(ops) == []


# -------------------------------------------------------------- open-bag ----
# siruk-web/ops/apps/api/src/modules/stock/open-bag.controller.ts POST /stock/open-bag; OpenBagResult in packages/contracts/src/api/backoffice.ts
def open_bag_fixture(ops):
    """Ops as it behaves: the POST takes `bags` off the bag's count at the location."""
    def post(b):
        for st in ops.state[b["bagVariantId"]]["stock"]:
            if st["locationId"] == b["locationId"]:
                st["quantity"] -= b["bags"]
        return {"documentId": "d-1", "documentNumber": "BO-1", "bagVariantId": ID, "looseVariantId": LOOSE,
                "bags": b["bags"], "poured": 2000, "bagQuantityAfter": 5, "looseQuantityAfter": 2000}
    ops.on("POST", "/stock/open-bag", post)


UUID_RE = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}")


def test_open_bag_posts_the_dto_fields_with_a_v4_request_id(ops, capsys):
    # siruk-web/ops/apps/api/src/modules/stock/dto/open-bag.dto.ts: locationId, bagVariantId, bags, looseVariantId?, clientRequestId? (a UUID)
    open_bag_fixture(ops)
    argv = ["ops", "open-bag", "SHOP", "387957", "2", "--loose", "387957-KG"]
    assert apply(argv, capsys) == 0
    (_, path, body), = writes(ops)
    assert path == "/stock/open-bag"
    assert set(body) == {"locationId", "bagVariantId", "bags", "looseVariantId", "clientRequestId"}
    assert (body["locationId"], body["bagVariantId"], body["bags"], body["looseVariantId"]) == (SHOP, ID, 2, LOOSE)
    assert body["clientRequestId"] == guard.idem_uuid("open-bag", SHOP, ID, 2, LOOSE, None, 7)
    assert UUID_RE.fullmatch(body["clientRequestId"])


def test_open_bag_without_a_loose_good_omits_the_field(ops, capsys):
    open_bag_fixture(ops)
    assert apply(["ops", "open-bag", "SHOP", "387957", "1"], capsys) == 0
    assert "looseVariantId" not in writes(ops)[0][2]


def test_a_retry_after_a_failed_attempt_keeps_the_request_id(ops, capsys):
    argv = ["ops", "open-bag", "SHOP", "387957", "1"]
    ops.on("POST", "/stock/open-bag", O.OpsError(500, "POST", "/stock/open-bag", '{"message":"boom"}'))
    assert dry(argv, capsys)["requests"][0]["body"]["clientRequestId"] == \
        dry(argv, capsys)["requests"][0]["body"]["clientRequestId"]
    assert apply(argv, capsys) == 2
    open_bag_fixture(ops)
    assert apply(argv, capsys) == 0
    first, second = (w[2]["clientRequestId"] for w in writes(ops))
    assert first == second and ops.state[ID]["stock"][0]["quantity"] == 6


def test_a_genuine_repeat_after_an_opening_is_a_new_request(ops, capsys):
    open_bag_fixture(ops)
    argv = ["ops", "open-bag", "SHOP", "387957", "1"]
    assert apply(argv, capsys) == 0 and apply(argv, capsys) == 0
    first, second = (w[2]["clientRequestId"] for w in writes(ops))
    assert first != second and ops.state[ID]["stock"][0]["quantity"] == 5


def test_a_tag_or_a_different_count_is_a_different_request(ops, capsys):
    ids = set()
    for argv in (["ops", "open-bag", "SHOP", "387957", "1"], ["ops", "open-bag", "SHOP", "387957", "2"],
                 ["ops", "open-bag", "SHOP", "387957", "1", "--tag", "second"]):
        ids.add(dry(argv, capsys)["requests"][0]["body"]["clientRequestId"])
    assert len(ids) == 3


def test_open_bag_dry_run_shows_the_count_before_and_after(ops, capsys):
    assert run(["ops", "open-bag", "SHOP", "387957", "2"]) == 0
    out = capsys.readouterr().out
    assert "tier       irreversible" in out and "on hand 7 pcs → 5 pcs" in out and writes(ops) == []


def test_a_replayed_answer_with_an_unchanged_count_is_refused(ops, capsys):
    # an earlier opening's document comes back and nothing moves (stock/stock-documents.service.ts)
    ops.on("POST", "/stock/open-bag", {"documentId": "d-0", "documentNumber": "BO-0", "bagVariantId": ID,
                                       "looseVariantId": LOOSE, "bags": 2, "poured": 4000,
                                       "bagQuantityAfter": 7, "looseQuantityAfter": 0})
    assert apply(["ops", "open-bag", "SHOP", "387957", "2"], capsys) == 1
    assert "refused: Ops returned earlier opening BO-0; nothing opened; --tag opens another" in \
        capsys.readouterr().err


def test_a_normal_opening_reads_the_count_back_and_exits_0(ops, capsys):
    open_bag_fixture(ops)
    assert apply(["ops", "open-bag", "SHOP", "387957", "2"], capsys) == 0
    assert ops.state[ID]["stock"][0]["quantity"] == 5
    assert ops.calls[-1][:2] == ("GET", f"/goods/{ID}")


def test_an_unreadable_read_back_after_the_post_is_an_unknown_outcome(ops, capsys):
    open_bag_fixture(ops)
    argv = ["ops", "open-bag", "SHOP", "387957", "1"]
    code = dry(argv, capsys)["code"]
    ops.on("GET", f"/goods/{ID}", O.OpsError(503, "GET", f"/goods/{ID}", "unavailable"))
    assert run([*argv, "--apply", code]) == 3
    err = capsys.readouterr().err
    assert "outcome unknown: the bag count could not be read back" in err and f"siruk ops goods show {ID}" in err


@pytest.mark.parametrize("body", [None, [], "ok"])
def test_an_empty_or_non_object_read_back_is_an_unknown_outcome_not_a_traceback(ops, capsys, body):
    open_bag_fixture(ops)
    argv = ["ops", "open-bag", "SHOP", "387957", "1"]
    code = dry(argv, capsys)["code"]
    ops.on("GET", f"/goods/{ID}", body)
    assert run([*argv, "--apply", code]) == 3
    assert "outcome unknown: the bag count could not be read back" in capsys.readouterr().err


def test_open_bag_unknown_outcome_exits_3(ops, capsys):
    ops.on("POST", "/stock/open-bag", O.UnknownOutcome(0, "POST", "/stock/open-bag", "network error"))
    assert apply(["ops", "open-bag", "SHOP", "387957", "1"], capsys) == 3
    assert "outcome unknown" in capsys.readouterr().err


@pytest.mark.parametrize("argv", [["SHOP", "387957", "0"], ["SHOP", "387957", "-1"], ["SHOP", "387957-KG", "1"],
                                  ["HAFO", "387957", "1"], ["NOPE", "387957", "1"]])
def test_open_bag_refuses_a_bad_request(ops, argv):
    code = run(["ops", "open-bag", *argv])
    assert code == 1 and writes(ops) == []


def test_every_write_path_passes_the_policy(ops):
    from siruk.ops import policy
    for m, p in (("PATCH", f"/goods/{ID}"), ("POST", f"/goods/{ID}/barcodes"), ("DELETE", f"/goods/{ID}/barcodes/ABCD-1"),
                 ("PUT", f"/goods/{ID}/plu"), ("POST", "/locations"), ("PATCH", f"/locations/{SHOP}"),
                 ("POST", "/stock/open-bag")):
        assert policy.allowed(m, p) is None, (m, p)
