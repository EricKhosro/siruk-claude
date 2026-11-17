"""Admin foundation: the write guard and its writer, the policy, `siruk admin api`, and `register_crud`.
Shapes come from siruk-web/backend: routes/admin.php (what exists), Http/Controllers/Admin/Catalog/BrandController.php
(`validatedData` requires name and slug; `index` is an unpaginated `->get()`; destroy answers 204) and
Http/Resources/Admin/Catalog/BrandResource.php (the record). A validation error is Laravel's
`{message, errors}`; `search` and `perPage` are read from the request, the page count from `meta.last_page`."""
import argparse, io, json, urllib.error

import pytest

from siruk import cli, client as C, commands, config
from siruk.admin import guard, policy, resource
from siruk.admin.guard import Step
from siruk.ops import client as O

from admin_fakes import FakePacer

# BrandResource::toArray
def brand(i=5, **kw):
    return {"id": i, "name": "Gemon", "slug": "gemon", "image": None, "productsCount": 0, "deleteLocked": False,
            "createdAt": "2026-01-02T03:04:05.000000Z", "updatedAt": "2026-01-02T03:04:05.000000Z", **kw}


BRANDS = resource.Resource("brand", "/brands", required=("name", "slug"), label="name",
                           source="Http/Controllers/Admin/Catalog/BrandController.php")
VALIDATION = {"message": "The name field is required.", "errors": {"name": ["The name field is required."]}}


def run(argv):
    with pytest.raises(SystemExit) as e:
        cli.main(["-q", *argv])
    return e.value.code


def writes(fc):
    return [c for c in fc.calls if c[0] != "GET"]


def plan_code(capsys, argv):
    assert run([*argv, "--json"]) == 0
    return json.loads(capsys.readouterr().out)["code"]


# ------------------------------------------------------------- the seam ----
def test_parser_builds_with_only_admin_core(monkeypatch):
    monkeypatch.setattr(commands, "GROUPS", ("admin_core", "no_such_admin_group"))
    a = cli.build_parser().parse_args(["admin", "api", "GET", "/brands"])
    assert a.fn and a.cmd == "admin"


def test_commands_lists_admin_api(capsys):
    assert run(["commands", "--json"]) == 0
    by = {r["name"]: r for r in json.loads(capsys.readouterr().out)}
    assert by["admin api"]["backend"] == "admin" and by["admin api"]["tier"] == "irreversible"
    assert "api" in by and by["api"]["backend"] == "admin"


def test_admin_help_names_the_group(capsys):
    with pytest.raises(SystemExit) as e:
        cli.main(["--help"])
    assert e.value.code == 0 and "the admin panel through its API" in capsys.readouterr().out


# ------------------------------------------------------- the writer, real Client ----
class Resp(io.BytesIO):
    def __init__(self, status, raw):
        super().__init__(raw)
        self.status = status


def real_client(seq, seen, monkeypatch, token="T"):
    """A real Client over a scripted opener, with a config that WOULD retry: one attempt is what is asserted."""
    monkeypatch.delenv("SIRUK_LANG", raising=False)
    cfg = config.load(env={"SIRUK_CONFIG": "nonexistent.json", "SIRUK_NO_PACE": "1"})
    cfg["retry"].update(attempts=3, backoff_seconds=0)

    def opener(req, timeout=None):
        seen.append(req)
        step = seq.pop(0)
        if isinstance(step, Exception):
            raise step
        status, raw = step
        if status >= 400:
            raise urllib.error.HTTPError(req.full_url, status, "x", {}, io.BytesIO(raw))
        return Resp(status, raw)
    c = C.Client(base="https://x.test/api/admin", token=token, opener=opener, sleep=lambda s: None,
                 cfg_loader=lambda: cfg, pacer=FakePacer())
    C.set_default(c)
    return c


@pytest.fixture(autouse=False)
def reset_default():
    yield
    C.set_default(None)


@pytest.mark.parametrize("step", [urllib.error.URLError("down"), (502, b"bad gateway"), (504, b""),
                                  (200, b"<html>maintenance</html>")])
def test_writer_one_attempt_and_unknown_outcome(step, monkeypatch, reset_default):
    seen = []
    real_client([step, (200, b"{}"), (200, b"{}")], seen, monkeypatch)
    with pytest.raises(O.UnknownOutcome):
        guard.writer().write("POST", "/brands", {"name": "x"})
    assert len(seen) == 1


