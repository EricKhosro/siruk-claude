"""`siruk-mcp` — the Siruk admin as MCP tools (stdio).

Reads are free. Every write tool takes `confirm` (default false): without it the
tool returns the exact body and the field diff and writes nothing; call again
with confirm=true once the user agrees. The same siruk.products / translations /
stock / media code as the CLI enforces the rules. Deliberately absent: deletes,
a raw-API tool, and the below-cost / no-image / force overrides — those need the
user's explicit say-so and stay in the CLI (`siruk … --allow-below-cost`).
"""
import functools, json, os

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations

from siruk import client as _client
from siruk import config, lookups, media, products, refdata, stock, translations
from siruk.payload import PayloadError

INSTRUCTIONS = """Siruk PetShop admin (production: api.siruk.am). Rules that matter here (CLAUDE.md):
- Search before create: find_products first; an existing product gets the row as a variant.
- Sale price comes from hafo (hafo_lookup, price_source must be "variant") or a confirmed zoovet/nemo
  match — never markup or arithmetic, and always above cost (the server-side tools refuse otherwise).
- Pack size is measure_type + content (g/ml/pcs) + pack_count, never in the product name; the name
  never contains the brand either. New variants: initial_stock 10.
- Every write tool is a dry run unless confirm=true. Show the user the diff and get a yes first.
- Stock changes only through the stock_* tools, with a note. No deletes exist here."""

mcp = MCPServer("siruk", title="Siruk admin", instructions=INSTRUCTIONS)

READ = ToolAnnotations(read_only_hint=True, open_world_hint=True)
WRITE = ToolAnnotations(read_only_hint=False, destructive_hint=True, idempotent_hint=False, open_world_hint=True)


def _clean(fn):
    """Rule refusals and API errors reach the model as their message (ToolError); any other
    exception is a crash and mcp 2.x hides its text."""
    @functools.wraps(fn)
    def wrap(*a, **kw):
        try:
            return fn(*a, **kw)
        except PayloadError as e:
            raise ToolError(f"refused by a rule: {e}") from None
        except _client.ApiError as e:
            raise ToolError(str(e)) from None
    return wrap


def _write(res):
    d = res.as_dict()
    if d["dry_run"]:
        d["next_step"] = "nothing was written — show the user this diff; call again with confirm=true to write"
    return d


# ------------------------------------------------------------------- reads ----
@mcp.tool(annotations=READ)
@_clean
def account_status() -> dict:
    """Which admin this server talks to and whether the token works."""
    u = (_client.default().get("/account") or {}).get("currentUser") or {}
    return {"api": config.api_base(), "production": config.is_production(),
            "account": u.get("email"), "role": u.get("role")}


@mcp.tool(annotations=READ)
@_clean
def list_reference(kind: str) -> list:
    """Live ids. kind: brands | categories | types (product types) | attributes."""
    return refdata.ids(kind)


@mcp.tool(annotations=READ)
@_clean
def find_products(text: str) -> list:
    """Search products by name (the only search the API has). Run before creating anything."""
    return products.find(text)


@mcp.tool(annotations=READ)
@_clean
def get_product(product_id: int, lang: str = "en", full: bool = False) -> dict:
    """A product with its variants (price, cost, margin, stock, codes, options).
    lang: en | ru | hy. full=true returns the raw GET body."""
    p = products.get(product_id, lang=lang)
    if not p:
        raise ToolError(f"product {product_id} not found")
    return p if full else products.summary(p)


@mcp.tool(annotations=READ)
@_clean
def get_product_type(type_id: int) -> dict:
    """A product type (attribute family): its attributes with role (option/attribute) and flags."""
    return refdata.product_type(type_id)


@mcp.tool(annotations=READ)
@_clean
def get_translation(product_id: int, lang: str) -> dict:
    """The ru/hy name and variant texts next to the English ones."""
    return translations.current(product_id, lang)


@mcp.tool(annotations=READ)
@_clean
def validate_payload(payload: dict) -> dict:
    """Check a create payload (or {"product_id": id, "variant": {...}}) against the live product
    type without writing. Returns {ok, warnings} or raises with the reasons."""
    return {"ok": True, "warnings": products.check_payload(payload)}


@mcp.tool(annotations=READ)
@_clean
def stock_movements(variant_id: int) -> list:
    """The stock ledger of one variant (receipts, sales, write-offs, corrections)."""
    return stock.movements(variant_id) or []


@mcp.tool(annotations=READ)
@_clean
def hafo_lookup(code: str, name: str = "") -> dict:
    """hafo.am by article code (name only as a fallback, then confirmed=false). Usable as a sale
    price only when confirmed is true and price_source is "variant"."""
    return lookups.hafo(code, name)


@mcp.tool(annotations=READ)
@_clean
def zoovet_search(search: str = "", brand: str = "", url: str = "", limit: int = 10) -> dict:
    """zoovet.am candidates by name (Russian), a brand slug, or one product url. Never confirmed —
    a human confirms identity (brand, line, flavour, pack) before a price or photo is used."""
    return lookups.zoovet(search=search or None, brand=brand or None, url=url or None, limit=limit)


