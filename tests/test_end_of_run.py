"""verify-translations, the hafo recheck and bulk create — offline, on the fake client."""
import copy

import pytest

from siruk import bulk, pricecheck, verify
from siruk import payload as P


@pytest.fixture
def no_dict(monkeypatch):
    monkeypatch.setattr(verify, "_dict", {"strings": {}, "paragraphs": {}, "names": {}})


def test_verify_flags_untranslated_product(fake, no_dict):
    res = verify.translations(only=[874], catalogue=False)
    fields = {(l, f) for _, l, f, _ in res["missing"]["product"]}
    assert ("ru", "name") in fields and ("hy", "387957.about_this_item") in fields
    assert not res["complete"]


def test_verify_accepts_real_translation(fake, no_dict, monkeypatch):
    def get(path, lang=None, **kw):
        d = type(fake).get(fake, path, lang)
        if lang in ("ru", "hy") and path.startswith("/products/"):
            d = copy.deepcopy(d)
            d["data"]["name"] = f"name-{lang}"
            for v in d["data"]["variants"]:
                for f in P.VTEXT:
                    v[f] = f"{f}-{lang}"
        return d
    fake.get = get
    assert verify.translations(only=[874], catalogue=False)["complete"]


class FakeHafo:
    def __init__(self, price, flags=False):
        self.price, self.flags = price, flags

    def find(self, sku, brand_id, cost=0):
        if sku != "387957":
            return None, None, "not on hafo"
        listing = {"id": 1, "slug": "x", "discount": 5 if self.flags else None}
        return listing, {"id": 9, "sku": sku, "price": self.price, "wholesale_price": 1300}, ""

    def change(self, lid, row):
        return {"price": row["price"]}


def test_recheck_mismatch_is_fixable_and_sibling_fallback(fake, monkeypatch):
    monkeypatch.setattr(pricecheck, "Hafo", lambda: FakeHafo(2200))
    rows = pricecheck.check([874])
    by = {r["sku"]: r for r in rows}
    assert by["387957"]["status"] == "MISMATCH"
    assert by["387967"]["status"] == "SIBLING MISMATCH"  # same cost, sibling's hafo price differs from ours
    assert pricecheck.fixes(rows) == {874: {"387957": 2200}}


def test_recheck_flagged_mismatch_not_fixable(fake, monkeypatch):
    monkeypatch.setattr(pricecheck, "Hafo", lambda: FakeHafo(2200, flags=True))
    assert pricecheck.fixes(pricecheck.check([874])) == {}


def test_foreign_supplier_suffix_is_not_our_article():
    assert pricecheck.foreign_suffix("04123IVS", "4123") == "ivs"   # Trixie 4123 vs an Iv San Bernard shampoo
    assert pricecheck.foreign_suffix("41116Tx", "41116") is None
    assert pricecheck.foreign_suffix("TX 35718Trx", "35718") is None
    assert pricecheck.foreign_suffix("013117MG", "013117", brand_id=3) is None   # not Trixie: no guard


def test_apply_prices_dry_run_and_cost_guard(fake):
    res = pricecheck.apply_prices(874, {"387957": 2200}, dry_run=True)
    assert [d for d in res.diff if d["field"] == "price"] == [
        {"sku": "387957", "field": "price", "old": 2100, "new": 2200}] and not fake.writes
    with pytest.raises(P.PayloadError, match="nothing to apply"):
        pricecheck.apply_prices(874, {"387957": 1300}, dry_run=True)


def payload(slug="gemon-new-thing", **over):
    p = {"name": {"en": "New Thing", "ru": "Новое", "hy": "Նոր"}, "slug": slug, "category_ids": [4],
         "brand_id": 18, "attribute_family_id": 2,
         "variants": [{"sku": f"NEW-{slug}", "name": "Salmon 400 g", "price": 900, "cost_price": 600,
                       "measure_type": "mass", "content": 400, "images": [1],
                       "attribute_values": {"flavor": [38]}}]}
    p.update(over)
    return p


@pytest.fixture
def no_similar(fake):
    orig = type(fake).get

    def get(path, lang=None, **kw):
        if path.startswith("/products?search="):
            return {"data": [], "meta": {"last_page": 1}}
        return orig(fake, path, lang)
    fake.get = get
    return fake


def test_bulk_dry_run_ready_and_refusals(no_similar):
    items = [("a", payload("a-one")), ("b", payload("a-one")),               # repeated slug
             ("c", payload("c-one", name={"en": "Only English"})),            # no ru/hy
             ("d", payload("d-one", existing_id=874))]
    res = bulk.create(items, dry_run=True)
    assert res["a"]["status"] == "ready" and res["b"]["status"] == "refused"
    assert "repeats" in res["b"]["errors"] and "translation" in res["c"]["errors"]
    assert "add_variant" in res["d"]["errors"] and not no_similar.writes
    assert bulk.create([("c", payload("c-one", name={"en": "Only English"}))], dry_run=True,
                       en_only=True)["c"]["status"] == "ready"


def test_bulk_below_cost_refused(no_similar):
    p = payload("x-one")
    p["variants"][0]["price"] = 500
    assert bulk.create([("x", p)], dry_run=True)["x"]["status"] == "refused"


def test_bulk_translations_block_merges(no_similar):
    p = payload("t-one", name="Plain")
    p["variants"][0]["about_this_item"] = "about"
    p["translations"] = {"ru": {"name": "Ру", "variants": {"NEW-t-one": {"about_this_item": "о"}}},
                         "hy": {"name": "Հայ", "variants": {"NEW-t-one": {"about_this_item": "հ"}}}}
    body = bulk.create([("t", p)], dry_run=True)["t"]["body"]
    assert body["name"] == {"en": "Plain", "ru": "Ру", "hy": "Հայ"}
    assert body["variants"][0]["about_this_item"] == {"en": "about", "ru": "о", "hy": "հ"}


def test_mcp_new_tools_listed(fake):
    pytest.importorskip("mcp")
    import asyncio
    from siruk.mcp_server import mcp

    async def go():
        return {t.name: t for t in await mcp.list_tools()}
    tools = asyncio.run(go())
    for n in ("verify_translations", "hafo_price_recheck", "apply_hafo_prices", "bulk_create_products"):
        assert n in tools
    assert tools["verify_translations"].annotations.read_only_hint
    assert not tools["bulk_create_products"].annotations.read_only_hint
