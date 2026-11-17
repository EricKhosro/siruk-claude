"""`siruk ops orders accept | gift add | gift rm | pack | ship | damaged`, `siruk ops services add | set` and
`siruk ops promotions add | set` — preparing web orders and keeping the till's services and promotions.

Every command is a dry run until `--apply <code>`. Not here by decision: printing the HDM receipt, Glovo's
ready-for-pickup and the ArmSoft goods import (the Ops app does them).
"""
from siruk.ops import guard, prep as P

ANY = "any signed-in user"
MANAGER = "owner, manager"
ORDER = ["GET /web-orders/:id", "GET /web-orders"]   # an order is named by id or number


def _order(a, built, tier, state=None):
    steps, summary = built
    return guard.run(a, steps=steps, summary=summary, tier=tier, shown_state=state,
                     verify=f"siruk ops orders show {P.number(a.detail)}")


def _with_order(fn):
    def run(a):
        a.detail = P.find_order(a.order)
        return fn(a)
    return run


@_with_order
def cmd_accept(a):
    return _order(a, P.accept(a.detail), "draft", P.shown(a.detail))


@_with_order
def cmd_gift_add(a):
    return _order(a, P.gift_add(a.detail, a.good, a.quantity), "draft", P.shown(a.detail))


@_with_order
def cmd_gift_rm(a):
    return _order(a, P.gift_rm(a.detail, a.line), "draft", P.shown(a.detail))


@_with_order
def cmd_pack(a):
    return _order(a, P.pack(a.detail), "irreversible", P.shown(a.detail))


@_with_order
def cmd_ship(a):
    return _order(a, P.ship(a.detail), "real-world", P.shown(a.detail))


@_with_order
def cmd_damaged(a):
    return _order(a, P.damaged(a.detail, a.lines), "irreversible", P.shown(a.detail))


def _names(a):
    return {"hy": a.name_hy, "en": a.name_en, "ru": a.name_ru}


def _service_fields(a):
    return dict(price=a.price, ask_price=a.ask_price, fiscal_name=a.fiscal_name, adg_code=a.adg_code, active=a.active)


def cmd_services_add(a):
    rows = P.services()
    steps, summary = P.service_add(rows, a.code, _names(a), **_service_fields(a))
    return guard.run(a, steps=steps, summary=summary, tier="real-world", shown_state=P.services_state(rows),
                     verify="siruk ops services list")


def cmd_services_set(a):
    rows = P.services()
    steps, summary = P.service_set(rows, a.service, _names(a), **_service_fields(a))
    return guard.run(a, steps=steps, summary=summary, tier="real-world", shown_state=P.services_state(rows),
                     verify="siruk ops services list")


def _promotion_fields(a):
    return dict(name=a.name, variant=a.variant, product=a.product, brand=a.brand, percent=a.percent,
                amount=a.amount, starts=a.date_from, ends=a.to, active=a.active)


def cmd_promotions_add(a):
    rows = P.promotions()
    steps, summary = P.promotion_add(P.promotion_body(None, **_promotion_fields(a), no_end=False))
    return guard.run(a, steps=steps, summary=summary, tier="real-world", shown_state=P.promotions_state(rows),
                     verify="siruk ops promotions list")


def cmd_promotions_set(a):
    rows = P.promotions()
    row = P.find_promotion(rows, a.promotion)
    steps, summary = P.promotion_set(row, P.promotion_body(row, **_promotion_fields(a), no_end=a.no_end))
    return guard.run(a, steps=steps, summary=summary, tier="real-world", shown_state=P.promotions_state(rows),
                     verify="siruk ops promotions list")


# ---------------------------------------------------------------- registration ----
def _active(p):
    g = p.add_mutually_exclusive_group()
    g.add_argument("--active", dest="active", action="store_true", default=None, help="sellable / running")
    g.add_argument("--inactive", dest="active", action="store_false", default=None, help="switch it off")


def _service_options(p, adding):
    for lang in P.LANGS:
        p.add_argument(f"--name-{lang}", metavar="TEXT", help=f"the name in {lang} (at most {P.MAX_NAME} characters)")
    g = p.add_mutually_exclusive_group()
    g.add_argument("--price", metavar="AMD", help="fixed price per piece" + ("" if adding else "; --ask-price to clear it"))
    g.add_argument("--ask-price", action="store_true", help="no fixed price: the cashier types it at each sale")
    p.add_argument("--fiscal-name", metavar="TEXT", help=f"name on the receipt, at most {P.MAX_FISCAL} characters"
                   + ("" if adding else "; empty clears it"))
    p.add_argument("--adg-code", metavar="CODE", help="ADG classifier, needed before it can be sold"
                   + ("" if adding else "; empty clears it"))
    _active(p)


