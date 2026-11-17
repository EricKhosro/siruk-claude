"""Web-order prep, services and shop promotions in Ops: what each command checks and sends. Paths and bodies
follow ops/apps/api/src/modules/{web-orders,services,shop-promotions} (controllers + dto/).

Rules: nothing is sent for an order that is closed or past the step; gifts change only before packing; damage is
marked only on own lines that were packed; a service's name is sent whole (the server replaces it); a promotion
is sent whole too (PUT), with exactly one target and one discount. No DTO has an idempotency field, so each
dry run is bound to the order's prep status and lines, or to the current services or promotions.
"""
import datetime, re, urllib.parse

from siruk.ops import client as _ops, guard, resolve, units
from siruk.payload import PayloadError

CLOSED = ("cancelled", "refunded")          # WebOrderStatus
PACKED = ("packed", "shipped")              # WebOrderPrepStatus
TARGETS = ("variant", "product", "brand")   # ShopPromotionTarget
LANGS = ("hy", "en", "ru")                  # ServiceNameDto
SERVICE_CODE = re.compile(r"[A-Z0-9][A-Z0-9_-]{1,31}")   # CreateServiceDto.code
AMOUNT_MINOR = re.compile(r"[1-9]\d{0,11}")               # ShopPromotionDto.amountMinor
MAX_GIFT, MAX_LINES, MAX_MINOR = 1_000_000, 200, 1_000_000_000_000   # AddGiftDto, MarkDamagedDto, limits.ts
MAX_NAME, MAX_FISCAL, MAX_ADG, MAX_PROMO_NAME = 120, 50, 16, 80
SHOP_TZ = datetime.timezone(datetime.timedelta(hours=4))   # Yerevan, no daylight saving


def _quote(x):
    return urllib.parse.quote(str(x), safe="")


# ------------------------------------------------------------------ web orders ----
def find_order(ref):
    """The order's detail, by id or exact number."""
    ref = str(ref).strip()
    if not resolve.UUID.fullmatch(ref):
        rows = (_ops.default().get("/web-orders", {"q": ref, "limit": 500}) or {}).get("items") or []
        hit = [o for o in rows if str(o.get("number")).lower() == ref.lower()]
        if len(hit) != 1:
            raise PayloadError(f"{len(hit)} web orders have the number {ref!r}" if hit else f"no web order has the number {ref!r}")
        ref = hit[0]["id"]
    return _ops.default().get(f"/web-orders/{_quote(ref)}") or {}


def base(d):
    return f"/web-orders/{_quote(d['order']['id'])}"


def number(d):
    return d["order"].get("number")


def own_lines(d):
    return d.get("ownLines") or []


def shown(d):
    """What the dry run showed of the order: the state every order code is bound to."""
    o = d["order"]
    line = lambda src, ln: {"id": ln.get("id"), "sku": ln.get("sku"), "quantity": ln.get("quantity"),
                            "isGift": ln.get("isGift"), "source": src, "costMinor": ln.get("costMinor")}
    return {"id": o.get("id"), "number": o.get("number"), "status": o.get("status"), "prepStatus": o.get("prepStatus"),
            "lines": [*(line("own", x) for x in own_lines(d)), *(line("hafo", x) for x in d.get("hafoLines") or [])]}


def _open(d):
    o = d["order"]
    if o.get("status") in CLOSED:
        raise PayloadError(f"order {o.get('number')} is {o.get('status')}")
    return o


def accept(d):
    o = _open(d)
    if o.get("prepStatus") in PACKED:
        raise PayloadError(f"order {o.get('number')} is already {o.get('prepStatus')}")
    if o.get("prepStatus") == "picking":
        raise PayloadError(f"order {o.get('number')} is already being picked: nothing to do")
    return ([guard.Step("POST", f"{base(d)}/picking", None, "accept (start picking)")],
            f"accept order {number(d)}: {o.get('prepStatus')} -> picking")


def _before_packing(d, what):
    o = _open(d)
    if o.get("prepStatus") in PACKED:
        raise PayloadError(f"order {o.get('number')} is {o.get('prepStatus')}: {what} only before packing")


