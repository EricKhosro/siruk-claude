"""Ops staff, tills, settings and auto-sync. Paths and bodies are the Ops sources':
siruk-web/ops/apps/api/src/modules/auth/{users,tills}.controller.ts + dto/{create-user,update-user,update-till}.dto.ts,
settings/settings.controller.ts + settings.definitions.ts, catalog/catalog.controller.ts + dto/set-auto-sync.dto.ts;
fixture shapes are siruk-web/ops/packages/contracts/src/api/{auth,backoffice}.ts."""
import json, re

import pytest

from siruk import cli, commands
from siruk.ops import admin as A

ANNA = "0b9c3a52-7c1d-4e0a-9d52-3f1d6c1f0a11"
BORIS = "0b9c3a52-7c1d-4e0a-9d52-3f1d6c1f0a12"
BORIS2 = "0b9c3a52-7c1d-4e0a-9d52-3f1d6c1f0a13"
TILL = "9c1d2e3f-4a5b-4c6d-8e7f-0a1b2c3d4e5f"
TILL2 = "9c1d2e3f-4a5b-4c6d-8e7f-0a1b2c3d4e60"
LOC = "11111111-1111-4111-8111-111111111111"
NAMES = ["ops staff list", "ops staff add", "ops staff set", "ops tills list", "ops tills set",
         "ops settings set", "ops catalog auto-sync"]


@pytest.fixture(autouse=True)
def only_ops_admin(monkeypatch):
    monkeypatch.setattr(commands, "GROUPS", ("ops_core", "ops_admin"))


# contracts/src/api/auth.ts StaffUser
def user(uid, name, email, role="cashier", active=True, **over):
    return {"id": uid, "name": name, "email": email, "role": role, "isActive": active, "hasPassword": False,
            "hasPin": True, "pinLocked": False, "pinDisabled": False, "pinLastFailureAt": None,
            "createdAt": "2026-10-01T08:00:00.000Z", **over}


# contracts/src/api/auth.ts TillSummary
def till(tid, name, active=True):
    return {"id": tid, "name": name, "locationId": LOC, "locationName": "Main shop", "isActive": active,
            "createdAt": "2026-10-01T08:00:00.000Z"}


# contracts/src/api/auth.ts SettingEntry
def entry(key, value, default=None, is_default=False):
    return {"key": key, "value": value, "default": default, "isDefault": is_default,
            "description": "d", "updatedAt": None}


class Shop:
    """The faked Ops: its rows can change between a dry run and the apply."""

    def __init__(self, fake):
        self.users = [user(ANNA, "Anna Petrosyan", "anna@siruk.am", "manager"), user(BORIS, "Boris Avetyan", None)]
        self.tills = [till(TILL, "Till 1"), till(TILL2, "Till 2")]
        self.settings = [entry("hafo.placeDryRun", True, True, True), entry("stock.lowStockDefault", None, None, True),
                         entry("reorder.autoPlace", False, False, True), entry("glovo.pushAssortment", False, False)]
        self.status = {"lastSyncAt": None, "autoSync": True, "tokenSource": "stored", "running": False}
        fake.on("GET", "/users", lambda p: self.users)
        fake.on("GET", "/tills", lambda p: self.tills)
        fake.on("GET", "/settings", lambda p: self.settings)
        fake.on("GET", "/catalog/status", lambda p: self.status)
        fake.on("POST", "/users", lambda b: user("new", b["name"], b.get("email"), b["role"]))
        fake.on("PATCH", re.compile(r"/users/[^/]+"), lambda b: self.users[0])
        fake.on("PATCH", re.compile(r"/tills/[^/]+"), lambda b: self.tills[0])
        fake.on("PUT", re.compile(r"/settings/[^/]+"), lambda b: self.settings[0])
        fake.on("PUT", "/catalog/auto-sync", lambda b: self.status)
        self.fake = fake


@pytest.fixture
def shop(ops_fake):
    return Shop(ops_fake)


def run(argv):
    with pytest.raises(SystemExit) as e:
        cli.main(["-q", *argv])
    return e.value.code