def _promotion_options(p):
    p.add_argument("--name", metavar="TEXT", help=f"at most {P.MAX_PROMO_NAME} characters")
    p.add_argument("--variant", metavar="GOOD", help="on one sell unit: id, SKU or barcode")
    p.add_argument("--product", metavar="GOOD", help="on every sell unit of the product of this good")
    p.add_argument("--brand", metavar="NAME", help="on every product of this brand")
    g = p.add_mutually_exclusive_group()
    g.add_argument("--percent", type=int, metavar="N", help="whole percent off, 1 to 100")
    g.add_argument("--amount", metavar="AMD", help="AMD off each unit")
    p.add_argument("--from", dest="date_from", metavar="DAY", help="first day YYYY-MM-DD (shop time) or ISO time with offset")
    p.add_argument("--to", metavar="DAY", help="last day, included, or ISO time with offset")
    _active(p)


def register(reg):
    reg.command(("ops", "orders", "accept"), cmd_accept, "accept a web order: start picking it",
                api=[*ORDER, "POST /web-orders/:id/picking"], tier="draft", roles=ANY,
                example="siruk ops orders accept 10452").add_argument("order", help="id or number")

    p = reg.command(("ops", "orders", "gift", "add"), cmd_gift_add, "add a gift at 0 AMD from our own stock, before packing",
                    api=[*ORDER, "GET /goods", "GET /goods/:variantId", "POST /web-orders/:id/gifts"], tier="draft",
                    roles=ANY, example="siruk ops orders gift add 10452 RC-1 2")
    p.add_argument("order", help="id or number")
    p.add_argument("good", help="id, SKU or barcode")
    p.add_argument("quantity", help="base units (pieces or grams), or with a unit: 2, 500g, 1.5kg")

    p = reg.command(("ops", "orders", "gift", "rm"), cmd_gift_rm, "remove a gift added in Ops, before it is packed",
                    api=[*ORDER, "DELETE /web-orders/:id/gifts/:lineId"], tier="draft", roles=ANY,
                    example="siruk ops orders gift rm 10452 RC-1")
    p.add_argument("order", help="id or number")
    p.add_argument("line", help="the gift line: id or SKU")

    reg.command(("ops", "orders", "pack"), cmd_pack, "pack a web order: its own-warehouse lines leave stock",
                api=[*ORDER, "POST /web-orders/:id/pack"], tier="irreversible", roles=ANY,
                example="siruk ops orders pack 10452").add_argument("order", help="id or number")

    reg.command(("ops", "orders", "ship"), cmd_ship, "ship a packed web order: the courier has it",
                api=[*ORDER, "POST /web-orders/:id/ship"], tier="real-world", roles=ANY,
                example="siruk ops orders ship 10452").add_argument("order", help="id or number")

    p = reg.command(("ops", "orders", "damaged"), cmd_damaged, "mark packed lines of an order as unfit to sell: their value is written off",
                    api=[*ORDER, "POST /web-orders/:id/damaged"], tier="irreversible", roles="owner, manager, warehouse",
                    example="siruk ops orders damaged 10452 --lines RC-1,RC-2")
    p.add_argument("order", help="id or number")
    p.add_argument("--lines", nargs="+", required=True, metavar="LINE", help="own lines: ids or SKUs, spaces or commas")

    p = reg.command(("ops", "services", "add"), cmd_services_add, "add a service sold at the till (delivery, nail trim…)",
                    api=["GET /services", "POST /services"], tier="real-world", roles=MANAGER,
                    example='siruk ops services add NAIL_TRIM --name-en "Nail trim" --price 3000')
    p.add_argument("code", help="2 to 32 capitals, digits, _ or -")
    _service_options(p, True)

    p = reg.command(("ops", "services", "set"), cmd_services_set, "change a service: name, price, receipt name, ADG code, on or off",
                    api=["GET /services", "PATCH /services/:id"], tier="real-world", roles=MANAGER,
                    example="siruk ops services set NAIL_TRIM --price 3500")
    p.add_argument("service", help="id or code")
    _service_options(p, False)

    p = reg.command(("ops", "promotions", "add"), cmd_promotions_add, "add a shop promotion: percent or amount off a good, product or brand",
                    api=["GET /shop-promotions", "GET /goods", "GET /goods/:variantId", "POST /shop-promotions"],
                    tier="real-world", roles=MANAGER,
                    example='siruk ops promotions add --name "Autumn" --brand Monge --percent 10 --from 2026-11-20 --to 2026-11-30')
    _promotion_options(p)

    p = reg.command(("ops", "promotions", "set"), cmd_promotions_set, "change a shop promotion (it is replaced whole)",
                    api=["GET /shop-promotions", "GET /goods", "GET /goods/:variantId", "PUT /shop-promotions/:id"],
                    tier="real-world", roles=MANAGER, example="siruk ops promotions set Autumn --percent 15 --inactive")
    p.add_argument("promotion", help="id or exact name")
    _promotion_options(p)
    p.add_argument("--no-end", action="store_true", help="run without an end")
