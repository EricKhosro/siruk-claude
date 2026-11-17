"""`siruk price-types` and `siruk prices show | set` — the price types and each variant's price and barcode per type.

`set` goes through the write guard: a dry run prints the one `PUT /product-variants/<id>` and a code,
`--apply <code>` sends it once and reads the variant back. The website row has no barcode of its own;
every other type may have one. A price at or below the variant's cost is refused (CLAUDE.md rule 5) unless
`--allow-below-cost`. Needs a price-types server (the website type also works on a flat one).
"""
import re, sys

from siruk import client as _client
from siruk import output
from siruk.admin import guard as adminguard
from siruk.ops import guard
from siruk.payload import PayloadError

WRITE_PATH = re.compile(r"/(product-variants|products)/\d+")


def _policy(method, path):
    return None if method.upper() == "PUT" and WRITE_PATH.fullmatch(path) else "prices set writes one variant only"


def _variant(p, sku):
    v = next((x for x in p.get("variants") or [] if x.get("sku") == sku), None)
    if v is None:
        raise PayloadError(f"product {p.get('id')} has no variant with sku {sku}")
    return v


def cmd_price_types(a):
    try:
        rows = (_client.default().get("/price-types") or {}).get("data") or []
    except _client.ApiError as e:
        if e.status == 404:
            raise PayloadError("this server has one flat price per variant — no price types") from e
        raise
    if a.json:
        output.dump(rows)
        return 0
    output.table([{**r, "is_active": "yes" if r.get("is_active") else "no"} for r in rows],
                 [("id", "id"), ("code", "code"), ("name", "name"), ("is_active", "active"), ("sort_order", "order")])
    return 0


def cmd_show(a):
    from siruk import products
    p = products.get(a.product_id)
    if not p:
        raise PayloadError(f"product {a.product_id} not found")
    rows = []
    for v in p.get("variants") or []:
        for code, r in products.prices_by_code(v).items():
            rows.append({"variant_id": v.get("id"), "sku": v.get("sku"), "main_barcode": v.get("barcode"), "type": code,
                         "price": r["price"], "compare_at_price": r["compare_at_price"],
                         "min_allowed_price": r["min_allowed_price"], "barcode": r["barcode"]})
    if a.json:
        output.dump(rows)
        return 0
    print(f"product {p.get('id')}  {p.get('name')}")
    output.table(rows, [("variant_id", "variant"), ("sku", "sku"), ("main_barcode", "main barcode"), ("type", "type"),
                        ("price", "price"), ("compare_at_price", "compare-at"), ("min_allowed_price", "min allowed"),
                        ("barcode", "type barcode")])
    return 0


def _spec(a):
    if a.remove:
        if any(x is not None for x in (a.price, a.compare_at, a.min_allowed, a.barcode)):
            raise PayloadError("--remove takes no other value")
        return None
    spec = {k: v for k, v in (("price", a.price), ("compare_at_price", a.compare_at),
                              ("min_allowed_price", a.min_allowed), ("barcode", a.barcode)) if v is not None}
    if not spec:
        raise PayloadError("nothing to set: give --price, --compare-at, --min-allowed, --barcode or --remove")
    return spec


def _problems(variant, code, spec):
    """What a read-back shows that differs from what was asked."""
    from siruk import products
    got = products.prices_by_code(variant).get(code)
    if spec is None:
        return [f"type {code} is still there"] if got else []
    if not got:
        return [f"type {code} is missing"]
    return [f"{k} reads back as {got.get(k)!r}, asked {v!r}" for k, v in spec.items()
            if str(got.get(k)) != str(v)]


def cmd_set(a):
    from siruk import products
    spec = _spec(a)
    patch = {"prices": {a.type: spec}}
    res = products.update_variant(a.product_id, a.sku, patch, dry_run=True,
                                  allow_below_cost=True if a.allow_below_cost else None)
    if not res.diff:
        print("nothing to change")
        return 0
    for w in res.warnings:
        print(f"⚠ {w}", file=sys.stderr)
    if not a.json:
        output.diff(res.diff, sys.stderr)
    steps = [guard.Step(*res.request, label=f"{a.type} price of {a.sku}")]
    code = guard.run(a, steps=steps, summary=f"{'remove' if spec is None else 'set'} the {a.type} price of {a.sku} "
                     f"on product {a.product_id}", tier="draft", shown_state=res.diff,
                     verify=f"siruk prices show {a.product_id}", client=adminguard.writer(), policy=_policy)
    if code or not a.apply:
        return code
    bad = _problems(_variant(products.get(a.product_id), a.sku), a.type, spec)
    if bad:
        print(f"error: written, but the read-back differs: {'; '.join(bad)}", file=sys.stderr)
        return 2
    if not a.json:
        print(f"read back ok — `siruk prices show {a.product_id}`")
    return 0


def register(reg):
    reg.command(("price-types",), cmd_price_types, "the price types (website, store, glovo, …)",
                api=["GET /price-types"], example="siruk price-types")
    p = reg.command(("prices", "show"), cmd_show, "every variant's price and barcode per price type",
                    api=["GET /products/:id"], example="siruk prices show 874")
    p.add_argument("product_id", type=int)
    p = reg.command(("prices", "set"), cmd_set, "set or remove one variant's price / barcode for one price type",
                    api=["GET /products/:id", "GET /price-types", "PUT /product-variants/:id"], tier="draft",
                    example="siruk prices set 874 387957 --type store --price 2000 --barcode 20001")
    p.add_argument("product_id", type=int)
    p.add_argument("sku")
    p.add_argument("--type", required=True, metavar="CODE", help="price type code: website, store, glovo, …")
    p.add_argument("--price", type=int)
    p.add_argument("--compare-at", type=int, dest="compare_at")
    p.add_argument("--min-allowed", type=int, dest="min_allowed")
    p.add_argument("--barcode")
    p.add_argument("--remove", action="store_true", help="drop this type's row (not the website's)")
    p.add_argument("--allow-below-cost", action="store_true", help="only on the user's explicit say-so (or ALLOW_BELOW_COST=1)")
