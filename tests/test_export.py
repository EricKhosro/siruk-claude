"""The catalogue export: query building, the audit, the file writers and the MCP tools — offline."""
import json

import pytest

from siruk import client as _client
from siruk import export


def rec(**over):
    r = {"product_id": 1, "product_name": "P", "product_type": "Dry Food", "variant_id": 10, "sku": "A",
         "price": 900, "cost_price": 600, "barcode": "4011905313429", "accounting_code": "0214",
         "image_ids": [5], "price_source_url": "https://hafo.am/products/x", "sale_mode": "pack",
         "content": 400, "is_purchasable": True, "available": 10}
    r.update(over)
    return r


def test_query_carries_filters_and_refuses_bad_lang():
    q = export._query("hy", "2026-10-20", "royal canin", "01/10/2026,20/10/2026", "json")
    assert q.startswith("/products/export?") and "lang=hy" in q and "format=json" in q
    assert "updated_since=2026-10-20" in q and "search=royal+canin" in q and "dates=01%2F10%2F2026" in q
    with pytest.raises(ValueError):
        export._query("de")


def test_audit_finds_each_problem():
    rows = [rec(),
            rec(variant_id=11, sku="B", price=600),                         # at cost
            rec(variant_id=12, sku="C", barcode=None, accounting_code=""),   # codes missing
            rec(variant_id=13, sku="D", image_ids=[], content=None),        # gallery, size
            rec(variant_id=14, sku="E", product_type="Toys", content=None),  # unsized type: fine
            rec(variant_id=15, sku="a", barcode="4011905313429"),           # dup sku (case) + dup barcode
            rec(product_id=2, variant_id=None, sku=None)]                   # no variants
    a = export.audit(rows, sized={"Dry Food"})
    c = a["counts"]
    assert (c["below_cost"], c["no_barcode"], c["no_accounting_code"], c["no_images"]) == (1, 1, 1, 1)
    assert c["no_content"] == 1 and c["no_variants"] == 1
    assert c["duplicate_sku"] == 1 and c["duplicate_barcode"] == 1
    assert a["products"] == 2 and a["variants"] == 6


class ExportClient(_client.Client):
    def __init__(self, rows):
        super().__init__(base="https://offline.test/api/admin", token="T",
                         opener=lambda *a, **k: (_ for _ in ()).throw(AssertionError("network")))
        self.pacer = type("P", (), {"pace": lambda *a, **k: None, "read_state": lambda *a: (0, 0)})()
        self.rows, self.seen = rows, []

    def request(self, method, path, body=None, lang=None, **kw):
        self.seen.append(path)
        if path.startswith("/products/export"):
            return {"data": self.rows}
        if path.startswith("/attribute-families"):
            return {"data": [{"id": 1, "name": "Dry Food", "measureType": "mass"}, {"id": 5, "name": "Toys"}]}
        raise AssertionError(path)

    def download(self, path, timeout=None):
        self.seen.append(path)
        return b"PK\x03\x04fake-xlsx", "products_en.xlsx"


@pytest.fixture
def exp_client():
    c = ExportClient([rec(), rec(variant_id=11, sku="B", about_this_item="long text")])
    _client.set_default(c)
    yield c
    _client.set_default(None)


def test_save_writes_each_format(exp_client, tmp_path):
    x = export.save(str(tmp_path / "a.xlsx"), "xlsx")
    assert x["bytes"] > 0 and "format=json" not in exp_client.seen[-1]
    j = export.save(str(tmp_path / "a.json"), "json")
    assert j["rows"] == 2 and json.loads((tmp_path / "a.json").read_text(encoding="utf-8"))[1]["sku"] == "B"
    c = export.save(str(tmp_path / "a.csv"), "csv")
    text = (tmp_path / "a.csv").read_text(encoding="utf-8-sig")
    assert c["rows"] == 2 and text.splitlines()[0].startswith("product_id") and "5" in text


def test_mcp_export_tools(exp_client):
    pytest.importorskip("mcp")
    import asyncio
    from siruk.mcp_server import mcp

    async def go():
        names = {t.name for t in await mcp.list_tools()}
        assert {"export_catalogue", "catalogue_audit", "save_catalogue_export"} <= names
        r = await mcp.call_tool("export_catalogue", {"limit": 1})
        return json.loads(r.content[0].text)
    d = asyncio.run(go())
    assert d["total"] == 2 and d["more"] and len(d["rows"]) == 1
    assert "about_this_item" not in d["rows"][0]           # compact by default
