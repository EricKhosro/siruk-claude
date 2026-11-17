"""Admin lifecycle and inventory: variants (archive, restore, release-sku, move), products (discontinue, merge),
suppliers, supplier products, warehouses, the Ops proxies and the order resend.
Shapes come from siruk-web/backend: routes/admin.php (what exists); Http/Requests/Admin/Product/{MoveVariantRequest,
MergeProductRequest}.php (`target_product_id`, `attribute_values`, `variants.<id>.attribute_values`);
Http/Requests/Admin/Inventory/{SupplierRequest,SupplierProductRequest,WarehouseRequest}.php; Controllers
Admin/Catalog/{ProductController,ProductVariantController}.php, Admin/Inventory/*, Admin/Integration/*;
Http/Resources/Admin/Catalog/SingleProductResource.php, Admin/Inventory/*Resource.php, Admin/Order/SingleOrderResource.php;
ops/docs/contracts/siruk-stock.md for the Ops proxies."""
import json

import pytest

from siruk import cli, client as C
from siruk.admin import lifecycle as L, policy

U1 = "0b7e1c52-6f1c-4a90-b417-2a9000000000"
U2 = "2a900000-6f1c-4a90-b417-2a9000000001"


def run(argv):
    with pytest.raises(SystemExit) as e:
        cli.main(["-q", *argv])
    return e.value.code


def writes(fc):
    return [c for c in fc.calls if c[0] != "GET"]


def plan(capsys, argv):
    capsys.readouterr()   # whatever an earlier apply printed
    assert run([*argv, "--json"]) == 0
    return json.loads(capsys.readouterr().out)


# AttributeFamilyResource::toArray (GET /attribute-families/:id is wrapped in data)
def family(**kw):
    return {"data": {"id": 3, "name": "Dry food", "code": "dry-food", "measureType": "mass", "attributes": [
        {"id": 12, "name": "Flavour", "code": "flavor", "inputType": "select", "role": "option", "isRequired": False},
        {"id": 20, "name": "Life stage", "code": "lifestage", "inputType": "multiselect", "role": "attribute",
         "isRequired": False}], **kw}}


# SingleProductResource::variantData (the keys the plans read)
def var(i, sku, flavour=None, content=2000, pack=1, life=None, **kw):
    values = {"12": [flavour]} if flavour else {}
    labels = [{"attributeId": 12, "attributeName": "Flavour", "role": "option", "valueId": flavour,
               "label": f"flavour {flavour}"}] if flavour else []
    if life:
        values["20"] = [life]
        labels.append({"attributeId": 20, "attributeName": "Life stage", "role": "attribute", "valueId": life,
                       "label": "Adult"})
    return {"id": i, "name": f"{sku} label", "sku": sku, "is_default": False, "sale_mode": "pack", "measure_type": "mass",
            "item_content": content, "pack_count": pack, "delete_locked": False, "delete_blockers": [],
            "will_archive": False, "stock_to_write_off": 0, "available_quantity": 5, "attribute_values": values,
            "attribute_value_labels": labels, **kw}


# SingleProductResource::toArray
def product(pid, variants, **kw):
    return {"data": {"id": pid, "name": f"Product {pid}", "attribute_family_id": 3, "attribute_family_name": "Dry food",
                     "is_discontinued": False, "variants": variants, **kw}}


SOURCE = [var(101, "S-1", 38), var(102, "S-2", 39)]
TARGET = [var(201, "T-1", 40), var(202, "T-2", 41)]


@pytest.fixture
def shop(admin_fake):
    admin_fake.on("GET", "/attribute-families/3", family())
    admin_fake.on("GET", "/products/10", product(10, SOURCE))
    admin_fake.on("GET", "/products/20", product(20, TARGET))
    # ProductVariantController::{move,destroy}, ProductController::{merge,discontinue}
    admin_fake.on("POST", "/product-variants/101/move", {"data": {"id": 101, "sku": "S-1", "product_id": 20, "url": "/dp/20"}})
    admin_fake.on("POST", "/products/10/merge", {"data": {"target_product_id": 20, "source": "deleted"}})
    admin_fake.on("POST", "/products/10/discontinue", {"data": {"id": 10, "is_discontinued": True}})
    for vid in (101, 102):
        admin_fake.on("DELETE", f"/product-variants/{vid}", {"data": {"archived": False}})
    return admin_fake


# ---------------------------------------------------------- the manifest ----
EXPECTED = {
    "variants list": "read", "variants archived": "read", "variants archive": "irreversible", "variants restore": "draft",
    "variants release-sku": "draft", "variants move-targets": "read", "variants move": "irreversible",
    "products discontinue": "irreversible", "products merge-targets": "read", "products merge": "irreversible",
    "suppliers list": "read", "suppliers show": "read", "suppliers create": "draft", "suppliers update": "draft",
    "suppliers delete": "irreversible", "suppliers products": "read", "suppliers add-product": "draft",
    "suppliers stock-check": "real-world", "suppliers ops-stock-sync": "real-world",
    "supplier-products set": "draft", "supplier-products rm": "irreversible", "supplier-products set-stock": "draft",
    "warehouses list": "read", "warehouses create": "draft", "warehouses update": "draft",
    "ops purchase-orders": "read", "ops purchase-order": "read", "ops locations": "read", "ops location-stock": "read",
    "ops resend-order": "real-world"}


def test_every_command_exists_with_its_manifest_fields(capsys):
    assert run(["commands", "--json"]) == 0
    by = {r["name"]: r for r in json.loads(capsys.readouterr().out)}
    for name, tier in EXPECTED.items():
        row = by[f"admin {name}"]
        assert row["tier"] == tier and row["backend"] == "admin", name
        assert row["help"] and row["example"] and row["api"] and row["roles"], name
        assert row["example"].startswith("siruk admin "), name


