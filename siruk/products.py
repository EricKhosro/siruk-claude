"""Product reads and the guarded writes — the Python twins of find-product.sh,
show-product.sh, create-product.sh, add-variant.sh, set-variant.sh and
rename-product.sh, shared by the CLI, the TUI and the MCP server.

Every write: GET fresh → build the body through siruk.payload → invariants
(no variant id dropped, default count right) → PUT/POST → read back. With
dry_run=True it stops before the write and returns the body and the diff.
PUT /products/<id> REPLACES the whole variants array, which is why nothing here
ever sends a hand-written body.

On a price-types server (siruk.payload.server_model) a variant carries `prices` rows instead of a flat
price: get() adds the website price back as price / compare_at_price / min_allowed_price, and set-variant
saves through PUT /product-variants/<id> so no sibling is re-sent.
"""
import json, os
from dataclasses import dataclass, field

from siruk import client as _client
from siruk import payload as P
from siruk import seo
from siruk.config import CACHE

PayloadError = P.PayloadError


class DuplicateError(PayloadError):
    def __init__(self, name, matches):
        self.matches = matches
        super().__init__(f"the catalogue already has products like '{name}': "
                         + "; ".join(f"{m['id']} {m['name']}" for m in matches)
                         + " — add the row as a variant, or force a separate product")


@dataclass
class WriteResult:
    action: str
    product_id: object
    dry_run: bool
    body: dict
    diff: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    after: dict | None = None
    request: tuple | None = None   # (method, path, body) of the write, set by _put

    def as_dict(self):
        return {"action": self.action, "product_id": self.product_id, "dry_run": self.dry_run,
                "written": not self.dry_run, "diff": self.diff, "warnings": self.warnings,
                "body": self.body, "after": summary(self.after) if self.after else None}


def _c():
    return _client.default()