def gift_add(d, good, quantity):
    _before_packing(d, "gifts change")
    v = resolve.variant(good)
    n = units.parse_quantity(quantity, v.get("stockUnit"))
    if not 1 <= n <= MAX_GIFT:
        raise PayloadError(f"a gift is 1 to {MAX_GIFT} base units, got {n}")
    return ([guard.Step("POST", f"{base(d)}/gifts", {"variantId": v["variantId"], "quantity": n},
                   f"gift {v.get('sku')} x {units.format_quantity(n, v.get('stockUnit'))} at 0 AMD")],
            f"add a gift of {v.get('sku')} x {units.format_quantity(n, v.get('stockUnit'))} to order {number(d)}")


def _own_line(d, ref, only=lambda x: True):
    """An own line by its id or SKU."""
    ref = str(ref).strip()
    rows = [x for x in own_lines(d) if only(x)]
    hit = [x for x in rows if str(x.get("id")).lower() == ref.lower()] or \
          [x for x in rows if str(x.get("sku")).lower() == ref.lower()]
    return resolve.one(ref, "own line", hit, lambda x: f"{x.get('id')} {x.get('sku')} x {x.get('quantity')}")


def gift_rm(d, ref):
    _before_packing(d, "gifts change")
    if not any(x.get("addedInOps") for x in own_lines(d)):
        raise PayloadError(f"order {number(d)} has no gift added in Ops: only those can be removed here")
    ln = _own_line(d, ref, lambda x: x.get("addedInOps"))
    if ln.get("costMinor") is not None:
        raise PayloadError(f"the gift {ln.get('sku')} is already packed")
    return ([guard.Step("DELETE", f"{base(d)}/gifts/{_quote(ln['id'])}", None, f"remove the gift {ln.get('sku')}")],
            f"remove the gift {ln.get('sku')} x {ln.get('quantity')} from order {number(d)}")


def pack(d):
    o = _open(d)
    if o.get("prepStatus") in PACKED and all(x.get("costMinor") is not None for x in own_lines(d)):
        raise PayloadError(f"order {o.get('number')} is already {o.get('prepStatus')}: nothing left to pack")
    n = sum(1 for x in own_lines(d) if x.get("costMinor") is None)
    return ([guard.Step("POST", f"{base(d)}/pack", None, f"pack {n} own line(s): they leave stock now")],
            f"pack order {number(d)}: {n} own line(s) leave stock, hafo lines are untouched")


def ship(d):
    o = _open(d)
    if o.get("channel") == "glovo":
        raise PayloadError(f"order {o.get('number')} is a Glovo order: its handover is Ready for pickup in the Ops app")
    if o.get("prepStatus") == "shipped":
        raise PayloadError(f"order {o.get('number')} is already shipped")
    if o.get("prepStatus") != "packed":
        raise PayloadError(f"order {o.get('number')} is {o.get('prepStatus')}: pack it before shipping")
    return ([guard.Step("POST", f"{base(d)}/ship", None, "ship (handed to the courier)")],
            f"ship order {number(d)}: packed -> shipped")


def damaged(d, refs):
    """Packed own lines that came back unfit to sell. A closed order is allowed: the server writes the
    restocked goods off at once; an open one is written off instead of restocked when it closes."""
    refs = [x.strip() for r in refs for x in str(r).split(",") if x.strip()]
    if not refs:
        raise PayloadError("--lines needs at least one line (id or SKU)")
    ids, skus = [], []
    for ref in refs:
        hafo = [x for x in d.get("hafoLines") or [] if ref.lower() in (str(x.get("id")).lower(), str(x.get("sku")).lower())]
        if hafo:
            raise PayloadError(f"{hafo[0].get('sku')} is a hafo line: only own-warehouse lines can be damaged")
        ln = _own_line(d, ref)
        if ln.get("costMinor") is None:
            raise PayloadError(f"{ln.get('sku')} was never packed, so nothing came back")
        if ln["id"] not in ids:
            ids.append(ln["id"])
            skus.append(str(ln.get("sku")))
    if len(ids) > MAX_LINES:
        raise PayloadError(f"at most {MAX_LINES} lines at once, got {len(ids)}")
    return ([guard.Step("POST", f"{base(d)}/damaged", {"lineIds": ids}, "mark damaged: the value is written off")],
            f"mark {', '.join(skus)} of order {number(d)} damaged: " + (
                f"the order is {d['order'].get('status')}, so the goods are written off now"
                if d["order"].get("status") in CLOSED else "written off instead of restocked if the order is closed later"))