def test_the_ops_proxies_are_reads_only(admin_fake, capsys):
    assert run(["commands", "--json"]) == 0
    by = {r["name"]: r for r in json.loads(capsys.readouterr().out)}
    for name in ("purchase-orders", "purchase-order", "locations", "location-stock"):
        assert by[f"admin ops {name}"]["tier"] == "read"
        assert all(x.startswith("GET ") for x in by[f"admin ops {name}"]["api"])
    assert run(["admin", "ops", "locations", "--apply", "abcd1234"]) == 2   # a read takes no --apply
    assert admin_fake.calls == []


# ----------------------------------------------------------- the reads ----
# ProductVariantController::index (minimal shape + meta) and ::archived; VariantMoveService::targetsFor
VARIANT_ROW = {"id": 4512, "name": "RC-2 — Royal (2 kg)", "product_id": 874, "product_name": "Royal", "sale_mode": "pack",
               "cost_price": 9250.0}
TARGETS = {"data": [{"id": 880, "name": "Royal Mini", "brand": "Royal Canin", "attribute_family_id": 3, "variants_count": 4}]}


def test_variant_and_target_reads_print_a_table_and_json_unmodified(admin_fake, capsys):
    page = {"data": [VARIANT_ROW], "meta": {"current_page": 1, "last_page": 1, "per_page": 15, "total": 1}}
    admin_fake.on("GET", "/product-variants", page).on("GET", "/product-variants/archived", ARCHIVED)
    admin_fake.on("GET", "/product-variants/4512/move-targets", TARGETS).on("GET", "/products/874/merge-targets", TARGETS)
    cases = [(["variants", "list", "--product", "874", "--search", "royal"], "Royal", page,
              "/product-variants?product_id=874&q=royal"),
             (["variants", "archived", "--product", "10"], "OLD-1", ARCHIVED, "/product-variants/archived?product_id=10"),
             (["variants", "move-targets", "4512"], "Royal Mini", TARGETS, "/product-variants/4512/move-targets"),
             (["products", "merge-targets", "874"], "Royal Mini", TARGETS, "/products/874/merge-targets")]
    for argv, needle, answer, path in cases:
        admin_fake.calls.clear()
        capsys.readouterr()
        assert run(["admin", *argv]) == 0 and needle in capsys.readouterr().out
        assert run(["admin", *argv, "--json"]) == 0 and json.loads(capsys.readouterr().out) == answer
        assert [c[:2] for c in admin_fake.calls] == [("GET", path)] * 2


# ---------------------------------------------------------------- move ----
MOVE = ["admin", "variants", "move", "101", "--product", "10", "--to", "20", "--values", '{"12": [38]}']


def test_move_dry_run_shows_both_products_and_writes_nothing(shop, capsys):
    out = plan(capsys, MOVE)
    assert out["tier"] == "irreversible" and writes(shop) == []
    for needle in ("#10 Product 10", "#20 Product 20", "S-1", "S-2", "T-1", "T-2", "flavour 40", "Flavour=[38]", "<- incoming"):
        assert needle in out["summary"], needle
    assert out["requests"][0]["method"] == "POST" and out["requests"][0]["path"] == "/product-variants/101/move"


def test_move_sends_target_product_id_and_attribute_values(shop, capsys):
    code = plan(capsys, MOVE)["code"]
    assert run([*MOVE, "--apply", code]) == 0
    # MoveVariantRequest: target_product_id required|integer, attribute_values present|array
    assert writes(shop) == [("POST", "/product-variants/101/move",
                             {"target_product_id": 20, "attribute_values": {"12": [38]}})]


def test_move_accepts_an_attribute_code_and_a_bare_value(shop, capsys):
    out = plan(capsys, ["admin", "variants", "move", "101", "--product", "10", "--to", "20", "--values", '{"flavor": 38}'])
    assert out["requests"][0]["body"] == {"target_product_id": 20, "attribute_values": {"12": [38]}}


def test_move_to_a_twin_is_refused_before_any_write(shop, capsys):
    argv = [*MOVE[:-1], '{"12": [40]}']   # T-1 already has flavour 40 at 2000x1
    assert run(argv) == 1
    assert "same options and size" in capsys.readouterr().err
    assert run([*argv, "--apply", "deadbeef"]) == 1 and writes(shop) == []


def test_move_a_different_size_is_not_a_twin(shop, capsys):
    shop.on("GET", "/products/10", product(10, [var(101, "S-1", 38, content=500), var(102, "S-2", 39)]))
    shop.on("GET", "/products/20", product(20, [var(201, "T-1", 38, content=2000), var(202, "T-2", 41)]))
    assert plan(capsys, MOVE)["requests"][0]["body"]["target_product_id"] == 20


def test_move_without_an_option_the_siblings_use_is_refused(shop, capsys):
    assert run([*MOVE[:-1], "{}"]) == 1
    assert "Flavour is set on some variants but not on the incoming S-1" in capsys.readouterr().err
    assert writes(shop) == []


def test_move_that_leaves_a_sibling_without_the_option_is_refused(shop, capsys):
    shop.on("GET", "/products/30", product(30, [var(301, "U-1", None, content=1000)]))
    assert run(["admin", "variants", "move", "101", "--product", "10", "--to", "30", "--values", '{"12": [38]}']) == 1
    assert "not on the target's U-1" in capsys.readouterr().err and writes(shop) == []


def test_a_gap_the_target_already_had_is_a_warning(shop, capsys):
    shop.on("GET", "/products/40", product(40, [var(401, "V-1", 40), var(402, "V-2", None, content=1000)]))
    out = plan(capsys, ["admin", "variants", "move", "101", "--product", "10", "--to", "40", "--values", '{"12": [38]}'])
    assert "warning: Flavour is already missing on the target's V-2" in out["summary"]


