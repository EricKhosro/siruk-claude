"""Turn what a person types into the Ops object it names: exactly one, or a refusal listing the candidates.

Each function returns the API's own object. GET /goods is paged (`{items, total, page, pageSize}`);
GET /locations and GET /suppliers answer bare arrays.
"""
import re, urllib.parse

from siruk.ops import client as _ops
from siruk.payload import PayloadError

UUID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", re.I)
MAX_PAGES = 200


def _is_uuid(ref):
    return bool(UUID.fullmatch(str(ref).strip()))


def one(ref, kind, rows, describe):
    if len(rows) == 1:
        return rows[0]
    if not rows:
        raise PayloadError(f"no {kind} matches {ref!r}")
    raise PayloadError(f"{len(rows)} {kind}s match {ref!r}; use the id: " + "; ".join(describe(r) for r in rows[:10]))


_one = one   # the old name, kept for code that already imports it


def variant(ref):
    ref = str(ref).strip()
    if _is_uuid(ref):
        return _ops.default().get(f"/goods/{urllib.parse.quote(ref, safe='')}")
    want, rows = ref.lower(), []
    for page in range(1, MAX_PAGES + 1):
        r = _ops.default().get("/goods", {"q": ref, "page": page}) or {}
        items = r.get("items") or []
        for g in items:
            codes = [g.get("sku"), g.get("barcode"), g.get("accountingCode"),
                     *[b.get("code") for b in g.get("extraBarcodes") or []]]
            if any(c is not None and str(c).lower() == want for c in codes):
                rows.append(g)
        if not items or page * int(r.get("pageSize") or len(items)) >= int(r.get("total") or 0):
            break
    else:
        raise PayloadError(f"too many matches for {ref!r} (more than {MAX_PAGES} pages): narrow the query")
    return one(ref, "good", rows, lambda g: f"{g.get('variantId')} {g.get('sku')} "
                f"{(g.get('productName') or {}).get('en') or ''} {g.get('label') or ''}".strip())


# A document of this many lines or more reads the whole goods list once (GET /goods, 200 a page: ~9 calls
# for the catalogue) instead of one GET per line. 380 lines went from ~380 paced calls to ~9 (2026-11-19).
BULK_FROM = 20
PAGE_MAX = 200


class Catalogue:
    """Every good in Ops, read once, answering `variant(ref)` from memory with the same matching as
    `variant()`: a variant id, or an exact SKU, barcode, accounting code or extra barcode. A ref the
    list doesn't settle (absent, or several goods) falls back to `variant()`, so the answer and its
    refusal are the same as one lookup per line."""

    def __init__(self, goods):
        self.by_id, self.by_code = {}, {}
        for g in goods:
            if g.get("variantId"):
                self.by_id[str(g["variantId"]).lower()] = g
            codes = {g.get("sku"), g.get("barcode"), g.get("accountingCode"),
                     *[b.get("code") for b in g.get("extraBarcodes") or []]}
            for c in codes:
                if c is not None:
                    self.by_code.setdefault(str(c).lower(), []).append(g)

    @classmethod
    def load(cls):
        goods = []
        for page in range(1, MAX_PAGES + 1):
            r = _ops.default().get("/goods", {"page": page, "pageSize": PAGE_MAX}) or {}
            items = r.get("items") or []
            goods += items
            if not items or page * int(r.get("pageSize") or len(items)) >= int(r.get("total") or 0):
                return cls(goods)
        raise PayloadError(f"the goods list has more than {MAX_PAGES} pages")

    def variant(self, ref):
        key = str(ref).strip().lower()
        if _is_uuid(key):
            hit = self.by_id.get(key)
        else:
            rows = self.by_code.get(key) or []
            hit = rows[0] if len(rows) == 1 else None
        return hit if hit is not None else variant(ref)


def variant_lookup(count):
    """`variant` for a few refs; a `Catalogue` read once when there are `count` >= BULK_FROM of them."""
    return Catalogue.load().variant if count >= BULK_FROM else variant


def location(ref):
    ref = str(ref).strip()
    rows = _ops.default().get("/locations") or []
    want = ref.lower()
    hit = [x for x in rows if (x.get("id") or "").lower() == want] if _is_uuid(ref) else \
          [x for x in rows if (x.get("code") or "").lower() == want]
    return one(ref, "location", hit, lambda x: f"{x.get('id')} {x.get('code')}")


def supplier(ref):
    ref = str(ref).strip()
    rows = _ops.default().get("/suppliers") or []
    want = ref.lower()
    if _is_uuid(ref):
        hit = [x for x in rows if (x.get("id") or "").lower() == want]
    else:
        hit = [x for x in rows if x.get("tin") and str(x["tin"]).lower() == want] or \
              [x for x in rows if (x.get("name") or "").strip().lower() == want]
    return one(ref, "supplier", hit, lambda x: f"{x.get('id')} {x.get('name')} {x.get('tin') or ''}".strip())
