"""Listing order: name resolution, guards, the read-back and the CLI / MCP faces."""
import asyncio

import pytest

from siruk import cli, listing
from siruk import client as _client
from siruk.payload import PayloadError

BRANDS = [{"id": 5, "name": "Monge", "slug": "monge"}, {"id": 1, "name": "Acana", "slug": "acana"}]
CATEGORIES = [{"id": 1, "name": "Dog", "parent_id": None, "children": [
    {"id": 2, "name": "Food", "parent_id": 1, "children": [
        {"id": 3, "name": "Dry Food", "parent_id": 2, "children": None}]}]}]


@pytest.fixture
def lfake(fake, monkeypatch):
    fake.groups = []
    get, request = fake.get, fake.request

    def g(path, lang=None, **kw):
        if path.startswith("/brands"):
            return {"data": BRANDS}
        if path.startswith("/categories"):
            return {"data": CATEGORIES}
        if path == "/listing-groups":
            return {"data": [dict(x, id=i + 1, position=i + 1) for i, x in enumerate(fake.groups)]}
        return get(path, lang=lang)

    def r(method, path, body=None, lang=None, **kw):
        if method.upper() == "PUT" and path == "/listing-groups":
            fake.writes.append((method, path, body))
            fake.groups = body["groups"]
            return {"data": fake.groups}
        return request(method, path, body=body, lang=lang)
    monkeypatch.setattr(fake, "get", g)
    monkeypatch.setattr(fake, "request", r)
    return fake


def test_categories_tree_is_flattened(lfake):
    from siruk import refdata
    assert [c["id"] for c in refdata.ids("categories")] == [1, 2, 3]
    assert refdata.ids("categories")[2]["parent_id"] == 2


def test_brand_names_resolve_and_labels_show_the_path(lfake):
    res = listing.set_groups([{"brand": "monge", "category": 3}, {"brand": 1, "category": None}], dry_run=True)
    assert res["body"] == {"groups": [{"brand_id": 5, "category_id": 3}, {"brand_id": 1, "category_id": None}]}
    assert res["after"][0]["category"] == "Dog › Food › Dry Food" and res["after"][1]["category"] == "(whole brand)"
    assert not lfake.writes


def test_refuses_unknown_duplicate_and_empty(lfake):
    with pytest.raises(PayloadError, match="unknown brand"):
        listing.set_groups([{"brand": "Nope"}], dry_run=True)
    with pytest.raises(PayloadError, match="unknown category"):
        listing.set_groups([{"brand": 5, "category": 99}], dry_run=True)
    with pytest.raises(PayloadError, match="already in the list"):
        listing.set_groups([{"brand": 5, "category": 3}, {"brand": "Monge", "category": 3}], dry_run=True)
    with pytest.raises(PayloadError, match="empty list"):
        listing.set_groups([], dry_run=True)


def test_write_reads_back_and_add_remove(lfake):
    res = listing.set_groups([{"brand": 5, "category": 3}], dry_run=False)
    assert res["written"] and lfake.groups == [{"brand_id": 5, "category_id": 3}]
    listing.add("Acana", 3, at=1)
    assert [g["brand_id"] for g in lfake.groups] == [1, 5]
    listing.remove(1)
    assert lfake.groups == [{"brand_id": 5, "category_id": 3}]
    n = len(lfake.writes)
    assert not listing.set_groups([{"brand": 5, "category": 3}])["changed"] and len(lfake.writes) == n


def test_cli_dry_run_and_mcp_default_write_nothing(lfake, capsys):
    with pytest.raises(SystemExit) as e:
        cli.main(["-q", "listing-order", "set", '[{"brand": "Monge", "category": 3}]', "--dry-run"])
    assert e.value.code == 0 and not lfake.writes
    assert "Dog › Food › Dry Food" in capsys.readouterr().out
    pytest.importorskip("mcp")
    from siruk.mcp_server import mcp
    _client.set_default(lfake)

    async def go():
        await mcp.call_tool("set_listing_order", {"groups": [{"brand": "Monge", "category": 3}]})
    asyncio.run(go())
    assert not lfake.writes