def test_move_refuses_a_measure_a_missing_variant_and_the_same_product(shop, capsys):
    shop.on("GET", "/attribute-families/3", family(measureType="volume"))
    assert run(MOVE) == 1 and "measured in mass" in capsys.readouterr().err
    shop.on("GET", "/attribute-families/3", family())
    assert run(["admin", "variants", "move", "999", "--product", "10", "--to", "20"]) == 1
    assert run(["admin", "variants", "move", "101", "--product", "10", "--to", "10"]) == 1
    assert run([*MOVE[:-1], '{"99": [1]}']) == 1   # an attribute outside the target's type
    assert writes(shop) == []


def test_a_variant_added_to_the_target_after_the_dry_run_voids_the_code(shop, capsys):
    code = plan(capsys, MOVE)["code"]
    shop.on("GET", "/products/20", product(20, [*TARGET, var(203, "T-3", 42)]))
    assert run([*MOVE, "--apply", code]) == 1
    assert "different plan" in capsys.readouterr().err and writes(shop) == []
    assert run([*MOVE, "--apply", plan(capsys, MOVE)["code"]]) == 0 and len(writes(shop)) == 1


def test_stock_and_dates_do_not_void_the_code(shop, capsys):
    code = plan(capsys, MOVE)["code"]
    shop.on("GET", "/products/10", product(10, [{**v, "available_quantity": 1, "updated": "later"} for v in SOURCE]))
    assert run([*MOVE, "--apply", code]) == 0


# VariantMoveService::move syncs the variant's whole value set to what is sent
def life_shop(shop, source=None):
    shop.on("GET", "/products/10", product(10, source or [var(101, "S-1", 38, life=27), var(102, "S-2", 39)]))


def test_move_that_would_drop_a_descriptive_value_needs_drop_values(shop, capsys):
    life_shop(shop)
    assert run(MOVE) == 1
    assert "Life stage=Adult on S-1" in capsys.readouterr().err and writes(shop) == []
    out = plan(capsys, [*MOVE, "--drop-values"])
    assert "drops on S-1: Life stage=Adult" in out["summary"]
    assert out["requests"][0]["body"]["attribute_values"] == {"12": [38]}


def test_resending_the_descriptive_value_keeps_it_with_no_drop_line(shop, capsys):
    life_shop(shop)
    out = plan(capsys, [*MOVE[:-1], '{"12": [38], "20": [27]}'])
    assert "drops" not in out["summary"]
    assert out["requests"][0]["body"]["attribute_values"] == {"12": [38], "20": [27]}


def test_a_dropped_option_is_listed_and_a_value_the_variant_never_had_is_not(shop, capsys):
    shop.on("GET", "/products/10", product(10, [var(101, "S-1", 38), var(102, "S-2", 39)]))
    assert "drops" not in plan(capsys, MOVE)["summary"]


def test_merge_names_the_dropped_values_and_asks_for_the_flag(shop, capsys):
    life_shop(shop)
    assert run(MERGE) == 1 and "Life stage=Adult on S-1" in capsys.readouterr().err
    out = plan(capsys, [*MERGE, "--drop-values"])
    assert "drops on S-1: Life stage=Adult" in out["summary"] and "S-2: " not in out["summary"].split("drops on")[1]
    kept = '{"101": {"attribute_values": {"12": [38], "20": [27]}}, "102": {"attribute_values": {"12": [39]}}}'
    assert "drops" not in plan(capsys, [*MERGE[:-1], kept])["summary"]


def test_a_drop_changes_the_code(shop, capsys):
    life_shop(shop)
    code = plan(capsys, [*MOVE, "--drop-values"])["code"]
    life_shop(shop, [var(101, "S-1", 38, life=28), var(102, "S-2", 39)])
    assert run([*MOVE, "--drop-values", "--apply", code]) == 1 and writes(shop) == []


def test_move_says_what_follows_and_warns_when_the_source_is_emptied(shop, capsys):
    assert "its stock, orders, carts and gifts follow it" in plan(capsys, MOVE)["summary"]
    shop.on("GET", "/products/10", product(10, [var(101, "S-1", 38)]))
    assert "product 10 is left with no variants" in plan(capsys, MOVE)["summary"]


# --------------------------------------------------------------- merge ----
# MergeProductRequest: variants present|array, variants.*.attribute_values present|array, every live variant of the source
MERGE = ["admin", "products", "merge", "10", "--to", "20", "--variants",
         '{"101": {"attribute_values": {"12": [38]}}, "102": {"attribute_values": {"12": [39]}}}']


def test_merge_dry_run_then_apply_sends_every_variant(shop, capsys):
    out = plan(capsys, MERGE)
    assert out["tier"] == "irreversible" and writes(shop) == []
    for needle in ("#10 Product 10", "#20 Product 20", "deleted, or discontinued"):
        assert needle in out["summary"], needle
    assert run([*MERGE, "--apply", out["code"]]) == 0
    assert writes(shop) == [("POST", "/products/10/merge", {
        "target_product_id": 20,
        "variants": {"101": {"attribute_values": {"12": [38]}}, "102": {"attribute_values": {"12": [39]}}}})]


def test_merge_needs_options_for_every_live_variant_and_no_stranger(shop, capsys):
    assert run([*MERGE[:-1], '{"101": {"attribute_values": {"12": [38]}}}']) == 1
    assert "missing 102" in capsys.readouterr().err
    assert run([*MERGE[:-1], '{"101": {"attribute_values": {"12": [38]}}, "102": {"attribute_values": {"12": [39]}}, '
                '"103": {"attribute_values": {}}}']) == 1
    assert run([*MERGE[:-1], '{"101": {"12": [38]}, "102": {"12": [39]}}']) == 1   # not the server's shape
    assert writes(shop) == []


def test_merge_refuses_two_incoming_variants_the_shop_cannot_tell_apart(shop, capsys):
    assert run([*MERGE[:-1], '{"101": {"attribute_values": {"12": [38]}}, "102": {"attribute_values": {"12": [38]}}}']) == 1
    assert "S-1 and S-2 have the same options and size" in capsys.readouterr().err


