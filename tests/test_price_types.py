"""The catalogue commands on both server models: flat prices (production) and price-types rows.

Field names come from siruk-web: the prohibited keys from backend/app/Http/Requests/Admin/Product/Concerns/
VariantRules.php:58-64, the row rules from :195-232, the GET shape from SingleProductResource::typePrices
(fixtures in conftest.py), the single-variant PUT from ProductVariantRequest and
resources/js/catalog/products/variantPayload.js, the export's `prices` keyed by code from ProductCatalogExport::prices.
"""
import json, re

import pytest

from siruk import bulk, cli, export, pricecheck, products, stock
from siruk import payload as P
from siruk.payload import PayloadError

PROHIBITED = ("price", "compare_at_price", "min_allowed_price", "initial_stock", "initial_stock_warehouse_id",
              "initial_stock_unit_cost")
MAIN_BARCODE = "8009470387958"   # the fixture's variants' own barcode


def new_variant(**over):
    v = {"sku": "TEST-1", "name": "Salmon 400 g", "price": 900, "cost_price": 600, "measure_type": "mass",
         "content": 400, "images": [1], "attribute_values": {"flavor": [38], "lifestage": [27]}, "initial_stock": 10}
    v.update(over)
    return v


def create_payload(**over):
    return {"name": "New Thing", "slug": "gemon-new-thing", "category_ids": [4], "brand_id": 18,
            "attribute_family_id": 2, "variants": [new_variant(**over)]}


def website_rows(v):
    return [r for r in v["prices"] if r["price_type_id"] == 1]


def assert_price_types_body(variants):
    for v in variants:
        assert not set(v) & set(PROHIBITED), v["sku"]
        assert len(website_rows(v)) == 1, v["sku"]
        assert "barcode" not in website_rows(v)[0]


# ----------------------------------------------------------------- the model ----
def test_model_is_read_from_the_get_or_probed_once(fake, fake_pt, monkeypatch):
    assert P.server_model(fake_pt.product) == P.PRICE_TYPES
    assert P.server_model(fake.product) == P.LEGACY
    probes = []
    get = fake_pt.get
    monkeypatch.setattr(fake_pt, "get", lambda path, **kw: (probes.append(path), get(path, **kw))[1])
    P._model = P._ptypes = None
    assert P.server_model() == P.PRICE_TYPES and P.server_model() == P.PRICE_TYPES
    assert probes == ["/price-types?forSelect=1"]


def test_legacy_probe_is_a_404_and_other_errors_are_not_cached(fake, monkeypatch):
    assert P.server_model() == P.LEGACY
    P._model = P._ptypes = None
    from siruk import client as _client

    def boom(path, **kw):
        raise _client.ApiError(500, "GET", path, "")
    monkeypatch.setattr(fake, "get", boom)
    with pytest.raises(_client.ApiError):
        P.server_model()
    assert P._ptypes is None


def test_get_gets_the_flat_website_keys_on_the_new_model(fake_pt):
    v = products.get(874)["variants"][0]
    assert (v["price"], v["compare_at_price"], v["min_allowed_price"]) == (2100, None, None)
    assert [r["price_type_code"] for r in v["prices"]] == ["website", "store"]
    api_v = P.api("GET", "/products/874")["data"]["variants"][0]
    assert api_v["price"] == 2100 and P.website_price(api_v) == 2100


def test_website_price_reads_every_shape(fake_pt):
    assert P.website_price({"price": 900}) == 900
    assert P.website_price({"prices": {"website": {"price": 1000}}, "price": 900}) == 1000
    assert P.website_price({"prices": [{"price_type_id": 1, "price": 1100.0}]}) == 1100
    assert P.website_price({"prices": [{"price_type_code": "website", "compare_at_price": 1500.0}], "sku": "x"},
                           "compare_at_price") == 1500
    assert P.website_price({"prices": {"store": {"price": 5}}}) is None