def test_writer_422_is_an_api_error_not_unknown(monkeypatch, reset_default):
    seen = []
    real_client([(422, json.dumps(VALIDATION).encode())], seen, monkeypatch)
    with pytest.raises(C.ApiError) as e:
        guard.writer().write("POST", "/brands", {})
    assert not isinstance(e.value, O.UnknownOutcome) and e.value.status == 422 and len(seen) == 1


def test_writer_sends_content_language_and_an_empty_204_is_none(monkeypatch, reset_default):
    seen = []
    real_client([(204, b""), (200, b'{"data": {"id": 5}}')], seen, monkeypatch)
    assert guard.writer("ru").write("DELETE", "/brands/5") is None
    assert guard.writer().write("PUT", "/brands/5", {"name": "x"}) == {"data": {"id": 5}}
    assert dict(seen[0].header_items())["Content-language"] == "ru"
    assert "Content-language" not in dict(seen[1].header_items())


def test_writer_without_a_token_sends_nothing_and_is_not_unknown(monkeypatch, tmp_path, reset_default):
    seen = []
    monkeypatch.delenv("SIRUK_TOKEN", raising=False)
    monkeypatch.setenv("SIRUK_TOKEN_FILE", str(tmp_path / "no-token"))
    real_client([], seen, monkeypatch, token=None)
    with pytest.raises(C.ApiError) as e:
        guard.writer().write("POST", "/brands", {})
    assert not isinstance(e.value, O.UnknownOutcome) and seen == []


# ---------------------------------------------------------- the guard ----
def args(**kw):
    return argparse.Namespace(**{"json": True, "apply": None, **kw})


def steps2():
    return [Step("POST", "/brands", {"name": "A", "slug": "a"}, "first"),
            Step("PUT", "/brands/5", {"name": "B", "slug": "b"}, "second")]


def code_of(capsys, **kw):
    assert guard.run(args(), **{"steps": steps2(), "summary": "s", "tier": "draft", **kw}) == 0
    return json.loads(capsys.readouterr().out)["code"]


def test_dry_run_sends_nothing(admin_fake, capsys):
    assert guard.run(args(), steps=steps2(), summary="two brands", tier="draft") == 0
    out = json.loads(capsys.readouterr().out)
    assert out["dry_run"] and len(out["requests"]) == 2 and admin_fake.calls == []


def test_wrong_code_exits_1_and_sends_nothing(admin_fake, capsys):
    assert guard.run(args(apply="deadbeef"), steps=steps2(), summary="s", tier="draft") == 1
    assert admin_fake.calls == [] and "different plan" in capsys.readouterr().err


def test_right_code_sends_each_step_once(admin_fake, capsys):
    admin_fake.on("POST", "/brands", {"data": brand(6)}).on("PUT", "/brands/5", {"data": brand(5)})
    code = code_of(capsys)
    assert guard.run(args(apply=code), steps=steps2(), summary="s", tier="draft") == 0
    assert [c[:2] for c in admin_fake.calls] == [("POST", "/brands"), ("PUT", "/brands/5")]
    assert admin_fake.calls[0][2] == {"name": "A", "slug": "a"}


def test_lang_and_shown_state_change_the_code(admin_fake, capsys):
    base = code_of(capsys)
    assert code_of(capsys) == base
    assert len({base, code_of(capsys, lang="ru"), code_of(capsys, lang="hy"),
                code_of(capsys, shown_state={"name": "old"})}) == 4
    admin_fake.on("POST", "/brands", {}).on("PUT", "/brands/5", {})
    assert guard.run(args(apply=base), steps=steps2(), summary="s", tier="draft", lang="ru") == 1
    assert admin_fake.calls == []


def test_lang_goes_out_as_content_language(admin_fake, capsys):
    admin_fake.on("PUT", "/brands/5", {"data": brand()})
    s = [Step("PUT", "/brands/5", {"name": "Джемон"})]
    assert guard.run(args(), steps=s, summary="s", tier="draft", lang="ru") == 0
    code = json.loads(capsys.readouterr().out)["code"]
    assert guard.run(args(apply=code), steps=s, summary="s", tier="draft", lang="ru") == 0
    assert admin_fake.langs == ["ru"]


def test_policy_refusal_sends_nothing_and_exits_1(admin_fake, capsys):
    assert guard.run(args(apply="x"), steps=[Step("PUT", "/products/5", {})], summary="s", tier="draft") == 1
    assert admin_fake.calls == [] and "refused" in capsys.readouterr().err


