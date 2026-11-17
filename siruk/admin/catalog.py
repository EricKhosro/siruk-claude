"""Admin catalogue structure: the Resources for categories, brands, attributes, attribute values, product
types (the API's attribute families), price types, reviews and review reports, and the rules checked
before any write.

Rules: a price-type code matches `^[a-z0-9-]+$`; the `website` price type is never deleted, re-coded or
deactivated; a category with subcategories or products is not deleted (the count is shown); a brand's
logo and a category's image are media ids; a product type's attributes carry a role.
"""
import re

from siruk import client as _client
from siruk.admin import resource
from siruk.payload import PayloadError

CTRL = "backend/app/Http/Controllers/Admin/Catalog/"
PRICE_CODE = re.compile(r"[a-z0-9-]+")
WEBSITE = "website"
ROLES = ("option", "attribute")   # app/Enums/AttributeRole.php
FLAGS = ("is_required", "is_filterable", "show_on_product_card")
ENUMS = {"default_sale_mode": ("pack", "weight"),                          # app/Enums/SaleMode.php
         "measure_type": ("mass", "volume", "count"),                      # app/Enums/MeasureType.php
         "unit_price_basis": ("per_kg", "per_100g", "per_l", "per_100ml")}  # app/Enums/UnitPriceBasis.php

CATEGORIES = resource.Resource("category", "/categories", required=("name", "slug"), translatable=True,
                               source=CTRL + "CategoryController.php (validatedData)")
BRANDS = resource.Resource("brand", "/brands", required=("name", "slug"), translatable=True,
                           source=CTRL + "BrandController.php (validatedData)")
ATTRIBUTES = resource.Resource("attribute", "/attributes", required=("name", "code"), translatable=True,
                               source=CTRL + "AttributeController.php (validatedData)")
ATTRIBUTE_VALUES = resource.Resource("attribute value", "/attribute-values", required=("attribute_id", "value"),
                                     translatable=True, label="label",
                                     source=CTRL + "AttributeValueController.php (validatedData)")
PRODUCT_TYPES = resource.Resource("product type", "/attribute-families", required=("name", "code"),
                                  translatable=True, source=CTRL + "AttributeFamilyController.php (validatedData)")
PRICE_TYPES = resource.Resource("price type", "/price-types", required=("code", "name"), translatable=True,
                                source="backend/app/Http/Requests/Admin/Catalog/PriceTypeRequest.php")
REVIEWS = resource.Resource("review", "/product-reviews", required=(), deletable=False, label="title",
                            source=CTRL + "ProductReviewController.php (update)")
REVIEW_REPORTS = resource.Resource("review report", "/product-review-reports", required=(), deletable=False,
                                   label="description",
                                   source=CTRL + "ProductReviewReportController.php (update)")


def media_ids(body, *keys):
    """A media field is the id `siruk media` gives, never a URL, a path or a name."""
    for k in keys:
        v = body.get(k)
        if v is not None and (isinstance(v, bool) or not isinstance(v, int)):
            raise PayloadError(f"{k} is a media id (a whole number), got {v!r}: upload with `siruk media` first")


def category_body(body):
    media_ids(body, "image", "featured_image")


def category_update(cur, body):
    # validatedData sets list_as_products from the request, so a body without it turns it off
    if cur.get("list_as_products") and "list_as_products" not in body:
        raise PayloadError("a category body without list_as_products turns it off: send "
                           "\"list_as_products\": true to keep it")


def brand_body(body):
    media_ids(body, "image")


def value_body(body):
    media_ids(body, "image")


def price_type_body(body):
    code = body.get("code")
    if code is not None and not (isinstance(code, str) and PRICE_CODE.fullmatch(code) and len(code) <= 40):
        raise PayloadError(f"price-type code {code!r} must match ^[a-z0-9-]+$ (lower case, digits, hyphens; up to 40)")
    if body.get("is_active", True) not in (True, False, 0, 1, "0", "1"):
        raise PayloadError(f"is_active must be true or false, got {body['is_active']!r}")


