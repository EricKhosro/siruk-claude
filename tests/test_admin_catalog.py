"""Admin catalogue structure: categories, brands, attributes, values, product types, price types, reviews.
Shapes come from siruk-web/backend: the controllers in app/Http/Controllers/Admin/Catalog (validatedData for the
bodies, `destroy` and CatalogUsageGuard for the delete rules), PriceTypeRequest.php (code regex), and the Resources in
app/Http/Resources/Admin/Catalog for the records."""
import json

import pytest

from siruk import cli
from siruk.admin import catalog as C

from test_admin_core import plan_code, run, writes   # same helpers as the admin foundation tests


# app/Http/Resources/Admin/Catalog/CategoryResource.php: CategoryResource::toArray (children is null or a list; productsCount is 0 on show)
def category(i=12, **kw):
    return {"id": i, "parent_id": 3, "name": "Dog food", "slug": "dog-food", "path": "dogs/dog-food",
            "description": None, "image": None, "featured_image": None, "quick_links": [], "related_searches": None,
            "list_as_products": True, "complement_category_ids": [], "children": None, "productsCount": 0,
            "deleteLocked": False, **kw}


# app/Http/Resources/Admin/Catalog/PriceTypeResource.php: PriceTypeResource::toArray
def price_type(i=1, code="website", **kw):
    return {"id": i, "code": code, "name": "Website", "is_active": True, "sort_order": 0, **kw}


# app/Http/Resources/Admin/Catalog/AttributeFamilyResource.php: toArray (attributes carry the pivot role and flags in camelCase)
def family(**kw):
    attrs = [{"id": 3, "name": "Lifestage", "code": "lifestage", "inputType": "select", "role": "attribute",
              "isRequired": False, "isFilterable": True, "showOnProductCard": False, "position": 0},
             {"id": 5, "name": "Flavor", "code": "flavor", "inputType": "select", "role": "option",
              "isRequired": True, "isFilterable": True, "showOnProductCard": True, "position": 1}]
    return {"id": 2, "name": "Wet Food", "code": "wet-food", "defaultSaleMode": "pack", "measureType": "mass",
            "unitPriceBasis": None, "lowStockThreshold": None, "lowStockGrams": None, "sortOrder": 0,
            "attributes": attrs, "deleteLocked": False, **kw}


# app/Http/Resources/Admin/Catalog/ProductReviewResource.php: toArray (the keys these tests read)
def review(**kw):
    return {"id": 9, "product_id": 874, "title": "Great", "rating": 5, "comment": "ok", "reply": "Thank you",
            "is_approved": True, "is_recommended": True, "is_seen": True, **kw}


NOUNS = {"categories": "list show create update delete", "brands": "list show create update delete",
         "attributes": "list show create update delete", "attribute-values": "list show create update delete",
         "product-types": "list show create update delete", "price-types": "list show create update delete",
         "reviews": "list show update", "review-reports": "list show update"}


def by_name(capsys):
    assert run(["commands", "--json"]) == 0
    return {r["name"]: r for r in json.loads(capsys.readouterr().out)}


def test_every_noun_and_verb_is_in_the_manifest_with_its_fields(capsys):
    by = by_name(capsys)
    for noun, verbs in NOUNS.items():
        for verb in verbs.split():
            e = by[f"admin {noun} {verb}"]
            assert e["backend"] == "admin" and e["api"] and e["help"] and e["example"] and e["roles"]
            assert e["tier"] == {"list": "read", "show": "read", "delete": "irreversible"}.get(verb, "draft")
    assert not {"admin reviews create", "admin reviews delete", "admin review-reports create",
                "admin review-reports delete"} & set(by)
    assert "price-types" in by   # the Phase 1 read is untouched
    # the validators of ProductReviewController::update and ProductReviewReportController::update
    assert by["admin reviews update"]["example"] == "siruk admin reviews update 9 '{\"is_approved\": true, \"reply\": \"…\"}'"
    assert by["admin review-reports update"]["example"] == "siruk admin review-reports update 2 '{\"is_resolved\": true}'"


def test_every_resource_names_what_it_requires_and_where_it_was_read():
    for r in (C.CATEGORIES, C.BRANDS, C.ATTRIBUTES, C.ATTRIBUTE_VALUES, C.PRODUCT_TYPES, C.PRICE_TYPES):
        assert r.required and r.source and r.translatable
    assert C.REVIEWS.source and C.REVIEW_REPORTS.source and not C.REVIEWS.deletable


