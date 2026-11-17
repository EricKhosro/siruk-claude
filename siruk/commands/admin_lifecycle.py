"""`siruk admin variants|products|suppliers|supplier-products|warehouses|ops`: archive, restore, move and merge,
discontinue, supplier and warehouse upkeep, the Ops proxies (reads) and the order resend.

Every write is a dry run until `--apply <code>`; the plan (siruk/admin/lifecycle.py) reads the live records and
refuses what the server refuses, and rule 9a, before the guard. A move or merge dry run prints both products.
"""
import urllib.parse

from siruk import client as _client, output
from siruk.admin import guard, lifecycle as L, resource as R
from siruk.payload import PayloadError

ROLES = "admin"
RESEND_ROLES = "developer, admin"
VALUES = '{"12": [38]}'


def _body(arg, what="the body"):
    from siruk.cli import _load_json
    try:
        return _load_json(arg)
    except (OSError, ValueError) as e:
        raise PayloadError(f"{what} is not JSON: {e}")


def _page_arg(s):
    if s == "all" or s.isdigit():
        return s
    raise PayloadError("--page is a number or 'all'")


def _cell(v):
    return v if v is None or isinstance(v, (str, int, float, bool)) else str(v)


def _run(a, plan, tier, verify):
    steps, summary, shown = plan
    return guard.run(a, steps=steps, summary=summary, tier=tier, shown_state=shown, verify=verify)


def _list(a, res, cols, params=None):
    """One page (or --page all) of a list endpoint as a table; --json prints the API's answer."""
    if a.json and a.page != "all":
        output.dump(R.list_page(res, page=a.page, params=params))
        return 0
    rows = R.list_rows(res, page=a.page, params=params)
    if a.json:
        output.dump({"data": rows})
        return 0
    output.table([{k: _cell(v) for k, v in r.items()} for r in rows], cols)
    return 0


def _read(path, params=None):
    q = urllib.parse.urlencode({k: v for k, v in (params or {}).items() if v is not None})
    return _client.default().get(path + ("?" + q if q else ""))


def _rows(r):
    return (r.get("data") if isinstance(r, dict) else r) or []


# ----------------------------------------------------------- variants ----
def variants_list(a):
    cols = [("id", "id"), ("name", "name"), ("product_id", "product"), ("product_name", "product name"),
            ("sale_mode", "mode"), ("cost_price", "cost")]
    return _list(a, L.VARIANTS, cols, {"product_id": a.product, "q": a.search})


def variants_archived(a):
    r = _read("/product-variants/archived", {"product_id": a.product})
    if a.json:
        output.dump(r)
        return 0
    output.table([{k: _cell(v) for k, v in x.items()} for x in _rows(r)],
                 [("id", "id"), ("product_id", "product"), ("product_name", "product name"), ("name", "name"),
                  ("sku", "sku"), ("released_sku", "released from"), ("archived_at", "archived")])
    return 0


def variants_archive(a):
    return _run(a, L.plan_archive(a.id, a.product), "irreversible",
                f"siruk admin variants archived --product {a.product}")


def variants_restore(a):
    return _run(a, L.plan_restore(a.id, a.product), "draft", "siruk admin variants archived")


def variants_release_sku(a):
    return _run(a, L.plan_release_sku(a.id, a.product), "draft", "siruk admin variants archived")


def _targets(r, json_out):
    if json_out:
        output.dump(r)
        return 0
    output.table([{k: _cell(v) for k, v in x.items()} for x in _rows(r)],
                 [("id", "id"), ("name", "name"), ("brand", "brand"), ("attribute_family_id", "type"),
                  ("variants_count", "variants")])
    return 0


def variants_move_targets(a):
    return _targets(_read(f"/product-variants/{L._id(a.id, 'variant id')}/move-targets"), a.json)


def variants_move(a):
    plan = L.plan_move(a.id, a.product, a.to, _body(a.values, "--values"), a.drop_values)
    return _run(a, plan, "irreversible", f"siruk show {L._id(a.to, '--to')}")


# ----------------------------------------------------------- products ----
def products_merge_targets(a):
    return _targets(_read(f"/products/{L._id(a.id, 'product id')}/merge-targets"), a.json)


def products_discontinue(a):
    return _run(a, L.plan_discontinue(a.id), "irreversible", f"siruk show {a.id}")