def test_merge_refuses_a_twin_in_the_target_and_itself(shop, capsys):
    assert run([*MERGE[:-1], '{"101": {"attribute_values": {"12": [40]}}, "102": {"attribute_values": {"12": [39]}}}']) == 1
    assert run(["admin", "products", "merge", "10", "--to", "10", "--variants", "{}"]) == 1
    assert writes(shop) == []


def test_merge_is_voided_by_a_change_in_the_source(shop, capsys):
    code = plan(capsys, MERGE)["code"]
    shop.on("GET", "/products/10", product(10, [*SOURCE, var(103, "S-3", 37)]))
    assert run([*MERGE, "--apply", code]) == 1 and writes(shop) == []


# --------------------------------------------------------- discontinue ----
def test_discontinue_posts_without_a_body_and_refuses_twice(shop, capsys):
    out = plan(capsys, ["admin", "products", "discontinue", "10"])
    assert out["tier"] == "irreversible" and out["requests"][0]["body"] is None
    assert run(["admin", "products", "discontinue", "10", "--apply", out["code"]]) == 0
    assert writes(shop) == [("POST", "/products/10/discontinue", None)]
    shop.on("GET", "/products/11", product(11, SOURCE, is_discontinued=True))
    assert run(["admin", "products", "discontinue", "11"]) == 1


# ------------------------------------------------------------- archive ----
def test_archive_says_whether_the_server_archives_or_deletes(shop, capsys):
    shop.on("GET", "/products/10", product(10, [var(101, "S-1", 38, will_archive=True, stock_to_write_off=4), var(102, "S-2", 39)]))
    argv = ["admin", "variants", "archive", "101", "--product", "10"]
    out = plan(capsys, argv)
    assert out["tier"] == "irreversible" and "archive (soft delete" in out["summary"]
    assert "4 on hand written off" in out["summary"]
    assert run([*argv, "--apply", out["code"]]) == 0
    assert writes(shop) == [("DELETE", "/product-variants/101", None)]
    assert "delete for good" in plan(capsys, ["admin", "variants", "archive", "102", "--product", "10"])["summary"]


def test_archive_is_refused_for_the_last_variant_and_for_reserved_stock(shop, capsys):
    shop.on("GET", "/products/11", product(11, [var(111, "L-1", 38)]))
    assert run(["admin", "variants", "archive", "111", "--product", "11"]) == 1
    assert "last variant" in capsys.readouterr().err
    shop.on("GET", "/products/12", product(12, [var(121, "B-1", 38, delete_blockers=["it has stock reserved for orders"]),
                                                 var(122, "B-2", 39)]))
    assert run(["admin", "variants", "archive", "121", "--product", "12"]) == 1
    assert "stock reserved" in capsys.readouterr().err
    assert run(["admin", "variants", "archive", "555", "--product", "10"]) == 1
    assert writes(shop) == []


# ----------------------------------------------- restore and release-sku ----
# ProductVariantController::archived
ARCHIVED = {"data": [{"id": 77, "product_id": 10, "product_name": "Product 10", "name": "old", "sku": "OLD-1",
                      "released_sku": None, "archived_at": "2026-11-01T10:00:00+00:00"},
                     {"id": 78, "product_id": 10, "product_name": "Product 10", "name": "older",
                      "sku": "OLD-2~archived-78", "released_sku": "OLD-2", "archived_at": "2026-10-01T10:00:00+00:00"}]}


def test_restore_posts_without_a_body(admin_fake, capsys):
    admin_fake.on("GET", "/product-variants/archived", ARCHIVED).on("POST", "/product-variants/77/restore", {"data": {"id": 77}})
    out = plan(capsys, ["admin", "variants", "restore", "77"])
    assert out["tier"] == "draft" and writes(admin_fake) == []
    assert run(["admin", "variants", "restore", "77", "--apply", out["code"]]) == 0
    assert writes(admin_fake) == [("POST", "/product-variants/77/restore", None)]
    assert "its SKU returns to OLD-2" in plan(capsys, ["admin", "variants", "restore", "78"])["summary"]
    assert admin_fake.calls[0][1] == "/product-variants/archived"


def test_release_sku_posts_without_a_body_and_refuses_a_released_one(admin_fake, capsys):
    admin_fake.on("GET", "/product-variants/archived", ARCHIVED).on("POST", "/product-variants/77/release-sku", {"data": {}})
    out = plan(capsys, ["admin", "variants", "release-sku", "77", "--product", "10"])
    assert run(["admin", "variants", "release-sku", "77", "--product", "10", "--apply", out["code"]]) == 0
    assert writes(admin_fake) == [("POST", "/product-variants/77/release-sku", None)]
    assert admin_fake.calls[0][1] == "/product-variants/archived?product_id=10"
    assert run(["admin", "variants", "release-sku", "78"]) == 1 and run(["admin", "variants", "restore", "999"]) == 1


# ----------------------------------------------------------- suppliers ----
# SupplierResource::toArray
def supplier(i=3, **kw):
    return {"id": i, "code": "hafo", "name": "hafo", "legal_name": None, "contact_name": None, "email": None, "phone": None,
            "address": None, "currency": "AMD", "payment_terms": None, "default_lead_days": 2, "notes": None,
            "is_active": True, "stock_checked_at": None, "ops_stock_source": None, "ops_stock_pulled_at": None,
            "products_count": 0, **kw}


def test_supplier_create_posts_the_body(admin_fake, capsys):
    admin_fake.on("GET", "/suppliers", {"data": []}).on("POST", "/suppliers", {"data": supplier(9)})
    body = {"code": "pet-house", "name": "Pet House", "default_lead_days": 3, "ops_stock_source": None}
    argv = ["admin", "suppliers", "create", json.dumps(body)]
    out = plan(capsys, argv)
    assert out["tier"] == "draft" and writes(admin_fake) == []
    assert run([*argv, "--apply", out["code"]]) == 0
    assert writes(admin_fake) == [("POST", "/suppliers", body)]


