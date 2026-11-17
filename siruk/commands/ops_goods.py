"""`siruk ops goods | locations | open-bag` — find a good in Ops, see its stock per warehouse, set the
Ops-only fields ArmSoft used to hold. Every write goes through guard.run (dry run, then `--apply <code>`).
"""
import sys

from siruk import client as _admin, output
from siruk.ops import client as _ops, goods as G, guard, resolve, units
from siruk.payload import PayloadError

ANY = "any signed-in user"
EDITORS = "manager, warehouse"
CLEARABLE = ("fiscal-name", "adg", "low-stock-at", "reorder-point", "reorder-target")


def _name(g):
    return G.name_of(g)


def _quantity(g, n):
    return units.format_quantity(n, g.get("stockUnit")) if n is not None else "-"


def _detail(ref):
    g = resolve.variant(ref)
    if "movements" in g:
        return g
    return _ops.default().get(f"/goods/{G.good_id(g)}")


def cmd_list(a):
    params = {"q": a.q, "stockUnit": a.unit, "page": a.page, "pageSize": a.page_size}
    if a.location:
        params["locationId"] = resolve.location(a.location)["id"]
    if a.low:
        params["lowStock"] = True
    r = _ops.default().get("/goods", params) or {}
    if a.json:
        output.dump(r)
        return 0
    rows = [{"sku": g.get("sku"), "name": _name(g), "barcode": g.get("barcode"), "unit": g.get("stockUnit"),
             "avail": _quantity(g, g.get("totalAvailable")), "low": "LOW" if g.get("isLow") else ""}
            for g in r.get("items") or []]
    output.table(rows, [("sku", "SKU"), ("name", "name"), ("barcode", "barcode"), ("unit", "unit"),
                        ("avail", "available"), ("low", "")])
    print(f"\npage {r.get('page')} of {-(-int(r.get('total') or 0) // max(1, int(r.get('pageSize') or 1)))}"
          f"  ({r.get('total')} goods)")
    return 0


def _stock_rows(g):
    rows = []
    for s in g.get("stock") or []:
        if s.get("kind") == "supplier":
            have = "-" if s.get("quantity") is None else _quantity(g, s["quantity"])
            rows.append({"loc": s.get("locationCode"), "kind": "supplier", "qty": have, "res": "-",
                         "avail": "in stock" if s.get("inStock") else "out" if s.get("inStock") is False else "?"})
        else:
            rows.append({"loc": s.get("locationCode"), "kind": s.get("kind"), "qty": _quantity(g, s.get("quantity")),
                         "res": _quantity(g, s.get("reserved")), "avail": _quantity(g, s.get("available"))})
    return rows


def cmd_show(a):
    g = _detail(a.ref)
    if a.json:
        output.dump(g)
        return 0
    print(f"{G.title(g)}   {g.get('stockUnit')}  id {g.get('variantId')}")
    print(f"barcodes     {G.barcodes_text(g)}")
    print(f"fiscal name  {g.get('fiscalName') or '-'}    ADG {g.get('adgCode') or '-'}")
    print(f"low stock at {_quantity(g, g.get('lowStockAt')) if g.get('lowStockAt') is not None else 'shop default'}"
          f"    reorder {g.get('reorderMode')} point {g.get('reorderPoint')} target {g.get('reorderTarget')}"
          f" ({g.get('reorderSource')})")
    print(f"available    {_quantity(g, g.get('totalAvailable'))}" + ("   LOW" if g.get("isLow") else "") + "\n")
    output.table(_stock_rows(g), [("loc", "location"), ("kind", "kind"), ("qty", "quantity"),
                                  ("res", "reserved"), ("avail", "available")])
    moves = (g.get("movements") or [])[:10]
    if moves:
        print("\nlast movements")
        output.table([{**m, "d": m.get("quantityDelta")} for m in moves],
                     [("createdAt", "when"), ("kind", "kind"), ("locationName", "location"), ("d", "change"),
                      ("quantityAfter", "after"), ("documentNumber", "document")])
    return 0


def _raw_fields(a):
    raw = {k: getattr(a, k) for k in G.FIELDS if getattr(a, k, None) is not None}
    for c in a.clear or []:
        key = c.replace("-", "_")
        if key in raw:
            raise PayloadError(f"--{c} and --clear {c} together: pick one")
        raw[key] = None
    return raw