def test_unknown_outcome_exits_3_and_a_422_exits_2(admin_fake, capsys):
    s = [Step("POST", "/brands", {"name": "A", "slug": "a"})]
    code = code_of(capsys, steps=s)
    admin_fake.on("POST", "/brands", C.ApiError(502, "POST", "/brands", "bad gateway"))
    # the fake raises what Client.request would; the writer turns a gateway answer into UnknownOutcome
    assert guard.run(args(apply=code), steps=s, summary="s", tier="draft") == 3
    admin_fake.on("POST", "/brands", C.ApiError(422, "POST", "/brands", json.dumps(VALIDATION)))
    assert guard.run(args(apply=code), steps=s, summary="s", tier="draft") == 2
    assert len(admin_fake.calls) == 2


# ---------------------------------------------------------- the policy ----
@pytest.mark.parametrize("method,path", [
    ("POST", "/create-new-admin-user"), ("POST", "/api-keys"), ("DELETE", "/customers/5"), ("PUT", "/products/5"),
    ("POST", "/products/bulk"), ("PUT", "/stock/variants/5"), ("POST", "/medias-clear-unused"),
    ("POST", "/clear-logs"), ("POST", "/login"), ("POST", "/logout"), ("PUT", "/update-admin-user/3"),
    ("POST", "/update-current-user"), ("POST", "/api-keys/4/revoke"), ("DELETE", "/admin-users/3"),
    ("POST", "/web-push-tokens"), ("POST", "/medias"), ("POST", "/medias-replace"), ("PUT", "/global-data"),
    ("POST", "/reposition"), ("POST", "/replicate-record"), ("PUT", "/products/bulk"), ("POST", "/products"),
    ("POST", "/products/export"), ("POST", "/stock/variants/5/receive"), ("POST", "/orders/5/refund"),
    ("DELETE", "/orders/5"), ("POST", "/pages-x"), ("POST", "/brandsx"), ("PUT", "/brands?x=1"),
    ("PUT", "/brands/%2e%2e/stock"), ("PUT", "/brands//5"), ("POST", "/Products/5"), ("POST", "brands"),
    ("POST", "/products/5/merge/x"), ("POST", "/brands/"), ("PUT", "/BRANDS/5"), ("PUT", "/brands/5/"),
    ("POST", "//brands"), ("PUT", "/brands//5")])
def test_refused_and_nothing_sent(admin_fake, method, path):
    assert policy.allowed(method, path)
    assert guard.run(args(), steps=[Step(method, path, {})], summary="s", tier="draft") == 1
    assert admin_fake.calls == []


@pytest.mark.parametrize("method,path", [
    ("POST", "/orders/5/update-status"), ("POST", "/orders/5/update-payment-status"),
    ("POST", "/update-order-payment-type"), ("POST", "/payments/9/check-status"),
    ("POST", "/customers/5/adjust-balance"), ("PUT", "/categories/5"), ("POST", "/brands"), ("DELETE", "/brands/5"),
    ("PUT", "/promotions/2"), ("POST", "/campaigns/2/send"), ("PUT", "/delivery-settings"),
    ("PUT", "/pages/about"), ("POST", "/search/index/rebuild"), ("POST", "/algolia/sync-all"),
    ("PUT", "/product-variants/9"), ("POST", "/products/5/discontinue"), ("POST", "/products/5/merge"),
    ("PUT", "/listing-groups"), ("PUT", "/supplier-products/3"), ("POST", "/ops/orders/7/resend"),
    ("GET", "/admin-users"), ("GET", "/products/5"), ("GET", "/stock?search=x"),
    ("HEAD", "/medias")])
def test_allowed(method, path):
    assert policy.allowed(method, path) is None


@pytest.mark.parametrize("path,fixed", [("/brands/", "/brands"), ("/BRANDS/5", "/brands/5"), ("//brands", "/brands"),
                                         ("/brands/5/", "/brands/5")])
def test_a_path_the_server_would_redirect_names_the_canonical_one(admin_fake, capsys, path, fixed):
    assert policy.allowed("PUT", path) == f"use the canonical path {fixed}"
    assert guard.run(args(apply="x"), steps=[Step("PUT", path, {})], summary="s", tier="draft") == 1
    assert admin_fake.calls == [] and f"use the canonical path {fixed}" in capsys.readouterr().err
    assert policy.allowed("PUT", fixed) is None