def writes(fake):
    return [c for c in fake.calls if c[0] != "GET"]


def dry(argv, capsys):
    capsys.readouterr()
    assert run([*argv, "--json"]) == 0
    return json.loads(capsys.readouterr().out)


def applied(argv, capsys, shop):
    """Dry run (writes nothing), then the same command with its code; returns the one write."""
    d = dry(argv, capsys)
    assert d["dry_run"] is True and d["tier"] == "real-world" and writes(shop.fake) == []
    assert run([*argv, "--apply", d["code"]]) == 0
    assert len(writes(shop.fake)) == 1
    return writes(shop.fake)[0]


def no_secret(body):
    assert not set(body) & {"password", "pin"}, body


# ------------------------------------------------------------------ manifest ----
def test_commands_exist_with_manifest_fields_and_every_write_is_real_world(capsys):
    assert run(["commands", "--json"]) == 0
    rows = {r["name"]: r for r in json.loads(capsys.readouterr().out)}
    for n in NAMES:
        r = rows[n]
        assert r["backend"] == "ops" and r["api"] and r["roles"] and r["help"] and r["example"], n
        assert r["example"].startswith("siruk " + n.split()[0]) and r["tier"] == ("read" if n.endswith("list") else "real-world")
    assert not any("rotate-key" in e or e.startswith("POST /tills") for r in rows.values() for e in r["api"])


def test_the_parser_has_no_password_or_pin_option(capsys):
    for argv in (["staff", "add", "--name", "X", "--role", "cashier"], ["staff", "set", "Anna Petrosyan"]):
        for opt in ("--password", "--pin"):
            capsys.readouterr()
            assert run(["ops", *argv, opt, "1234"]) == 2
            assert "unrecognized arguments" in capsys.readouterr().err
    for argv in (["staff", "add"], ["staff", "set"], ["tills", "set"], ["settings", "set"]):
        with pytest.raises(SystemExit):
            cli.main(["ops", *argv, "--help"])
        assert not re.search(r"password|\bpin\b", capsys.readouterr().out, re.I), argv


def test_no_tills_create_or_rotate_command_exists(capsys):
    for argv in (["tills", "create"], ["tills", "add"], ["tills", "rotate-key"]):
        assert run(["ops", *argv]) == 2
        capsys.readouterr()


def test_admin_rejects_a_body_with_a_secret():
    from siruk.payload import PayloadError
    with pytest.raises(PayloadError):
        A._body({"name": "x", "pin": "1234"})


# --------------------------------------------------------------------- staff ----
def test_staff_list_shows_roles_and_json_is_unmodified(shop, capsys):
    assert run(["ops", "staff", "list"]) == 0
    out = capsys.readouterr().out
    assert "Anna Petrosyan" in out and "manager" in out
    assert run(["ops", "staff", "list", "--json"]) == 0
    assert json.loads(capsys.readouterr().out) == shop.users


def test_staff_add_posts_the_create_user_dto_fields(shop, capsys):
    # create-user.dto.ts: name, email?, role, isActive? (password and pin exist there; the CLI never sends them)
    call = applied(["ops", "staff", "add", "--name", " Carlos Dun ", "--role", "warehouse", "--email", "c@siruk.am",
                    "--inactive"], capsys, shop)
    assert call == ("POST", "/users", {"name": "Carlos Dun", "role": "warehouse", "email": "c@siruk.am",
                                       "isActive": False})
    no_secret(call[2])


def test_staff_add_minimal_body_and_an_email_already_taken_is_refused(shop, capsys):
    call = applied(["ops", "staff", "add", "--name", "Dana", "--role", "cashier"], capsys, shop)
    assert call == ("POST", "/users", {"name": "Dana", "role": "cashier"})
    shop.fake.calls.clear()
    assert run(["ops", "staff", "add", "--name", "Other", "--role", "cashier", "--email", "ANNA@siruk.am"]) == 1
    assert writes(shop.fake) == []


def test_staff_add_refuses_a_role_the_enum_lacks(shop):
    assert run(["ops", "staff", "add", "--name", "X", "--role", "admin"]) == 2