def cmd_set(a):
    checked = G.check_fields(_raw_fields(a))
    good = resolve.variant(a.ref)
    plan = G.plan_set(good, checked)
    if not plan:
        print(f"nothing to change: {G.title(good)} already has these values")
        return 0
    steps, summary, state = plan
    return guard.run(a, steps=steps, summary=summary, tier="draft", shown_state=state,
                     verify=f"siruk ops goods show {good['variantId']}")


def _load_rows(path):
    from siruk.cli import _load_json
    try:
        rows = _load_json(path)
    except (OSError, ValueError) as e:
        raise PayloadError(f"{path} is not JSON: {e}")
    if not isinstance(rows, list) or not rows or not all(isinstance(r, dict) for r in rows):
        raise PayloadError('set-many takes a JSON list of {"ref": …, "fiscal_name": …, "adg": …, …}')
    return rows


def cmd_set_many(a):
    rows, checked = _load_rows(a.file), []
    for i, r in enumerate(rows, 1):
        r = dict(r)
        ref = r.pop("ref", None)
        try:
            if not ref or not isinstance(ref, str):
                raise PayloadError("each row needs a ref (SKU, barcode, accounting code or id)")
            checked.append((ref, G.check_fields(r)))
        except PayloadError as e:
            raise PayloadError(f"row {i}: {e}")
    steps, lines, state, seen = [], [], [], {}
    for i, (ref, fields) in enumerate(checked, 1):
        try:
            good = resolve.variant(ref)
            if good["variantId"] in seen:
                raise PayloadError(f"{ref} is the same good as row {seen[good['variantId']]}")
            seen[good["variantId"]] = i
            plan = G.plan_set(good, fields)
        except PayloadError as e:
            raise PayloadError(f"row {i} ({ref}): {e}")
        if plan:
            steps += plan[0]
            lines += [f"{i}. {G.title(good)}", *["   " + x.strip() for x in plan[1].split("\n")[1:]]]
            state.append(plan[2])
        else:
            lines.append(f"{i}. {G.title(good)}: no change")
    if not steps:
        print("nothing to change: every row already has these values")
        return 0
    summary = G.block(f"set Ops fields of {len(steps)} of {len(checked)} goods, one PATCH each, stopping at the "
                      "first that fails", lines)
    return guard.run(a, steps=steps, summary=summary, tier="draft", shown_state=state,
                     verify="siruk ops goods show <sku> for each row")


def cmd_barcode_add(a):
    G.check_barcode(a.code, a.units)
    good = resolve.variant(a.ref)
    steps, summary, state = G.plan_barcode_add(good, a.code, a.units, False if a.receiving_only else None)
    return guard.run(a, steps=steps, summary=summary, tier="draft", shown_state=state,
                     verify=f"siruk ops goods show {good['variantId']}")


def cmd_barcode_rm(a):
    G.check_barcode(a.code)
    good = resolve.variant(a.ref)
    steps, summary, state = G.plan_barcode_rm(good, a.code)
    return guard.run(a, steps=steps, summary=summary, tier="draft", shown_state=state,
                     verify=f"siruk ops goods show {good['variantId']}")


def cmd_plu(a):
    good = resolve.variant(a.ref)
    steps, summary, state = G.plan_plu(good, a.plu)
    return guard.run(a, steps=steps, summary=summary, tier="irreversible", shown_state=state,
                     verify=f"siruk ops goods show {good['variantId']}")


def cmd_locations_list(a):
    rows = _ops.default().get("/locations") or []
    if a.json:
        output.dump(rows)
        return 0
    output.table([{**r, "on": "yes" if r.get("isActive") else "no"} for r in rows],
                 [("code", "code"), ("name", "name"), ("kind", "kind"), ("on", "active"),
                  ("sirukWarehouseCode", "siruk warehouse"), ("armsoftStorage", "armsoft")])
    return 0


def cmd_locations_create(a):
    body = {"code": a.code, "name": a.name, "kind": a.kind}
    for key, val in (("sirukWarehouseCode", a.siruk_warehouse_code), ("armsoftStorage", a.armsoft_storage)):
        if val is not None:
            body[key] = val
    body = G.check_location(body)
    codes = [x.get("code") or "" for x in _ops.default().get("/locations") or []]
    steps, summary, state = G.plan_location_create(body, codes)
    return guard.run(a, steps=steps, summary=summary, tier="draft", shown_state=state,
                     verify="siruk ops locations list")


