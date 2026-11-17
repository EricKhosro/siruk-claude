"""Ops foundation: the command seam and manifest, the client (one attempt per write), the write guard,
the policy, the units, the resolvers. Field names in fixtures come from
siruk-web/ops/packages/contracts/src/api/backoffice.ts (GoodsItem, Paged, StockLocationRow, SupplierRow)
and apps/api/src/common/domain-exception.filter.ts (`{message, error, details}`)."""
import argparse, base64, io, json, os, re, subprocess, sys, time, urllib.error, urllib.request

import pytest

from siruk import cli, commands, config
from siruk.ops import client as O, guard, policy, resolve, units
from siruk.payload import PayloadError

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXISTING = ["doctor", "token", "ids", "refresh", "find", "show", "check", "create", "add-variant", "set-variant",
            "rename", "translate", "stock", "listing-order", "bulk-create", "verify-translations",
            "recheck-prices", "export", "media", "price", "api", "pace", "tui", "mcp"]
KEY = "ops_" + "k3yK3yK3yK3y" + "SECRETSECRETSECRET"
UUID = "0b9c3a52-7c1d-4e0a-9d52-3f1d6c1f0a11"


def run(argv, monkeypatch=None, stdin=None):
    if stdin is not None:
        monkeypatch.setattr(sys, "stdin", io.StringIO(stdin))
    with pytest.raises(SystemExit) as e:
        cli.main(["-q", *argv])
    return e.value.code


def jwt(exp):
    seg = lambda d: base64.urlsafe_b64encode(json.dumps(d).encode()).rstrip(b"=").decode()
    return f"{seg({'alg': 'HS256'})}.{seg({'sub': 'u1', 'exp': exp})}.c2lnbmF0dXJlU0VDUkVU"


# ---------------------------------------------------------------- the seam ----
def test_parser_builds_with_only_ops_core(monkeypatch):
    monkeypatch.setattr(commands, "GROUPS", ("ops_core", "no_such_group"))
    a = cli.build_parser().parse_args(["ops", "doctor"])
    assert a.fn and a.cmd == "ops"


def _group(tmp_path, monkeypatch, name, source):
    (tmp_path / f"{name}.py").write_text(source)
    monkeypatch.setattr(commands, "__path__", [*commands.__path__, str(tmp_path)])
    monkeypatch.setattr(commands, "GROUPS", (name,))
    import importlib
    importlib.invalidate_caches()


@pytest.mark.parametrize("source,exc", [
    ("import a_module_that_is_not_installed_xyz\ndef register(reg): pass\n", ModuleNotFoundError),
    ("from siruk.commands import nothing_here\ndef register(reg): pass\n", ImportError)])
def test_import_error_inside_a_group_is_not_swallowed(tmp_path, monkeypatch, source, exc):
    _group(tmp_path, monkeypatch, "broken_group", source)
    with pytest.raises(exc):
        cli.build_parser()


def test_a_present_group_is_registered(tmp_path, monkeypatch):
    _group(tmp_path, monkeypatch, "good_group",
           "def register(reg):\n    reg.command(('ops', 'x', 'y'), lambda a: 0, 'h', api=['GET /x'], tier='draft')\n")
    a = cli.build_parser().parse_args(["ops", "x", "y", "--apply", "abcd1234"])
    assert a.apply == "abcd1234" and a.cmd2 == "x"


def test_commands_manifest_lists_everything(capsys):
    assert run(["commands", "--json"]) == 0
    rows = json.loads(capsys.readouterr().out)
    assert all(set(r) == set(commands.MANIFEST_KEYS) for r in rows)
    names = [r["name"] for r in rows]
    assert set(EXISTING) <= set(names) and {"ops doctor", "ops token set", "ops whoami", "ops api"} <= set(names)
    assert not [n for n in names if "login" in n]
    by = {r["name"]: r for r in rows}
    assert by["ops api"]["backend"] == "ops" and by["stock"]["backend"] == "admin"
    assert by["stock"]["tier"] == "irreversible" and by["find"]["tier"] == "read"
    assert by["tui"]["tier"] == by["mcp"]["tier"] == "draft" and by["tui"]["api"] and by["mcp"]["api"]
    assert "GET /brands" in by["media"]["api"] and "GET /brands" in by["recheck-prices"]["api"]


def test_commands_markdown(capsys):
    assert run(["commands", "--markdown"]) == 0
    out = capsys.readouterr().out
    assert "| `siruk ops doctor` | ops | read |" in out
    row = next(l for l in out.split("\n") if l.startswith("| `siruk ops api`"))
    assert "GET /\\*" not in row and "POST\\|PUT\\|PATCH\\|DELETE" in row and "siruk ops api GET" in row
    assert all(l.count("|") - l.count("\\|") == 8 for l in out.strip().split("\n"))


def test_ops_commands_have_no_password_or_dry_run_flags():
    a = cli.build_parser().parse_args(["ops", "api", "POST", "/documents", "--apply", "ab"])
    assert a.apply == "ab" and not hasattr(a, "dry_run")


# ------------------------------------------------------------------ client ----
class Resp(io.BytesIO):
    def __init__(self, status, body):
        super().__init__(body if isinstance(body, bytes) else json.dumps(body).encode())
        self.status, self.headers = status, {}