def products_merge(a):
    plan = L.plan_merge(a.id, a.to, _body(a.variants, "--variants"), a.drop_values)
    return _run(a, plan, "irreversible", f"siruk show {L._id(a.to, '--to')}")


# ---------------------------------------------------------- suppliers ----
def suppliers_list(a):
    cols = [("id", "id"), ("code", "code"), ("name", "name"), ("is_active", "active"), ("products_count", "products"),
            ("ops_stock_source", "ops source")]
    return _list(a, L.SUPPLIERS, cols, {"q": a.search, "is_active": {"yes": 1, "no": 0}.get(a.active)})


def suppliers_create(a):
    return _run(a, L.plan_supplier_create(_body(a.body)), "draft", "siruk admin suppliers list")


def suppliers_update(a):
    return _run(a, L.plan_supplier_update(a.id, _body(a.body)), "draft", f"siruk admin suppliers show {a.id}")


def suppliers_products(a):
    res = R.Resource("supplier product", f"/suppliers/{L._id(a.id, 'supplier id')}/products", label="supplier_sku")
    if a.json and a.page != "all":
        output.dump(R.list_page(res, page=a.page, params={"q": a.search}))
        return 0
    rows = R.list_rows(res, page=a.page, params={"q": a.search})
    if a.json:
        output.dump({"data": rows})
        return 0
    output.table([{"id": x.get("id"), "supplier_sku": x.get("supplier_sku"), "sku": (x.get("variant") or {}).get("sku"),
                   "product": (x.get("variant") or {}).get("product_name"), "cost": x.get("cost_price"),
                   "stock": x.get("stock_qty"), "active": x.get("is_active"), "ops": x.get("ops_managed")}
                  for x in rows],
                 [("id", "id"), ("supplier_sku", "supplier sku"), ("sku", "sku"), ("product", "product"),
                  ("cost", "cost"), ("stock", "stock"), ("active", "active"), ("ops", "from Ops")])
    return 0


def suppliers_add_product(a):
    return _run(a, L.plan_add_supplier_product(a.id, _body(a.body)), "draft", f"siruk admin suppliers products {a.id}")


def suppliers_stock_check(a):
    return _run(a, L.plan_stock_check(a.id), "real-world", f"siruk admin suppliers show {a.id}")


def suppliers_ops_stock_sync(a):
    return _run(a, L.plan_ops_stock_sync(a.id), "real-world", f"siruk admin suppliers show {a.id}")


def sp_set(a):
    return _run(a, L.plan_supplier_product_set(a.supplier, a.id, _body(a.body)), "draft",
                f"siruk admin suppliers products {a.supplier}")


def sp_rm(a):
    return _run(a, L.plan_supplier_product_rm(a.supplier, a.id), "irreversible",
                f"siruk admin suppliers products {a.supplier}")


def sp_set_stock(a):
    return _run(a, L.plan_supplier_product_stock(a.supplier, a.id, a.qty), "draft",
                f"siruk admin suppliers products {a.supplier}")


# --------------------------------------------------------- warehouses ----
def warehouses_list(a):
    r = _read("/warehouses")
    if a.json:
        output.dump(r)
        return 0
    output.table([{k: _cell(v) for k, v in x.items()} for x in _rows(r)],
                 [("id", "id"), ("code", "code"), ("name", "name"), ("type", "type"), ("supplier_name", "supplier"),
                  ("lead_days", "lead days"), ("is_active", "active"), ("variants_with_stock", "variants"),
                  ("on_hand_total", "on hand")])
    return 0


def warehouses_create(a):
    return _run(a, L.plan_warehouse_create(_body(a.body)), "draft", "siruk admin warehouses list")


def warehouses_update(a):
    return _run(a, L.plan_warehouse_update(a.id, _body(a.body)), "draft", "siruk admin warehouses list")


# ------------------------------------------------- the Ops proxies (reads) ----
def ops_purchase_orders(a):
    r = _read("/ops/purchase-orders", {"status": a.status, "kind": a.kind, "q": a.search})
    if a.json:
        output.dump(r)
        return 0
    output.table([{**x, "web": ", ".join(str(w.get("number")) for w in x.get("web_orders") or []),
                   "cost": output.money(x.get("known_cost_amd")) + ("" if x.get("all_costs_known") else " (partial)")}
                  for x in _rows(r)],
                 [("number", "number"), ("kind", "kind"), ("status", "status"), ("web", "web orders"),
                  ("line_count", "lines"), ("cost", "known cost"), ("placed_at", "placed"), ("id", "id")])
    return 0


