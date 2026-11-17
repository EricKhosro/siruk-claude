"""What the CLI may write to the admin API: a second lock behind the admin role.

GET is free. A write is allowed only under the areas below, and never on the never-list,
which is checked first. Paths are matched whole-segment and case-insensitively, after the same
hygiene as the Ops policy. Routes: siruk-web/backend/routes/admin.php.
"""
import re

from siruk.ops.policy import _clean

AREAS = ("/promotions", "/vouchers", "/segments", "/campaigns", "/campaign-templates", "/delivery-zones",
         "/delivery-settings", "/faq-categories", "/faqs", "/post-categories", "/authors", "/vets", "/posts",
         "/pages", "/search-settings", "/search-synonyms", "/search-rules", "/algolia", "/categories", "/brands",
         "/attributes", "/attribute-values", "/attribute-families", "/price-types", "/product-reviews",
         "/product-review-reports", "/product-variants", "/listing-groups", "/suppliers", "/supplier-products",
         "/warehouses")
ACTIONS = tuple(re.compile(p) for p in (
    r"/orders/[^/]+/update-(payment-)?status", r"/update-order-payment-type", r"/payments/[^/]+/check-status",
    r"/customers/[^/]+/adjust-balance", r"/search/index/rebuild", r"/products/[^/]+/(discontinue|merge)",
    r"/ops/orders/[^/]+/resend"))
BY_HAND = "not from the CLI: do it in the admin panel"
NEVER = (
    (re.compile(r"/(login|admin-users|api-keys)|/(logout|create-new-admin-user|update-current-user)$"
                r"|/update-admin-user(/|$)"), "sign-in, admin users and API keys are not for the CLI"),
    (re.compile(r"/(clear-logs|medias-clear-unused|web-push-tokens)$"), BY_HAND),
    (re.compile(r"/products(/[^/]+)?$"), "product bodies go through `siruk create` and the payload rules"),
    (re.compile(r"/stock(/|$)"), "stock lives in Ops: use `siruk ops`"),
    (re.compile(r"/medias"), "media goes through `siruk media`"),
    (re.compile(r"/(global-data|reposition|replicate-record)$"), BY_HAND),
)


def allowed(method, path):
    """None when the CLI may send it, else the reason it may not."""
    method = str(method).upper()
    if method in ("GET", "HEAD"):
        return None
    p = _clean(path)
    if p is None:
        fixed = _clean(re.sub(r"/{2,}", "/", str(path or "")))
        if fixed is None:
            return f"{BY_HAND} (unusable path {str(path)[:80]!r})"
        return allowed(method, fixed) or f"use the canonical path {fixed}"
    for rule, why in NEVER:
        if rule.match(p):
            return why
    if method == "DELETE" and re.fullmatch(r"/customers/[^/]+", p):
        return "customers are not deleted from the CLI"
    if not (any(p == a or p.startswith(a + "/") for a in AREAS) or any(r.fullmatch(p) for r in ACTIONS)):
        return f"{BY_HAND} (not in the areas the CLI may write)"
    # the server redirects a non-canonical path, and a redirected write may apply nothing
    return None if path == p else f"use the canonical path {p}"