# ------------------------------------------------------- siruk admin api ----
def test_admin_api_get_is_free_and_sends_lang(admin_fake, capsys):
    admin_fake.on("GET", "/brands", {"data": [brand()]})
    assert run(["admin", "api", "GET", "/brands", "--lang", "hy"]) == 0
    assert json.loads(capsys.readouterr().out)["data"][0]["slug"] == "gemon"
    assert admin_fake.calls == [("GET", "/brands", {})] and admin_fake.langs == ["hy"]


def test_admin_api_write_is_a_dry_run_then_a_code(admin_fake, capsys):
    admin_fake.on("POST", "/brands", {"data": brand(7)})
    body = '{"name": "New", "slug": "new"}'
    assert run(["admin", "api", "POST", "/brands", body]) == 0
    out = capsys.readouterr().out
    code = out.split("--apply ")[1].split()[0]
    assert admin_fake.calls == [] and "irreversible" in out
    assert run(["admin", "api", "POST", "/brands", body, "--apply", code]) == 0
    assert admin_fake.calls == [("POST", "/brands", {"name": "New", "slug": "new"})]


def test_admin_api_refusals(admin_fake, capsys):
    assert run(["admin", "api", "PUT", "/products/5", "{}"]) == 1
    assert run(["admin", "api", "POST", "/brands", "{not json"]) == 1
    assert run(["admin", "api", "TRACE", "/brands"]) == 1
    assert run(["admin", "api", "GET", "brands"]) == 1
    assert admin_fake.calls == []


# ------------------------------------------------------ register_crud ----
@pytest.fixture
def crud(tmp_path, monkeypatch):
    (tmp_path / "admin_demo.py").write_text(
        "from siruk.admin.resource import Resource, register_crud\n"
        "BRANDS = Resource('brand', '/brands', required=('name', 'slug'), source='BrandController.php')\n"
        "LOCKED = Resource('author', '/authors', translatable=True, deletable=False)\n"
        "def register(reg):\n"
        "    register_crud(reg, 'brands', BRANDS)\n"
        "    register_crud(reg, 'authors', LOCKED)\n")
    monkeypatch.setattr(commands, "__path__", [*commands.__path__, str(tmp_path)])
    monkeypatch.setattr(commands, "GROUPS", ("admin_demo",))
    import importlib
    importlib.invalidate_caches()


def test_the_five_verbs_exist_and_delete_is_irreversible(crud, capsys):
    assert run(["commands", "--json"]) == 0
    by = {r["name"]: r for r in json.loads(capsys.readouterr().out)}
    assert {f"admin brands {v}" for v in ("list", "show", "create", "update", "delete")} <= set(by)
    assert by["admin brands delete"]["tier"] == "irreversible"
    assert by["admin brands create"]["tier"] == by["admin brands update"]["tier"] == "draft"
    assert by["admin brands list"]["tier"] == by["admin brands show"]["tier"] == "read"
    assert "admin authors delete" not in by and "admin authors update" in by


def test_create_refuses_a_missing_required_key_before_any_call(crud, admin_fake):
    assert run(["admin", "brands", "create", '{"name": "New"}']) == 1
    assert run(["admin", "brands", "create", '{"name": "", "slug": "x"}']) == 1
    assert run(["admin", "brands", "create", "[1]"]) == 1
    assert admin_fake.calls == []


def test_create_dry_run_then_apply_once(crud, admin_fake, capsys):
    admin_fake.on("GET", "/brands", {"data": [brand(3, name="New")]}).on("POST", "/brands", {"data": brand(8)})
    argv = ["admin", "brands", "create", '{"name": "New", "slug": "new"}']
    assert run([*argv, "--json"]) == 0
    plan = json.loads(capsys.readouterr().out)
    assert plan["tier"] == "draft" and writes(admin_fake) == []
    assert admin_fake.calls[0][:2] == ("GET", "/brands?search=New")
    assert run([*argv, "--apply", plan["code"]]) == 0
    assert writes(admin_fake) == [("POST", "/brands", {"name": "New", "slug": "new"})]


def test_a_same_name_neighbour_changes_the_create_code(crud, admin_fake, capsys):
    argv = ["admin", "brands", "create", '{"name": "New", "slug": "new"}']
    admin_fake.on("GET", "/brands", {"data": []})
    first = plan_code(capsys, argv)
    admin_fake.on("GET", "/brands", {"data": [brand(9, name="New")]})
    assert plan_code(capsys, argv) != first