def test_staff_set_sends_only_what_changes_and_shows_before_after(shop, capsys):
    # update-user.dto.ts: name?, email?, role?, isActive?
    d = dry(["ops", "staff", "set", "anna@siruk.am", "--role", "cashier", "--name", "Anna Petrosyan", "--inactive"], capsys)
    assert d["requests"][0]["body"] == {"role": "cashier", "isActive": False}
    assert "role: manager → cashier" in d["summary"] and "isActive: true → false" in d["summary"]
    shop.fake.calls.clear()
    call = applied(["ops", "staff", "set", ANNA, "--email", "anna@new.am"], capsys, shop)
    assert call == ("PATCH", f"/users/{ANNA}", {"email": "anna@new.am"})
    no_secret(call[2])


def test_staff_set_finds_a_person_by_id_email_or_exact_name_and_refuses_no_change(shop, capsys):
    for ref in (ANNA, "ANNA@siruk.am", "anna petrosyan"):
        assert dry(["ops", "staff", "set", ref, "--role", "owner"], capsys)["requests"][0]["path"] == f"/users/{ANNA}"
    assert run(["ops", "staff", "set", "Anna Petrosyan"]) == 1
    assert run(["ops", "staff", "set", "Anna Petrosyan", "--role", "manager"]) == 1
    assert run(["ops", "staff", "set", "Nobody", "--role", "owner"]) == 1
    assert writes(shop.fake) == []


def test_two_people_with_the_same_name_are_refused_with_the_candidates(shop, capsys):
    shop.users += [user(BORIS2, "Boris Avetyan", "boris2@siruk.am")]
    capsys.readouterr()
    assert run(["ops", "staff", "set", "Boris Avetyan", "--role", "manager"]) == 1
    err = capsys.readouterr().err
    assert BORIS in err and BORIS2 in err and "boris2@siruk.am" in err
    assert writes(shop.fake) == []
    assert dry(["ops", "staff", "set", BORIS2, "--role", "manager"], capsys)["requests"][0]["path"] == f"/users/{BORIS2}"


def test_making_a_person_with_a_login_a_cashier_says_the_login_is_removed(shop, capsys):
    # users.service.ts update(): role cashier with a passwordHash clears it
    shop.users[0]["hasPassword"] = True
    d = dry(["ops", "staff", "set", ANNA, "--role", "cashier"], capsys)
    assert "back-office login is removed" in d["summary"]
    assert "back-office login" not in dry(["ops", "staff", "set", ANNA, "--role", "warehouse"], capsys)["summary"]
    shop.users[0]["hasPassword"] = False
    assert "back-office login" not in dry(["ops", "staff", "set", ANNA, "--role", "cashier"], capsys)["summary"]
    shop.users[0]["hasPassword"] = True
    code = dry(["ops", "staff", "set", ANNA, "--role", "warehouse"], capsys)["code"]
    shop.users[0]["hasPassword"] = False   # hasPassword is part of the shown state
    assert run(["ops", "staff", "set", ANNA, "--role", "warehouse", "--apply", code]) == 1


def test_an_email_is_compared_and_sent_in_lower_case(shop, capsys):
    shop.users[0]["email"] = "Anna@Siruk.am"
    assert run(["ops", "staff", "set", ANNA, "--email", "ANNA@SIRUK.AM"]) == 1   # same address
    call = applied(["ops", "staff", "set", ANNA, "--email", "New@Siruk.am"], capsys, shop)
    assert call[2] == {"email": "new@siruk.am"}


def test_staff_set_active_and_inactive_cannot_be_combined(shop):
    assert run(["ops", "staff", "set", "Anna Petrosyan", "--active", "--inactive"]) == 2


def test_a_staff_change_between_dry_run_and_apply_invalidates_the_code(shop, capsys):
    argv = ["ops", "staff", "set", ANNA, "--role", "cashier"]
    code = dry(argv, capsys)["code"]
    shop.users[0]["name"] = "Anna P."
    assert run([*argv, "--apply", code]) == 1
    assert writes(shop.fake) == []