# ------------------------------------------------------- bodies, new model ----
def test_create_sends_rows_and_drops_stock_with_a_warning(fake_pt):
    res = products.create(create_payload(prices={"store": {"price": 1000, "barcode": "20001"}, "glovo": None}),
                          dry_run=True, force=True)
    v = res.body["variants"][0]
    assert_price_types_body([v])
    assert v["prices"] == [{"price_type_id": 1, "price": 900, "compare_at_price": None, "min_allowed_price": None},
                           {"price_type_id": 2, "price": 1000, "compare_at_price": None, "min_allowed_price": None,
                            "barcode": "20001"}]
    assert any("siruk ops docs new receipt" in w for w in res.warnings)
    assert res.diff[0]["new"]["price"] == 900


def test_create_writes_the_rows(fake_pt):
    products.create(create_payload(), dry_run=False, force=True)
    method, path, body = fake_pt.writes[0]
    assert (method, path) == ("POST", "/products")
    assert_price_types_body(body["variants"])


def test_add_variant_keeps_the_ids_of_the_existing_rows(fake_pt):
    res = products.add_variant(874, new_variant(prices={"store": {"price": 1000}}), dry_run=False)
    method, path, body = fake_pt.writes[0]
    assert (method, path) == ("PUT", "/products/874")
    assert_price_types_body(body["variants"])
    first, second, new = body["variants"]
    assert [r["id"] for r in first["prices"]] == [10300, 10301]
    assert [r["id"] for r in second["prices"]] == [10310]
    assert all("id" not in r for r in new["prices"]) and len(new["prices"]) == 2
    assert first["prices"][1]["barcode"] == "20001"
    assert res.after and len(res.after["variants"]) == 3


def test_set_variant_writes_one_variant_through_the_variant_endpoint(fake_pt):
    res = products.update_variant(874, "387957", {"price": 2200}, dry_run=False)
    assert [(m, p) for m, p, _ in fake_pt.writes] == [("PUT", "/product-variants/1030")]
    body = fake_pt.writes[0][2]
    assert not set(body) & set(PROHIBITED) and "is_default" not in body
    assert [(r["price_type_id"], r["id"], r["price"]) for r in body["prices"]] == [(1, 10300, 2200), (2, 10301, 1900)]
    assert body["prices"][1]["barcode"] == "20001"
    assert res.diff == [{"sku": "387957", "field": "price", "old": 2100, "new": 2200}]
    assert P.website_price(res.after["variants"][0]) == 2200 and P.website_price(res.after["variants"][1]) == 2100


def test_set_variant_dict_changes_one_type_and_removes_another(fake_pt):
    res = products.update_variant(874, "387957", {"prices": {"store": {"price": 2000}, "glovo": {"price": 2400}}},
                                  dry_run=True)
    rows = res.request[2]["prices"]
    assert [(r["price_type_id"], r.get("id"), r["price"]) for r in rows] == [(1, 10300, 2100), (2, 10301, 2000), (3, None, 2400)]
    assert rows[1]["barcode"] == "20001"        # not named in the patch, so kept
    assert {d["field"] for d in res.diff} == {"prices.store", "prices.glovo"}
    gone = products.update_variant(874, "387957", {"prices": {"store": None}}, dry_run=True)
    assert [r["price_type_id"] for r in gone.request[2]["prices"]] == [1]
    assert gone.diff == [{"sku": "387957", "field": "prices.store",
                          "old": {"price": 1900, "compare_at_price": None, "min_allowed_price": None, "barcode": "20001"},
                          "new": None}]


def test_dict_beats_flat_beats_baseline(fake_pt):
    res = products.update_variant(874, "387957", {"price": 2300, "prices": {"website": {"price": 2400}}}, dry_run=True)
    assert res.request[2]["prices"][0]["price"] == 2400
    res = products.update_variant(874, "387957", {"price": 2300}, dry_run=True)
    assert res.request[2]["prices"][0]["price"] == 2300


