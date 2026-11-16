"""The restock check (cost update + highest-of-three price recheck) — offline."""
import copy

import pytest

from siruk import payload as P
from siruk import pricecheck, restock


class FakeHafo:
    """387957 is on hafo at `price`; nothing else is."""

    def __init__(self, price, discount=False):
        self.price, self.discount = price, discount

    def find(self, sku, brand_id, cost=0):
        if sku != "387957" or self.price is None:
            return None, None, "not on hafo"
        listing = {"id": 1, "slug": "gemon-chunks", "discount": 5 if self.discount else None}
        return listing, {"id": 9, "sku": sku, "price": self.price, "wholesale_price": 1300}, ""

    def change(self, lid, row):
        return {"price": row["price"]}


@pytest.fixture
def shop(fake, monkeypatch):
    """fake catalogue + hafo at 2100 (= ours); zoovet/nemo pages answer from `pages`."""
    pages = {}
    state = {"hafo": FakeHafo(2100)}
    monkeypatch.setattr(restock, "PacedHafo", lambda: state["hafo"])
    monkeypatch.setattr(restock, "_pause", lambda: None)
    monkeypatch.setattr(restock.lookups, "zoovet", lambda url=None, **kw: {"price": pages[url]})
    monkeypatch.setattr(restock.lookups, "nemo", lambda url=None, **kw: {"price": pages[url]})
    monkeypatch.setattr(restock.export, "records", lambda: [
        {"product_id": fake.product["id"], "sku": v["sku"], "accounting_code": v.get("accounting_code")}
        for v in fake.product["variants"]])
    fake.product["variants"][1]["accounting_code"] = "0353"
    fake.pages, fake.state = pages, state
    return fake


def run(lines, urls=None):
    return {r["sku"]: r for r in restock.check(restock.load_lines(lines), urls=urls or {})}


def test_cost_change_and_raise_from_hafo(shop):
    shop.state["hafo"] = FakeHafo(2300)
    r = run(["0352=1400"])["387957"]
    assert (r["cost_status"], r["new_cost"], r["price_status"], r["highest"]) == ("COST CHANGE", 1400, "RAISE", 2300)
    assert restock.fixes([r]) == {874: {"387957": {
        "cost_price": 1400, "price": 2300, "price_source_url": "https://hafo.am/products/gemon-chunks"}}}


def test_same_cost_and_match_changes_nothing(shop):
    r = run(["387957=1300"])["387957"]
    assert (r["cost_status"], r["price_status"]) == ("same", "match") and restock.fixes([r]) == {}


def test_highest_of_three_wins(shop):
    shop.pages.update({"https://zoovet.am/x": 2500, "https://www.nemo.am/x": 2200})
    urls = {"387957": {"zoovet": "https://zoovet.am/x", "nemo": "https://www.nemo.am/x"}}
    r = run(["0352=1300"], urls)["387957"]
    assert (r["price_status"], r["highest"], r["highest_source"]) == ("RAISE", 2500, "zoovet")
    assert restock.fixes([r])[874]["387957"]["price_source_url"] == "https://zoovet.am/x"


def test_lower_only_when_every_shop_is_settled(shop):
    shop.state["hafo"] = FakeHafo(2000)
    r = run(["0352=1300"])["387957"]                      # zoovet / nemo have no confirmed page
    assert r["price_status"] == "CHECK BY HAND" and "price" not in restock.fixes([r]).get(874, {}).get("387957", {})
    r = run(["0352=1300"], {"387957": {"zoovet": "none", "nemo": "none"}})["387957"]
    assert r["price_status"] == "LOWER" and restock.fixes([r])[874]["387957"]["price"] == 2000


def test_price_source_url_is_a_confirmed_page(shop):
    shop.state["hafo"] = FakeHafo(None)
    shop.product["variants"][0]["price_source_url"] = "https://zoovet.am/y"
    shop.pages["https://zoovet.am/y"] = 2250
    r = run(["0352=1300"])["387957"]
    assert (r["hafo"], r["zoovet"], r["price_status"], r["highest"]) == ("not sold", 2250, "RAISE", 2250)


def test_flags_block_the_write(shop):
    assert run(["0352=1600"])["387957"]["cost_status"] == "COST FLAGGED"          # +23 %
    shop.state["hafo"] = FakeHafo(3000)
    assert run(["0352=1300"])["387957"]["price_status"] == "PRICE FLAGGED"        # +43 %
    shop.state["hafo"] = FakeHafo(2300, discount=True)
    r = run(["0352=1300"])["387957"]
    assert r["price_status"] == "not checked" and "discount" in r["flags"]
    shop.product["variants"][0]["price"] = 1400
    shop.state["hafo"] = FakeHafo(1400)
    r = run(["0352=1450"])["387957"]                                              # cost above the sale price
    assert r["cost_status"] == "COST FLAGGED" and restock.fixes([r]) == {}


def test_unknown_and_ambiguous_codes(shop):
    assert run(["9999=100"])[""]["cost_status"] == "NOT IN SIRUK"
    shop.product["variants"][1]["accounting_code"] = "0352"
    assert restock.check(restock.load_lines(["0352=1300"]), urls={})[0]["cost_status"] == "AMBIGUOUS"


def test_loose_variants_follow_the_bag(shop):
    kg = copy.deepcopy(shop.product["variants"][0])
    kg.update(id=1032, sku="387957-KG", content="1000.000", price=2000, cost_price=1040, is_default=False)
    shop.product["variants"].append(kg)
    rows = run(["0352=1120/kg"])                          # 1.25 kg bag at 1,120 per kg = 1,400
    assert rows["387957"]["new_cost"] == 1400
    assert (rows["387957-KG"]["role"], rows["387957-KG"]["new_cost"], rows["387957-KG"]["cost_status"]) == (
        "1 kg", 1120, "COST CHANGE")
    assert set(restock.fixes(list(rows.values()))[874]) == {"387957", "387957-KG"}


def test_apply_goes_through_the_guarded_put(shop):
    res = restock.apply(874, {"387957": {"cost_price": 1400, "price": 2300}}, dry_run=True)
    assert {(d["field"], d["new"]) for d in res[0].diff} == {("cost_price", 1400), ("price", 2300)} and not shop.writes
    with pytest.raises(P.PayloadError, match="below cost"):
        restock.apply(874, {"387957": {"cost_price": 2100}}, dry_run=True)


def test_load_lines(tmp_path):
    f = tmp_path / "lines.csv"
    f.write_text("code,cost,per\n0352,1400,\n0353,\"1,120\",kg\n", encoding="utf-8")
    assert restock.load_lines([str(f), "0354=90/kg"]) == [
        {"code": "0352", "cost": 1400.0, "per": "pack"}, {"code": "0353", "cost": 1120.0, "per": "kg"},
        {"code": "0354", "cost": 90.0, "per": "kg"}]
    with pytest.raises(P.PayloadError):
        restock.load_lines(["nonsense"])


def test_hafo_listing_cache_is_per_day(fake, monkeypatch, tmp_path):
    import json, os, time
    monkeypatch.setattr(pricecheck, "CACHE", str(tmp_path))
    monkeypatch.setattr(pricecheck.lookups, "_script", lambda name: object())
    path = tmp_path / "hafo-price-cache.json"
    path.write_text(json.dumps({"387957": [{"id": 1}]}), encoding="utf-8")
    assert pricecheck.Hafo().cache                         # today's file is used
    old = time.time() - 3 * 86400
    os.utime(path, (old, old))
    assert pricecheck.Hafo().cache == {}                   # an older one is not
