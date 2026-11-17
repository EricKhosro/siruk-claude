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
        if path.startswith("/price-types"):
            raise _client.ApiError(404, "GET", path, '{"message": "Not found.", "error": "not_found"}')
        if path.startswith("/stock?"):   # StockController::index meta.stock_in_ops (Controllers/Admin/Catalog)
            return {"data": [], "meta": {"stock_in_ops": getattr(self, "stock_in_ops", False)}}
        if path.startswith("/attribute-families/"):
            return {"data": copy.deepcopy(PTYPE)}
        if path.startswith("/attributes"):
            return {"data": copy.deepcopy(ATTRS)}
        if path.startswith("/products/"):
            return {"data": copy.deepcopy(self.product)}
        if path.startswith("/products?search="):
            return {"data": [{"id": 874, "name": PRODUCT["name"], "brand": "Gemon", "categories": []}],
                    "meta": {"last_page": 1}}
        if path.startswith("/brands"):
            return {"data": [{"id": 18, "name": "Gemon"}]}
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
    _reset_payload_caches()
    monkeypatch.setattr("siruk.products.CACHE", str(tmp_path))
    for var in ("ALLOW_BELOW_COST", "ALLOW_NO_IMAGE", "ALLOW_NO_SIZE", "FORCE"):
        monkeypatch.delenv(var, raising=False)
    yield fc
    _client.set_default(None)
    _reset_payload_caches()


def _reset_payload_caches():
    P._types.clear()
    P._attrs = None
    P._model = P._ptypes = None


# siruk-web SingleProductResource::typePrices (Resources/Admin/Catalog): `prices` rows and no flat price, floats.
# PriceTypeController::index?forSelect=1 (Controllers/Admin/Catalog) answers {data: [{id, code, name}]}.
PRICE_TYPES = [{"id": 1, "code": "website", "name": "Website"}, {"id": 2, "code": "store", "name": "Store"},
               {"id": 3, "code": "glovo", "name": "Glovo"}, {"id": 4, "code": "yandex", "name": "Yandex"}]


def _price_row(row_id, type_id, price, compare=None, barcode=None):
    t = next(t for t in PRICE_TYPES if t["id"] == type_id)
    return {"id": row_id, "price_type_id": type_id, "price_type_code": t["code"], "price_type_name": t["name"],
            "price": float(price), "compare_at_price": compare, "min_allowed_price": None, "barcode": barcode}


def pt_variant(i, sku, flavor, price=2100, cost=1300, default=False, rows=()):
    v = variant(i, sku, flavor, price, cost, default)
    for k in ("price", "compare_at_price", "min_allowed_price"):
        v.pop(k, None)
    v["prices"] = [_price_row(i * 10, 1, price)] + [_price_row(i * 10 + n + 1, *r) for n, r in enumerate(rows)]
    return v


PT_PRODUCT = {**PRODUCT, "variants": [pt_variant(1030, "387957", "Salmon", default=True, rows=[(2, 1900, None, "20001")]),
                                      pt_variant(1031, "387967", "Veal")]}


class FakePriceTypesClient(FakeClient):
    """The price-types backend: GET /price-types answers, variant `prices` are rows, writes are applied."""

    def __init__(self):
        super().__init__()
        self.product = copy.deepcopy(PT_PRODUCT)
        self.next_id = 5000

    def get(self, path, lang=None, **kw):
        if path.startswith("/price-types"):
            return {"data": copy.deepcopy(PRICE_TYPES)}
        return super().get(path, lang=lang, **kw)

    def _rows(self, rows):
        out = []
        for r in rows:
            self.next_id += 1
            out.append(_price_row(r.get("id") or self.next_id, r["price_type_id"], r["price"], r.get("compare_at_price"),
                                  r.get("barcode")))
        return out

    def request(self, method, path, body=None, lang=None, **kw):
        method = method.upper()
        if method == "GET":
            return self.get(path, lang=lang)
        self.writes.append((method, path, body))
        if method == "PUT" and path.startswith("/product-variants/"):
            vid = int(path.rsplit("/", 1)[1])
            for v in self.product["variants"]:
                if v["id"] == vid:
                    v.update({k: x for k, x in body.items() if k != "prices"})
                    v["prices"] = self._rows(body["prices"])
            return {"data": {"id": vid}}
        if method == "PUT" and path.startswith("/products/"):
            variants = []
            for nv in body["variants"]:
                old = next((v for v in self.product["variants"] if v.get("id") == nv.get("id")), {})
                self.next_id += 1
                variants.append({**old, **{k: x for k, x in nv.items() if k != "prices"}, "id": old.get("id") or self.next_id,
                                 "prices": self._rows(nv["prices"])})
            self.product = {**self.product, **{k: v for k, v in body.items() if k != "variants"}, "variants": variants}
            return {"data": {"id": self.product["id"]}}
        return super().request(method, path, body, lang)


@pytest.fixture
def fake_pt(monkeypatch, tmp_path):
    fc = FakePriceTypesClient()
    _client.set_default(fc)
    _reset_payload_caches()
    monkeypatch.setattr("siruk.products.CACHE", str(tmp_path))
    for var in ("ALLOW_BELOW_COST", "ALLOW_NO_IMAGE", "ALLOW_NO_SIZE", "FORCE"):
        monkeypatch.delenv(var, raising=False)
    yield fc
    _client.set_default(None)
    _reset_payload_caches()


@pytest.fixture
def ops_fake(monkeypatch, tmp_path):
    from ops_fakes import FakeOpsClient
    from siruk.ops import client as _ops
    for var in ("SIRUK_OPS_TOKEN", "SIRUK_OPS_API"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("SIRUK_OPS_TOKEN_FILE", str(tmp_path / ".ops-token"))
    monkeypatch.setenv("SIRUK_CONFIG", str(tmp_path / "no-config.json"))
    fc = FakeOpsClient()
    _ops.set_default(fc)
    yield fc
    _ops.set_default(None)


@pytest.fixture
def admin_fake(monkeypatch, tmp_path):
    from admin_fakes import FakeAdminClient
    monkeypatch.delenv("SIRUK_LANG", raising=False)
    monkeypatch.setenv("SIRUK_CONFIG", str(tmp_path / "no-config.json"))
    fc = FakeAdminClient()
    _client.set_default(fc)
    yield fc
    _client.set_default(None)
