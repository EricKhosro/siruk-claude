"""What the office reads from Ops, in the words the API uses: query parameters named as the DTOs
name them (siruk-web/ops/apps/api/src/modules/*/dto), and rows that show AMD and whole units.

Nothing here talks to the network. Money in a table is AMD (`minor_to_amd`), a quantity is humanised by
its unit; `--json` never goes through this module's formatting.
"""
import datetime, json, os, re

from siruk import config
from siruk.ops import resolve, units
from siruk.payload import PayloadError

CHANNELS = ("till", "siruk", "glovo")                         # reports/dto/report-channels.ts: SALES_CHANNELS
GROUPINGS = ("day", "variant", "payment", "priceType")        # reports/dto/sales-query.dto.ts
WEB_CHANNELS = ("siruk", "glovo")                             # prisma OrderChannel
WEB_STATUSES = ("accepted", "delivered", "cancelled", "refunded")
PREP_STATUSES = ("new", "picking", "waiting_hafo", "packed", "shipped")
FISCAL_STATUSES = ("pending", "succeeded", "failed", "unknown")
FISCAL_KINDS = ("sale", "return")
LIMITS = {"history": 1000, "sales": 200, "receipts": 200, "orders": 500}   # the DTOs' @Max
UNIT_KIND = {"g": "mass", "ml": "volume", "pcs": "count", "կգ": "mass", "հատ": "count",
             "pack": "count", "loose": "mass"}                  # the last two are a web-order line's stockUnit
BASE_UNITS = "base units"   # the column label where a row carries no unit and the number stays raw


def params(**kw):
    """Only what was given: an unset option is not sent."""
    return {k: v for k, v in kw.items() if v is not None and v != ""}


def limit(n, kind, minimum=1):
    if n is not None and not minimum <= n <= LIMITS[kind]:
        raise PayloadError(f"--limit must be between {minimum} and {LIMITS[kind]}")
    return n


def uuid(ref, what):
    if ref is not None and not resolve.UUID.fullmatch(str(ref).strip()):
        raise PayloadError(f"{what} must be an id (UUID), got {ref!r}")
    return None if ref is None else str(ref).strip()


def channels(text):
    """`till,glovo` → the one comma string the DTO splits; every channel when none is given."""
    if not text:
        return None
    names = [c.strip() for c in text.split(",") if c.strip()]
    bad = [c for c in names if c not in CHANNELS]
    if bad:
        raise PayloadError(f"unknown channel {', '.join(bad)}; one or more of {', '.join(CHANNELS)}")
    return ",".join(names)


def month(text):
    if not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", text or ""):
        raise PayloadError(f"the month looks like 2026-10, got {text!r}")
    return text


def accountant_path(out, mon, filename, today=None):
    """-o a file → that file; -o a folder (existing, or written with a trailing slash) or nothing → the server's
    file name in it (default runs/<date>/)."""
    name = os.path.basename((filename or "").replace("\\", "/"))
    if name in ("", ".", ".."):
        name = f"siruk-accountant-{mon}.xlsx"
    if out and not (os.path.isdir(out) or out.endswith(("/", os.sep))):
        return out
    return os.path.join(out or os.path.join(config.ROOT, "runs", today or datetime.date.today().isoformat()), name)


# ------------------------------------------------------------------ display ----
def amd(minor):
    """Minor units (a decimal string, or a JSON number on web orders) → AMD; None → '-'."""
    if minor is None:
        return "-"
    return units.minor_to_amd(str(int(minor)) if isinstance(minor, (int, float)) else minor)


def qty(n, unit=None):
    """A count in base units, humanised by the unit the row carries (g / ml / pcs, or the till's կգ / հատ)."""
    if n is None:
        return "-"
    kind = UNIT_KIND.get(unit)
    return units.format_quantity(n, kind) if kind else str(n)


def delta(n, unit=None):
    return ("+" if n and n > 0 else "") + qty(n, unit)


def name(x):
    """A product name: the report rows carry a string, goods and services a {en, hy, ru} object."""
    if isinstance(x, dict):
        return x.get("en") or next((v for v in x.values() if v), "")
    return x or ""


def outbox_target(topic):
    """Who a failed message goes to again: the order ping is posted to Telegram, everything else to siruk."""
    return "Telegram" if str(topic).startswith("telegram.") else "siruk"


def short(text, n=60):
    text = " ".join(str(text or "").split())
    return text if len(text) <= n else text[:n - 1] + "…"


def stock_rows(report):
    return [{"sku": r.get("sku"), "product": name(r.get("productName")), "label": r.get("label"),
             "location": r.get("locationCode"), "qty": qty(r.get("quantity"), r.get("unit")),
             "reserved": qty(r.get("reserved"), r.get("unit")), "value": amd(r.get("valueMinor"))}
            for r in report.get("rows") or []]


def history_rows(h):
    unit = (h.get("variant") or {}).get("unit")
    return [{"at": m.get("at"), "location": m.get("locationCode"), "kind": m.get("kind"),
             "document": f"{m.get('documentType')} {m.get('documentNumber')}",
             "change": delta(m.get("quantityDelta"), unit), "after": qty(m.get("quantityAfter"), unit),
             "reserved": delta(m.get("reservedDelta"), unit), "value": amd(m.get("valueDeltaMinor")),
             "value_after": amd(m.get("valueAfterMinor")), "flag": "NEGATIVE" if m.get("wentNegative") else ""}
            for m in h.get("movements") or []]


