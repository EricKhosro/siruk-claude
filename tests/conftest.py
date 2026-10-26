"""Offline fixtures: a fake API client with one product type and one product."""
import copy, os, sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from siruk import client as _client  # noqa: E402
from siruk import payload as P  # noqa: E402

PTYPE = {"id": 2, "name": "Wet Food", "code": "wet-food", "measureType": "mass", "defaultSaleMode": "pack",
         "attributes": [
             {"id": 3, "name": "Lifestage", "code": "lifestage", "role": "attribute", "inputType": "select",
              "isRequired": False, "position": 1},
             {"id": 5, "name": "Flavor", "code": "flavor", "role": "option", "inputType": "select",
              "isRequired": False, "position": 2}]}
ATTRS = [{"id": 3, "code": "lifestage", "name": "Lifestage", "inputType": "select",
          "values": [{"id": 27, "label": "Adult"}, {"id": 25, "label": "Puppy"}]},
         {"id": 5, "code": "flavor", "name": "Flavor", "inputType": "select",
          "values": [{"id": 38, "label": "Salmon"}, {"id": 39, "label": "Veal"}]}]


def variant(i, sku, flavor, price=2100, cost=1300, default=False):
    return {"id": i, "sku": sku, "name": f"{flavor} 1250 g", "price": price, "cost_price": cost,
            "sale_mode": "pack", "measure_type": "mass", "content": "1250.000", "pack_count": 1,
            "is_default": default, "images": [8293], "attribute_values": {"3": [27], "5": [38 if flavor == "Salmon" else 39]},
            "about_this_item": "about", "ingredient_information": "ingr", "feeding_instructions": "feed",
            "out_of_stock_policy": "deny", "track_inventory": True, "size_label": "1.25 kg",
            "available_quantity": 10, "barcode": "8009470387958", "accounting_code": "0352",
            "attribute_value_labels": [{"attributeName": "Flavor", "role": "option", "label": flavor}],
            "stock_levels": [], "images_media": [], "item_content": "server-only"}


PRODUCT = {"id": 874, "name": "All Breeds Adult Dog Chunks", "slug": "gemon-all-breeds-adult-dog-chunks",
           "category_ids": [4], "brand_id": 18, "attribute_family_id": 2, "attribute_family_name": "Wet Food",
           "is_best_seller": False, "is_on_sale": False, "is_discontinued": False, "show_unit_price": True,
           "merch_boost": 0,
           "variants": [variant(1030, "387957", "Salmon", default=True), variant(1031, "387967", "Veal")]}


class FakePacer:
    def pace(self, *a, **kw):
        pass

    def read_state(self, ch):
        return 0, 0


class FakeClient(_client.Client):
    """Routes GETs to canned data and records writes. Never opens a socket."""

    def __init__(self):
        def no_network(*a, **kw):
            raise AssertionError("a test tried to reach the network")
        super().__init__(base="https://offline.test/api/admin", token="T", opener=no_network)
        self.product = copy.deepcopy(PRODUCT)
        self.writes = []
        self.pacer = FakePacer()

    def request(self, method, path, body=None, lang=None, **kw):
        method = method.upper()
        if method == "GET":
            return self.get(path, lang=lang)
        self.writes.append((method, path, body))
        if method == "POST" and path == "/products":
            return {"data": {"id": 999}}
        if method == "PUT" and path.startswith("/products/"):
            self.product = {**self.product, **{k: v for k, v in body.items() if k != "variants"}}
            return {"data": {"id": self.product["id"]}}
        return {"data": {}}

    def get(self, path, lang=None, **kw):
        if path.startswith("/attribute-families/"):
            return {"data": copy.deepcopy(PTYPE)}
        if path.startswith("/attributes"):
            return {"data": copy.deepcopy(ATTRS)}
        if path.startswith("/products/"):
            return {"data": copy.deepcopy(self.product)}
        if path.startswith("/products?search="):
            return {"data": [{"id": 874, "name": PRODUCT["name"], "brand": "Gemon", "categories": []}],
                    "meta": {"last_page": 1}}
        if path == "/account":
            return {"currentUser": {"email": "dev@example.test", "role": "admin"}}
        raise AssertionError(f"unexpected GET {path}")

    def put(self, path, body=None, **kw):
        return self.request("PUT", path, body)

    def post(self, path, body=None, **kw):
        return self.request("POST", path, body)

    def paginate(self, path, lang=None, max_pages=200):
        return self.get(path + "&page=1").get("data")


@pytest.fixture
def fake(monkeypatch, tmp_path):
    fc = FakeClient()
    _client.set_default(fc)
    P._types.clear()
    P._attrs = None
    monkeypatch.setattr("siruk.products.CACHE", str(tmp_path))
    for var in ("ALLOW_BELOW_COST", "ALLOW_NO_IMAGE", "ALLOW_NO_SIZE", "FORCE"):
        monkeypatch.delenv(var, raising=False)
    yield fc
    _client.set_default(None)
    P._types.clear()
    P._attrs = None