def opener(seq, seen):
    def op(req, timeout=None):
        seen.append(req)
        step = seq.pop(0)
        if isinstance(step, Exception):
            raise step
        status, body = step
        if status >= 300:
            raise urllib.error.HTTPError(req.full_url, status, "x", {},
                                         io.BytesIO(body if isinstance(body, bytes) else json.dumps(body).encode()))
        return Resp(status, body)
    return op


def make(seq, seen, token=KEY):
    sleeps = []
    cfg = config.load(env={"SIRUK_CONFIG": "nonexistent.json", "SIRUK_NO_PACE": "1"})
    paced = []
    c = O.OpsClient(base="https://ops.offline.test/api", token=token, opener=opener(seq, seen),
                    sleep=sleeps.append, cfg_loader=lambda: cfg)
    c.pacer = type("P", (), {"pace": lambda self, ch, log=None: paced.append(ch)})()
    return c, sleeps, paced


def test_get_retries_network_errors_and_5xx_per_config():
    seen = []
    c, sleeps, paced = make([urllib.error.URLError("down"), (503, {}), (200, {"status": "ok"})], seen)
    assert c.get("/health", {"page": 2, "lowStock": True}) == {"status": "ok"}
    assert len(seen) == 3 and sleeps == [2.0, 4.0] and set(paced) == {"ops"}
    assert seen[0].full_url == "https://ops.offline.test/api/health?page=2&lowStock=true"
    assert dict(seen[0].header_items())["Authorization"] == f"Bearer {KEY}"


def test_write_makes_one_attempt_and_a_lost_answer_is_unknown():
    for lost in (urllib.error.URLError("reset"), TimeoutError("slow"), ConnectionResetError("cut"),
                 __import__("http.client").client.IncompleteRead(b"")):
        seen = []
        c, sleeps, _ = make([lost, (200, {"id": "x"})], seen)
        with pytest.raises(O.UnknownOutcome):
            c.write("POST", "/documents/x/post", {"a": 1})
        assert len(seen) == 1 and not sleeps


def test_write_does_not_retry_an_error_answer_and_parses_the_body():
    seen = []
    c, _, _ = make([(503, {}), (200, {})], seen)
    with pytest.raises(O.OpsError) as e:
        c.write("POST", "/documents", {})
    assert len(seen) == 1 and e.value.status == 503 and not isinstance(e.value, O.UnknownOutcome)
    seen = []
    c, _, _ = make([(409, {"message": "short", "error": "STOCK_SHORT", "details": {"sku": "A"}})], seen)
    with pytest.raises(O.OpsError) as e:
        c.write("POST", "/documents/x/post")
    assert (e.value.status, e.value.code, e.value.details) == (409, "STOCK_SHORT", {"sku": "A"})
    assert "STOCK_SHORT" in str(e.value) and KEY not in str(e.value)


def test_a_gateway_timeout_on_a_write_is_unknown():
    c, _, _ = make([(504, "<html>")], [])
    with pytest.raises(O.UnknownOutcome):
        c.write("PATCH", "/goods/x", {})


def test_write_ok_returns_the_json_and_sends_the_body():
    seen = []
    c, _, _ = make([(201, {"id": "d1"})], seen)
    assert c.write("post", "/documents", {"type": "receipt"}) == {"id": "d1"}
    assert seen[0].get_method() == "POST" and json.loads(seen[0].data) == {"type": "receipt"}


def test_validation_message_lists_are_joined():
    c, _, _ = make([(400, {"message": ["a must be x", "b is required"], "error": "Bad Request",
                           "statusCode": 400})], [])
    with pytest.raises(O.OpsError, match="a must be x; b is required"):
        c.get("/goods")


def test_no_token_is_refused_before_anything_is_sent_but_health_is_public(monkeypatch, tmp_path):
    monkeypatch.delenv("SIRUK_OPS_TOKEN", raising=False)
    monkeypatch.setenv("SIRUK_OPS_TOKEN_FILE", str(tmp_path / "none"))
    seen = []
    c, _, _ = make([(200, {"status": "ok"})], seen, token=None)
    with pytest.raises(O.OpsError, match="no Ops token"):
        c.get("/goods")
    assert not seen
    assert c.get("/health") == {"status": "ok"} and "Authorization" not in dict(seen[0].header_items())


def test_a_path_that_could_redirect_the_token_is_refused():
    seen = []
    c, _, _ = make([], seen)
    with pytest.raises(O.OpsError):
        c.get("@evil.test/x")
    assert not seen


def test_ops_config_resolution(tmp_path):
    cfgf = tmp_path / "c.json"
    cfgf.write_text(json.dumps({"ops": {"api": "http://localhost:4300/api/"}}))
    assert config.ops_api_base({"SIRUK_CONFIG": str(tmp_path / "none.json")}) == config.DEFAULT_OPS_API
    assert config.ops_api_base({"SIRUK_CONFIG": str(cfgf)}) == "http://localhost:4300/api"
    assert config.ops_api_base({"SIRUK_CONFIG": str(cfgf), "SIRUK_OPS_API": "https://x.test/api"}) == "https://x.test/api"
    assert config.ops_token_file({}) == os.path.join(config.ROOT, ".ops-token")
    f = tmp_path / "t"
    f.write_text(" ops_abc \n")
    assert config.ops_token({"SIRUK_OPS_TOKEN_FILE": str(f)}) == "ops_abc"
    assert config.ops_token({"SIRUK_OPS_TOKEN_FILE": str(f), "SIRUK_OPS_TOKEN": "ops_env"}) == "ops_env"
    assert config.ops_token({"SIRUK_OPS_TOKEN_FILE": str(tmp_path / "none")}) is None
    for api, prod in (("https://ops.siruk.am/api", True), ("http://localhost:4300/api", False),
                      ("http://127.0.0.1:4300/api", False), ("http://host.docker.internal:4300/api", False),
                      ("https://ops.siruk.test/api", False), ("https://notlocalhost.example/api", True)):
        assert config.ops_is_production({"SIRUK_OPS_API": api}) is prod