def ops_purchase_order(a):
    r = _read(f"/ops/purchase-orders/{L.uuid_arg(a.id, 'a purchase order id')}")
    if a.json:
        output.dump(r)
        return 0
    po = r.get("data", r) if isinstance(r, dict) else {}
    print(f"{po.get('number')}  {po.get('kind')}  {po.get('status')}  supplier {po.get('supplier_name')}  "
          f"placed {po.get('placed_at')}  ref {po.get('external_ref')}")
    output.table([{**x, "cost": output.money(x.get("unit_cost_amd"))} for x in po.get("lines") or []],
                 [("sku", "sku"), ("product_name", "product"), ("label", "label"), ("quantity", "qty"),
                  ("cost", "unit cost"), ("hafo_in_stock", "supplier has it")])
    return 0


def ops_locations(a):
    r = _read("/ops/locations")
    if a.json:
        output.dump(r)
        return 0
    output.table(_rows(r), [("id", "id"), ("code", "code"), ("name", "name"), ("kind", "kind"), ("is_active", "active"),
                            ("siruk_warehouse_code", "website warehouse"), ("connector", "connector")])
    return 0


def ops_location_stock(a):
    r = _read(f"/ops/locations/{L.uuid_arg(a.id, 'a location id')}/stock", {"q": a.search, "page": a.page})
    if a.json:
        output.dump(r)
        return 0
    output.table(_rows(r), [("sku", "sku"), ("product_name", "product"), ("label", "label"), ("stock_unit", "unit"),
                            ("on_hand", "on hand"), ("reserved", "reserved"), ("available", "available"),
                            ("in_stock", "in stock")])
    meta = r.get("meta") or {} if isinstance(r, dict) else {}
    print(f"\npage {meta.get('page')} ({meta.get('total')} goods)")
    return 0


def ops_resend_order(a):
    return _run(a, L.plan_resend(a.id), "real-world", f"siruk admin orders show {a.id}")