@pytest.mark.parametrize("argv", [["categories", "create"], ["attributes", "create"], ["attributes", "update"],
                                  ["attribute-values", "create"]])
def test_creating_help_says_it_needs_an_explicit_ask(argv, capsys):
    with pytest.raises(SystemExit):
        cli.main(["admin", *argv, "--help"])
    assert "explicit ask" in capsys.readouterr().out


# ------------------------------------------------------------ category ----
def test_category_create_posts_the_form_fields_after_a_dry_run(admin_fake, capsys):
    admin_fake.on("GET", "/categories", {"data": []}).on("POST", "/categories", {"data": category()})
    body = {"name": "Dog food", "slug": "dog-food", "parent_id": 3, "image": 41, "list_as_products": True}
    argv = ["admin", "categories", "create", json.dumps(body)]
    assert run([*argv, "--json"]) == 0
    plan = json.loads(capsys.readouterr().out)
    assert plan["tier"] == "draft" and writes(admin_fake) == []
    assert plan["requests"][0]["method"] == "POST" and plan["requests"][0]["path"] == "/categories"
    assert run([*argv, "--apply", plan["code"]]) == 0
    assert writes(admin_fake) == [("POST", "/categories", body)]


def test_category_create_is_en_only_and_refuses_a_missing_slug(admin_fake):
    assert run(["admin", "categories", "create", '{"name": "x", "slug": "x"}', "--lang", "ru"]) == 1
    assert run(["admin", "categories", "create", '{"name": "x"}']) == 1
    assert admin_fake.calls == []


@pytest.mark.parametrize("body", [{"image": "https://x.test/a.jpg"}, {"image": 4.5}, {"featured_image": "41"},
                                  {"image": True}])
def test_a_category_image_must_be_a_media_id(body, admin_fake):
    full = {"name": "x", "slug": "x", **body}
    assert run(["admin", "categories", "create", json.dumps(full)]) == 1
    assert admin_fake.calls == []


def test_a_brand_logo_must_be_a_media_id(admin_fake):
    assert run(["admin", "brands", "create", '{"name": "x", "slug": "x", "image": "logo.png"}']) == 1
    assert run(["admin", "brands", "update", "5", '{"name": "x", "slug": "x", "image": "logo.png"}']) == 1
    assert admin_fake.calls == []


def test_a_category_update_without_list_as_products_would_turn_it_off(admin_fake, capsys):
    admin_fake.on("GET", "/categories/12", {"data": category()}).on("PUT", "/categories/12", {"data": category()})
    assert run(["admin", "categories", "update", "12", '{"name": "Dog food", "slug": "dog-food"}',
                "--apply", "deadbeef"]) == 1
    assert "list_as_products" in capsys.readouterr().err and writes(admin_fake) == []
    body = {"name": "Dog food", "slug": "dog-food", "list_as_products": True}
    code = plan_code(capsys, ["admin", "categories", "update", "12", json.dumps(body)])
    assert run(["admin", "categories", "update", "12", json.dumps(body), "--apply", code]) == 0
    assert writes(admin_fake) == [("PUT", "/categories/12", body)]


def test_category_delete_with_children_is_refused_with_the_count(admin_fake, capsys):
    kids = [category(13, parent_id=12), category(14, parent_id=12)]
    admin_fake.on("GET", "/categories/12", {"data": category(children=kids, deleteLocked=True)})
    admin_fake.on("GET", "/categories", {"data": []}).on("DELETE", "/categories/12", None)
    assert run(["admin", "categories", "delete", "12", "--apply", "deadbeef"]) == 1
    assert "2 subcategories" in capsys.readouterr().err and writes(admin_fake) == []


def test_category_delete_with_products_is_refused_with_the_count(admin_fake, capsys):
    admin_fake.on("GET", "/categories/12", {"data": category(deleteLocked=True)})
    admin_fake.on("GET", "/categories", {"data": [category(12, productsCount=40)]})
    assert run(["admin", "categories", "delete", "12", "--json"]) == 1
    assert "40 products" in capsys.readouterr().err and writes(admin_fake) == []
    assert admin_fake.calls[-1][:2] == ("GET", "/categories?search=Dog+food")


def test_an_empty_category_deletes_as_irreversible(admin_fake, capsys):
    admin_fake.on("GET", "/categories/12", {"data": category()}).on("DELETE", "/categories/12", None)
    assert run(["admin", "categories", "delete", "12", "--json"]) == 0
    plan = json.loads(capsys.readouterr().out)
    assert plan["tier"] == "irreversible"
    assert run(["admin", "categories", "delete", "12", "--apply", plan["code"]]) == 0
    assert writes(admin_fake) == [("DELETE", "/categories/12", None)]