def test_guards_apply_to_a_price_given_only_in_the_dict(fake_pt):
    with pytest.raises(PayloadError, match="below cost"):
        products.update_variant(874, "387957", {"prices": {"website": {"price": 1000}}}, dry_run=True)
    with pytest.raises(PayloadError, match="below cost"):
        products.add_variant(874, new_variant(price=None, prices={"website": {"price": 600}}), dry_run=True)


def test_rename_and_unchanged_resend_see_no_price_change(fake_pt):
    assert products.rename(874, "Adult Chunks", dry_run=True).diff == [
        {"sku": None, "field": "name", "old": fake_pt.product["name"], "new": "Adult Chunks"}]
    assert not products.update_variant(874, "387957", {"price": 2100}, dry_run=True).diff


def test_bulk_create_bodies_have_rows_and_no_flat_keys(fake_pt):
    items = [("a", {**create_payload(prices={"store": {"price": 1000}}), "name": {"en": "A Thing"}, "slug": "a-thing"}),
             ("b", {**create_payload(sku="TEST-2"), "name": {"en": "B Thing"}, "slug": "b-thing"})]
    res = bulk.create(items, dry_run=True, en_only=True, force=True)
    for r in res.values():
        assert r["status"] == "ready", r
        assert_price_types_body(r["body"]["variants"])
        assert any("siruk ops docs new receipt" in w for w in r["warnings"])
    assert len(res["a"]["body"]["variants"][0]["prices"]) == 2


def test_apply_prices_keeps_the_rows_and_reads_back(fake_pt):
    res = pricecheck.apply_prices(874, {"387957": 2200}, dry_run=True)
    assert res.diff == [{"sku": "387957", "field": "price", "old": 2100, "new": 2200}] and not fake_pt.writes
    assert_price_types_body(res.body["variants"])
    res = pricecheck.apply_prices(874, {"387957": 2200})
    method, path, body = fake_pt.writes[0]
    assert (method, path) == ("PUT", "/products/874")
    assert_price_types_body(body["variants"])
    assert [r["id"] for r in body["variants"][0]["prices"]] == [10300, 10301]
    assert P.website_price(res.after["variants"][0]) == 2200
    with pytest.raises(PayloadError, match="nothing to apply"):
        pricecheck.apply_prices(874, {"387957": 1300}, dry_run=True)


def test_recheck_reads_the_website_price(fake_pt, monkeypatch):
    class Hafo:
        def find(self, sku, brand_id, cost=0):
            return {"id": 1, "slug": "x"}, {"id": 9, "sku": sku, "price": 2200, "wholesale_price": 1300}, ""

        def change(self, lid, row):
            return {"price": row["price"]}
    monkeypatch.setattr(pricecheck, "Hafo", Hafo)
    assert {r["sku"]: r["siruk_price"] for r in pricecheck.check([874])} == {"387957": 2100, "387967": 2100}


# ------------------------------------------------------------- legacy model ----
def test_legacy_keeps_the_flat_price_and_initial_stock(fake):
    res = products.create(create_payload(), dry_run=True, force=True)
    v = res.body["variants"][0]
    assert (v["price"], v["initial_stock"]) == (900, 10) and "prices" not in v and not res.warnings
    body = products.add_variant(874, new_variant(), dry_run=True).body
    assert body["variants"][2]["price"] == 900 and body["variants"][2]["initial_stock"] == 10
    assert body["variants"][0]["price"] == 2100 and "prices" not in body["variants"][0]
    res = bulk.create([("a", {**create_payload(), "name": {"en": "A Thing"}})], dry_run=True, en_only=True, force=True)
    assert res["a"]["body"]["variants"][0]["price"] == 900


def test_legacy_set_variant_is_still_one_product_put(fake):
    products.update_variant(874, "387957", {"price": 2200}, dry_run=False)
    assert [(m, p) for m, p, _ in fake.writes] == [("PUT", "/products/874")]
    assert fake.writes[0][2]["variants"][0]["price"] == 2200


