"""Ops staff, tills, shop settings and the catalogue auto-sync switch: what each command checks and sends.
Paths and bodies follow ops/apps/api/src/modules/{auth,settings,catalog} (controllers + dto/).

Rules: a body never holds `password` or `pin` and no command can create a till or rotate its key (the server
refuses both to an office key too); a person or till is found by id, exact email or exact name and must be
exactly one; only what differs from the current row is sent; a setting is refused unless GET /settings lists it.
The loud settings below reach hafo, Telegram, Glovo, siruk or the fiscal receipt, so their dry run carries
a warning block.
"""
import difflib, json, urllib.parse

from siruk.ops import client as _ops, resolve
from siruk.ops.guard import Step
from siruk.payload import PayloadError

ROLES = ("owner", "manager", "cashier", "warehouse")   # prisma UserRole
SECRET_FIELDS = ("password", "pin")
MAX_USER_NAME, MAX_TILL_NAME, MAX_EMAIL = 120, 80, 254   # CreateUserDto, UpdateTillDto

LOUD = {
    "reorder.autoPlace": "Ops puts an accepted restock list into hafo's basket by itself, with nobody asked each time.",
    "hafo.placeDryRun": "On, Ops only fills and checks the hafo.am basket and empties it. Off, it can place real orders "
                        "with hafo.",
    "hafo.placeMaxTotalAmd": "The largest hafo order Ops may put in the basket; unset means never. Raising it lets "
                             "bigger real orders go through.",
    "hafo.placeMaxLines": "The most lines one hafo basket may hold; unset means never. Raising it lets bigger real "
                          "orders go through.",
    "telegram.hafoConfirmers": "Who may confirm a hafo basket in Telegram; empty means anyone in the manager chat.",
    "telegram.managerChatId": "The Telegram chat that hears about restock lists and confirms baskets; a wrong id "
                              "hands them to strangers.",
    "glovo.pushAssortment": "Glovo's customers see the prices and free shop stock Ops pushes.",
    "glovo.sendOrderStatus": "Ops tells Glovo 'ready for pickup' on live orders, which sends the courier.",
    "siruk.pushStock": "Ops pushes its stock, cost and barcodes to siruk, the public website.",
    "einvoices.autoPull": "Ops pulls supplier e-invoices from the tax service on a schedule, with the owner's saved "
                          "login.",
    "telegram.ordersChatId": "The Telegram channel that hears about every new order; a wrong id hands orders to "
                             "strangers.",
    "telegram.notifyTillSales": "Till sales are posted to the orders channel too.",
    "hafo.pushToSiruk": "Ops pushes hafo's stock to siruk's hafo warehouse.",
    "reorder.enabled": "Ops builds the hafo restock list every day at 15:30; the manager chat hears about each new "
                       "one.",
    "fiscal.deliveryAdgCode": "The ADG code printed on the delivery line of a web order, on the fiscal receipt.",
}
NOTES = {"stock.lowStockDefault": "this queues a full stock push to siruk"}   # only while siruk.pushStock is on


def _quote(x):
    return urllib.parse.quote(str(x), safe="")


def _body(fields):
    """The fields that were given; a secret never goes out through here."""
    body = {k: v for k, v in fields.items() if v is not None}
    if any(k in body for k in SECRET_FIELDS):
        raise PayloadError("a password or PIN is never set from the CLI: do it in the Ops app")
    return body


def _show(v):
    return "-" if v is None else v if isinstance(v, str) else json.dumps(v)


def _json(v):
    return json.dumps(v, ensure_ascii=False)


def _changes(current, wanted):
    """(body of what differs, 'field: before → after' lines); nothing differing is a refusal."""
    diff = {k: v for k, v in wanted.items() if v is not None and current.get(k) != v}
    if not diff:
        raise PayloadError("nothing to change: that is how it already is")
    return _body(diff), "; ".join(f"{k}: {_show(current.get(k))} → {_show(v)}" for k, v in diff.items())


def _text(value, what, limit):
    value = str(value).strip()
    if not value:
        raise PayloadError(f"{what} must not be empty")
    if len(value) > limit:
        raise PayloadError(f"{what} is at most {limit} characters")
    return value


def _email(value):
    return None if value is None else _text(value, "the email", MAX_EMAIL).lower()   # the server lowercases it


# ------------------------------------------------------------------ staff ----
def people():
    return _ops.default().get("/users") or []


def _who(p):
    return f"{p.get('id')} {p.get('name')} {p.get('email') or '-'} {p.get('role')}"


def find_person(ref):
    ref = str(ref).strip()
    rows, want = people(), ref.lower()
    if resolve.UUID.fullmatch(ref):
        hit = [p for p in rows if (p.get("id") or "").lower() == want]
    else:
        hit = [p for p in rows if p.get("email") and p["email"].lower() == want] or \
              [p for p in rows if (p.get("name") or "").strip().lower() == want]
    return resolve.one(ref, "person", hit, _who)