# -------------------------------------------------------------------- services ----
def services():
    return _ops.default().get("/services") or []


def services_state(rows):
    keys = ("id", "code", "name", "priceMinor", "fiscalName", "adgCode", "isActive")
    return [{k: r.get(k) for k in keys} for r in rows]


def find_service(rows, ref):
    ref = str(ref).strip().lower()
    hit = [r for r in rows if str(r.get("id")).lower() == ref] or [r for r in rows if str(r.get("code")).lower() == ref]
    return resolve.one(ref, "service", hit, lambda r: f"{r.get('id')} {r.get('code')}")


def _text(value, limit, what):
    t = str(value).strip()
    if len(t) > limit:
        raise PayloadError(f"{what} is at most {limit} characters")
    return t


def _price(price, ask):
    if ask:
        return None
    minor = int(units.amd_to_minor(price))
    if not 1 <= minor <= MAX_MINOR:
        raise PayloadError("a service price is at least 0.01 AMD and below 10 billion AMD")
    return minor


def service_fields(*, names, price=None, ask_price=False, fiscal_name=None, adg_code=None, active=None):
    """The ServiceFieldsDto fields that were given; an empty fiscal name or ADG code clears it."""
    body = {}
    if price is not None or ask_price:
        body["priceMinor"] = _price(price, ask_price)
    if fiscal_name is not None:
        body["fiscalName"] = _text(fiscal_name, MAX_FISCAL, "the fiscal name") or None
    if adg_code is not None:
        body["adgCode"] = _text(adg_code, MAX_ADG, "the ADG code") or None
    if active is not None:
        body["isActive"] = bool(active)
    name = {k: _text(v, MAX_NAME, f"the {k} name") for k, v in names.items() if v is not None}
    return body, name


def service_add(rows, code, names, **fields):
    code = str(code).strip()
    if not SERVICE_CODE.fullmatch(code):
        raise PayloadError("a service code is 2-32 capitals, digits, _ or -, starting with a capital or digit")
    if any(str(r.get("code")).upper() == code for r in rows):
        raise PayloadError(f"a service with the code {code} exists")
    body, name = service_fields(names=names, **fields)
    if not any(name.values()):
        raise PayloadError("give the service a name in at least one language (--name-hy, --name-en, --name-ru)")
    body = {"code": code, "name": name, **body}
    return ([guard.Step("POST", "/services", body, f"add the service {code}")],
            f"add the service {code}" + ("" if "priceMinor" in body else " (price typed at each sale)"))


def service_set(rows, ref, names, **fields):
    row = find_service(rows, ref)
    body, name = service_fields(names=names, **fields)
    if name:
        merged = {k: (row.get("name") or {}).get(k) for k in LANGS}
        merged.update(name)
        if not any(merged.values()):
            raise PayloadError("a service keeps a name in at least one language")
        body = {"name": merged, **body}
    if not body:
        raise PayloadError("nothing to change: give --name-hy/--name-en/--name-ru, --price, --ask-price, "
                           "--fiscal-name, --adg-code, --active or --inactive")
    return ([guard.Step("PATCH", f"/services/{_quote(row['id'])}", body, f"change the service {row.get('code')}")],
            f"change the service {row.get('code')}: " + ", ".join(body))


# ------------------------------------------------------------------ promotions ----
def promotions():
    return _ops.default().get("/shop-promotions") or []


def promotions_state(rows):
    keys = ("id", "name", "target", "variantId", "productId", "brand", "percent", "amountMinor", "startsAt",
            "endsAt", "isActive")
    return [{k: r.get(k) for k in keys} for r in rows]


def find_promotion(rows, ref):
    ref = str(ref).strip().lower()
    hit = [r for r in rows if str(r.get("id")).lower() == ref] or [r for r in rows if str(r.get("name")).lower() == ref]
    return resolve.one(ref, "promotion", hit, lambda r: f"{r.get('id')} {r.get('name')}")