def test_legacy_takes_a_website_only_dict_and_refuses_another_type(fake):
    res = products.update_variant(874, "387957", {"prices": {"website": {"price": 2200}}}, dry_run=True)
    assert res.diff == [{"sku": "387957", "field": "price", "old": 2100, "new": 2200}]
    with pytest.raises(PayloadError, match="price-types backend"):
        products.update_variant(874, "387957", {"prices": {"store": {"price": 2000}}}, dry_run=True)
    with pytest.raises(PayloadError, match="price-types backend"):
        products.add_variant(874, new_variant(prices={"glovo": None}), dry_run=True)


# ------------------------------------------------------------------ refusals ----
@pytest.mark.parametrize("patch, match", [
    ({"price": 2205}, "multiple of 10"),
    ({"prices": {"store": {"price": 1995}}}, "multiple of 10"),
    ({"prices": {"store": {"price": 1900, "compare_at_price": 1905}}}, "multiple of 10"),
    ({"prices": {"store": {"price": 1900, "compare_at_price": 1900}}}, "above the price"),
    ({"prices": {"website": {"price": 2100, "barcode": "5"}}}, "no barcode of its own"),
    ({"prices": {"store": {"barcode": MAIN_BARCODE}}}, "main barcode"),
    ({"prices": {"glovo": {"price": 1900, "barcode": "20001"}}}, "already on"),
    ({"prices": {"glovo": {"price": 1900, "barcode": "9" * 33}}}, "longer than 32"),
    ({"prices": {"nope": {"price": 1900}}}, "unknown price type"),
    ({"prices": {"website": None}}, "cannot be removed"),
    ({"prices": {"glovo": {"cost": 1}}}, "no field"),
])
def test_new_model_refusals(fake_pt, patch, match):
    with pytest.raises(PayloadError, match=match):
        products.update_variant(874, "387957", patch, dry_run=True)
    assert not fake_pt.writes


@pytest.mark.parametrize("fixture", ["fake", "fake_pt"])
def test_a_scalar_price_entry_is_refused_not_skipped(request, fixture):
    request.getfixturevalue(fixture)
    with pytest.raises(PayloadError, match="must be an object"):
        products.update_variant(874, "387957", {"prices": {"website": 1000}}, dry_run=True)


def test_a_patch_without_a_price_still_loses_the_stock_keys(fake_pt):
    res = products.update_variant(874, "387957", {"initial_stock": 5, "name": "Salmon 1250 g"}, dry_run=True)
    assert not set(res.request[2]) & set(PROHIBITED) and any("siruk ops docs new receipt" in w for w in res.warnings)


def test_a_deactivated_type_keeps_its_row_and_shows_no_phantom_diff(fake_pt):
    # a row of a type that is no longer in /price-types?forSelect=1 (only active types are listed)
    fake_pt.product["variants"][0]["prices"].append(
        {"id": 77, "price_type_id": 9, "price_type_code": "old", "price_type_name": "Old", "price": 1800.0,
         "compare_at_price": None, "min_allowed_price": None, "barcode": None})
    res = products.update_variant(874, "387957", {"price": 2200}, dry_run=True)
    assert [r["id"] for r in res.request[2]["prices"]] == [10300, 10301, 77]
    assert res.diff == [{"sku": "387957", "field": "price", "old": 2100, "new": 2200}]
    assert not products.update_variant(874, "387957", {"price": 2100}, dry_run=True).diff
    assert [r["price_type_id"] for r in products.update_variant(
        874, "387957", {"prices": {"old": {"price": 1700}}}, dry_run=True).request[2]["prices"]] == [1, 2, 9]


def test_bulk_read_back_compares_the_website_price_of_rows(fake_pt):
    body = {"variants": [{"sku": "387957", "prices": [{"price_type_id": 1, "price": 2100}], "images": [8293]},
                         {"sku": "387967", "prices": [{"price_type_id": 1, "price": 2100}], "images": [8293]}],
            "name": {"en": "All Breeds Adult Dog Chunks"}}
    assert bulk.read_back(874, body) == []
    body["variants"][0]["prices"][0]["price"] = 2200
    assert bulk.read_back(874, body) == ["387957 price 2100 ≠ 2200"]