# ------------------------------------------------------------------- guard ----
class Rec:
    base = "https://ops.rec.test/api"

    def __init__(self, fail=None):
        self.calls, self.fail = [], fail

    def write(self, method, path, body=None):
        self.calls.append((method, path, body))
        if self.fail and len(self.calls) == self.fail[0]:
            raise self.fail[1]
        return {"ok": len(self.calls)}


STEPS = [guard.Step("POST", "/documents", {"type": "receipt"}, "draft"),
         guard.Step("POST", "/documents/d1/post", None, "post")]


def code_for(steps, state=None, base=Rec.base):
    return guard.confirm_code(steps, state, base)


def go(rec, apply=None, steps=STEPS, **kw):
    args = argparse.Namespace(apply=apply, json=False)
    return guard.run(args, steps=steps, summary="receive", tier="irreversible", client=rec, **kw)


def test_dry_run_writes_nothing_and_prints_the_plan(capsys):
    rec = Rec()
    assert go(rec, verify="v") == 0 and not rec.calls
    out = capsys.readouterr().out
    code = code_for(STEPS)
    assert f"re-run with --apply {code}" in out
    assert "https://ops.rec.test/api" in out and "not production" in out and "irreversible" in out
    assert "POST /documents/d1/post" in out and '{"type": "receipt"}' in out


def test_production_is_named_for_a_production_target(capsys):
    rec = Rec()
    rec.base = "https://ops.siruk.am/api"
    go(rec)
    assert "(PRODUCTION)" in capsys.readouterr().out


def test_wrong_code_exits_1_and_writes_nothing(capsys):
    rec = Rec()
    assert go(rec, apply="deadbeef") == 1 and not rec.calls
    assert f"--apply {code_for(STEPS)}" in capsys.readouterr().out


def test_right_code_sends_each_step_once_in_order(capsys):
    rec = Rec()
    assert go(rec, apply=code_for(STEPS)) == 0
    assert rec.calls == [("POST", "/documents", {"type": "receipt"}), ("POST", "/documents/d1/post", None)]
    assert '"ok": 2' in capsys.readouterr().out


def test_a_changed_shown_state_changes_the_code():
    a, b = code_for(STEPS, {"qty": 5}), code_for(STEPS, {"qty": 6})
    assert a != b and a == code_for(STEPS, {"qty": 5}) and re.fullmatch(r"[0-9a-f]{8}", a)
    rec = Rec()
    assert go(rec, apply=a, shown_state={"qty": 6}) == 1 and not rec.calls
    assert code_for(STEPS) != code_for(STEPS[:1]) != code_for(STEPS[::-1])


def test_unknown_outcome_exits_3_and_names_the_check(capsys):
    rec = Rec(fail=(1, O.UnknownOutcome(0, "POST", "/documents", "network error: reset")))
    assert go(rec, apply=code_for(STEPS), verify="siruk ops docs list") == 3
    assert len(rec.calls) == 1
    assert "outcome unknown: check with `siruk ops docs list` before repeating" in capsys.readouterr().err


def test_an_api_error_stops_at_the_first_failing_step(capsys):
    rec = Rec(fail=(1, O.OpsError(409, "POST", "/documents", json.dumps({"message": "no", "error": "X"}))))
    assert go(rec, apply=code_for(STEPS)) == 2 and len(rec.calls) == 1
    assert "409" in capsys.readouterr().err


def test_custom_client_and_policy_are_the_ones_used(ops_fake):
    rec, seen = Rec(), []
    odd = [guard.Step("POST", "/sales", {})]

    def allow_all(method, path):
        seen.append((method, path))

    assert go(rec, apply=code_for(odd), steps=odd, policy=allow_all) == 0
    assert rec.calls == [("POST", "/sales", {})] and seen == [("POST", "/sales")] and not ops_fake.calls
    rec2 = Rec()
    assert go(rec2, apply=code_for(STEPS), policy=lambda m, p: "no") == 1 and not rec2.calls


def test_one_refused_step_stops_the_whole_plan_before_any_write():
    rec = Rec()
    steps = [STEPS[0], guard.Step("POST", "/purchase-orders/p1/place")]
    assert go(rec, apply=code_for(steps), steps=steps) == 1 and not rec.calls


def test_the_code_is_bound_to_the_target():
    local, prod = "http://127.0.0.1:4300/api", "https://ops.siruk.am/api"
    assert guard.confirm_code(STEPS, {"q": 1}, local) != guard.confirm_code(STEPS, {"q": 1}, prod)
    assert guard.confirm_code(STEPS, None, prod) == guard.confirm_code(STEPS, None, prod)
    a, b = Rec(), Rec()
    a.base, b.base = local + "/", prod
    assert go(a) == 0
    code_local = code_for(STEPS, None, local)   # run strips the trailing slash
    assert go(b, apply=code_local) == 1 and not b.calls
    assert go(a, apply=code_local) == 0 and len(a.calls) == 2