# --------------------------------------------------------- product type ----
def test_product_type_update_sends_attributes_with_role_and_flags(admin_fake, capsys):
    admin_fake.on("GET", "/attribute-families/2", {"data": family()}).on("PUT", "/attribute-families/2", {"data": family()})
    body = {"name": "Wet Food", "code": "wet-food", "measure_type": "mass", "default_sale_mode": "pack",
            "attributes": [{"id": 5, "role": "option", "is_required": True, "is_filterable": True,
                            "show_on_product_card": True},
                           {"id": 8, "role": "attribute", "is_filterable": False}]}
    argv = ["admin", "product-types", "update", "2", json.dumps(body)]
    assert run([*argv, "--json"]) == 0
    plan = json.loads(capsys.readouterr().out)
    assert plan["tier"] == "draft" and writes(admin_fake) == []
    assert "+8(attribute)" in plan["summary"] and "-lifestage" in plan["summary"]
    assert run([*argv, "--apply", plan["code"]]) == 0
    assert writes(admin_fake) == [("PUT", "/attribute-families/2", body)]


def test_product_type_update_names_a_role_change(admin_fake, capsys):
    admin_fake.on("GET", "/attribute-families/2", {"data": family()})
    body = {"name": "Wet Food", "code": "wet-food",
            "attributes": [{"id": 3, "role": "option", "is_required": False, "is_filterable": True},
                           {"id": 5, "role": "option", "is_required": True}]}
    assert run(["admin", "product-types", "update", "2", json.dumps(body), "--json"]) == 0
    assert "~lifestage: role attribute→option" in json.loads(capsys.readouterr().out)["summary"]


@pytest.mark.parametrize("attrs", [[{"id": 3}], [{"id": 3, "role": "axis"}], [{"id": "3", "role": "option"}],
                                   [{"id": 3, "role": "option"}, {"id": 3, "role": "attribute"}],
                                   [{"id": 3, "role": "option", "is_required": "yes"}]])
def test_product_type_attributes_without_a_valid_role_are_refused(attrs, admin_fake):
    body = {"name": "Wet Food", "code": "wet-food", "attributes": attrs}
    assert run(["admin", "product-types", "update", "2", json.dumps(body)]) == 1
    assert admin_fake.calls == []


def test_product_type_enums_are_checked(admin_fake):
    assert run(["admin", "product-types", "create", '{"name": "x", "code": "x", "measure_type": "length"}']) == 1
    assert admin_fake.calls == []


# ----------------------------------------------------------- price type ----
def test_price_type_create_posts_code_name_active_and_order(admin_fake, capsys):
    admin_fake.on("GET", "/price-types", {"data": [price_type()]}).on("POST", "/price-types", {"data": price_type(4)})
    body = {"code": "wholesale-2", "name": "Wholesale", "is_active": True, "sort_order": 30}
    argv = ["admin", "price-types", "create", json.dumps(body)]
    code = plan_code(capsys, argv)
    assert writes(admin_fake) == []
    assert run([*argv, "--apply", code]) == 0
    assert writes(admin_fake) == [("POST", "/price-types", body)]


def test_price_type_is_active_must_be_a_boolean(admin_fake):
    assert run(["admin", "price-types", "create", '{"code": "x", "name": "X", "is_active": "false"}']) == 1
    assert admin_fake.calls == []


@pytest.mark.parametrize("code", ["Wholesale", "whole sale", "whole_sale", "", "a" * 41])
def test_a_bad_price_type_code_is_refused_before_any_call(code, admin_fake):
    assert run(["admin", "price-types", "create", json.dumps({"code": code, "name": "W"})]) == 1
    assert run(["admin", "price-types", "update", "4", json.dumps({"code": code, "name": "W"})]) == 1
    assert admin_fake.calls == []


def test_the_website_price_type_is_never_deleted(admin_fake, capsys):
    admin_fake.on("GET", "/price-types/1", {"data": price_type()}).on("DELETE", "/price-types/1", None)
    assert run(["admin", "price-types", "delete", "1", "--json"]) == 1
    assert run(["admin", "price-types", "delete", "1", "--apply", "deadbeef"]) == 1
    assert "website" in capsys.readouterr().err and writes(admin_fake) == []


@pytest.mark.parametrize("body", [{"code": "web", "name": "Website"}, {"code": "website", "name": "Website", "is_active": False},
                                  {"code": "website", "name": "Website", "is_active": 0}])