def test_a_type_barcode_may_not_equal_a_main_barcode_in_the_product_on_create(fake_pt):
    with pytest.raises(PayloadError, match="main barcode"):
        products.add_variant(874, new_variant(barcode="4048422122074", prices={"store": {"price": 1000, "barcode": "4048422122074"}}),
                             dry_run=True)


def test_a_new_variant_without_a_website_price_is_refused(fake_pt):
    with pytest.raises(PayloadError, match="price"):
        products.add_variant(874, new_variant(price=None, prices={"store": {"price": 1000}}), dry_run=True)


# ---------------------------------------------------------------- prices set ----
def run(argv, capsys):
    with pytest.raises(SystemExit) as e:
        cli.main(["-q", *argv])
    out = capsys.readouterr()
    return e.value.code, out.out, out.err


SET = ["prices", "set", "874", "387957", "--type", "store", "--price", "2000", "--barcode", "20002"]


def test_prices_set_dry_run_writes_nothing_then_apply_writes_one_put(fake_pt, capsys):
    code, out, _ = run(SET, capsys)
    assert code == 0 and not fake_pt.writes
    token = re.search(r"--apply (\w{8})", out).group(1)
    assert "/product-variants/1030" in out
    code, out, err = run([*SET, "--apply", token], capsys)
    assert code == 0, err
    assert [(m, p) for m, p, _ in fake_pt.writes] == [("PUT", "/product-variants/1030")]
    row = fake_pt.product["variants"][0]["prices"][1]
    assert (row["price"], row["barcode"], row["id"]) == (2000, "20002", 10301)
    assert "read back ok" in out


def test_prices_set_wrong_code_writes_nothing(fake_pt, capsys):
    code, _, err = run([*SET, "--apply", "deadbeef"], capsys)
    assert code == 1 and not fake_pt.writes and "different plan" in err


def test_prices_set_remove_and_no_change(fake_pt, capsys):
    argv = ["prices", "set", "874", "387957", "--type", "store", "--remove"]
    token = re.search(r"--apply (\w{8})", run(argv, capsys)[1]).group(1)
    assert run([*argv, "--apply", token], capsys)[0] == 0
    assert [r["price_type_code"] for r in fake_pt.product["variants"][0]["prices"]] == ["website"]
    assert run(["prices", "set", "874", "387957", "--type", "website", "--price", "2100"], capsys)[1].startswith("nothing")


def test_prices_set_refusals_exit_1(fake_pt, capsys):
    assert run(["prices", "set", "874", "387957", "--type", "website", "--price", "2105"], capsys)[0] == 1
    assert run(["prices", "set", "874", "387957", "--type", "store"], capsys)[0] == 1
    assert run(["prices", "set", "874", "387957", "--type", "store", "--remove", "--price", "5"], capsys)[0] == 1
    assert not fake_pt.writes


def test_prices_set_on_legacy_takes_the_website_type_only(fake, capsys):
    assert run(["prices", "set", "874", "387957", "--type", "store", "--price", "2000"], capsys)[0] == 1
    code, out, _ = run(["prices", "set", "874", "387957", "--type", "website", "--price", "2200"], capsys)
    token = re.search(r"--apply (\w{8})", out).group(1)
    assert code == 0 and not fake.writes
    request = fake.request   # the legacy fake keeps its variants on a PUT; this one stores the sent ones
    fake.request = lambda m, p, body=None, **kw: (request(m, p, body, **kw), fake.product.update(variants=body["variants"]))[0] \
        if m == "PUT" else request(m, p, body, **kw)
    assert run(["prices", "set", "874", "387957", "--type", "website", "--price", "2200", "--apply", token], capsys)[0] == 0
    assert [(m, p) for m, p, _ in fake.writes] == [("PUT", "/products/874")]