def test_json_failure_keeps_the_answers_of_the_applied_steps(capsys):
    for fail, rc, unknown in ((O.OpsError(409, "POST", "/documents/d1/post", json.dumps({"message": "no", "error": "X"})), 2, False),
                              (O.UnknownOutcome(0, "POST", "/documents/d1/post", "network error: reset"), 3, True)):
        rec = Rec(fail=(2, fail))
        args = argparse.Namespace(apply=code_for(STEPS), json=True)
        assert guard.run(args, steps=STEPS, summary="s", tier="draft", client=rec) == rc
        out = json.loads(capsys.readouterr().out)
        assert out["applied"] == [{"method": "POST", "path": "/documents", "label": "draft", "response": {"ok": 1}}]
        assert out["failed"]["step"] == 2 and out["failed"]["outcome_unknown"] is unknown
        assert out["failed"]["path"] == "/documents/d1/post" and "ok" not in out["failed"]


def test_a_redirect_on_a_write_applies_nothing_and_never_leaks_the_token(capsys):
    seen = []
    c, _, _ = make([(302, {"message": "moved"}), (200, {"id": "x"})], seen)
    args = argparse.Namespace(apply=guard.confirm_code(STEPS[:1], None, c.base), json=False)
    assert guard.run(args, steps=STEPS[:1], summary="s", tier="draft", client=c) == 2
    assert len(seen) == 1
    err = capsys.readouterr().err
    assert "302" in err and KEY not in err
    with pytest.raises(O.OpsError) as e:
        make([(301, {})], [])[0].get("/goods")
    assert e.value.status == 301


def test_the_default_opener_does_not_follow_redirects():
    req = urllib.request.Request("https://ops.offline.test/api/documents", data=b"{}", method="POST",
                                 headers={"Authorization": f"Bearer {KEY}"})
    handler = O._NoRedirect()
    assert handler.redirect_request(req, None, 302, "Found", {}, "https://evil.test/x") is None


def test_idem_key_is_stable_and_shaped():
    k = guard.idem_key("receipt", "d1", {"b": 1, "a": 2})
    assert k == guard.idem_key("receipt", "d1", {"a": 2, "b": 1}) and re.fullmatch(r"cli-[0-9a-f]{32}", k)
    assert k != guard.idem_key("receipt", "d2", {"a": 2, "b": 1}) != guard.idem_key("pay", "d2", {"a": 2, "b": 1})


def test_idem_uuid_is_a_stable_v4_uuid():
    u = guard.idem_uuid("payment", "s1", {"b": 1, "a": 2})
    assert u == guard.idem_uuid("payment", "s1", {"a": 2, "b": 1})
    assert re.fullmatch(r"[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}", u)
    assert u != guard.idem_uuid("payment", "s2", {"a": 2, "b": 1}) != guard.idem_uuid("adjust", "s2", {"a": 2, "b": 1})
    assert u != guard.idem_uuid("payment", "s1", {"a": 2, "b": 2}) and u != guard.idem_uuid("payment", "s1")
    assert len(guard.idem_key("payment", "s1")) == 36   # unchanged: "cli-" + 32 hex


def test_resolve_one_refuses_zero_and_several_rows():
    row = lambda i: {"id": i}
    assert resolve.one("x", "thing", [row(1)], lambda r: str(r["id"])) == row(1)
    with pytest.raises(PayloadError, match="no thing matches 'x'"):
        resolve.one("x", "thing", [], str)
    with pytest.raises(PayloadError, match=r"2 things match 'x'.*1.*2"):
        resolve.one("x", "thing", [row(1), row(2)], lambda r: str(r["id"]))
    assert resolve._one is resolve.one


# ------------------------------------------------------------------ policy ----
@pytest.mark.parametrize("argv", [
    ["POST", "/sales"], ["PUT", "/fiscal/device"], ["POST", "/purchase-orders/x/place"],
    ["POST", "/purchase-orders/x/release"], ["POST", "/einvoices/x/acknowledge-replacement"],
    ["POST", "/web-orders/x/print-hdm"], ["POST", "/tills"], ["POST", "/tills/x/rotate-key"],
    ["POST", "/catalog/armsoft-goods"]])
def test_ops_api_refuses_what_the_cli_may_not_write(ops_fake, argv, capsys):
    assert run(["ops", "api", *argv]) == 1
    assert run(["ops", "api", *argv, "--apply", guard.confirm_code([guard.Step(argv[0], argv[1])])]) == 1
    assert not ops_fake.calls and "not from the CLI" in capsys.readouterr().err


def test_ops_api_get_passes_and_prints_the_answer_unmodified(ops_fake, capsys):
    ops_fake.on("GET", "/sales", {"items": [], "total": 0})
    assert run(["ops", "api", "GET", "/sales"]) == 0
    assert json.loads(capsys.readouterr().out) == {"items": [], "total": 0}
    assert ops_fake.calls == [("GET", "/sales", None)]