# --------------------------------------------------------------------- tills ----
def test_tills_list(shop, capsys):
    assert run(["ops", "tills", "list"]) == 0
    assert "Till 2" in capsys.readouterr().out
    assert run(["ops", "tills", "list", "--json"]) == 0
    assert json.loads(capsys.readouterr().out) == shop.tills


def test_tills_set_patches_the_update_till_dto_fields(shop, capsys):
    # update-till.dto.ts: name?, isActive?
    call = applied(["ops", "tills", "set", "till 2", "--name", "Back till", "--inactive"], capsys, shop)
    assert call == ("PATCH", f"/tills/{TILL2}", {"name": "Back till", "isActive": False})
    shop.fake.calls.clear()
    assert run(["ops", "tills", "set", TILL, "--active"]) == 1   # already active: nothing to change
    assert run(["ops", "tills", "set", TILL]) == 1
    assert run(["ops", "tills", "set", "Till 3", "--inactive"]) == 1
    assert writes(shop.fake) == []


def test_tills_set_with_a_name_two_tills_share_lists_both(shop, capsys):
    shop.tills[1]["name"] = "Till 1"
    capsys.readouterr()
    assert run(["ops", "tills", "set", "Till 1", "--inactive"]) == 1
    err = capsys.readouterr().err
    assert TILL in err and TILL2 in err


# ------------------------------------------------------------------ settings ----
def test_settings_set_puts_the_value_as_json_and_shows_before_after(shop, capsys):
    # settings.controller.ts PUT :key, put-setting.dto.ts { value }
    d = dry(["ops", "settings", "set", "stock.lowStockDefault", "12"], capsys)
    assert d["requests"][0]["method"] == "PUT" and d["requests"][0]["body"] == {"value": 12}
    assert "null → 12" in d["summary"]
    shop.fake.calls.clear()
    call = applied(["ops", "settings", "set", "stock.lowStockDefault", "12"], capsys, shop)
    assert call == ("PUT", "/settings/stock.lowStockDefault", {"value": 12})


def test_settings_set_unknown_key_or_bad_json_is_refused_before_any_call(shop, capsys):
    shop.fake.calls.clear()
    capsys.readouterr()
    assert run(["ops", "settings", "set", "hafo.placeDryRn", "false"]) == 1
    assert "hafo.placeDryRun" in capsys.readouterr().err   # the near miss is offered
    assert run(["ops", "settings", "set", "stock.lowStockDefault", "twelve"]) == 1
    assert run(["ops", "settings", "set", "stock.lowStockDefault", "NaN"]) == 1
    assert all(c[0] == "GET" for c in shop.fake.calls) and writes(shop.fake) == []


def test_unknown_key_makes_no_settings_write_even_with_a_code(shop):
    assert run(["ops", "settings", "set", "nope.key", "true", "--apply", "deadbeef"]) == 1
    assert writes(shop.fake) == []


@pytest.mark.parametrize("key,value", [("hafo.placeDryRun", "false"), ("reorder.autoPlace", "true"),
                                       ("glovo.pushAssortment", "true")])
def test_a_loud_setting_dry_run_carries_the_warning_block(shop, capsys, key, value):
    capsys.readouterr()
    assert run(["ops", "settings", "set", key, value]) == 0
    out = capsys.readouterr().out
    assert "REAL-WORLD SWITCH" in out and A.LOUD[key] in out and "nothing sent" in out
    assert "owner's yes" in out
    assert "REAL-WORLD SWITCH" in dry(["ops", "settings", "set", key, value], capsys)["summary"]


def test_a_quiet_setting_dry_run_has_no_warning_block(shop, capsys):
    capsys.readouterr()
    assert run(["ops", "settings", "set", "stock.lowStockDefault", "5"]) == 0
    assert "REAL-WORLD" not in capsys.readouterr().out