@pytest.mark.parametrize("body", [
    {"name": "x"}, {"code": "Bad Code", "name": "x"}, {"code": "x", "name": "x", "ops_stock_source": "other"},
    {"code": "x", "name": "x", "default_lead_days": 400}, {"code": "x", "name": "x", "currency": "AM"}])
def test_supplier_create_refuses_what_the_request_refuses(admin_fake, body):
    assert run(["admin", "suppliers", "create", json.dumps(body)]) == 1 and admin_fake.calls == []


def test_supplier_update_needs_the_whole_form_and_diffs_the_sent_keys(admin_fake, capsys):
    admin_fake.on("GET", "/suppliers/3", {"data": supplier()}).on("PUT", "/suppliers/3", {"data": supplier()})
    assert run(["admin", "suppliers", "update", "3", '{"name": "x"}']) == 1
    body = {"code": "hafo", "name": "hafo ltd", "default_lead_days": 2}
    argv = ["admin", "suppliers", "update", "3", json.dumps(body)]
    out = plan(capsys, argv)
    assert 'name: "hafo" → "hafo ltd"' in out["summary"] and "unchanged: code, default_lead_days" in out["summary"]
    assert run([*argv, "--apply", out["code"]]) == 0 and writes(admin_fake) == [("PUT", "/suppliers/3", body)]


def test_an_ops_pull_between_dry_run_and_apply_keeps_a_supplier_code(admin_fake, capsys):
    admin_fake.on("GET", "/suppliers/3", {"data": supplier()}).on("PUT", "/suppliers/3", {"data": supplier()})
    admin_fake.on("DELETE", "/suppliers/3", None)
    update = ["admin", "suppliers", "update", "3", '{"code": "hafo", "name": "hafo ltd"}']
    delete = ["admin", "suppliers", "delete", "3"]
    codes = plan(capsys, update)["code"], plan(capsys, delete)["code"]
    moved = supplier(stock_checked_at="2026-11-16T09:00:00+00:00", ops_stock_pulled_at="2026-11-16T09:00:00+00:00",
                     products_count=7, open_purchase_orders_count=1, open_fulfillments_count=2,
                     updatedAt="2026-11-16T09:00:00.000000Z")
    admin_fake.on("GET", "/suppliers/3", {"data": moved})
    assert run([*update, "--apply", codes[0]]) == 0 and run([*delete, "--apply", codes[1]]) == 0
    admin_fake.on("GET", "/suppliers/3", {"data": supplier(name="renamed")})
    assert run([*delete, "--apply", codes[1]]) == 1


def test_supplier_delete_is_irreversible(admin_fake, capsys):
    admin_fake.on("GET", "/suppliers/3", {"data": supplier()}).on("DELETE", "/suppliers/3", None)
    out = plan(capsys, ["admin", "suppliers", "delete", "3"])
    assert out["tier"] == "irreversible"
    assert run(["admin", "suppliers", "delete", "3", "--apply", out["code"]]) == 0
    assert writes(admin_fake) == [("DELETE", "/suppliers/3", None)]


def test_suppliers_list_searches_with_q(admin_fake, capsys):
    admin_fake.on("GET", "/suppliers", {"data": [supplier()]})
    assert run(["admin", "suppliers", "list", "--search", "haf", "--active", "yes"]) == 0
    assert admin_fake.calls[0][1] == "/suppliers?q=haf&is_active=1" and "hafo" in capsys.readouterr().out


def test_supplier_products_list_and_add_product(admin_fake, capsys):
    # SupplierController::products paginates (q, perPage); SupplierProductResource is the row
    row = {"id": 17, "supplier_id": 3, "variant": {"id": 4512, "sku": "RC-2", "product_name": "Royal"}, "supplier_sku": "H-1",
           "cost_price": 9250.0, "stock_qty": 4, "is_active": True, "ops_managed": False}
    admin_fake.on("GET", "/suppliers/3/products", {"data": [row], "meta": {"current_page": 1, "last_page": 1}})
    assert run(["admin", "suppliers", "products", "3", "--search", "royal"]) == 0
    assert admin_fake.calls[0][1] == "/suppliers/3/products?q=royal" and "RC-2" in capsys.readouterr().out
    admin_fake.on("GET", "/suppliers/3", {"data": supplier()}).on("POST", "/suppliers/3/products", {"data": row})
    body = {"product_variant_id": 4512, "cost_price": 9250, "is_preferred": True}
    argv = ["admin", "suppliers", "add-product", "3", json.dumps(body)]
    out = plan(capsys, argv)
    assert run([*argv, "--apply", out["code"]]) == 0
    assert writes(admin_fake) == [("POST", "/suppliers/3/products", body)]
    for bad in ({"cost_price": 1}, {"product_variant_id": 1, "colour": "red"}, {"product_variant_id": 1, "lead_days": 400}):
        assert run(["admin", "suppliers", "add-product", "3", json.dumps(bad)]) == 1
    assert len(writes(admin_fake)) == 1


def test_stock_check_and_ops_stock_sync_are_real_world(admin_fake, capsys):
    admin_fake.on("GET", "/suppliers/3", {"data": supplier(ops_stock_source="hafo")})
    admin_fake.on("GET", "/suppliers/4", {"data": supplier(4)})
    admin_fake.on("POST", "/suppliers/3/stock-check", {"stock_checked_at": "2026-11-16T09:00:00+00:00"})
    admin_fake.on("POST", "/suppliers/3/ops-stock-sync", {"queued": True})
    for verb in ("stock-check", "ops-stock-sync"):
        out = plan(capsys, ["admin", "suppliers", verb, "3"])
        assert out["tier"] == "real-world" and out["requests"][0]["body"] is None
        assert run(["admin", "suppliers", verb, "3", "--apply", out["code"]]) == 0
    assert writes(admin_fake) == [("POST", "/suppliers/3/stock-check", None), ("POST", "/suppliers/3/ops-stock-sync", None)]
    # SupplierController::opsStockSync answers 422 no_ops_source for a supplier with no source
    assert run(["admin", "suppliers", "ops-stock-sync", "4"]) == 1 and len(writes(admin_fake)) == 2