def test_prices_show_and_price_types(fake_pt, capsys):
    code, out, _ = run(["prices", "show", "874", "--json"], capsys)
    assert code == 0
    rows = json.loads(out)
    assert [(r["sku"], r["type"], r["price"], r["barcode"]) for r in rows] == [
        ("387957", "website", 2100, None), ("387957", "store", 1900, "20001"), ("387967", "website", 2100, None)]
    get = fake_pt.get
    fake_pt.get = lambda path, **kw: ({"data": [{"id": 1, "code": "website", "name": "Website", "is_active": True, "sort_order": 0}]}
                                      if path == "/price-types" else get(path, **kw))
    assert run(["price-types"], capsys)[0] == 0


def test_price_types_on_legacy_is_a_refusal(fake, capsys):
    assert run(["price-types"], capsys)[0] == 1


# ------------------------------------------------------------------- readers ----
def test_summary_shows_the_website_price_on_both_models(fake, fake_pt):
    from siruk import client as _client
    new = products.summary(products.get(874))["variants"][0]
    assert new["price"] == 2100 and new["margin_pct"] == products.margin(2100, 1300) and not new["below_cost"]
    assert new["prices"]["store"] == {"price": 1900, "compare_at_price": None, "min_allowed_price": None, "barcode": "20001"}
    _client.set_default(fake)
    P._model = P._ptypes = None
    old = products.summary(products.get(874))["variants"][0]
    assert old["price"] == 2100 and list(old["prices"]) == ["website"] and old["prices"]["website"]["price"] == 2100


def test_audit_reads_the_export_website_price_on_both_models():
    # ProductCatalogExport: flat `price` is the website price; `prices` is keyed by type code
    rec = {"product_id": 1, "product_name": "X", "variant_id": 5, "sku": "S", "price": 1300.0, "cost_price": 1300.0,
           "barcode": "1", "accounting_code": "1", "image_ids": [1], "price_source_url": "u", "sale_mode": "pack",
           "is_purchasable": True, "available": 3,
           "prices": {"website": {"price": 1300.0}, "store": {"price": 900.0}}}
    res = export.audit([rec, {k: v for k, v in rec.items() if k != "prices"} | {"variant_id": 6, "sku": "T"}], sized=[])
    assert res["counts"]["below_cost"] == 2 and res["examples"]["below_cost"][0]["price"] == 1300.0


# --------------------------------------------------------------------- stock ----
def test_stock_writes_are_refused_when_the_ledger_is_in_ops(fake_pt):
    fake_pt.stock_in_ops = True
    for call in (lambda: stock.receive(1030, 5, "delivery"), lambda: stock.write_off(1030, 1, "lost", "n"),
                 lambda: stock.set_count(1030, 4, "correction", "n")):
        with pytest.raises(PayloadError, match=r"siruk ops docs new"):
            call()
    assert not fake_pt.writes
    fake_pt.stock_in_ops = False
    assert stock.receive(1030, 5, "delivery", dry_run=True)["dry_run"]


def test_stock_cli_refusal_exit_code(fake_pt):
    fake_pt.stock_in_ops = True
    with pytest.raises(SystemExit) as e:
        cli.main(["-q", "stock", "receive", "1030", "5", "--note", "delivery", "--dry-run"])
    assert e.value.code == 1


def test_commands_manifest_lists_the_price_commands():
    parser = cli.build_parser()
    rows = {r["name"]: r for r in parser.parse_args(["commands"]).manifest}
    assert rows["prices set"]["tier"] == "draft" and rows["prices show"]["tier"] == "read" and "price-types" in rows
    a = parser.parse_args(["prices", "set", "874", "S", "--type", "store", "--price", "2000"])
    assert a.type == "store" and a.price == 2000 and a.apply is None


# ------------------------------------------------- the write adapter's errors ----
def failing_put(fake_pt, status, error_body):
    """Make the variant PUT fail the way client.py reports it; returns the recorded calls."""
    from siruk import client as _client
    calls, request = [], fake_pt.request

    def req(method, path, body=None, lang=None, **kw):
        if method.upper() == "PUT":
            calls.append((method, path, kw))
            raise _client.ApiError(status, method, path, error_body)
        return request(method, path, body, lang, **kw)
    fake_pt.request = req
    return calls