def price_type_update(cur, body):
    if cur.get("code") != WEBSITE:
        return
    if body.get("code") != WEBSITE:
        raise PayloadError("the website price type cannot be re-coded")
    if body.get("is_active", True) in (False, 0, "0"):
        raise PayloadError("the website price type cannot be deactivated")


def price_type_delete(cur):
    if cur.get("code") == WEBSITE:
        raise PayloadError("the website price type cannot be deleted")


def _plural(n, one, many):
    return f"{n} {one if n == 1 else many}"


def _products_count(cur):
    """The show endpoint leaves productsCount at 0, so the flat search listing (withCount) is asked."""
    if cur.get("productsCount"):
        return cur["productsCount"]
    name = cur.get("name")
    try:
        rows = resource.list_rows(CATEGORIES, search=name) if isinstance(name, str) and name else []
    except _client.ApiError:
        return None
    return next((r.get("productsCount") for r in rows if r.get("id") == cur.get("id")), None)


def category_delete(cur):
    kids = cur.get("children") or []
    if not (kids or cur.get("deleteLocked")):
        return
    uses = []
    if kids:
        uses.append(_plural(len(kids), "subcategory", "subcategories"))
    n = _products_count(cur)
    if n:
        uses.append(_plural(n, "product", "products"))
    elif not kids:
        uses.append("products or promotions")
    raise PayloadError(f"category {cur.get('id')} still has {', '.join(uses)}: move or remove them first")


def product_type_body(body):
    for k, allowed in ENUMS.items():
        if body.get(k) is not None and body[k] not in allowed:
            raise PayloadError(f"{k} must be one of {', '.join(allowed)}, got {body[k]!r}")
    attrs = body.get("attributes")
    if attrs is None:
        return
    if not isinstance(attrs, list):
        raise PayloadError("attributes is a list of {id, role, is_required?, is_filterable?, show_on_product_card?}")
    seen = set()
    for i, a in enumerate(attrs):
        aid = a.get("id") if isinstance(a, dict) else None
        if isinstance(aid, bool) or not isinstance(aid, int):
            raise PayloadError(f"attributes[{i}] needs a numeric id")
        if aid in seen:
            raise PayloadError(f"attribute {aid} is listed twice")
        seen.add(aid)
        if a.get("role") not in ROLES:
            raise PayloadError(f"attribute {aid} needs a role: {' or '.join(ROLES)}")
        bad = [f for f in FLAGS if f in a and not isinstance(a[f], bool)]
        if bad:
            raise PayloadError(f"attribute {aid}: {', '.join(bad)} must be true or false")


def product_type_note(cur, body):
    """What the attributes list does to the record: it replaces the set, so a missing id is detached."""
    if "attributes" not in body:
        return ""
    now = {a.get("id"): a for a in cur.get("attributes") or []}
    sent = {a["id"]: a for a in body["attributes"] or []}
    out = [f"+{i}({a['role']})" for i, a in sent.items() if i not in now]
    out += [f"-{a.get('code') or i}" for i, a in now.items() if i not in sent]
    for i, a in sent.items():
        was = now.get(i)
        if not was:
            continue
        # is_required omitted means false; the two display flags keep their saved value
        eff = {"role": a["role"], "isRequired": a.get("is_required", False),
               "isFilterable": a.get("is_filterable", was.get("isFilterable")),
               "showOnProductCard": a.get("show_on_product_card", was.get("showOnProductCard"))}
        diff = [f"{k} {was.get(k)}→{v}" for k, v in eff.items() if was.get(k) != v]
        if diff:
            out.append(f"~{was.get('code') or i}: {', '.join(diff)}")
    return "attributes " + (", ".join(out) if out else "unchanged")


def review_update(cur, body):
    if cur.get("reply") and "reply" not in body:
        raise PayloadError("the API clears a review's reply when the body has none: send "
                           "\"reply\" with the current text (this re-stamps replied_at and the replier as you) "
                           "or null to clear it on purpose")