def test_translatable_create_refuses_a_language_from_the_environment(crud, admin_fake, monkeypatch):
    monkeypatch.setenv("SIRUK_LANG", "ru")
    assert run(["admin", "authors", "create", '{"name": "x"}']) == 1 and admin_fake.calls == []
    monkeypatch.setenv("SIRUK_LANG", "en")
    admin_fake.on("GET", "/authors", {"data": []})
    assert run(["admin", "authors", "create", '{"name": "x"}']) == 0


def test_resource_fields_after_path_are_keyword_only():
    with pytest.raises(TypeError):
        resource.Resource("brand", "/brands", ("name",))


def test_update_sends_the_body_as_it_is_and_the_summary_diffs_sent_keys(crud, admin_fake, capsys):
    admin_fake.on("GET", "/brands/5", {"data": brand()}).on("PUT", "/brands/5", {"data": brand()})
    body = {"name": "Gemon Pro", "slug": "gemon"}
    argv = ["admin", "brands", "update", "5", json.dumps(body)]
    assert run([*argv, "--json"]) == 0
    plan = json.loads(capsys.readouterr().out)
    assert 'name: "Gemon" → "Gemon Pro"' in plan["summary"] and "unchanged: slug" in plan["summary"]
    assert "productsCount" not in plan["summary"] and plan["requests"][0]["body"] == body
    assert run([*argv, "--apply", plan["code"]]) == 0
    assert writes(admin_fake) == [("PUT", "/brands/5", body)]


# Http/Resources/Admin/Catalog/AttributeFamilyResource-style camelCase records; the form posts snake_case
CAMEL = {"id": 2, "name": "Wet Food", "measureType": "mass", "defaultSaleMode": "pack"}