# ----------------------------------------------------- supplier-products ----
ROW = {"id": 17, "supplier_id": 3, "variant": {"id": 4512, "sku": "RC-2", "product_name": "Royal"}, "supplier_sku": "H-1",
       "cost_price": 9250.0, "min_order_qty": 1, "pack_multiple": 1, "lead_days": None, "is_preferred": False,
       "dropship_allowed": False, "stock_qty": 4, "is_active": True, "ops_managed": False}


def rows(admin_fake, *items):
    admin_fake.on("GET", "/suppliers/3/products", {"data": list(items), "meta": {"current_page": 1, "last_page": 1}})


def test_supplier_product_set_sends_only_the_keys_given(admin_fake, capsys):
    rows(admin_fake, ROW)
    admin_fake.on("PUT", "/supplier-products/17", {"data": ROW})
    argv = ["admin", "supplier-products", "set", "17", '{"is_active": false, "lead_days": 3}', "--supplier", "3"]
    out = plan(capsys, argv)
    assert "is_active: true → false" in out["summary"] and admin_fake.calls[0][1] == "/suppliers/3/products?perPage=100&page=1"
    assert run([*argv, "--apply", out["code"]]) == 0
    assert writes(admin_fake) == [("PUT", "/supplier-products/17", {"is_active": False, "lead_days": 3})]


def test_a_stock_pull_does_not_void_a_set_but_does_void_set_stock(admin_fake, capsys):
    rows(admin_fake, ROW)
    admin_fake.on("GET", "/suppliers/3", {"data": supplier()})
    admin_fake.on("PUT", "/supplier-products/17", {"data": ROW}).on("PUT", "/supplier-products/17/stock", {"data": ROW})
    set_argv = ["admin", "supplier-products", "set", "17", '{"is_active": false}', "--supplier", "3"]
    stock_argv = ["admin", "supplier-products", "set-stock", "17", "12", "--supplier", "3"]
    set_code, stock_code = plan(capsys, set_argv)["code"], plan(capsys, stock_argv)["code"]
    rows(admin_fake, {**ROW, "stock_qty": 9, "stock_updated_at": "2026-11-16T10:00:00+00:00"})
    assert run([*set_argv, "--apply", set_code]) == 0
    assert run([*stock_argv, "--apply", stock_code]) == 1 and len(writes(admin_fake)) == 1


def test_set_notes_what_the_server_does_besides(admin_fake, capsys):
    rows(admin_fake, ROW)
    out = plan(capsys, ["admin", "supplier-products", "set", "17", '{"is_preferred": true, "min_order_qty": null}',
                        "--supplier", "3"])["summary"]
    assert "stop being preferred" in out and "stored as 1" in out
    assert "preferred" not in plan(capsys, ["admin", "supplier-products", "set", "17", '{"is_active": false}',
                                            "--supplier", "3"])["summary"]


def test_supplier_product_set_refuses_what_the_request_refuses(admin_fake):
    rows(admin_fake, ROW)
    for bad in ('{"colour": 1}', '{"min_order_qty": 0}', '{"product_variant_id": 9999}', '{"is_active": "yes"}'):
        assert run(["admin", "supplier-products", "set", "17", bad, "--supplier", "3"]) == 1
    assert run(["admin", "supplier-products", "set", "99", "{}", "--supplier", "3"]) == 1
    assert writes(admin_fake) == []


def test_supplier_product_rm_is_irreversible_and_not_for_an_ops_row(admin_fake, capsys):
    rows(admin_fake, ROW, {**ROW, "id": 18, "ops_managed": True})
    admin_fake.on("DELETE", "/supplier-products/17", None)
    out = plan(capsys, ["admin", "supplier-products", "rm", "17", "--supplier", "3"])
    assert out["tier"] == "irreversible"
    assert run(["admin", "supplier-products", "rm", "17", "--supplier", "3", "--apply", out["code"]]) == 0
    assert writes(admin_fake) == [("DELETE", "/supplier-products/17", None)]
    assert run(["admin", "supplier-products", "rm", "18", "--supplier", "3"]) == 1 and len(writes(admin_fake)) == 1


def test_supplier_product_set_stock_sends_stock_qty(admin_fake, capsys):
    rows(admin_fake, ROW)
    admin_fake.on("GET", "/suppliers/3", {"data": supplier()})
    admin_fake.on("PUT", "/supplier-products/17/stock", {"data": ROW})
    argv = ["admin", "supplier-products", "set-stock", "17", "12", "--supplier", "3"]
    out = plan(capsys, argv)
    assert "4 → 12" in out["summary"]
    assert run([*argv, "--apply", out["code"]]) == 0
    assert writes(admin_fake) == [("PUT", "/supplier-products/17/stock", {"stock_qty": 12})]
    assert run(["admin", "supplier-products", "set-stock", "17", "-1", "--supplier", "3"]) == 1
    assert "overwrites" not in out["summary"]
    admin_fake.on("GET", "/suppliers/3", {"data": supplier(ops_stock_source="hafo")})
    assert "next pull overwrites" in plan(capsys, argv)["summary"]
    rows(admin_fake, {**ROW, "ops_managed": True})
    admin_fake.on("GET", "/suppliers/3", {"data": supplier()})
    assert "next pull overwrites" in plan(capsys, argv)["summary"]


