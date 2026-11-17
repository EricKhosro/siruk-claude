"""What the CLI may write to Ops: the second lock behind the server's own table.

GET is free everywhere. A write is allowed only under the areas below (the server's key table is
ops/docs/contracts/office-api-keys.md), and never on the actions that put an order in a supplier's
hands, settle a replacement, print the HDM receipt or hand out a till's secret — those stay in the
Ops app. Paths are matched whole-segment and case-insensitively (Express routes ignore case).
"""
import re, urllib.parse

WRITE_AREAS = ("/documents", "/goods", "/locations", "/stock/open-bag", "/suppliers", "/purchase-orders",
               "/einvoices", "/goods-links", "/hafo/reorder", "/catalog/sync", "/outbox", "/web-orders", "/services",
               "/shop-promotions", "/users", "/tills", "/settings", "/catalog/auto-sync")
NEVER = (re.compile(r"^/purchase-orders/[^/]+/(place|release)$"),
         re.compile(r"^/einvoices/[^/]+/acknowledge-replacement$"),
         re.compile(r"^/web-orders/[^/]+/print-hdm$"),
         re.compile(r"^/tills$"),
         re.compile(r"^/tills/[^/]+/rotate-key$"))
NOT_FROM_CLI = "not from the CLI: do it in the Ops app"


ODD = re.compile(r"[?#;\\\s\x00-\x1f\x7f]|//|%2f|%5c", re.I)


def _clean(path):
    """The path the server would route on, lower-cased; None when it is not a plain path.
    A write has no use for a query, a fragment, `;` params or an encoded slash, so any of them refuses."""
    path = str(path or "")
    decoded = urllib.parse.unquote(path)
    if not path.startswith("/") or ODD.search(path) or ODD.search(decoded) or "%" in decoded \
            or any(s in (".", "..") for s in decoded.split("/")):
        return None
    return decoded.rstrip("/").lower() or "/"


def allowed(method, path):
    """None when the CLI may send it, else the reason it may not."""
    if str(method).upper() in ("GET", "HEAD"):
        return None
    p = _clean(path)
    if p is None:
        return f"{NOT_FROM_CLI} (unusable path {str(path)[:80]!r})"
    if any(r.match(p) for r in NEVER):
        return f"{NOT_FROM_CLI} (placing or releasing an order, settling a replacement, the HDM receipt and a till's secret stay there)"
    if any(p == a or p.startswith(a + "/") for a in WRITE_AREAS):
        return None
    return NOT_FROM_CLI