def cmd_locations_set(a):
    body = {}
    for key, val in (("name", a.name), ("isActive", a.active), ("sirukWarehouseCode", a.siruk_warehouse_code),
                     ("armsoftStorage", a.armsoft_storage)):
        if val is not None:
            body[key] = val
    for c in a.clear or []:
        key = {"siruk-warehouse-code": "sirukWarehouseCode", "armsoft-storage": "armsoftStorage"}[c]
        if key in body:
            raise PayloadError(f"--{c} and --clear {c} together: pick one")
        body[key] = None
    if not body:
        raise PayloadError("nothing to set: give --name, --active/--inactive, --siruk-warehouse-code or "
                           "--armsoft-storage")
    body = G.check_location(body)
    loc = resolve.location(a.ref)
    plan = G.plan_location_set(loc, body)
    if not plan:
        print(f"nothing to change: {loc.get('code')} already has these values")
        return 0
    steps, summary, state = plan
    return guard.run(a, steps=steps, summary=summary, tier="draft", shown_state=state,
                     verify="siruk ops locations list")


def cmd_open_bag(a):
    loc, bag = resolve.location(a.location), resolve.variant(a.bag)
    loose = resolve.variant(a.loose) if a.loose else None
    steps, summary, state, before = G.plan_open_bag(loc, bag, a.bags, loose, a.tag)
    seen = G.Recording(_ops.default())
    rc = guard.run(a, steps=steps, summary=summary, tier="irreversible", shown_state=state,
                   verify=f"siruk ops goods show {bag['variantId']}", client=seen)
    if rc or not seen.answers:
        return rc
    answer = seen.answers[0] or {}
    try:
        fresh = _ops.default().get(f"/goods/{G.good_id(bag)}")
    except _admin.ApiError:
        fresh = None
    now = G.own_quantity(fresh, loc["id"]) if isinstance(fresh, dict) else None
    if before is not None and now is None:
        print("outcome unknown: the bag count could not be read back; check with "
              f"`siruk ops goods show {bag['variantId']}` before repeating", file=sys.stderr)
        return 3
    if G.replayed(before, now, a.bags):
        print(f"refused: Ops returned earlier opening {answer.get('documentNumber')}; nothing opened; "
              "--tag opens another", file=sys.stderr)
        return 1
    return 0


