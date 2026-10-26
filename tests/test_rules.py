"""The rules, through siruk.products (what the CLI, TUI and MCP all call)."""
import pytest

from siruk import payload as P
from siruk import products, translations


def new_variant(**over):
    v = {"sku": "TEST-1", "name": "Salmon 400 g", "price": 900, "cost_price": 600, "measure_type": "mass",
         "content": 400, "images": [1], "attribute_values": {"flavor": [38], "lifestage": [27]}}
    v.update(over)
    return v


def test_add_variant_dry_run_resends_every_variant(fake):
    res = products.add_variant(874, new_variant(), dry_run=True)
    assert not fake.writes
    assert [v["sku"] for v in res.body["variants"]] == ["387957", "387967", "TEST-1"]
    assert all("item_content" not in v for v in res.body["variants"])  # server-only field stripped
    assert res.diff[0]["field"] == "(new variant)"


def test_add_variant_writes_then_reads_back(fake):
    res = products.add_variant(874, new_variant(), dry_run=False)
    assert fake.writes[0][0:2] == ("PUT", "/products/874") and res.after


def test_below_cost_refused_unless_allowed(fake):
    with pytest.raises(P.PayloadError, match="below cost"):
        products.add_variant(874, new_variant(price=600), dry_run=True)
    res = products.add_variant(874, new_variant(price=600), dry_run=True, allow_below_cost=True)
    assert any("below cost" in w for w in res.warnings)


def test_update_variant_price_guard_and_diff(fake):
    with pytest.raises(P.PayloadError, match="below cost"):
        products.update_variant(874, "387957", {"price": 1000}, dry_run=True)
    res = products.update_variant(874, "387957", {"price": 2200}, dry_run=True)
    assert res.diff == [{"sku": "387957", "field": "price", "old": 2100, "new": 2200}]


def test_same_options_and_size_refused(fake):
    with pytest.raises(P.PayloadError, match="cannot tell them apart"):
        products.add_variant(874, new_variant(content=1250), dry_run=True)


def test_size_in_name_refused(fake):
    with pytest.raises(P.PayloadError, match="pack size"):
        products.rename(874, "Adult Chunks 400 g", dry_run=True)


def test_merch_fields_refused(fake):
    with pytest.raises(P.PayloadError, match="PM"):
        products.update_variant(874, "387957", {"merch_boost": 5}, dry_run=True)


def test_no_image_refused(fake):
    payload = {"name": "New Thing", "slug": "brand-new-thing", "category_ids": [4], "brand_id": 18,
               "attribute_family_id": 2, "variants": [new_variant(images=[])]}
    fake.get = lambda path, lang=None, **kw: ({"data": [], "meta": {"last_page": 1}}
                                              if path.startswith("/products?") else type(fake).get(fake, path, lang))
    with pytest.raises(P.PayloadError, match="images"):
        products.create(payload, dry_run=True)


def test_create_refuses_duplicate_name(fake):
    payload = {"name": "All Breeds Adult Dog Chunks", "slug": "x", "category_ids": [4], "brand_id": 18,
               "attribute_family_id": 2, "variants": [new_variant()]}
    with pytest.raises(products.DuplicateError):
        products.create(payload, dry_run=True)


def test_invariants_catch_a_dropped_variant(fake):
    before = fake.get("/products/874")["data"]
    body = {"variants": [{"id": 1030, "sku": "387957", "is_default": True}]}
    with pytest.raises(P.PayloadError, match="dropped"):
        products._check_invariants(before, body)


def test_translation_keeps_single_language_fields_from_en(fake):
    res = translations.set_translation(874, "ru", {"name": "Кусочки", "variants": {"387957": {
        "about_this_item": "о товаре"}}}, dry_run=True)
    assert res.body["locale"] == "ru" and res.body["slug"] == "gemon-all-breeds-adult-dog-chunks"
    v = res.body["variants"][0]
    assert v["about_this_item"] == "о товаре" and v["name"] == "Salmon 1250 g"
    with pytest.raises(P.PayloadError, match="single-language"):
        translations.set_translation(874, "ru", {"sku": "x"}, dry_run=True)


def test_shim_is_the_same_module():
    import importlib, os, sys
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "scripts"))
    shim = importlib.import_module("siruk_payload")
    assert shim is P