def apply_set(capsys, *extra):
    token = re.search(r"--apply (\w{8})", run(SET, capsys)[1]).group(1)
    return run([*SET, "--apply", token, *extra], capsys)


def test_a_422_is_an_api_error_with_the_json_failure_shape(fake_pt, capsys):
    calls = failing_put(fake_pt, 422, '{"message": "The given data was invalid."}')
    code, out, err = apply_set(capsys, "--json")
    assert code == 2 and "outcome unknown" not in err
    failed = json.loads(out)["failed"]
    assert (failed["method"], failed["path"], failed["outcome_unknown"]) == ("PUT", "/product-variants/1030", False)
    assert len(calls) == 1 and calls[0][2]["retry"] is False


@pytest.mark.parametrize("status, body", [(502, "bad gateway"), (504, ""), (0, "network error: timed out"),
                                          (200, "not JSON: <html>")])
def test_an_unreadable_or_lost_answer_is_an_unknown_outcome(fake_pt, capsys, status, body):
    calls = failing_put(fake_pt, status, body)
    code, out, err = apply_set(capsys, "--json")
    assert code == 3 and "outcome unknown: check with `siruk prices show 874`" in err
    assert json.loads(out)["failed"]["outcome_unknown"] is True
    assert len(calls) == 1 and calls[0][2]["retry"] is False


# ------------------------------------------------------- below cost, any type ----
# The fixture's variant 387957 has cost 1300, a website price of 2100 and a store price of 1900 (conftest PT_PRODUCT).
def test_prices_set_refuses_a_price_at_or_below_cost_before_any_write(fake_pt, capsys):
    for price in ("1300", "1290"):
        code, _, err = run(["prices", "set", "874", "387957", "--type", "store", "--price", price], capsys)
        assert code == 1 and "store" in err and "387957" in err and "below cost" in err
    assert not fake_pt.writes


def test_prices_set_allow_below_cost_goes_on_to_the_dry_run(fake_pt, capsys):
    code, out, _ = run(["prices", "set", "874", "387957", "--type", "store", "--price", "1290", "--allow-below-cost"], capsys)
    assert code == 0 and "--apply" in out and not fake_pt.writes


def test_prices_set_below_cost_honours_the_env_override(fake_pt, capsys, monkeypatch):
    monkeypatch.setenv("ALLOW_BELOW_COST", "1")
    code, out, _ = run(["prices", "set", "874", "387957", "--type", "store", "--price", "1290"], capsys)
    assert code == 0 and "--apply" in out


def test_update_variant_refuses_any_type_below_cost(fake_pt):
    with pytest.raises(PayloadError, match=r"type=glovo"):
        products.update_variant(874, "387957", {"prices": {"glovo": {"price": 1000}}}, dry_run=True)
    with pytest.raises(PayloadError, match=r"type=store.*387957|387957.*type=store"):
        products.update_variant(874, "387957", {"cost_price": 2000}, dry_run=True)
    assert products.update_variant(874, "387957", {"cost_price": 1800}, dry_run=True).request
    res = products.update_variant(874, "387957", {"prices": {"glovo": {"price": 1000}}}, dry_run=True,
                                  allow_below_cost=True)
    assert any("below cost, allowed" in w and "type=glovo" in w for w in res.warnings)


def test_a_removed_row_or_a_fixed_price_is_not_checked(fake_pt):
    products.update_variant(874, "387957", {"cost_price": 2000, "prices": {"store": None}}, dry_run=True)
    products.update_variant(874, "387957", {"cost_price": 2000, "prices": {"store": {"price": 2200}}}, dry_run=True)
    products.update_variant(874, "387957", {"prices": {"store": {"compare_at_price": 3000, "min_allowed_price": 10}}},
                            dry_run=True)


def test_a_variant_without_cost_is_not_checked(fake_pt):
    products.add_variant(874, new_variant(cost_price=None, prices={"store": {"price": 100}}), dry_run=True)
    products.add_variant(874, new_variant(cost_price=0, prices={"store": {"price": 100}}), dry_run=True)