@mcp.tool(annotations=READ)
@_clean
def nemo_search(search: str = "", brand: str = "", url: str = "", limit: int = 10) -> dict:
    """nemo.am candidates by name, brand slug or product url. Never confirmed (see zoovet_search)."""
    return lookups.nemo(search=search or None, brand=brand or None, url=url or None, limit=limit)


# ------------------------------------------------------------------ writes ----
@mcp.tool(annotations=WRITE)
@_clean
def create_product(payload: dict, confirm: bool = False) -> dict:
    """Create a product. payload: name (no brand, no size), slug (with brand), brand_id,
    attribute_family_id, category_ids (leaves), variants [{sku, name, price, cost_price,
    measure_type, content, pack_count, initial_stock: 10, images, attribute_values, barcode,
    accounting_code, price_source_url}]. Refused if a similar name already exists."""
    return _write(products.create(payload, dry_run=not confirm, force=False,
                                  allow_below_cost=False, allow_no_image=False))


@mcp.tool(annotations=WRITE)
@_clean
def add_variant(product_id: int, variant: dict, confirm: bool = False) -> dict:
    """Append one new variant (no id) to an existing product; every other variant is re-sent unchanged."""
    return _write(products.add_variant(product_id, variant, dry_run=not confirm,
                                       allow_below_cost=False, allow_no_image=False))


@mcp.tool(annotations=WRITE)
@_clean
def update_variant(product_id: int, sku: str, patch: dict, replace_attrs: bool = False,
                   confirm: bool = False) -> dict:
    """Patch one variant in place (price, cost_price, name, texts, barcode, accounting_code,
    price_source_url, attribute_values by id or code, images, content…). Not stock."""
    return _write(products.update_variant(product_id, sku, patch, replace_attrs, dry_run=not confirm,
                                          allow_below_cost=False))


@mcp.tool(annotations=WRITE)
@_clean
def rename_product(product_id: int, name: str, slug: str = "", confirm: bool = False) -> dict:
    """Rename a product (en). The name carries neither the brand nor the pack size."""
    return _write(products.rename(product_id, name, slug or None, dry_run=not confirm))


@mcp.tool(annotations=WRITE)
@_clean
def set_translation(product_id: int, lang: str, translation: dict, confirm: bool = False) -> dict:
    """Store a ru or hy translation: {"name": "…", "variants": {"<sku>": {"about_this_item": "…",
    "ingredient_information": "…", "feeding_instructions": "…"}}}. Keys left out keep their text."""
    res = translations.set_translation(product_id, lang, translation, dry_run=not confirm)
    d = _write(res)
    d["after"] = None
    return d


@mcp.tool(annotations=WRITE)
@_clean
def stock_receive(variant_id: int, quantity: float, note: str, unit_cost: float | None = None,
                  confirm: bool = False) -> dict:
    """Receive stock into the main warehouse (needs a note)."""
    return stock.receive(variant_id, quantity, note, unit_cost, dry_run=not confirm)


@mcp.tool(annotations=WRITE)
@_clean
def stock_write_off(variant_id: int, quantity: float, reason: str, note: str, confirm: bool = False) -> dict:
    """Write stock off. reason: damaged | lost | expired | write_off."""
    return stock.write_off(variant_id, quantity, reason, note, dry_run=not confirm)


@mcp.tool(annotations=WRITE)
@_clean
def stock_set(variant_id: int, on_hand: float, reason: str, note: str, confirm: bool = False) -> dict:
    """Set the on-hand count. reason: correction | damaged | lost | found | expired | write_off."""
    return stock.set_count(variant_id, on_hand, reason, note, dry_run=not confirm)


@mcp.tool(annotations=WRITE)
@_clean
def upload_media(source: str, folder: str, keep_alpha: bool = False, confirm: bool = False) -> dict:
    """Upload an image (local path or url) into products/<brand-slug>/<type>, logos, categories or
    banners, verify it is readable, and return its media id for a variant's images."""
    return media.upload(source, folder, keep_alpha=keep_alpha, dry_run=not confirm)


# --------------------------------------------------------------- resources ----
def _ref(name):
    with open(os.path.join(config.ROOT, "reference", name), encoding="utf-8") as f:
        return f.read()


@mcp.resource("siruk://reference/product-types", mime_type="application/json",
              description="Product types with their attributes, roles and flags (snapshot)")
def product_types_resource() -> str:
    return _ref("product-types.json")


@mcp.resource("siruk://reference/attribute-values", mime_type="application/json",
              description="The closed attribute-value menu: code → {attribute_id, values: label → id}")
def attribute_values_resource() -> str:
    return _ref("attribute-values.json")


def main():
    mcp.run("stdio")


if __name__ == "__main__":
    main()