def sale_rows(sales):
    return [{"number": s.get("number"), "sold": s.get("soldAt"), "status": s.get("status"),
             "total": amd(s.get("totalMinor")),
             "paid": ", ".join(f"{p.get('method')} {amd(p.get('amountMinor'))}" for p in s.get("payments") or []),
             "flags": ", ".join(s.get("flags") or []) + (" treat" if s.get("isTreat") else "")}
            for s in sales or []]


def sale_line_rows(sale):
    return [{"name": ln.get("fiscalName"), "qty": qty(ln.get("quantity"), ln.get("unit")),
             "price": amd(ln.get("unitPriceMinor")), "discount": amd(ln.get("discountMinor")),
             "total": amd(ln.get("lineTotalMinor")),
             "returned": qty(ln["returnedQuantity"], ln.get("unit")) if ln.get("returnedQuantity") else "",
             "price_type": ln.get("priceTypeCode")} for ln in sale.get("lines") or []]


REPORT_COLUMNS = {
    "day": [("day", "day"), ("till", "till sales"), ("web", "web orders"), ("total", "total"), ("cash", "cash"),
            ("noncash", "non-cash"), ("returns", "returns"), ("net", "net")],
    "variant": [("sku", "sku"), ("product", "product"), ("label", "label"), ("qty", BASE_UNITS),
                ("revenue", "revenue"), ("cost", "cost"), ("uncosted", "uncosted lines")],
    "payment": [("method", "method"), ("count", "receipts"), ("amount", "amount")],
    "priceType": [("code", "price type"), ("lines", "lines"), ("revenue", "revenue")],
}


def sales_report_rows(report):
    kind = report.get("groupBy") or "day"
    rows = []
    for r in report.get("rows") or []:
        if kind == "day":
            rows.append({"day": r.get("day"), "till": r.get("tillSales"), "web": r.get("webOrders"),
                         "total": amd(r.get("totalMinor")), "cash": amd(r.get("cashMinor")),
                         "noncash": amd(r.get("nonCashMinor")), "returns": amd(r.get("returnsMinor")),
                         "net": amd(r.get("netMinor"))})
        elif kind == "variant":
            rows.append({"sku": r.get("sku"), "product": name(r.get("productName")), "label": r.get("label"),
                         "qty": r.get("quantity"), "revenue": amd(r.get("revenueMinor")),
                         "cost": amd(r.get("costMinor")), "uncosted": r.get("uncostedLines")})
        elif kind == "payment":
            rows.append({"method": r.get("method"), "count": r.get("count"), "amount": amd(r.get("amountMinor"))})
        else:
            rows.append({"code": r.get("code"), "lines": r.get("lines"), "revenue": amd(r.get("revenueMinor"))})
    return kind, REPORT_COLUMNS.get(kind, REPORT_COLUMNS["day"]), rows


def order_rows(orders):
    return [{"number": o.get("number"), "channel": o.get("channel"), "status": o.get("status"),
             "prep": o.get("prepStatus"), "received": o.get("receivedAt"), "total": amd(o.get("totalMinor")),
             "customer": o.get("customerName"), "phone": o.get("phone"), "receipt": o.get("saleReceiptStatus")}
            for o in orders or []]


def order_line_rows(detail):
    lines = [*(detail.get("ownLines") or []), *(detail.get("hafoLines") or [])]
    return [{"sku": ln.get("sku"), "name": ln.get("name"), "qty": qty(ln.get("quantity"), ln.get("stockUnit")),
             "price": amd(ln.get("unitPriceMinor")), "total": amd(ln.get("lineTotalMinor")),
             "gift": "gift" if ln.get("isGift") else ""} for ln in lines]


def receipt_rows(receipts):
    return [{"id": r.get("id"), "kind": r.get("kind"), "status": r.get("status"),
             "total": amd(r.get("totalMinor")), "fiscal": r.get("fiscalNumber"), "issued": r.get("issuedAt"),
             "attempts": r.get("attempts"), "error": short(r.get("errorMessage") or r.get("errorCode"), 50)}
            for r in receipts or []]


def incident_rows(incidents):
    return [{"at": i.get("createdAt"), "kind": i.get("kind"), "receipt": i.get("receiptId"),
             "till": i.get("tillId"), "detail": short(json.dumps(i.get("detail"), ensure_ascii=False), 70)} for i in incidents or []]


def outbox_rows(items):
    return [{"id": m.get("id"), "topic": m.get("topic"), "attempts": m.get("attempts"),
             "created": m.get("createdAt"), "error": short(m.get("lastError"), 70)} for m in items or []]


def setting_rows(entries):
    return [{"key": e.get("key"), "value": short(e.get("value"), 40), "default": short(e.get("default"), 30),
             "set": "" if e.get("isDefault") else "yes", "description": short(e.get("description"), 70)}
            for e in entries or []]


def service_rows(services):
    return [{"code": s.get("code"), "name": name(s.get("name")), "price": amd(s.get("priceMinor")),
             "fiscal": s.get("fiscalName"), "adg": s.get("adgCode"), "active": "yes" if s.get("isActive") else "no"}
            for s in services or []]


def promotion_rows(promotions):
    return [{"name": p.get("name"), "on": p.get("targetLabel"),
             "off": f"{p['percent']}%" if p.get("percent") is not None else f"{amd(p.get('amountMinor'))} AMD",
             "from": p.get("startsAt"), "until": p.get("endsAt"), "active": "yes" if p.get("isActive") else "no"}
            for p in promotions or []]