def test_create_and_add_variant_refuse_a_below_cost_other_type(fake_pt):
    low = {"store": {"price": 600}}
    with pytest.raises(PayloadError, match=r"sku=TEST-1 type=store"):
        products.create(create_payload(prices=low), dry_run=True, force=True)
    with pytest.raises(PayloadError, match=r"sku=TEST-1 type=store"):
        products.add_variant(874, new_variant(prices=low), dry_run=True)
    assert products.create(create_payload(prices=low), dry_run=True, force=True, allow_below_cost=True).warnings
    assert not fake_pt.writes


def test_bulk_create_refuses_a_below_cost_other_type_for_that_product_only(fake_pt):
    items = [("a", {**create_payload(prices={"glovo": {"price": 500}}), "name": {"en": "A Thing"}, "slug": "a-thing"}),
             ("b", {**create_payload(sku="TEST-2"), "name": {"en": "B Thing"}, "slug": "b-thing"})]
    res = bulk.create(items, dry_run=True, en_only=True, force=True)
    assert res["a"]["status"] == "refused" and "type=glovo" in str(res["a"])
    assert res["b"]["status"] == "ready"


def test_legacy_below_cost_is_the_website_price_only(fake):
    with pytest.raises(PayloadError, match=r"type=website"):
        products.update_variant(874, "387957", {"price": 1300}, dry_run=True)
    with pytest.raises(PayloadError, match=r"type=website"):
        products.update_variant(874, "387957", {"cost_price": 2100}, dry_run=True)
    assert products.update_variant(874, "387957", {"cost_price": 2000}, dry_run=True).request


# A glovo row already on the server, at 1000 (below the fixture's cost 1300); the shape is conftest._price_row's.
def kept_glovo_row(fake_pt, price=1000.0):
    fake_pt.product["variants"][0]["prices"].append(
        {"id": 10303, "price_type_id": 3, "price_type_code": "glovo", "price_type_name": "Glovo", "price": price,
         "compare_at_price": None, "min_allowed_price": None, "barcode": None})


def test_a_kept_below_cost_row_the_patch_does_not_set_is_a_warning_not_a_refusal(fake_pt):
    kept_glovo_row(fake_pt)
    for patch in ({"prices": {"store": {"barcode": "20003"}}}, {"prices": {"store": None}}, {"price": 2200}):
        res = products.update_variant(874, "387957", patch, dry_run=True)
        assert any("type=glovo sale=1000 cost=1300 is already below cost on the server; not changed" in w
                   for w in res.warnings), patch


def test_a_price_the_patch_sets_is_still_refused_beside_a_kept_below_cost_row(fake_pt):
    kept_glovo_row(fake_pt)
    with pytest.raises(PayloadError, match="type=store"):
        products.update_variant(874, "387957", {"prices": {"store": {"price": 1200, "barcode": "20003"}}}, dry_run=True)
    with pytest.raises(PayloadError, match="type=website"):
        products.update_variant(874, "387957", {"price": 1300}, dry_run=True)


def test_raising_the_cost_checks_every_kept_row(fake_pt):
    kept_glovo_row(fake_pt, price=1500.0)
    with pytest.raises(PayloadError, match="type=glovo") as e:
        products.update_variant(874, "387957", {"cost_price": 1600}, dry_run=True)
    assert "type=store" not in str(e.value) and "type=website" not in str(e.value)


def test_prices_set_prints_the_override_and_the_stale_row_on_stderr(fake_pt, capsys):
    kept_glovo_row(fake_pt)
    code, _, err = run(["prices", "set", "874", "387957", "--type", "store", "--barcode", "20003"], capsys)
    assert code == 0 and "type=glovo" in err and "already below cost" in err
    code, _, err = run(["prices", "set", "874", "387957", "--type", "store", "--price", "1290", "--allow-below-cost"], capsys)
    assert code == 0 and "below cost, allowed by the user: sku=387957 type=store" in err
    assert not fake_pt.writes