def test_the_website_price_type_is_never_recoded_or_deactivated(body, admin_fake):
    admin_fake.on("GET", "/price-types/1", {"data": price_type()}).on("PUT", "/price-types/1", {"data": price_type()})
    assert run(["admin", "price-types", "update", "1", json.dumps(body), "--apply", "deadbeef"]) == 1
    assert writes(admin_fake) == []


def test_the_website_price_type_can_be_renamed_and_another_type_deleted(admin_fake, capsys):
    admin_fake.on("GET", "/price-types/1", {"data": price_type()}).on("GET", "/price-types/4", {"data": price_type(4, "glovo")})
    admin_fake.on("PUT", "/price-types/1", {"data": price_type()}).on("DELETE", "/price-types/4", None)
    assert run(["admin", "price-types", "update", "1", '{"code": "website", "name": "Web shop", "sort_order": 0}',
                "--json"]) == 0
    assert run(["admin", "price-types", "delete", "4", "--json"]) == 0
    assert writes(admin_fake) == []


# --------------------------------------------------------------- reviews ----
def test_a_review_update_without_reply_would_clear_it_and_is_refused(admin_fake, capsys):
    admin_fake.on("GET", "/product-reviews/9", {"data": review()}).on("PUT", "/product-reviews/9", {"data": review()})
    assert run(["admin", "reviews", "update", "9", '{"is_approved": false}', "--apply", "deadbeef"]) == 1
    err = capsys.readouterr().err
    assert "reply" in err and "re-stamps replied_at" in err and writes(admin_fake) == []
    body = {"is_approved": False, "reply": "Thank you"}
    code = plan_code(capsys, ["admin", "reviews", "update", "9", json.dumps(body)])
    assert run(["admin", "reviews", "update", "9", json.dumps(body), "--apply", code]) == 0
    assert writes(admin_fake) == [("PUT", "/product-reviews/9", body)]


def test_review_update_help_says_what_the_read_and_the_reply_do(capsys):
    for noun in ("reviews", "review-reports"):
        with pytest.raises(SystemExit):
            cli.main(["admin", noun, "update", "--help"])
        out = " ".join(capsys.readouterr().out.split())
        assert "marks" in out and "seen" in out
    with pytest.raises(SystemExit):
        cli.main(["admin", "reviews", "update", "--help"])
    assert "re-stamps replied_at" in " ".join(capsys.readouterr().out.split())


def test_a_review_report_is_resolved_through_a_put(admin_fake, capsys):
    # app/Http/Resources/Admin/Catalog/ProductReviewReportResource.php: toArray (the keys these tests read)
    rep = {"id": 2, "review_id": 9, "description": "spam", "is_resolved": False, "is_seen": True}
    admin_fake.on("GET", "/product-review-reports/2", {"data": rep}).on("PUT", "/product-review-reports/2", {"data": rep})
    body = {"is_resolved": True}
    code = plan_code(capsys, ["admin", "review-reports", "update", "2", json.dumps(body)])
    assert run(["admin", "review-reports", "update", "2", json.dumps(body), "--apply", code]) == 0
    assert writes(admin_fake) == [("PUT", "/product-review-reports/2", body)]


# ------------------------------------------------- the rest, one create each ----
def test_attribute_create_and_value_create_post_the_form_fields(admin_fake, capsys):
    # the 201 bodies are AttributeResource / AttributeValueResource; only `id` is read here
    admin_fake.on("GET", "/attributes", {"data": []}).on("POST", "/attributes", {"data": {"id": 1}})
    admin_fake.on("GET", "/attribute-values", {"data": []}).on("POST", "/attribute-values", {"data": {"id": 1}})
    attr = {"name": "Texture", "code": "texture", "input_type": "select"}
    val = {"attribute_id": 5, "value": "salmon", "label": "Salmon"}
    for noun, body in (("attributes", attr), ("attribute-values", val)):
        argv = ["admin", noun, "create", json.dumps(body)]
        code = plan_code(capsys, argv)
        assert run([*argv, "--apply", code]) == 0
        capsys.readouterr()
    assert [(m, p) for m, p, _ in writes(admin_fake)] == [("POST", "/attributes"), ("POST", "/attribute-values")]
    assert [b for *_, b in writes(admin_fake)] == [attr, val]


def test_an_update_missing_a_required_key_is_refused_before_any_call(admin_fake):
    assert run(["admin", "brands", "update", "5", '{"name": "Gemon"}']) == 1
    assert admin_fake.calls == []
