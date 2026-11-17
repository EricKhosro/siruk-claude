"""Manual stock documents for Ops: the POST /documents body from what a person types, and the review of a draft.

Shapes: siruk-web/ops/apps/api/src/modules/stock/dto/{create-document,document-line,replace-lines}.dto.ts and
packages/contracts/src/api/backoffice.ts. Quantities are whole base units, money is a minor-unit string, and
a posted document never changes, so every rule is checked here before the draft is sent.
"""
import datetime

from siruk.ops import guard, resolve, units
from siruk.payload import PayloadError

TYPES = ("opening_balance", "receipt", "supplier_return", "write_off", "count", "transfer", "bag_opening")
REASONS = ("damaged", "expired", "lost", "other")
COSTED = ("receipt", "opening_balance")
NEEDS_SUPPLIER = ("receipt", "supplier_return")
LINE_KEYS = ("variant", "quantity", "counted", "unit_cost_amd", "amount_amd", "target", "note")
MAX_LINES, MAX_NOTE, MAX_LINE_NOTE, MAX_SERIAL = 500, 500, 200, 32


def _text(value, what, limit):
    value = None if value is None else str(value).strip()
    if value and len(value) > limit:
        raise PayloadError(f"{what} is longer than {limit} characters")
    return value or None


def check_header(type_, *, to_location=None, supplier=None, invoice=None, reason=None, note=None, date=None):
    """The rules that need no lookup; returns the cleaned optional fields."""
    if type_ not in TYPES:
        raise PayloadError(f"unknown document type {type_!r}; one of {', '.join(TYPES)}")
    invoice, note = _text(invoice, "--invoice", MAX_SERIAL), _text(note, "--note", MAX_NOTE)
    if type_ in NEEDS_SUPPLIER and not (supplier and str(supplier).strip() and invoice):
        raise PayloadError(f"a {type_} needs --supplier and --invoice (the supplier's invoice number)")
    if type_ == "transfer" and not to_location:
        raise PayloadError("a transfer needs --to-location")
    if to_location and type_ != "transfer":
        raise PayloadError("only a transfer has --to-location")
    if type_ == "write_off" and not reason:
        raise PayloadError(f"a write_off needs --reason ({', '.join(REASONS)})")
    if reason and type_ != "write_off":
        raise PayloadError("only a write_off carries --reason")
    if reason and reason not in REASONS:
        raise PayloadError(f"--reason must be one of {', '.join(REASONS)}")
    if date:
        try:
            datetime.datetime.fromisoformat(str(date))
        except ValueError:
            raise PayloadError(f"--date {date!r} is not an ISO date (2026-11-16 or 2026-11-16T09:30:00Z)")
    return {"invoice": invoice, "note": note}


def check_lines_shape(type_, raw):
    """Every line a dict with a `variant` and only the keys its type uses; no lookup."""
    if not isinstance(raw, list) or not raw:
        raise PayloadError('--lines must be a non-empty JSON list: [{"variant": "<sku|barcode|uuid>", "quantity": 12}]')
    if len(raw) > MAX_LINES:
        raise PayloadError(f"a document takes at most {MAX_LINES} lines, got {len(raw)}")
    counted, costed = type_ == "count", type_ in COSTED
    for i, l in enumerate(raw, 1):
        at = f"line {i}"
        if not isinstance(l, dict) or not l.get("variant"):
            raise PayloadError(f'{at}: a line is an object with a "variant"')
        extra = sorted(set(l) - set(LINE_KEYS))
        if extra:
            raise PayloadError(f"{at}: unknown key {', '.join(extra)}; a line has {', '.join(LINE_KEYS)}")
        if counted and l.get("quantity") is not None:
            raise PayloadError(f'{at}: a count line uses "counted", not "quantity"')
        if counted and l.get("counted") is None:
            raise PayloadError(f'{at}: a count line needs "counted" (0 is allowed)')
        if not counted and l.get("counted") is not None:
            raise PayloadError(f'{at}: "counted" belongs to a count')
        if not counted and l.get("quantity") is None:
            raise PayloadError(f'{at}: a {type_} line needs "quantity"')
        costs = [k for k in ("unit_cost_amd", "amount_amd") if l.get(k) is not None]
        if costed and len(costs) != 1:
            raise PayloadError(f'{at}: a {type_} line needs exactly one of "unit_cost_amd" or "amount_amd"')
        if not costed and costs:
            raise PayloadError(f"{at}: a {type_} line takes no cost; the ledger values it")
        if l.get("target") is not None and type_ != "bag_opening":
            raise PayloadError(f'{at}: only a bag_opening has a "target"')