def _snapshot(pid, tag, data):
    os.makedirs(CACHE, exist_ok=True)
    with open(os.path.join(CACHE, f"product-{pid}-{tag}.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)


# ------------------------------------------------------------------- reads ----
def find(text, max_pages=5):
    """GET /products?search= (the only filter the API honours; others return everything).
    15 a page; the first max_pages pages."""
    rows = _c().paginate(f"/products?search={_client.quote(text)}", max_pages=max_pages)
    return [{"id": p.get("id"), "name": p.get("name"), "brand": p.get("brand"),
             "categories": p.get("categories") or [], "slug": p.get("slug")}
            for p in rows]


def get(pid, lang=None):
    return P.add_flat_prices((_c().get(f"/products/{int(pid)}", lang=lang) or {}).get("data") or {})


def margin(price, cost):
    if not cost or not price:
        return None
    return round((price - cost) / price * 100, 1)


def prices_by_code(v):
    """{type code: {price, compare_at_price, min_allowed_price, barcode}} of a GET variant; a flat-price
    server's variant has just its website price."""
    if isinstance(v.get("prices"), list):
        return {r.get("price_type_code") or f"type-{r.get('price_type_id')}":
                {k: P._amd(r.get(k)) if k != "barcode" else r.get(k) for k in P.ROW_FIELDS} for r in v["prices"]}
    return {P.WEBSITE: {**{k: P.website_price(v, k) for k in P.FLAT_PRICE_KEYS}, "barcode": None}}


def variant_row(v):
    price = P.website_price(v)
    return {"id": v.get("id"), "sku": v.get("sku"), "label": v.get("name"),
            "size": v.get("size_label"), "sale_mode": v.get("sale_mode"),
            "price": price, "prices": prices_by_code(v), "cost": v.get("cost_price"),
            "margin_pct": margin(price, v.get("cost_price")),
            "below_cost": bool(v.get("cost_price")) and (price or 0) <= (v.get("cost_price") or 0),
            "stock": v.get("available_quantity"), "default": bool(v.get("is_default")),
            "barcode": v.get("barcode"), "accounting_code": v.get("accounting_code"),
            "price_source_url": v.get("price_source_url"), "images": len(v.get("images") or []),
            "attribute_values": v.get("attribute_values") or {},
            "options": {l.get("attributeName"): l.get("label") for l in v.get("attribute_value_labels") or []
                        if l.get("role") == "option"},
            "attributes": {l.get("attributeName"): l.get("label") for l in v.get("attribute_value_labels") or []
                           if l.get("role") != "option"},
            "stock_levels": v.get("stock_levels") or [],
            "image_urls": [m.get("originalUrl") or m.get("url") for m in v.get("images_media") or []]}


def summary(p):
    """A compact view of a product GET — what the CLI table, the TUI and MCP show."""
    return {"id": p.get("id"), "name": p.get("name"), "slug": p.get("slug"),
            "brand_id": p.get("brand_id"), "brand": p.get("brand_name") or p.get("brand"),
            "category_ids": p.get("category_ids"),
            "product_type": p.get("attribute_family_name") or p.get("attribute_family_id"),
            "attribute_family_id": p.get("attribute_family_id"),
            "variants": [variant_row(v) for v in p.get("variants") or []]}


# -------------------------------------------------------------------- diff ----
DIFF_SKIP = ("sort_order",)


def _price_view(v, codes):
    """A variant's price fields as flat keys: the website price as price / compare_at_price / min_allowed_price
    (what the diff and its readers have always shown) and each other type as prices.<code>."""
    rows = v.get("prices")
    if not isinstance(rows, list):
        return {}
    view = {k: P.website_price({"prices": rows}, k) for k in P.FLAT_PRICE_KEYS}
    for r in rows:
        if not P._is_website(r):
            code = r.get("price_type_code") or codes.get(r.get("price_type_id")) or f"type-{r.get('price_type_id')}"
            view[f"prices.{code}"] = {k: P._amd(r.get(k)) if k != "barcode" else r.get(k) or None for k in P.ROW_FIELDS}
    return view


def diff_variants(before, after):
    """[{sku, field, old, new}] between a GET's variants and a body's variants (by sku)."""
    old = {v.get("sku"): v for v in before}
    codes = {t["id"]: c for c, t in P.price_types().items()} if any(isinstance(v.get("prices"), list) for v in after) else {}
    codes.update({r["price_type_id"]: r["price_type_code"] for v in before for r in v.get("prices") or []
                  if r.get("price_type_code")})   # a type deactivated since still has its row
    out = []
    for v in after:
        o = old.pop(v.get("sku"), None)
        if o is None:
            out.append({"sku": v.get("sku"), "field": "(new variant)", "old": None,
                        "new": {**{k: v[k] for k in ("name", "cost_price", "content") if k in v},
                                "price": P.website_price(v), **{k: x for k, x in _price_view(v, codes).items()
                                                               if k.startswith("prices.")}}})
            continue
        o = {k: x for k, x in o.items() if k != "prices"} | _price_view(o, codes)
        v = {k: x for k, x in v.items() if k != "prices"} | _price_view(v, codes)
        for gone in sorted(set(o) - set(v)):
            if gone.startswith("prices."):
                out.append({"sku": v.get("sku"), "field": gone, "old": o[gone], "new": None})
        for k, nv in v.items():
            if k in DIFF_SKIP or k == "id":
                continue
            ov = o.get(k)
            if k == "attribute_values":
                ov = {str(a): sorted(ids) for a, ids in (ov or {}).items() if ids}
                nv = {str(a): sorted(ids) for a, ids in (nv or {}).items() if ids}
            if k == "images":
                ov = [i if isinstance(i, int) else (i or {}).get("id") for i in ov or []]
            if _norm(ov) != _norm(nv):
                out.append({"sku": v.get("sku"), "field": k, "old": ov, "new": nv})
    for sku in old:
        out.append({"sku": sku, "field": "(variant removed)", "old": sku, "new": None})
    return out


def _norm(x):
    if isinstance(x, float) and x.is_integer():
        return int(x)
    if isinstance(x, str):
        try:
            f = float(x)
            return int(f) if f.is_integer() else f
        except ValueError:
            return x or None
    return x if x not in ("", []) else None


def _check_invariants(before, body, added=0):
    old_ids = {v["id"] for v in before["variants"] if v.get("id")}
    now_ids = {v["id"] for v in body["variants"] if v.get("id")}
    if old_ids - now_ids:
        raise PayloadError(f"internal: variant ids {sorted(old_ids - now_ids)} would be dropped — refusing to PUT")
    if len(body["variants"]) != len(before["variants"]) + added:
        raise PayloadError("internal: variant count would change unexpectedly — refusing to PUT")
    if sum(1 for v in body["variants"] if v.get("is_default")) != 1:
        raise PayloadError("internal: payload must have exactly one default variant")


def _put(pid, before, body, action, dry_run, warnings, added=0, only_id=None):
    """only_id: on a price-types server save just that variant (PUT /product-variants/<id>, no is_default),
    so a price edit never re-sends its siblings."""
    _check_invariants(before, body, added)
    diff = diff_variants(before["variants"], body["variants"])
    for k in ("name", "slug"):
        if body.get(k) != before.get(k):
            diff.insert(0, {"sku": None, "field": k, "old": before.get(k), "new": body.get(k)})
    res = WriteResult(action, pid, dry_run, body, diff, warnings)
    path, sent = f"/products/{pid}", body
    one = next((v for v in body["variants"] if v.get("id") == only_id), None) if only_id else None
    if one and P.server_model(before) == P.PRICE_TYPES:
        path, sent = f"/product-variants/{one['id']}", {k: x for k, x in one.items() if k != "is_default"}
    res.request = ("PUT", path, sent)
    if dry_run:
        return res
    _snapshot(pid, "put", body)
    _c().put(path, sent)
    res.after = get(pid)
    _snapshot(pid, "after", res.after)
    return res


# ------------------------------------------------------------------ writes ----
def check_payload(data):
    """Dry validation of a create payload, or of one variant against an existing product
    ({"product_id": …, "variant": {…}}) — `product-types.py --check`. Returns warnings."""
    warns = []
    if "product_id" in data:
        P.put_body(get(data["product_id"]), data.get("variant"), warnings=warns)
    else:
        P.post_body(data, warnings=warns)
    return warns


def create(payload, dry_run=False, force=False, allow_below_cost=None, allow_no_image=None):
    """create-product.sh: pre-flight, duplicate-name search, post_body, POST, read back."""
    if not (payload.get("name") and payload.get("slug") and isinstance(payload.get("category_ids"), list)
            and payload["category_ids"]):
        raise PayloadError("payload needs name, slug and a non-empty category_ids array")
    variants = payload.get("variants") or []
    if not variants or not all(v.get("sku") and (P.website_price(v) or 0) > 0 for v in variants):
        raise PayloadError("every variant needs sku and price (the pack price)")
    warns = P.price_guard(variants, allow_below_cost)
    P.image_guard(variants, allow=allow_no_image)
    name = payload["name"] if isinstance(payload["name"], str) else payload["name"].get("en")
    if not force:
        hits = find(name)
        if hits:
            raise DuplicateError(name, hits)
    body = P.post_body(payload, warnings=warns)
    brand = seo.brand_name(body.get("brand_id"))
    if brand:
        body["meta"] = seo.meta("en", brand, name)   # ru / hy meta comes with each translate
    diff = [{"sku": v["sku"], "field": "(new variant)", "old": None,
             "new": {**{k: v.get(k) for k in ("name", "cost_price", "content")}, "price": P.website_price(v)}}
            for v in body["variants"]]
    res = WriteResult("create", None, dry_run, body, diff, warns)
    if dry_run:
        return res
    made = _c().post("/products", body) or {}
    res.product_id = (made.get("data") or {}).get("id")
    res.warnings += [f"image alt set on media {m}" for m in seo.set_image_alts(res.product_id)]
    res.after = get(res.product_id)
    _snapshot(res.product_id, "after", res.after)
    return res


def add_variant(pid, variant, dry_run=False, allow_below_cost=None, allow_no_image=None):
    """add-variant.sh: GET → append → nothing dropped → PUT → read back."""
    if not isinstance(variant, dict):
        raise PayloadError("the variant must be a single object")
    if not (variant.get("sku") and (P.website_price(variant) or 0) > 0):
        raise PayloadError("variant needs sku and price (the pack price)")
    warns = P.price_guard([variant], allow_below_cost)
    before = get(pid)
    if not before:
        raise PayloadError(f"product {pid} not found")
    _snapshot(pid, "before", before)
    P.image_guard([variant], before.get("variants") or [], allow=allow_no_image)
    body = P.put_body(before, variant, warnings=warns)
    res = _put(int(pid), before, body, "add_variant", dry_run, warns, added=1)
    if not dry_run:
        seo.set_image_alts(pid)
    return res


def update_variant(pid, sku, patch, replace_attrs=False, dry_run=False, allow_below_cost=None):
    """set-variant.sh: patch one variant in place. Stock is not patchable (use siruk.stock)."""
    if not isinstance(patch, dict) or not patch:
        raise PayloadError("patch must be a non-empty JSON object")
    for k in P.MERCH_REFUSED:
        if k in patch:
            raise PayloadError(f"'{k}' belongs to the PM / the nightly jobs — an import never sends it")
    before = get(pid)
    if not before:
        raise PayloadError(f"product {pid} not found")
    _snapshot(pid, "before", before)
    cur = next((v for v in before["variants"] if v.get("sku") == sku), None)
    if cur is None:
        raise PayloadError(f"product {pid} has no variant with sku {sku}")
    warns = []
    if any(k in patch for k in ("price", "cost_price", "prices")):
        rows = cur.get("prices")
        kept = rows if isinstance(rows, list) else [{"price_type_code": P.WEBSITE, "price": P.website_price(cur)}]
        merged = {**patch, "sku": sku, "cost_price": patch.get("cost_price", cur.get("cost_price"))}
        only = None if "cost_price" in patch else P.set_codes(patch)
        warns += P.price_guard([merged], allow_below_cost, kept, only)
        if only is not None:
            checked = set(P.below_cost([merged], kept, only))
            warns += [f"{b} is already below cost on the server; not changed by this edit"
                      for b in P.below_cost([merged], kept) if b not in checked]
    body = P.put_body(before, patch_sku=sku, patch=patch, replace_attrs=replace_attrs, warnings=warns)
    return _put(int(pid), before, body, "update_variant", dry_run, warns, only_id=cur.get("id"))


def rename(pid, name, slug=None, dry_run=False):
    """rename-product.sh. The name carries neither the brand nor the pack size (rule 12)."""
    if P.SIZE_IN_NAME.search(name or ""):
        raise PayloadError(f"name '{name}' ends in a pack size — the size belongs in the variant only")
    before = get(pid)
    if not before:
        raise PayloadError(f"product {pid} not found")
    _snapshot(pid, "before", before)
    warns = []
    body = P.put_body(before, warnings=warns)
    body["name"] = name
    if slug:
        body["slug"] = slug
    brand = seo.brand_name(before.get("brand_id"))
    if brand:
        body["meta"] = seo.meta("en", brand, name)
        seo.keep_meta_image(body, before)                     # a meta PUT without it clears the SEO image
    res = _put(int(pid), before, body, "rename", dry_run, warns)
    if not dry_run:
        seo.set_image_alts(pid)
    return res