def when(text, what, last_day=False):
    """A day (shop time; as an end it is the last day, included) or a full ISO time with its offset."""
    t = str(text).strip()
    try:
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", t):
            day = datetime.datetime.combine(datetime.date.fromisoformat(t), datetime.time(), SHOP_TZ)
            return day + datetime.timedelta(days=1 if last_day else 0)
        dt = datetime.datetime.fromisoformat(t)
    except ValueError:
        raise PayloadError(f"{what} looks like 2026-12-01 or 2026-12-01T09:00:00+04:00, got {text!r}") from None
    if dt.tzinfo is None:
        raise PayloadError(f"{what} needs a UTC offset (+04:00) or a plain day, got {text!r}")
    return dt


def _target(given, current):
    """(target, variantId, productId, brand) from the one --variant/--product/--brand given, else the current row's."""
    named = {k: v for k, v in given.items() if v is not None}
    if len(named) > 1:
        raise PayloadError("a promotion is on one target: give only one of --variant, --product, --brand")
    if not named:
        if not current:
            raise PayloadError("a promotion needs its target: --variant GOOD, --product GOOD or --brand NAME")
        return {k: current.get(k) for k in ("target", "variantId", "productId", "brand")}
    (kind, ref), = named.items()
    if kind == "brand":
        brand = _text(ref, 120, "the brand")
        if not brand:
            raise PayloadError("--brand is empty")
        return {"target": "brand", "variantId": None, "productId": None, "brand": brand}
    g = resolve.variant(ref)
    if kind == "variant":
        return {"target": "variant", "variantId": g["variantId"], "productId": None, "brand": None}
    return {"target": "product", "variantId": None, "productId": g["productId"], "brand": None}


def promotion_body(current, *, name=None, variant=None, product=None, brand=None, percent=None, amount=None,
                   starts=None, ends=None, no_end=False, active=None):
    """The whole ShopPromotionDto: what was given laid over the current row (none on a new one)."""
    current = current or {}
    name = _text(name if name is not None else current.get("name") or "", MAX_PROMO_NAME, "the name")
    if not name:
        raise PayloadError("give the promotion a name (--name)")
    if percent is not None and amount is not None:
        raise PayloadError("a promotion is a percent or an amount off, not both")
    if percent is not None:
        if not isinstance(percent, int) or isinstance(percent, bool) or not 1 <= percent <= 100:
            raise PayloadError("--percent is a whole number from 1 to 100")
        disc = {"percent": percent}
    elif amount is not None:
        minor = units.amd_to_minor(amount)
        if not AMOUNT_MINOR.fullmatch(minor):
            raise PayloadError("--amount is at least 0.01 AMD and below 10 billion AMD")
        disc = {"amountMinor": minor}
    elif current.get("percent") is not None:
        disc = {"percent": current["percent"]}
    elif current.get("amountMinor") is not None:
        disc = {"amountMinor": str(current["amountMinor"])}
    else:
        raise PayloadError("give the discount: --percent N or --amount AMD")
    target = _target({"variant": variant, "product": product, "brand": brand}, current)
    first = when(starts, "--from") if starts else when(current["startsAt"], "startsAt") if current.get("startsAt") else None
    if first is None:
        raise PayloadError("give the first day (--from)")
    if no_end and ends:
        raise PayloadError("--to and --no-end are opposites")
    last = when(ends, "--to", last_day=True) if ends else None if no_end else \
        when(current["endsAt"], "endsAt") if current.get("endsAt") else None
    if last is not None and last <= first:
        raise PayloadError("a promotion ends after it starts")
    body = {"name": name, "target": target["target"], **{k: target[k] for k in ("variantId", "productId", "brand")
                                                        if target[k] is not None}, **disc, "startsAt": first.isoformat()}
    if last is not None:
        body["endsAt"] = last.isoformat()
    if active is not None:
        body["isActive"] = bool(active)
    return body


def _off(body):
    return f"{body['percent']}%" if "percent" in body else f"{units.minor_to_amd(body['amountMinor'])} AMD off each unit"


def promotion_add(body):
    return ([guard.Step("POST", "/shop-promotions", body, f"add the promotion {body['name']}")],
            f"add the promotion {body['name']}: {_off(body)} on a {body['target']}, from {body['startsAt']}")


def promotion_set(row, body):
    return ([guard.Step("PUT", f"/shop-promotions/{_quote(row['id'])}", body, f"replace the promotion {row.get('name')}")],
            f"replace the promotion {row.get('name')} with: {_off(body)} on a {body['target']}, from {body['startsAt']}")
