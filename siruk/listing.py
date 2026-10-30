"""Listing order (siruk-web d67fb7f8, 2026-10-27): an ordered list of brand + optional
category groups that leads every "Relevance" listing, ahead of relevance_score +
merch_boost. A product takes the first group whose brand matches and whose category
is empty or holds one of the product's categories (itself or a descendant); products
matching no group come after all of them. Category pins no longer lead Relevance.

GET /listing-groups lists it; PUT /listing-groups {"groups": [{brand_id, category_id}]}
replaces the whole list, positions from the array order. The order belongs to the
PM / the user — set it only on their ask. reference/admin-api.md → "Listing order".
"""
from siruk import client as _client
from siruk import refdata
from siruk.payload import PayloadError


def _names():
    brands = {b["id"]: b["name"] for b in refdata.ids("brands")}
    cats = {c["id"]: c for c in refdata.ids("categories")}
    return brands, cats


def _cat_label(cats, cid):
    if cid is None:
        return "(whole brand)"
    c = cats.get(cid)
    if not c:
        return f"#{cid}"
    parent = cats.get(c.get("parent_id"))
    grand = cats.get(parent.get("parent_id")) if parent else None
    return " › ".join(x["name"] for x in (grand, parent, c) if x)


def _rows(groups, brands, cats):
    return [{"position": i + 1, "brand_id": g["brand_id"], "brand": brands.get(g["brand_id"], f"#{g['brand_id']}"),
             "category_id": g.get("category_id"), "category": _cat_label(cats, g.get("category_id"))}
            for i, g in enumerate(groups)]


def _live():
    r = _client.default().get("/listing-groups") or {}
    data = r.get("data") if isinstance(r, dict) else r
    return [{"brand_id": g["brand_id"], "category_id": g.get("category_id")}
            for g in sorted(data or [], key=lambda g: g.get("position") or 0)]


def show():
    brands, cats = _names()
    return _rows(_live(), brands, cats)


def normalize(groups, brands=None, cats=None):
    """[{brand: id|name, category: id|null}] (or brand_id / category_id) → API groups.
    Brands resolve by id or exact name (case-insensitive); categories by id only, since
    names repeat across species (Dog › Food › Dry Food and Cat › Food › Dry Food)."""
    if brands is None:
        brands, cats = _names()
    by_name = {n.lower(): i for i, n in brands.items()}
    out, seen = [], set()
    for i, g in enumerate(groups):
        b = g.get("brand_id", g.get("brand"))
        bid = b if isinstance(b, int) else (int(b) if str(b).isdigit() else by_name.get(str(b).strip().lower()))
        if bid not in brands:
            raise PayloadError(f"group {i + 1}: unknown brand {b!r}")
        c = g.get("category_id", g.get("category"))
        cid = None if c in (None, "", "null") else int(c)
        if cid is not None and cid not in cats:
            raise PayloadError(f"group {i + 1}: unknown category id {c!r}")
        if (bid, cid) in seen:
            raise PayloadError(f"group {i + 1}: {brands[bid]} + {_cat_label(cats, cid)} is already in the list")
        seen.add((bid, cid))
        out.append({"brand_id": bid, "category_id": cid})
    return out


def set_groups(groups, dry_run=False, allow_empty=False):
    """Replace the whole list. Returns before / after rows; a real write is read back."""
    brands, cats = _names()
    new = normalize(groups, brands, cats)
    if not new and not allow_empty:
        raise PayloadError("an empty list clears the listing order — pass allow_empty (CLI: `listing-order clear`)")
    before = _live()
    res = {"action": "listing_order", "dry_run": dry_run, "written": False, "changed": before != new,
           "before": _rows(before, brands, cats), "after": _rows(new, brands, cats),
           "request": "PUT /listing-groups", "body": {"groups": new}}
    if dry_run or before == new:
        return res
    _client.default().put("/listing-groups", {"groups": new})
    got = _live()
    if got != new:
        raise _client.ApiError(f"listing order read back differs from what was sent: {got}")
    res["written"] = True
    return res


def add(brand, category=None, at=None, dry_run=False):
    """Insert one group at 1-based position `at` (default: the end)."""
    groups = _live()
    pos = len(groups) if at is None else max(0, min(len(groups), int(at) - 1))
    groups.insert(pos, {"brand": brand, "category": category})
    return set_groups(groups, dry_run=dry_run)


def remove(position, dry_run=False):
    groups = _live()
    if not 1 <= int(position) <= len(groups):
        raise PayloadError(f"no group at position {position} (the list has {len(groups)})")
    del groups[int(position) - 1]
    return set_groups(groups, dry_run=dry_run, allow_empty=True)