def test_update_summary_matches_snake_body_keys_to_camel_record_keys(crud, admin_fake, capsys):
    admin_fake.on("GET", "/brands/5", {"data": CAMEL})
    same = {"name": "Wet Food", "measure_type": "mass", "default_sale_mode": "pack"}
    assert run(["admin", "brands", "update", "5", json.dumps(same), "--json"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert "no sent key differs" in out["summary"] and "→" not in out["summary"]
    assert "new/unknown" not in out["summary"] and out["requests"][0]["body"] == same
    one = {**same, "default_sale_mode": "loose"}
    assert run(["admin", "brands", "update", "5", json.dumps(one), "--json"]) == 0
    summary = json.loads(capsys.readouterr().out)["summary"]
    assert 'default_sale_mode: "pack" → "loose"' in summary and "measure_type:" not in summary
    assert "unchanged: name, measure_type" in summary


def test_update_summary_marks_a_key_the_record_does_not_have(crud, admin_fake, capsys):
    admin_fake.on("GET", "/brands/5", {"data": CAMEL})
    assert run(["admin", "brands", "update", "5", '{"name": "Wet Food", "colour": "red"}', "--json"]) == 0
    summary = json.loads(capsys.readouterr().out)["summary"]
    assert "new/unknown to the record: colour" in summary and "colour:" not in summary.split(";")[0]


SUPPLIER = {"id": 3, "name": "Hafo", "stockCheckedAt": "2026-11-01 10:00"}


@pytest.mark.parametrize("verb,body", [("update", '{"name": "Hafo"}'), ("delete", None)])
def test_volatile_keys_stay_out_of_the_code(admin_fake, capsys, verb, body):
    plain = resource.Resource("supplier", "/suppliers")
    quiet = resource.Resource("supplier", "/suppliers", volatile=("stockCheckedAt",))

    def code(res, rec):
        admin_fake.on("GET", "/suppliers/3", {"data": rec})
        steps, summary, shown = (resource.plan_update(res, 3, json.loads(body)) if body
                                 else resource.plan_delete(res, 3))
        assert guard.run(args(), steps=steps, summary=summary, tier="draft", shown_state=shown) == 0
        return json.loads(capsys.readouterr().out)["code"]

    later = {**SUPPLIER, "stockCheckedAt": "2026-11-02 09:00"}
    renamed = {**SUPPLIER, "name": "Hafo Ltd"}
    snake = {"id": 3, "name": "Hafo", "stock_checked_at": "x"}
    assert code(quiet, SUPPLIER) == code(quiet, later) == code(quiet, snake | {"stock_checked_at": "y"}) \
        == code(quiet, {"id": 3, "name": "Hafo"})
    assert code(quiet, SUPPLIER) != code(quiet, renamed)
    assert code(plain, SUPPLIER) != code(plain, later)


def test_delete_summary_carries_the_record_so_it_can_be_rebuilt(crud, admin_fake, capsys):
    rec = {"id": 4, "name": "Мини", "is_active": True, "match_type": "exact"}
    admin_fake.on("GET", "/brands/4", {"data": rec})
    assert run(["admin", "brands", "delete", "4", "--json"]) == 0
    first, record = json.loads(capsys.readouterr().out)["summary"].split("\n")
    assert first == "delete brand 4 (Мини)"
    assert record == 'record {"id":4,"is_active":true,"match_type":"exact","name":"Мини"}'


def test_a_long_record_is_truncated_in_the_delete_summary(admin_fake):
    admin_fake.on("GET", "/brands/4", {"data": {"id": 4, "name": "x", "pinned": list(range(2000))}})
    _, summary, _ = resource.plan_delete(BRANDS, 4)
    note = "… (truncated; run show --json first)"
    assert summary.endswith(note) and len(summary.split("\n")[1]) == len("record ") + 2000 + len(note)


def test_update_after_the_record_changed_is_refused(crud, admin_fake, capsys):
    admin_fake.on("GET", "/brands/5", {"data": brand()})
    argv = ["admin", "brands", "update", "5", '{"name": "X", "slug": "x"}']
    code = plan_code(capsys, argv)
    admin_fake.on("GET", "/brands/5", {"data": brand(name="Changed meanwhile")})
    assert run([*argv, "--apply", code]) == 1 and writes(admin_fake) == []


def test_delete_is_irreversible_and_sends_one_delete(crud, admin_fake, capsys):
    admin_fake.on("GET", "/brands/5", {"data": brand()}).on("DELETE", "/brands/5", None)
    assert run(["admin", "brands", "delete", "5", "--json"]) == 0
    plan = json.loads(capsys.readouterr().out)
    assert plan["tier"] == "irreversible" and plan["requests"][0]["method"] == "DELETE"
    assert run(["admin", "brands", "delete", "5", "--apply", plan["code"]]) == 0
    assert writes(admin_fake) == [("DELETE", "/brands/5", None)]


def test_list_one_page_all_pages_and_json(crud, admin_fake, capsys):
    page1 = {"data": [brand(1), brand(2, name="Royal")], "meta": {"current_page": 1, "last_page": 2}}
    page2 = {"data": [brand(3, name="Acana")], "meta": {"current_page": 2, "last_page": 2}}
    admin_fake.on("GET", "/brands", lambda q: page2 if q.get("page") == "2" else page1)
    assert run(["admin", "brands", "list", "--search", "a"]) == 0
    out = capsys.readouterr().out
    assert "Royal" in out and "Acana" not in out and admin_fake.calls[0][1] == "/brands?search=a"
    assert run(["admin", "brands", "list", "--page", "all", "--json"]) == 0
    assert [r["id"] for r in json.loads(capsys.readouterr().out)["data"]] == [1, 2, 3]
    assert run(["admin", "brands", "list", "--page", "2", "--json"]) == 0
    assert json.loads(capsys.readouterr().out) == page2


def test_list_all_copes_with_an_unpaginated_endpoint(admin_fake):
    admin_fake.on("GET", "/brands", {"data": [brand(1), brand(2)]})
    assert [r["id"] for r in resource.list_rows(BRANDS, page="all")] == [1, 2]
    assert len(admin_fake.calls) == 1


def test_show_prints_the_record_and_json_is_unmodified(crud, admin_fake, capsys):
    admin_fake.on("GET", "/brands/5", {"data": brand()})
    assert run(["admin", "brands", "show", "5"]) == 0
    assert "slug" in capsys.readouterr().out
    assert run(["admin", "brands", "show", "5", "--json"]) == 0
    assert json.loads(capsys.readouterr().out) == {"data": brand()}


def test_translatable_create_is_en_only_and_update_carries_the_language(crud, admin_fake, capsys):
    assert run(["admin", "authors", "create", '{"name": "x"}', "--lang", "ru"]) == 1 and admin_fake.calls == []
    admin_fake.on("GET", "/authors/4", {"data": {"id": 4, "name": "Anna"}}).on("PUT", "/authors/4", {"data": {}})
    argv = ["admin", "authors", "update", "4", '{"name": "Анна"}', "--lang", "ru"]
    code = plan_code(capsys, argv)
    assert code != plan_code(capsys, ["admin", "authors", "update", "4", '{"name": "Анна"}', "--lang", "hy"])
    assert run([*argv, "--apply", code]) == 0
    assert admin_fake.langs[-1] == "ru" and writes(admin_fake) == [("PUT", "/authors/4", {"name": "Анна"})]