# ----------------------------------------------------------- warehouses ----
# WarehouseResource::toArray; WarehouseRequest: code/type on create only, name.en, lead_days, supplier_id only for dropship
def warehouse(i=2, **kw):
    return {"id": i, "code": "main", "name": "Main",
            "name_translations": {"en": "Main", "hy": "Գլխավոր", "ru": "Главный"},
            "type": "own", "supplier_id": None, "supplier_name": None, "lead_days": 0, "skip_non_working_days": False,
            "is_active": True, "sort_order": 1, "variants_with_stock": 5, "on_hand_total": 40, **kw}


def test_warehouse_create_posts_the_form(admin_fake, capsys):
    admin_fake.on("GET", "/warehouses", {"data": [warehouse()]}).on("POST", "/warehouses", {"data": warehouse(5)})
    body = {"code": "second", "type": "own", "name": {"en": "Second", "hy": "", "ru": ""}, "lead_days": 1}
    argv = ["admin", "warehouses", "create", json.dumps(body)]
    out = plan(capsys, argv)
    assert out["tier"] == "draft" and writes(admin_fake) == []
    assert run([*argv, "--apply", out["code"]]) == 0 and writes(admin_fake) == [("POST", "/warehouses", body)]


@pytest.mark.parametrize("body", [
    {"code": "main", "type": "own", "name": {"en": "Dup"}, "lead_days": 0},
    {"code": "x", "type": "own", "name": {"hy": "x"}, "lead_days": 0},
    {"code": "x", "type": "own", "name": {"en": "x"}},
    {"code": "x", "type": "other", "name": {"en": "x"}, "lead_days": 0},
    {"code": "x", "type": "dropship", "name": {"en": "x"}, "lead_days": 0},
    {"code": "x", "type": "own", "name": {"en": "x"}, "lead_days": 0, "supplier_id": 3},
    {"code": "x", "type": "own", "name": {"en": "x"}, "lead_days": 0, "address": "a"}])
def test_warehouse_create_refuses_what_the_request_refuses(admin_fake, body):
    admin_fake.on("GET", "/warehouses", {"data": [warehouse()]})
    assert run(["admin", "warehouses", "create", json.dumps(body)]) == 1 and writes(admin_fake) == []


def test_a_dropship_warehouse_names_its_supplier(admin_fake, capsys):
    admin_fake.on("GET", "/warehouses", {"data": []}).on("GET", "/suppliers/3", {"data": supplier()})
    body = {"code": "hafo-wh", "type": "dropship", "name": {"en": "hafo"}, "lead_days": 2, "supplier_id": 3}
    assert "for supplier 3 (hafo)" in plan(capsys, ["admin", "warehouses", "create", json.dumps(body)])["summary"]


def test_warehouse_update_reads_the_list_and_never_sends_code_or_type(admin_fake, capsys):
    admin_fake.on("GET", "/warehouses", {"data": [warehouse()]}).on("PUT", "/warehouses/2", {"data": warehouse()})
    body = {"name": {"en": "Main shop", "hy": "Գլխավոր", "ru": "Главный"}, "lead_days": 1}
    argv = ["admin", "warehouses", "update", "2", json.dumps(body)]
    out = plan(capsys, argv)
    assert "lead_days: 0 → 1" in out["summary"] and all(c[1] == "/warehouses" for c in admin_fake.calls)
    assert run([*argv, "--apply", out["code"]]) == 0 and writes(admin_fake) == [("PUT", "/warehouses/2", body)]
    for bad in ({**body, "code": "x"}, {**body, "type": "dropship"}, {"lead_days": 1}, {**body, "supplier_id": 3}):
        assert run(["admin", "warehouses", "update", "2", json.dumps(bad)]) == 1
    assert run(["admin", "warehouses", "update", "99", json.dumps(body)]) == 1 and len(writes(admin_fake)) == 1


def test_warehouses_list_prints_the_table(admin_fake, capsys):
    admin_fake.on("GET", "/warehouses", {"data": [warehouse()]})
    assert run(["admin", "warehouses", "list"]) == 0 and "main" in capsys.readouterr().out


# -------------------------------------------------------- Ops proxies ----
# siruk-stock.md: purchase orders and locations
PO = {"id": U1, "number": "PO-000042", "kind": "web_order", "status": "placed", "web_order_number": "N-K3F9QZ",
      "web_orders": [{"id": "9d21", "number": "N-K3F9QZ"}], "external_ref": "HAFO-77812", "placed_at": "2026-11-09T10:15:00.000Z",
      "note": None, "created_at": "2026-11-09T10:12:00.000Z", "line_count": 2, "known_cost_amd": 18500, "all_costs_known": True}
PO_DETAIL = {"data": {**PO, "supplier_name": "hafo", "invoices": [], "lines": [
    {"id": "c3a0", "ops_variant_id": "6f1c", "siruk_variant_id": 4512, "sku": "ROY-ADULT-2KG", "label": "2 kg",
     "barcode": "4770002000022", "product_name": "Royal Canin Adult", "quantity": 2, "unit_cost_amd": 9250, "hafo_sku": "RC-AD-2",
     "hafo_units": 1, "hafo_quantity": 2, "hafo_in_stock": True, "hafo_observed_at": None, "allocations": []}]}}
LOCATION = {"id": U2, "code": "01", "name": "Siruk shop", "kind": "shop", "is_active": True, "siruk_warehouse_code": "main",
            "connector": None}
STOCK = {"data": [{"ops_variant_id": "6f1c", "siruk_variant_id": 4512, "product_name": "Royal Canin Mini Adult", "label": "2 kg",
                   "sku": "RC-MINI-2", "barcode": "3182550702416", "stock_unit": "pack", "on_hand": 12, "reserved": 2,
                   "available": 10, "in_stock": True, "low_stock_at": 3, "as_of": "2026-11-16T09:20:00.000Z"}],
         "meta": {"total": 1, "page": 1, "page_size": 50, "location": LOCATION}}