def test_ops_api_write_flow_dry_run_then_apply(ops_fake, capsys):
    ops_fake.on("POST", "/suppliers", lambda body: {"id": "s9", **body})
    assert run(["ops", "api", "POST", "/suppliers", '{"name": "Hafo"}']) == 0
    assert not ops_fake.calls
    code = guard.confirm_code([guard.Step("POST", "/suppliers", {"name": "Hafo"})], None, ops_fake.base)
    out = capsys.readouterr().out
    assert f"--apply {code}" in out and "real-world" in out
    assert run(["ops", "api", "POST", "/suppliers", '{"name": "Hafo"}', "--apply", code]) == 0
    assert ops_fake.calls == [("POST", "/suppliers", {"name": "Hafo"})]


@pytest.mark.parametrize("method,path,command", [
    ("POST", "/hafo/reorder/list/r1/accept", "siruk ops reorder accept"),
    ("POST", "/einvoices/pull", "siruk ops einvoices pull"),
    ("POST", "/outbox/o1/resend", "siruk ops outbox resend"),
    ("POST", "/stock/open-bag", "siruk ops open-bag"),
    ("POST", "/documents", "siruk ops docs new"),
    ("POST", "/documents/d1/post", "siruk ops docs post"),
    ("POST", "/Documents/D1/POST/", "siruk ops docs post"),
    ("POST", "/hafo/reorder/list/r1/%61ccept", "siruk ops reorder accept"),
    ("POST", "/web-orders/w1/picking", "siruk ops orders accept"),
    ("POST", "/web-orders/w1/pack", "siruk ops orders pack"),
    ("POST", "/web-orders/w1/ship", "siruk ops orders ship"),
    ("POST", "/web-orders/w1/damaged", "siruk ops orders damaged"),
    ("POST", "/web-orders/w1/gifts", "siruk ops orders gift add"),
    ("DELETE", "/web-orders/w1/gifts/l1", "siruk ops orders gift rm"),
    ("PUT", "/settings/reorder.autoPlace", "siruk ops settings set"),
    ("POST", "/users", "siruk ops staff add"),
    ("PATCH", "/users/u1", "siruk ops staff set"),
    ("PATCH", "/tills/t1", "siruk ops tills set"),
    ("PUT", "/catalog/auto-sync", "siruk ops catalog auto-sync"),
    ("POST", "/services", "siruk ops services add"),
    ("PATCH", "/services/s1", "siruk ops services set"),
    ("POST", "/shop-promotions", "siruk ops promotions add"),
    ("PUT", "/shop-promotions/p1", "siruk ops promotions set")])
def test_ops_api_sends_guarded_writes_to_their_typed_command(ops_fake, capsys, method, path, command):
    for extra in ([], ["--apply", "deadbeef"]):
        assert run(["ops", "api", method, path, "{}", *extra]) == 1
    assert not ops_fake.calls
    assert f"use `{command}`" in capsys.readouterr().err


@pytest.mark.parametrize("body", ['{"pin": "1234"}', '{"profile": {"Password": "x"}}', '{"a": [{"pinHash": "h"}]}',
                                  '{"newPassword": "x"}'])
def test_ops_api_never_sets_a_password_or_pin(ops_fake, capsys, body):
    for extra in ([], ["--apply", "deadbeef"]):
        assert run(["ops", "api", "PATCH", "/users/u1", body, *extra]) == 1
    assert run(["ops", "api", "POST", "/users", body]) == 1
    assert not ops_fake.calls
    assert "passwords and PINs are set by the person in the Ops app" in capsys.readouterr().err


def test_ops_api_an_unlisted_write_without_credentials_goes_through_the_guard(ops_fake, capsys):
    ops_fake.on("PATCH", "/suppliers/s1", lambda body: {"id": "s1", **body})
    assert run(["ops", "api", "PATCH", "/suppliers/s1", '{"name": "A"}']) == 0 and not ops_fake.calls
    code = guard.confirm_code([guard.Step("PATCH", "/suppliers/s1", {"name": "A"})], None, ops_fake.base)
    assert f"--apply {code}" in capsys.readouterr().out
    assert run(["ops", "api", "PATCH", "/suppliers/s1", '{"name": "A"}', "--apply", code]) == 0
    assert ops_fake.calls == [("PATCH", "/suppliers/s1", {"name": "A"})]


def test_ops_api_is_a_real_world_tier_command(capsys):
    assert run(["commands", "--json"]) == 0
    assert {r["name"]: r["tier"] for r in json.loads(capsys.readouterr().out)}["ops api"] == "real-world"


def test_policy_table():
    ok = ["/documents", "/documents/1/post", "/goods/1", "/locations", "/stock/open-bag", "/suppliers/1/payments",
          "/purchase-orders", "/purchase-orders/1/lines", "/purchase-orders/1/receive", "/einvoices/1/post",
          "/goods-links", "/hafo/reorder", "/hafo/reorder/1/accept", "/catalog/sync", "/outbox/1/resend",
          "/GOODS/1", "/web-orders/1/pack", "/services/1", "/shop-promotions", "/users", "/tills/1", "/settings/k",
          "/catalog/auto-sync"]
    assert all(policy.allowed("POST", p) is None for p in ok)
    bad = ["/sales", "/goodsX", "/goods-x", "/stock", "/stock/open-bags", "/hafo", "/settings-x", "/documents/../sales",
           "/documents/%2e%2e/sales", "/documents//x", "documents", "/purchase-orders/1/place",
           "/purchase-orders/1/Release/", "/PURCHASE-ORDERS/1/PLACE", "/einvoices/1/acknowledge-replacement",
           "https://evil.test/documents", "/documents\\..\\sales", "/documents/%252e",
           "/purchase-orders/x%2Fy/place", "/purchase-orders/x%2fy/place", "/purchase-orders/x%5Cy/place",
           "/purchase-orders/x/place%3Fa", "/purchase-orders/x/place;a", "/purchase-orders/x/place?a=1",
           "/purchase-orders/x/place%23a", "/purchase-orders/x/place#a", "/documents/1?x=1", "/documents/%00",
           "/documents/a\nb", "/documents/a%0Ab", "/web-orders/1/print-hdm", "/WEB-ORDERS/1/Print-Hdm/", "/tills",
           "/tills/1/rotate-key", "/catalog/armsoft-goods", "/catalog/auto-syncs"]
    assert all(policy.allowed(m, p) for m in ("POST", "PUT", "PATCH", "DELETE") for p in bad)
    assert policy.allowed("GET", "/sales") is None and policy.allowed("get", "/anything/at/all") is None
    assert policy.allowed("POST", "/sales") == "not from the CLI: do it in the Ops app"