def test_low_stock_default_says_it_queues_a_siruk_push_only_while_siruk_push_stock_is_on(shop, capsys):
    argv = ["ops", "settings", "set", "stock.lowStockDefault", "5"]
    assert "queues" not in dry(argv, capsys)["summary"]   # siruk.pushStock is off (queueStockPush returns early)
    shop.settings.append(entry("siruk.pushStock", True, False))
    assert "queues a full stock push to siruk" in dry(argv, capsys)["summary"]


def test_null_on_a_setting_already_at_its_default_is_refused(shop):
    assert run(["ops", "settings", "set", "stock.lowStockDefault", "null"]) == 1
    shop.settings[1].update(value=5, isDefault=False)
    assert run(["ops", "settings", "set", "stock.lowStockDefault", "null"]) == 0


def test_the_settings_help_shows_telegram_ids_as_json_strings(capsys):
    with pytest.raises(SystemExit):
        cli.main(["ops", "settings", "set", "--help"])
    assert "'\"-100123\"'" in capsys.readouterr().out


def test_the_loud_keys_are_exactly_these_in_one_constant():
    assert set(A.LOUD) == {"telegram.ordersChatId", "telegram.notifyTillSales", "hafo.pushToSiruk",
                           "reorder.enabled", "fiscal.deliveryAdgCode", "reorder.autoPlace", "hafo.placeDryRun",
                           "hafo.placeMaxTotalAmd", "hafo.placeMaxLines", "telegram.hafoConfirmers", "telegram.managerChatId", "glovo.pushAssortment",
                           "glovo.sendOrderStatus", "siruk.pushStock", "einvoices.autoPull"}


def test_a_setting_changed_between_dry_run_and_apply_invalidates_the_code(shop, capsys):
    argv = ["ops", "settings", "set", "stock.lowStockDefault", "12"]
    code = dry(argv, capsys)["code"]
    shop.settings[1].update(value=9, isDefault=False)   # someone set a third value meanwhile
    capsys.readouterr()
    assert run([*argv, "--apply", code]) == 1
    assert "different plan" in capsys.readouterr().err
    assert writes(shop.fake) == []
    assert run([*argv, "--apply", dry(argv, capsys)["code"]]) == 0   # the fresh code works


def test_setting_a_value_it_already_has_is_refused_unless_it_is_only_the_default(shop):
    assert run(["ops", "settings", "set", "glovo.pushAssortment", "false"]) == 1
    assert run(["ops", "settings", "set", "reorder.autoPlace", "false"]) == 0   # still the default: this pins it


# ----------------------------------------------------------------- auto-sync ----
def test_catalog_auto_sync_puts_enabled(shop, capsys):
    # catalog.controller.ts PUT auto-sync, set-auto-sync.dto.ts { enabled: boolean }
    assert applied(["ops", "catalog", "auto-sync", "off"], capsys, shop) == ("PUT", "/catalog/auto-sync",
                                                                             {"enabled": False})
    shop.fake.calls.clear()
    assert run(["ops", "catalog", "auto-sync", "on"]) == 1   # already on
    shop.status["autoSync"] = False
    assert applied(["ops", "catalog", "auto-sync", "on"], capsys, shop)[2] == {"enabled": True}


def test_auto_sync_state_change_invalidates_the_code(shop, capsys):
    argv = ["ops", "catalog", "auto-sync", "off"]
    shop.status.clear()   # the status is unknown at the dry run
    code = dry(argv, capsys)["code"]
    shop.status["autoSync"] = True
    capsys.readouterr()
    assert run([*argv, "--apply", code]) == 1
    assert "different plan" in capsys.readouterr().err
    assert writes(shop.fake) == []


def test_auto_sync_with_no_status_says_unknown(shop, capsys):
    shop.status.clear()
    assert dry(["ops", "catalog", "auto-sync", "off"], capsys)["summary"].endswith("(now unknown)")


def test_the_code_is_valid_only_for_the_environment_it_was_made_against(shop, capsys):
    code = dry(["ops", "settings", "set", "stock.lowStockDefault", "7"], capsys)["code"]
    shop.fake.base = "https://other.offline.test/api"
    assert run(["ops", "settings", "set", "stock.lowStockDefault", "7", "--apply", code]) == 1
    assert writes(shop.fake) == []
