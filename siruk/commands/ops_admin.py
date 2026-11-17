"""`siruk ops staff | tills | settings set | catalog auto-sync` — people, tills and shop settings in Ops.

Every write is a dry run showing before → after until `--apply <code>`, and all are real-world: the owner's yes
each time. There is no option for a sign-in secret and no command to create a till or hand out its key: those stay
in the Ops app (an office key may not do them either). The loud settings, the ones that reach hafo, Telegram,
Glovo, siruk or the fiscal receipt, print a warning block in the dry run.
"""
from siruk import output
from siruk.ops import admin as A, client as _ops, guard

MANAGER = "owner, manager"


def _yes(v):
    return "yes" if v else "no"


def _list(a, rows, cols, data):
    if a.json:
        output.dump(data)
        return 0
    if rows:
        output.table(rows, cols)
    else:
        print("nothing")
    return 0


def _run(a, built, verify):
    steps, summary, state = built
    return guard.run(a, steps=steps, summary=summary, tier="real-world", shown_state=state, verify=verify)


# ---------------------------------------------------------------- staff ----
def cmd_staff_list(a):
    r = A.people()
    rows = [{**p, "active": _yes(p.get("isActive")), "login": _yes(p.get("hasPassword")), "till": _yes(p.get("hasPin")),
             "locked": "disabled" if p.get("pinDisabled") else "locked" if p.get("pinLocked") else ""} for p in r]
    return _list(a, rows, [("name", "name"), ("email", "email"), ("role", "role"), ("active", "active"),
                           ("login", "back-office login"), ("till", "till sign-in"), ("locked", "locked"),
                           ("id", "id")], r)


def cmd_staff_add(a):
    return _run(a, A.staff_add(a.name, a.role, a.email, a.inactive), "siruk ops staff list")


def cmd_staff_set(a):
    p = A.find_person(a.person)
    active = False if a.inactive else True if a.active else None
    return _run(a, A.staff_set(p, a.name, a.role, a.email, active), "siruk ops staff list")


# ---------------------------------------------------------------- tills ----
def cmd_tills_list(a):
    r = A.tills()
    return _list(a, [{**t, "active": _yes(t.get("isActive"))} for t in r],
                 [("name", "till"), ("locationName", "location"), ("active", "active"), ("id", "id")], r)


def cmd_tills_set(a):
    t = A.find_till(a.till)
    active = False if a.inactive else True if a.active else None
    return _run(a, A.till_set(t, a.name, active), "siruk ops tills list")


# ------------------------------------------------------ settings, catalogue ----
def cmd_settings_set(a):
    entry, entries = A.find_setting(a.key)
    return _run(a, A.settings_set(entry, A.parse_value(a.value), entries), "siruk ops settings list")


def cmd_auto_sync(a):
    status = _ops.default().get("/catalog/status") or {}
    return _run(a, A.auto_sync(a.state == "on", status), "siruk ops catalog status")


# ---------------------------------------------------------------- registration ----
def _active_flags(p, what):
    g = p.add_mutually_exclusive_group()
    g.add_argument("--active", action="store_true", help=f"let {what} work")
    g.add_argument("--inactive", action="store_true", help=f"stop {what} working")


def register(reg):
    reg.command(("ops", "staff", "list"), cmd_staff_list, "the people in Ops, their role and whether they can sign in",
                api=["GET /users"], roles=MANAGER, example="siruk ops staff list")
    p = reg.command(("ops", "staff", "add"), cmd_staff_add, "add a person (no sign-in is set up here)",
                    api=["GET /users", "POST /users"], tier="real-world", roles=MANAGER,
                    example="siruk ops staff add --name 'Anna Petrosyan' --role cashier")
    p.add_argument("--name", required=True)
    p.add_argument("--role", required=True, choices=A.ROLES)
    p.add_argument("--email")
    p.add_argument("--inactive", action="store_true", help="add them switched off")

    p = reg.command(("ops", "staff", "set"), cmd_staff_set, "change a person's name, email, role or whether they are active",
                    api=["GET /users", "PATCH /users/:id"], tier="real-world", roles=MANAGER,
                    example="siruk ops staff set boris@example.am --role warehouse")
    p.add_argument("person", metavar="PERSON", help="id, exact email or exact name")
    p.add_argument("--name")
    p.add_argument("--role", choices=A.ROLES)
    p.add_argument("--email")
    _active_flags(p, "them")

    reg.command(("ops", "tills", "list"), cmd_tills_list, "the tills and whether each is active",
                api=["GET /tills"], roles=MANAGER, example="siruk ops tills list")
    p = reg.command(("ops", "tills", "set"), cmd_tills_set, "rename a till or switch it on or off",
                    api=["GET /tills", "PATCH /tills/:id"], tier="real-world", roles=MANAGER,
                    example="siruk ops tills set 'Till 2' --inactive")
    p.add_argument("till", metavar="TILL", help="id or exact name")
    p.add_argument("--name")
    _active_flags(p, "the till")

    p = reg.command(("ops", "settings", "set"), cmd_settings_set,
                    "change one shop setting (before → after; the loud ones carry a warning)",
                    api=["GET /settings", "PUT /settings/:key"], tier="real-world", roles=MANAGER,
                    example="siruk ops settings set telegram.managerChatId '\"-100123\"'")
    p.add_argument("key", help="a key from `ops settings list`")
    p.add_argument("value", help="JSON: true, 5, null (back to the default where allowed), \"text\", [\"a\"]; "
                              "Telegram ids are strings, e.g. '\"-100123\"'")

    p = reg.command(("ops", "catalog", "auto-sync"), cmd_auto_sync, "turn the scheduled catalogue pull on or off",
                    api=["GET /catalog/status", "PUT /catalog/auto-sync"], tier="real-world", roles=MANAGER,
                    example="siruk ops catalog auto-sync off")
    p.add_argument("state", choices=("on", "off"))