def register(reg):
    p = reg.command(("ops", "goods", "list"), cmd_list, "find goods in Ops with their stock",
                    api=["GET /goods"], roles=ANY, example="siruk ops goods list royal --low")
    p.add_argument("q", nargs="?", help="name, brand, SKU, barcode, accounting code or fiscal name")
    p.add_argument("--location", metavar="REF", help="only goods held there (location code or id)")
    p.add_argument("--low", action="store_true", help="only goods at or below their low-stock level")
    p.add_argument("--unit", choices=G.STOCK_UNITS)
    p.add_argument("--page", type=int)
    p.add_argument("--page-size", type=int)
    p = reg.command(("ops", "goods", "show"), cmd_show, "one good: barcodes, Ops fields, stock per warehouse",
                    api=["GET /goods", "GET /goods/:id"], roles=ANY, example="siruk ops goods show 387957")
    p.add_argument("ref", help="SKU, barcode, accounting code or id")
    p = reg.command(("ops", "goods", "set"), cmd_set, "set the Ops-only fields: fiscal name, ADG, reorder levels",
                    api=["GET /goods", "PATCH /goods/:id"], tier="draft", roles=EDITORS,
                    example='siruk ops goods set 387957 --fiscal-name "Royal Canin Mini 2 kg" --adg 2309.10')
    p.add_argument("ref", help="SKU, barcode, accounting code or id")
    p.add_argument("--fiscal-name", dest="fiscal_name", help="the name on the receipt, at most 50 characters")
    p.add_argument("--adg", help="ADG code: digits and dots")
    p.add_argument("--low-stock-at", dest="low_stock_at", help="base units (g, ml, pcs) or with a unit: 5kg")
    p.add_argument("--reorder-mode", dest="reorder_mode", choices=G.REORDER_MODES)
    p.add_argument("--reorder-point", dest="reorder_point", help="pieces")
    p.add_argument("--reorder-target", dest="reorder_target", help="pieces")
    p.add_argument("--clear", action="append", choices=CLEARABLE, help="empty a field (repeatable)")
    p = reg.command(("ops", "goods", "set-many"), cmd_set_many,
                    "set the Ops-only fields of many goods from a JSON list: one dry run, one code",
                    api=["GET /goods", "PATCH /goods/:id"], tier="draft", roles=EDITORS,
                    example="siruk ops goods set-many fiscal.json")
    p.add_argument("file", help='JSON list of {"ref": SKU, "fiscal_name"?, "adg"?, "low_stock_at"?, '
                                '"reorder_mode"?, "reorder_point"?, "reorder_target"?} (file, \'-\' or inline)')
    p = reg.command(("ops", "goods", "barcode", "add"), cmd_barcode_add, "add an extra barcode to a good",
                    api=["GET /goods", "POST /goods/:id/barcodes"], tier="draft", roles=EDITORS,
                    example="siruk ops goods barcode add 387957 4048422122074 --units 26")
    p.add_argument("ref")
    p.add_argument("code", help="4 to 32 letters, digits or dashes")
    p.add_argument("--units", type=int, help="stock units one scan means (a case of 26)")
    p.add_argument("--receiving-only", action="store_true", help="not sellable at the till")
    p = reg.command(("ops", "goods", "barcode", "rm"), cmd_barcode_rm, "remove an extra barcode from a good",
                    api=["GET /goods", "DELETE /goods/:id/barcodes/:code"], tier="draft", roles=EDITORS,
                    example="siruk ops goods barcode rm 387957 4048422122074")
    p.add_argument("ref")
    p.add_argument("code")
    p = reg.command(("ops", "goods", "plu"), cmd_plu,
                    "make a PLU the main barcode of a loose good (its EAN moves to the extra barcodes)",
                    api=["GET /goods", "PUT /goods/:id/plu"], tier="irreversible", roles=EDITORS,
                    example="siruk ops goods plu 387957-KG 121")
    p.add_argument("ref")
    p.add_argument("plu", type=int, help="1 to 99999")
    reg.command(("ops", "locations", "list"), cmd_locations_list, "locations: shops, storerooms, supplier warehouses",
                api=["GET /locations"], roles=ANY, example="siruk ops locations list")
    p = reg.command(("ops", "locations", "create"), cmd_locations_create, "add a shop or storeroom",
                    api=["GET /locations", "POST /locations"], tier="draft", roles="manager",
                    example='siruk ops locations create --code SH2 --name "Shop 2" --kind shop')
    p.add_argument("--code", required=True, help="1 to 16 letters, digits, dashes or underscores")
    p.add_argument("--name", required=True)
    p.add_argument("--kind", required=True, choices=G.OWN_KINDS)
    p.add_argument("--siruk-warehouse-code", dest="siruk_warehouse_code")
    p.add_argument("--armsoft-storage", dest="armsoft_storage")
    p = reg.command(("ops", "locations", "set"), cmd_locations_set, "rename, (de)activate or re-map a location",
                    api=["GET /locations", "PATCH /locations/:id"], tier="draft", roles="manager",
                    example='siruk ops locations set SH2 --name "Shop 2 (new)"')
    p.add_argument("ref", help="location code or id")
    p.add_argument("--name")
    p.add_argument("--active", dest="active", action="store_const", const=True)
    p.add_argument("--inactive", dest="active", action="store_const", const=False)
    p.add_argument("--siruk-warehouse-code", dest="siruk_warehouse_code")
    p.add_argument("--armsoft-storage", dest="armsoft_storage")
    p.add_argument("--clear", action="append", choices=("siruk-warehouse-code", "armsoft-storage"))
    p = reg.command(("ops", "open-bag"), cmd_open_bag, "open sealed bags: their weight moves to the loose good",
                    api=["GET /goods", "GET /goods/:variantId", "GET /locations", "POST /stock/open-bag"],
                    tier="irreversible", roles=ANY,
                    example="siruk ops open-bag SHOP 387957 2")
    p.add_argument("location", help="location code or id")
    p.add_argument("bag", help="the sealed bag: SKU, barcode or id")
    p.add_argument("bags", type=int, help="how many bags")
    p.add_argument("--loose", metavar="REF", help="the loose good, only when the product has several")
    p.add_argument("--tag", help="makes a deliberate second identical opening a new request")