def test_the_ops_proxies_only_read_and_print_json_unmodified(admin_fake, capsys):
    admin_fake.on("GET", "/ops/purchase-orders", {"data": [PO], "meta": {"total": 1}})
    admin_fake.on("GET", f"/ops/purchase-orders/{U1}", PO_DETAIL).on("GET", "/ops/locations", {"data": [LOCATION]})
    admin_fake.on("GET", f"/ops/locations/{U2}/stock", STOCK)
    cases = [(["purchase-orders", "--status", "placed", "--kind", "web_order", "--search", "hafo"], "PO-000042",
              "/ops/purchase-orders?status=placed&kind=web_order&q=hafo"),
             (["purchase-order", U1], "ROY-ADULT-2KG", f"/ops/purchase-orders/{U1}"),
             (["locations"], "Siruk shop", "/ops/locations"),
             (["location-stock", U2, "--search", "royal", "--page", "2"], "RC-MINI-2",
              f"/ops/locations/{U2}/stock?q=royal&page=2")]
    for argv, needle, path in cases:
        admin_fake.calls.clear()
        assert run(["admin", "ops", *argv]) == 0 and needle in capsys.readouterr().out
        assert admin_fake.calls[0][:2] == ("GET", path)
        assert run(["admin", "ops", *argv, "--json"]) == 0
        answer = next(r[2] for r in admin_fake.routes if r[1] == path.split("?")[0])
        assert json.loads(capsys.readouterr().out) == answer
        assert [c[0] for c in admin_fake.calls] == ["GET", "GET"]


def test_an_ops_id_that_is_not_a_uuid_is_refused(admin_fake):
    assert run(["admin", "ops", "purchase-order", "123"]) == 1 and run(["admin", "ops", "location-stock", "x"]) == 1
    assert admin_fake.calls == []


def test_an_ops_proxy_failure_exits_2(admin_fake):
    down = '{"message": "down", "error": "ops_unavailable"}'
    admin_fake.on("GET", "/ops/locations", C.ApiError(502, "GET", "/ops/locations", down))
    assert run(["admin", "ops", "locations"]) == 2


# ---------------------------------------------------------- resend-order ----
# SingleOrderResource::opsSummary; OpsController::resend answers {data: {resent}}
def order(can_resend=True):
    return {"data": {"id": 5120, "order_number": "#N-K3F9QZ", "ops": {
        "can_resend": can_resend, "hdm_receipt": None, "hdm_return": None, "pushes": [
        {"event": "order.accepted", "status": "failed", "attempts": 12, "error": "timeout"},
        {"event": "order.delivered", "status": "sent", "attempts": 1, "error": None}]}}}


def test_resend_order_posts_without_a_body_after_showing_the_failed_pushes(admin_fake, capsys):
    admin_fake.on("GET", "/orders/5120", order()).on("POST", "/ops/orders/5120/resend", {"data": {"resent": 1}})
    out = plan(capsys, ["admin", "ops", "resend-order", "5120"])
    assert out["tier"] == "real-world" and "order.accepted: failed after 12 attempts — timeout" in out["summary"]
    assert "order.delivered" not in out["summary"] and writes(admin_fake) == []
    assert run(["admin", "ops", "resend-order", "5120", "--apply", out["code"]]) == 0
    assert writes(admin_fake) == [("POST", "/ops/orders/5120/resend", None)]


def test_resend_order_is_refused_when_nothing_failed(admin_fake):
    admin_fake.on("GET", "/orders/5120", order(False)).on("GET", "/orders/5121", {"data": {"id": 5121, "ops": None}})
    assert run(["admin", "ops", "resend-order", "5120"]) == 1 and run(["admin", "ops", "resend-order", "5121"]) == 1
    assert writes(admin_fake) == []


# ------------------------------------------------------------ the policy ----
@pytest.mark.parametrize("method,path", [
    ("POST", "/product-variants/101/move"), ("DELETE", "/product-variants/101"), ("POST", "/product-variants/77/restore"),
    ("POST", "/product-variants/77/release-sku"), ("POST", "/products/10/merge"), ("POST", "/products/10/discontinue"),
    ("POST", "/suppliers"), ("PUT", "/suppliers/3"), ("DELETE", "/suppliers/3"), ("POST", "/suppliers/3/products"),
    ("POST", "/suppliers/3/stock-check"), ("POST", "/suppliers/3/ops-stock-sync"), ("PUT", "/supplier-products/17"),
    ("DELETE", "/supplier-products/17"), ("PUT", "/supplier-products/17/stock"), ("POST", "/warehouses"),
    ("PUT", "/warehouses/2"), ("POST", "/ops/orders/5120/resend")])
def test_every_path_the_commands_write_is_allowed_by_the_policy(method, path):
    assert policy.allowed(method, path) is None


def test_every_step_the_plans_emit_passes_the_policy(shop, capsys):
    shop.on("GET", "/suppliers/3", {"data": supplier(ops_stock_source="hafo")})
    shop.on("GET", "/warehouses", {"data": [warehouse()]})
    shop.on("GET", "/orders/5120", order())
    shop.on("GET", "/product-variants/archived", ARCHIVED)
    rows(shop, ROW)
    plans = [L.plan_move(101, 10, 20, {"12": [38]}), L.plan_discontinue(10), L.plan_archive(101, 10), L.plan_restore(77),
             L.plan_release_sku(77), L.plan_stock_check(3), L.plan_ops_stock_sync(3), L.plan_resend(5120),
             L.plan_supplier_product_set(3, 17, {"is_active": False}), L.plan_supplier_product_rm(3, 17),
             L.plan_supplier_product_stock(3, 17, 5), L.plan_warehouse_update(2, {"name": {"en": "x"}, "lead_days": 0})]
    steps = [s for p in plans for s in p[0]]
    assert steps and all(policy.allowed(s.method, s.path) is None for s in steps)