def build_lines(type_, raw):
    """The API's line bodies; each variant is resolved and its quantity read in its own unit."""
    check_lines_shape(type_, raw)
    out, seen = [], set()
    for i, l in enumerate(raw, 1):
        good = resolve.variant(l["variant"])
        at = f"line {i} ({good.get('sku')})"
        if type_ == "count":
            if good["variantId"] in seen:
                raise PayloadError(f"{at}: count each good once")
            seen.add(good["variantId"])
        row = {"variantId": good["variantId"]}
        try:
            qty = units.parse_quantity(l["counted" if type_ == "count" else "quantity"], good.get("stockUnit"))
            if type_ != "count" and qty < 1:
                raise PayloadError("a quantity must be at least 1")
            row["countedQuantity" if type_ == "count" else "quantity"] = qty
            if l.get("unit_cost_amd") is not None:
                row["unitCostMinor"] = units.amd_to_minor(l["unit_cost_amd"])
            if l.get("amount_amd") is not None:
                row["amountMinor"] = units.amd_to_minor(l["amount_amd"])
        except PayloadError as e:
            raise PayloadError(f"{at}: {e}")
        if l.get("target") is not None:
            row["targetVariantId"] = resolve.variant(l["target"])["variantId"]
        note = _text(l.get("note"), f"{at}: note", MAX_LINE_NOTE)
        if note:
            row["note"] = note
        out.append(row)
    return out


def today():
    return datetime.date.today().isoformat()


def build_body(type_, *, location, lines, to_location=None, supplier=None, invoice=None, reason=None,
               note=None, date=None, key=None):
    """POST /documents body. `location` / `to_location` / `supplier` are the resolved API objects.
    The idempotencyKey is the same for the same document on the same day (without --date), so a re-run
    returns the draft it made; another day or a `key` makes a new one."""
    for loc in (location, to_location):
        if loc and (loc.get("kind") == "supplier" or loc.get("isActive") is False):
            raise PayloadError(f"location {loc.get('code')} is a supplier warehouse or switched off; no document can use it")
    if to_location and to_location["id"] == location["id"]:
        raise PayloadError("a transfer needs a different destination")
    body = {"type": type_, "locationId": location["id"]}
    for k, v in (("toLocationId", to_location and to_location["id"]), ("supplierId", supplier and supplier["id"]),
                 ("invoiceSerial", invoice), ("reason", reason), ("note", note), ("documentDate", date)):
        if v:
            body[k] = v
    body["lines"] = lines
    body["idempotencyKey"] = guard.idem_key("doc", body, *([key] if key else []), *([] if date else [today()]))
    return body


def qty_at(good, location_id):
    for s in good.get("stock") or []:
        if s.get("locationId") == location_id and s.get("kind") != "supplier":
            return int(s.get("quantity") or 0)
    return 0


def state(doc):
    """What a person reviews before posting; an edit to any of it changes the confirm code."""
    keys = ("variantId", "quantity", "countedQuantity", "amountMinor", "targetVariantId")
    return {"id": doc.get("id"), "number": doc.get("number"), "type": doc.get("type"), "status": doc.get("status"),
            "locationId": doc.get("locationId"), "toLocationId": doc.get("toLocationId"),
            "totalAmountMinor": doc.get("totalAmountMinor"), "lineCount": len(doc.get("lines") or []),
            "lines": [{k: l.get(k) for k in keys} for l in doc.get("lines") or []]}


def review(doc, fetch):
    """One row per stock figure the post will move: the stock now and after. `fetch(variantId)` → the good."""
    rows, type_, at = [], doc["type"], doc["locationId"]

    def row(n, good, where, loc_id, after_of):
        now = qty_at(good, loc_id)
        after, unit = after_of(now), good.get("stockUnit")
        fmt = lambda x: units.format_quantity(x, unit)
        rows.append({"line": n, "sku": good.get("sku"), "where": where, "now": fmt(now),
                     "change": "?" if after is None else ("+" if after > now else "") + fmt(after - now),
                     "after": "?" if after is None else fmt(after), "negative": after is not None and after < 0})

    for n, l in enumerate(doc.get("lines") or [], 1):
        good, q = fetch(l["variantId"]), int(l.get("quantity") or 0)
        here, there = doc.get("locationName") or at, doc.get("toLocationName") or doc.get("toLocationId")
        if type_ in ("opening_balance", "receipt"):
            row(n, good, here, at, lambda now: now + q)
        elif type_ in ("supplier_return", "write_off"):
            row(n, good, here, at, lambda now: now - q)
        elif type_ == "count":
            row(n, good, here, at, lambda now: int(l.get("countedQuantity") or 0))
        elif type_ == "transfer":
            row(n, good, here, at, lambda now: now - q)
            row(n, good, there, doc["toLocationId"], lambda now: now + q)
        elif type_ == "bag_opening":
            loose = fetch(l["targetVariantId"]) if l.get("targetVariantId") else None
            milli = good.get("contentMilli")
            if not milli or milli % 1000:
                raise PayloadError(f"line {n} ({good.get('sku')}): the bag has no whole net content to pour; "
                                   "Ops would refuse this bag_opening")
            grams = (milli // 1000) * int(good.get("packCount") or 1)
            row(n, good, here, at, lambda now: now - q)
            if loose:
                row(n, loose, here, at, lambda now: now + grams * q)
    return rows