# ------------------------------------------------------------ secrecy / doctor ----
# ops/apps/api/src/modules/auth/auth.types.ts (AuthUser); `apiKey` is not in siruk-web yet: the brief's
# {name, prefix, scopes}; the scope names are made up.
ME = {"userId": "u1", "companyId": "c1", "role": "manager"}
ME_KEY = {**ME, "apiKey": {"name": "Eric", "prefix": KEY[:12], "scopes": ["goods:write", "documents:write"]}}


def token_run(monkeypatch, tok):
    return run(["ops", "token", "set"], monkeypatch, stdin=tok + "\n")


@pytest.mark.parametrize("tok,me", [(KEY, ME_KEY), (jwt(int(time.time()) + 3600), ME)])
def test_token_never_appears_in_any_output(ops_fake, monkeypatch, capsys, tmp_path, tok, me):
    ops_fake.on("GET", "/auth/me", me).on("GET", "/health", {"status": "ok", "db": "ok"})
    assert token_run(monkeypatch, tok) == 0
    assert ops_fake.tokens == [tok] and (tmp_path / ".ops-token").read_text() == tok + "\n"
    ops_fake._token = tok
    assert run(["ops", "doctor"]) == 0
    assert run(["ops", "doctor", "--json"]) == 0
    assert run(["ops", "whoami"]) == 0
    cap = capsys.readouterr()
    for chunk in (tok, *tok.split(".")):
        assert chunk not in cap.out + cap.err
    assert "token ok for manager" in cap.out


def test_the_real_client_never_logs_or_raises_with_the_token():
    logs, seen = [], []
    c, _, _ = make([(401, {"message": "Unauthorized"}), (200, {"ok": 1}), (409, {"message": "m", "error": "E"}),
                    urllib.error.URLError("reset")], seen)
    c.log = logs.append
    texts = []
    with pytest.raises(O.OpsError) as e:
        c.get("/auth/me")
    texts.append(str(e.value))
    assert c.write("POST", "/documents", {"a": 1}) == {"ok": 1}
    for _ in range(2):
        with pytest.raises(O.OpsError) as e:
            c.write("POST", "/documents/x/post")
        texts.append(str(e.value))
    assert len(logs) >= 4 and not [t for t in logs + texts if KEY in t]
    assert "siruk ops doctor" in texts[0]


def test_with_token_changes_only_the_token():
    seen = []
    c, _, _ = make([(200, {"role": "owner"})], seen)
    c2 = c.with_token("ops_other")
    assert c2.base == c.base and c2.get("/auth/me") == {"role": "owner"}
    assert dict(seen[0].header_items())["Authorization"] == "Bearer ops_other" and c.token() == KEY


def test_download_returns_bytes_and_the_file_name():
    seen = []
    c, _, paced = make([(200, b"PK\x03\x04")], seen)
    ok = Resp(200, b"PK\x03\x04")
    ok.headers = {"Content-Disposition": 'attachment; filename="sales.xlsx"'}
    c.opener = lambda req, timeout=None: (seen.append(req), ok)[1]
    assert c.download("/reports/sales.xlsx", {"from": "2026-11-01"}) == (b"PK\x03\x04", "sales.xlsx")
    assert seen[0].full_url.endswith("/reports/sales.xlsx?from=2026-11-01") and dict(seen[0].header_items())["Accept"] == "*/*"


def test_doctor_reads_key_facts_when_the_server_gives_them(ops_fake, capsys):
    # HealthController answers {status: 'ok', db: 'ok'} (ops/apps/api/src/modules/health/health.controller.ts)
    ops_fake.on("GET", "/auth/me", ME_KEY).on("GET", "/health", {"status": "ok", "db": "ok"})
    assert run(["ops", "doctor", "--json"]) == 0
    d = json.loads(capsys.readouterr().out)
    assert (d["token"], d["kind"], d["role"], d["health"]) == (True, "key", "manager", "ok")
    assert d["key_prefix"] == KEY[:12] and d["key_scopes"] == ["goods:write", "documents:write"]
    assert d["production"] is False and len(d["key_prefix"]) == 12