# ------------------------------------------------------------ register ----
def register(reg):
    def paged(p, search=True):
        if search:
            p.add_argument("--search")
        p.add_argument("--page", type=_page_arg, help="a page number, or 'all'")

    def cmd(path, fn, help, api, tier="read", roles=ROLES, example=""):
        return reg.command(("admin", *path), fn, help, api=api, tier=tier, roles=roles, example=example)

    p = cmd(("variants", "list"), variants_list, "list variants (id, name, product), one page or --page all",
            ["GET /product-variants"], example="siruk admin variants list --product 874")
    p.add_argument("--product", help="only this product's variants")
    paged(p)
    p = cmd(("variants", "archived"), variants_archived, "archived variants (newest 500), with the SKU each released",
            ["GET /product-variants/archived"], example="siruk admin variants archived --product 874")
    p.add_argument("--product")
    p = cmd(("variants", "archive"), variants_archive,
            "archive a variant, or delete it for good when it has no history; "
            "refused for the last variant or reserved stock",
            ["GET /products/:id", "DELETE /product-variants/:id"], "irreversible",
            example="siruk admin variants archive 4512 --product 874")
    p.add_argument("id")
    p.add_argument("--product", required=True, help="the variant's product (read to show what the server will do)")
    p = cmd(("variants", "restore"), variants_restore, "restore an archived variant",
            ["GET /product-variants/archived", "POST /product-variants/:id/restore"], "draft",
            example="siruk admin variants restore 4512")
    p.add_argument("id")
    p.add_argument("--product", help="narrow the archived list to this product")
    p = cmd(("variants", "release-sku"), variants_release_sku, "free the SKU of an archived variant for reuse",
            ["GET /product-variants/archived", "POST /product-variants/:id/release-sku"], "draft",
            example="siruk admin variants release-sku 4512")
    p.add_argument("id")
    p.add_argument("--product", help="narrow the archived list to this product")
    p = cmd(("variants", "move-targets"), variants_move_targets, "products a variant can move into, same brand first",
            ["GET /product-variants/:id/move-targets"], example="siruk admin variants move-targets 4512")
    p.add_argument("id")
    p = cmd(("variants", "move"), variants_move,
            "move a variant into another product; the dry run shows both products, rule 9a is checked first",
            ["GET /products/:id", "GET /attribute-families/:id", "POST /product-variants/:id/move"], "irreversible",
            example=f"siruk admin variants move 4512 --product 874 --to 880 --values '{VALUES}'")
    p.add_argument("id")
    p.add_argument("--product", required=True, help="the variant's current product")
    p.add_argument("--to", required=True, help="the target product")
    p.add_argument("--drop-values", action="store_true",
                   help="allow dropping the variant's descriptive values the target does not receive")
    p.add_argument("--values", default="{}",
                   help="JSON (file, '-' or inline) {attribute id or code: [value ids]} on the target's type")

    p = cmd(("products", "merge-targets"), products_merge_targets,
            "products a product can be merged into, same brand first", ["GET /products/:id/merge-targets"],
            example="siruk admin products merge-targets 874")
    p.add_argument("id")
    p = cmd(("products", "discontinue"), products_discontinue, "mark a product discontinued",
            ["GET /products/:id", "POST /products/:id/discontinue"], "irreversible",
            example="siruk admin products discontinue 874")
    p.add_argument("id")
    p = cmd(("products", "merge"), products_merge,
            "fold a mis-split product into another: every variant moves; "
            "the dry run shows both products, rule 9a is checked first",
            ["GET /products/:id", "GET /attribute-families/:id", "POST /products/:id/merge"], "irreversible",
            example="siruk admin products merge 874 --to 880 --variants "
                    f"'{{\"4512\": {{\"attribute_values\": {VALUES}}}}}'")
    p.add_argument("id", help="the source product")
    p.add_argument("--to", required=True, help="the target product")
    p.add_argument("--drop-values", action="store_true",
                   help="allow dropping the variants' descriptive values the target does not receive")
    p.add_argument("--variants", required=True,
                   help="JSON (file, '-' or inline) "
                        '{"<source variant id>": {"attribute_values": {...}}} for every live variant')

    p = cmd(("suppliers", "list"), suppliers_list, "list suppliers", ["GET /suppliers"],
            example="siruk admin suppliers list --active yes")
    p.add_argument("--search")
    p.add_argument("--active", choices=("yes", "no"))
    p.add_argument("--page", type=_page_arg, help="a page number, or 'all'")
    R.register_crud(reg, "suppliers", L.SUPPLIERS, verbs=("show", "delete"), roles=ROLES)
    sample = '{"code": "hafo", "name": "hafo"}'
    p = cmd(("suppliers", "create"), suppliers_create, "create a supplier from a JSON body",
            ["GET /suppliers", "POST /suppliers"], "draft", example=f"siruk admin suppliers create '{sample}'")
    p.add_argument("body", help="JSON (file, '-' or inline)")
    p = cmd(("suppliers", "update"), suppliers_update,
            "update a supplier from a JSON body: code and name required, keys left out stay as they are",
            ["GET /suppliers/:id", "PUT /suppliers/:id"], "draft", example=f"siruk admin suppliers update 3 '{sample}'")
    p.add_argument("id")
    p.add_argument("body", help="JSON (file, '-' or inline): code, name and the keys to change")
    p = cmd(("suppliers", "products"), suppliers_products, "a supplier's product rows, 25 a page",
            ["GET /suppliers/:id/products"], example="siruk admin suppliers products 3 --search royal")
    p.add_argument("id")
    paged(p)
    p = cmd(("suppliers", "add-product"), suppliers_add_product,
            "link a variant to a supplier (product_variant_id and terms)",
            ["GET /suppliers/:id", "POST /suppliers/:id/products"], "draft",
            example="siruk admin suppliers add-product 3 '{\"product_variant_id\": 4512, \"cost_price\": 9250}'")
    p.add_argument("id")
    p.add_argument("body", help="JSON (file, '-' or inline)")
    p = cmd(("suppliers", "stock-check"), suppliers_stock_check,
            "record that every stock level of a supplier was read now (unchanged levels stay fresh)",
            ["GET /suppliers/:id", "POST /suppliers/:id/stock-check"], "real-world",
            example="siruk admin suppliers stock-check 3")
    p.add_argument("id")
    p = cmd(("suppliers", "ops-stock-sync"), suppliers_ops_stock_sync, "read a supplier's stock from Siruk Ops now",
            ["GET /suppliers/:id", "POST /suppliers/:id/ops-stock-sync"], "real-world",
            example="siruk admin suppliers ops-stock-sync 3")
    p.add_argument("id")

    p = cmd(("supplier-products", "set"), sp_set, "change a supplier product row (only the keys sent)",
            ["GET /suppliers/:id/products", "PUT /supplier-products/:id"], "draft",
            example="siruk admin supplier-products set 17 '{\"is_active\": false}' --supplier 3")
    p.add_argument("id")
    p.add_argument("body", help="JSON (file, '-' or inline)")
    p.add_argument("--supplier", required=True, help="the row's supplier (the row is read from its list)")
    p = cmd(("supplier-products", "rm"), sp_rm, "remove a supplier product row (not one Siruk Ops keeps)",
            ["GET /suppliers/:id/products", "DELETE /supplier-products/:id"], "irreversible",
            example="siruk admin supplier-products rm 17 --supplier 3")
    p.add_argument("id")
    p.add_argument("--supplier", required=True)
    p = cmd(("supplier-products", "set-stock"), sp_set_stock, "set a supplier row's stock quantity",
            ["GET /suppliers/:id/products", "PUT /supplier-products/:id/stock"], "draft",
            example="siruk admin supplier-products set-stock 17 12 --supplier 3")
    p.add_argument("id")
    p.add_argument("qty", help="whole number from 0")
    p.add_argument("--supplier", required=True)

    cmd(("warehouses", "list"), warehouses_list, "the site's own warehouses (not the Ops locations)",
        ["GET /warehouses"], example="siruk admin warehouses list")
    wh = '{"code": "main", "type": "own", "name": {"en": "Main", "hy": "", "ru": ""}, "lead_days": 0}'
    p = cmd(("warehouses", "create"), warehouses_create, "create a warehouse from a JSON body",
            ["GET /warehouses", "POST /warehouses"], "draft", example=f"siruk admin warehouses create '{wh}'")
    p.add_argument("body", help="JSON (file, '-' or inline)")
    p = cmd(("warehouses", "update"), warehouses_update,
            "update a warehouse from a JSON body: name and lead_days required, code and type never change",
            ["GET /warehouses", "PUT /warehouses/:id"], "draft",
            example="siruk admin warehouses update 2 '{\"name\": {\"en\": \"Main\"}, \"lead_days\": 1}'")
    p.add_argument("id")
    p.add_argument("body", help="JSON (file, '-' or inline)")

    p = cmd(("ops", "purchase-orders"), ops_purchase_orders, "Ops purchase orders, newest first (at most 200)",
            ["GET /ops/purchase-orders"], example="siruk admin ops purchase-orders --status placed")
    p.add_argument("--status", choices=("draft", "placed", "delivered", "invoiced", "cancelled"))
    p.add_argument("--kind", choices=("restock", "web_order"))
    p.add_argument("--search")
    p = cmd(("ops", "purchase-order"), ops_purchase_order, "one Ops purchase order with its lines",
            ["GET /ops/purchase-orders/:uuid"],
            example="siruk admin ops purchase-order 0b7e1c52-6f1c-4a90-b417-2a9000000000")
    p.add_argument("id", help="the Ops id (uuid)")
    cmd(("ops", "locations"), ops_locations, "Ops locations (warehouses, shop, supplier feeds)", ["GET /ops/locations"],
        example="siruk admin ops locations")
    p = cmd(("ops", "location-stock"), ops_location_stock, "one Ops location's goods, 50 a page, in Ops units",
            ["GET /ops/locations/:uuid/stock"],
            example="siruk admin ops location-stock 2a900000-6f1c-4a90-b417-2a9000000000 --search royal")
    p.add_argument("id", help="the Ops location id (uuid)")
    p.add_argument("--search")
    p.add_argument("--page", type=int)
    p = cmd(("ops", "resend-order"), ops_resend_order, "send an order's failed Ops pushes to Siruk Ops again",
            ["GET /orders/:id", "POST /ops/orders/:id/resend"], "real-world", RESEND_ROLES,
            example="siruk admin ops resend-order 5120")
    p.add_argument("id")