def staff_state(p):
    return {k: p.get(k) for k in ("id", "name", "email", "role", "isActive", "hasPassword")}


def staff_add(name, role, email, inactive):
    name, email = _text(name, "the name", MAX_USER_NAME), _email(email)
    rows = people()
    if email and any((p.get("email") or "").lower() == email.lower() for p in rows):
        raise PayloadError(f"{email} already belongs to a person: `siruk ops staff set` changes them")
    same = sorted(p["id"] for p in rows if (p.get("name") or "").strip().lower() == name.lower())
    body = _body({"name": name, "role": role, "email": email, "isActive": False if inactive else None})
    note = f" ({len(same)} people already have this name)" if same else ""
    return ([Step("POST", "/users", body)],
            f"add {name} as {role}{' (inactive)' if inactive else ''}; they cannot sign in until the Ops app "
            f"gives them a password or PIN{note}", {"sameName": same})


def staff_set(person, name, role, email, active):
    current = {**person, "email": (person.get("email") or "").lower() or None}
    body, shown = _changes(current, {"name": None if name is None else _text(name, "the name", MAX_USER_NAME),
                                     "role": role, "email": _email(email), "isActive": active})
    if (role or person.get("role")) == "cashier" and person.get("hasPassword"):
        shown += "; their back-office login is removed (a cashier has none)"
    return ([Step("PATCH", f"/users/{_quote(person['id'])}", body, label=person.get("name") or "")],
            f"change {person.get('name')}: {shown}", staff_state(person))


# ------------------------------------------------------------------ tills ----
def tills():
    return _ops.default().get("/tills") or []


def find_till(ref):
    ref = str(ref).strip()
    rows, want = tills(), ref.lower()
    if resolve.UUID.fullmatch(ref):
        hit = [t for t in rows if (t.get("id") or "").lower() == want]
    else:
        hit = [t for t in rows if (t.get("name") or "").strip().lower() == want]
    return resolve.one(ref, "till", hit, lambda t: f"{t.get('id')} {t.get('name')} {t.get('locationName') or '-'}")


def till_set(till, name, active):
    body, shown = _changes(till, {"name": None if name is None else _text(name, "the name", MAX_TILL_NAME),
                                  "isActive": active})
    state = {k: till.get(k) for k in ("id", "name", "isActive")}
    return [Step("PATCH", f"/tills/{_quote(till['id'])}", body, label=till.get("name") or "")], \
        f"change till {till.get('name')}: {shown}", state


# --------------------------------------------------------------- settings ----
def parse_value(text):
    def bad(c):
        raise PayloadError(f"{c} is not JSON")
    try:
        return json.loads(text, parse_constant=bad)
    except ValueError as e:
        raise PayloadError(f"the value must be JSON (true, 5, null, \"text\", [\"a\"]; quote it in the shell): {e}")


def find_setting(key):
    """(the setting's entry, every entry): the second is for what depends on another setting."""
    entries = _ops.default().get("/settings") or []
    hit = [e for e in entries if e.get("key") == key]
    if not hit:
        near = difflib.get_close_matches(key, [e.get("key") for e in entries], n=5, cutoff=0.5)
        raise PayloadError(f"there is no setting {key!r} (`siruk ops settings list`)"
                           + (f"; did you mean: {', '.join(near)}" if near else ""))
    return hit[0], entries


def warning(key, before, after):
    """The block a loud setting's dry run carries; '' for the others."""
    if key not in LOUD:
        return ""
    return (f"!! REAL-WORLD SWITCH: {key}   {_json(before)} → {_json(after)}\n!! {LOUD[key]}\n"
            "!! Nothing on the server stops this: the owner's yes is the only lock.")


def settings_set(entry, value, entries=()):
    key, before = entry["key"], entry.get("value")
    if value is None and entry.get("isDefault"):
        raise PayloadError(f"{key} is already at its default ({_json(before)})")
    if value == before and type(value) is type(before) and not entry.get("isDefault"):
        raise PayloadError(f"{key} is already {_json(before)}")
    block = warning(key, before, value)
    push = any(e.get("key") == "siruk.pushStock" and e.get("value") is True for e in entries)
    note = f" ({NOTES[key]})" if key in NOTES and push else ""
    return ([Step("PUT", f"/settings/{_quote(key)}", {"value": value})],
            f"set {key}: {_json(before)} → {_json(value)}{note}" + (f"\n{block}" if block else ""), before)


# ------------------------------------------------------------- auto-sync ----
def auto_sync(on, status):
    now = status.get("autoSync")
    if now is on:
        raise PayloadError(f"catalogue auto-sync is already {'on' if on else 'off'}")
    was = "unknown" if now is None else "on" if now else "off"
    return ([Step("PUT", "/catalog/auto-sync", {"enabled": on})],
            f"turn the scheduled catalogue pull {'on' if on else 'off'} (now {was})",
            {"autoSync": now})