def test_doctor_works_without_an_apikey_field_and_reads_a_jwt_expiry(ops_fake, capsys):
    ops_fake.on("GET", "/auth/me", ME).on("GET", "/health", {"status": "ok", "db": "ok"})
    ops_fake._token = jwt(int(time.time()) - 60)
    assert run(["ops", "doctor"]) == 0
    out = capsys.readouterr().out
    assert "kind         JWT" in out and "(EXPIRED)" in out and "role         manager" in out
    assert "key_prefix" not in out


def test_doctor_without_a_token_still_reports_health(ops_fake, capsys):
    ops_fake._token = None
    ops_fake.on("GET", "/health", {"status": "ok", "db": "ok"})
    assert run(["ops", "doctor"]) == 2
    out = capsys.readouterr().out
    assert "token        no" in out and "health       ok" in out and ("GET", "/auth/me", None) not in ops_fake.calls


def test_whoami_tolerates_odd_scopes(ops_fake, capsys):
    ops_fake.on("GET", "/auth/me", {**ME, "apiKey": {"name": "k", "prefix": KEY[:12], "scopes": "goods:write"}})
    assert run(["ops", "whoami"]) == 0
    assert "scopes: goods:write" in capsys.readouterr().out


def test_the_fake_lets_the_latest_route_win(ops_fake):
    ops_fake.on("GET", "/x", {"v": 1}).on("GET", "/x", {"v": 2})
    assert ops_fake.get("/x") == {"v": 2}
    with pytest.raises(AssertionError):
        ops_fake.get("/unregistered")


def test_whoami_json_is_the_unmodified_answer(ops_fake, capsys):
    ops_fake.on("GET", "/auth/me", ME_KEY)
    assert run(["ops", "whoami", "--json"]) == 0
    assert json.loads(capsys.readouterr().out) == ME_KEY


def test_token_set_refuses_a_terminal_and_a_non_token_and_writes_nothing(ops_fake, monkeypatch, tmp_path):
    class Tty(io.StringIO):
        isatty = lambda self: True
    monkeypatch.setattr(sys, "stdin", Tty(KEY))
    with pytest.raises(SystemExit) as e:
        cli.main(["ops", "token", "set"])
    assert e.value.code == 1
    assert token_run(monkeypatch, "hunter2") == 1
    assert not ops_fake.calls and not (tmp_path / ".ops-token").exists()


def test_there_is_no_login_and_no_password_flag():
    with pytest.raises(SystemExit):
        cli.build_parser().parse_args(["ops", "login"])
    help_text = [a for a in cli.build_parser()._subparsers._group_actions[0].choices["ops"].format_help().split()]
    assert "login" not in help_text and "password" not in " ".join(help_text).lower()


def test_gitignore_covers_the_token_files():
    lines = open(os.path.join(ROOT, ".gitignore"), encoding="utf-8").read().split("\n")
    assert ".ops-token*" in lines and ".siruk-token*" in lines


# ------------------------------------------------------------------- units ----
def test_amd_to_minor_and_back():
    assert units.amd_to_minor("1300") == "130000" and units.amd_to_minor("1300.5") == "130050"
    assert units.amd_to_minor(1300) == "130000" and units.amd_to_minor("0.07") == "7" and units.amd_to_minor("0") == "0"
    for bad in ("1.234", -1, "-1", "-0.5", "abc", "1e3", "", True, None, 0.1 + 0.2):
        with pytest.raises(PayloadError):
            units.amd_to_minor(bad)
    assert units.minor_to_amd("130000") == "1300" and units.minor_to_amd("130050") == "1300.50"
    assert units.minor_to_amd("-5") == "-0.05" and units.minor_to_amd(7) == "0.07"
    with pytest.raises(PayloadError):
        units.minor_to_amd("12.5")


def test_parse_quantity():
    assert units.parse_quantity(745, "loose") == 745 and units.parse_quantity("745", "loose") == 745
    assert units.parse_quantity("2.5kg", "loose") == 2500 and units.parse_quantity("500g", "loose") == 500
    assert units.parse_quantity("1.5l", "loose") == 1500 and units.parse_quantity("250 ML", "loose") == 250
    assert units.parse_quantity("3pcs", "pack") == 3 and units.parse_quantity(3, "pack") == 3
    assert units.parse_quantity("2kg", "mass") == 2000 and units.parse_quantity("1l", "volume") == 1000


@pytest.mark.parametrize("x,unit", [("2kg", "pack"), ("3pcs", "loose"), ("500g", "pack"), ("1l", "mass"),
                                    ("0.0005kg", "loose"), ("2.5", "pack"), ("many", "pack"), (2.5, "loose"),
                                    (True, "pack"), ("2kg", "crate")])
def test_parse_quantity_refusals(x, unit):
    with pytest.raises(PayloadError):
        units.parse_quantity(x, unit)


@pytest.mark.parametrize("x", [-1, "-3", "-2kg", "-0.5l", "-500g"])
def test_parse_quantity_refuses_a_negative(x):
    with pytest.raises(PayloadError, match="negative"):
        units.parse_quantity(x, "loose")
    for pack in (-3, "-3", "-3pcs"):
        with pytest.raises(PayloadError, match="negative"):
            units.parse_quantity(pack, "pack")


def test_parse_quantity_allows_zero():
    assert units.parse_quantity(0, "pack") == 0 and units.parse_quantity("0", "loose") == 0
    assert units.parse_quantity("0kg", "loose") == 0 and units.parse_quantity("-0", "pack") == 0


def test_format_quantity():
    assert units.format_quantity(745, "loose") == "745 g" and units.format_quantity(2500, "loose") == "2.5 kg"
    assert units.format_quantity(12000, "loose") == "12 kg" and units.format_quantity(3, "pack") == "3 pcs"
    assert units.format_quantity(1500, "volume") == "1.5 l"


# ----------------------------------------------------------------- resolve ----
# siruk-web/ops/packages/contracts/src/api/backoffice.ts: GoodsItem, Paged<T>, GoodsExtraBarcode
def good(sku, **kw):
    return {"variantId": f"v-{sku}", "sku": sku, "barcode": None, "accountingCode": None, "extraBarcodes": [],
            "productName": {"en": f"Good {sku}", "ru": None, "hy": None}, "label": None, **kw}


# GoodsListResponse: Paged<GoodsItem> = {items, total, page, pageSize}
def paged(pages, size=2):
    total = sum(len(p) for p in pages)

    def answer(params):
        n = params["page"]
        return {"items": pages[n - 1] if n <= len(pages) else [], "total": total, "page": n, "pageSize": size}
    return answer


def test_variant_pages_through_every_page(ops_fake):
    target = good("S3", barcode="4750000000017")
    ops_fake.on("GET", "/goods", paged([[good("S1"), good("S2")], [target, good("S4")], [good("S5")]]))
    assert resolve.variant("4750000000017") is target
    assert [c[2]["page"] for c in ops_fake.calls] == [1, 2, 3]   # a later page could hold a second match
    assert all(c[2]["q"] == "4750000000017" for c in ops_fake.calls)


def test_variant_matches_any_code_case_insensitively(ops_fake):
    ops_fake.on("GET", "/goods", paged([[good("A", extraBarcodes=[{"code": "26X", "units": 26, "sellable": False}]),
                                         good("B", accountingCode="0352")]]))
    assert resolve.variant("26x")["sku"] == "A" and resolve.variant("0352")["sku"] == "B"
    assert resolve.variant("b")["sku"] == "B"


def test_variant_refuses_zero_and_several_exact_matches(ops_fake):
    ops_fake.on("GET", "/goods", paged([[good("X1", barcode="777"), good("X2", extraBarcodes=[
        {"code": "777", "units": 1, "sellable": True}])], [good("X7777")]]))
    with pytest.raises(PayloadError, match="no good matches '999'"):
        resolve.variant("999")
    with pytest.raises(PayloadError, match=r"2 goods match '777'.*v-X1.*v-X2"):
        resolve.variant("777")


def test_variant_refuses_a_second_match_on_a_later_page(ops_fake):
    ops_fake.on("GET", "/goods", paged([[good("D1", barcode="5")], [good("Z")], [{**good("D2"), "sku": "d1"}]], size=1))
    with pytest.raises(PayloadError, match="2 goods match"):
        resolve.variant("d1")


def test_variant_refuses_to_resolve_on_a_truncated_list(ops_fake, monkeypatch):
    monkeypatch.setattr(resolve, "MAX_PAGES", 3)
    ops_fake.on("GET", "/goods", paged([[good(f"G{i}")] for i in range(6)], size=1))
    with pytest.raises(PayloadError, match="too many matches.*narrow the query"):
        resolve.variant("G1")
    assert [c[2]["page"] for c in ops_fake.calls] == [1, 2, 3]


def test_variant_by_uuid_reads_the_good(ops_fake):
    ops_fake.on("GET", f"/goods/{UUID}", good("U"))
    assert resolve.variant(UUID)["sku"] == "U"


def test_location_and_supplier(ops_fake):
    # StockLocationRow and SupplierRow (backoffice.ts), only the fields the resolvers read
    locs = [{"id": UUID, "code": "SHOP", "name": "Shop", "kind": "shop"},
            {"id": "11111111-1111-1111-1111-111111111111", "code": "STORE", "name": "Store", "kind": "storeroom"}]
    sups = [{"id": UUID, "name": "Hafo LLC", "tin": "01234567"},
            {"id": "22222222-2222-2222-2222-222222222222", "name": "Other", "tin": None},
            {"id": "33333333-3333-3333-3333-333333333333", "name": "other", "tin": "99"}]
    ops_fake.on("GET", "/locations", locs).on("GET", "/suppliers", sups)
    assert resolve.location("store")["code"] == "STORE" and resolve.location(UUID)["code"] == "SHOP"
    assert resolve.supplier("01234567")["name"] == "Hafo LLC" and resolve.supplier("hafo llc")["id"] == UUID
    assert resolve.supplier(UUID)["name"] == "Hafo LLC"
    with pytest.raises(PayloadError, match="no location"):
        resolve.location("NOPE")
    with pytest.raises(PayloadError, match="2 suppliers match"):
        resolve.supplier("other")


# ----------------------------------------------------------------- imports ----
def test_the_cli_starts_on_the_standard_library_alone():
    code = ("import sys, json\nbefore = set(sys.modules)\n"
            "sys.path.insert(0, %r)\n"
            "import siruk.cli, siruk.ops.client, siruk.ops.guard, siruk.commands\n"
            "print(json.dumps(sorted({m.split('.')[0] for m in set(sys.modules) - before})))\n" % ROOT)
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, cwd=ROOT, check=True).stdout
    foreign = set(json.loads(out)) - set(sys.stdlib_module_names) - {"siruk"}
    assert not {m for m in foreign if not m.startswith("_")}, foreign
