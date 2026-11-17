"""The Siruk Ops MCP server: three tools over `siruk ops`, writes as dry runs until the code, no stdout noise.
Fixture shape copied from siruk-web/ops/packages/contracts/src/api/backoffice.ts (StockLocationRow); the
POST body from apps/api/src/modules/stock/dto/create-location.dto.ts (code, name, kind)."""
import asyncio, json

import pytest

pytest.importorskip("mcp")

from siruk.ops import client as O
from siruk.ops_mcp import mcp

SHOP = "8f40bd31-5ea2-4c76-8d88-30916e4fad04"
# backoffice.ts StockLocationRow
LOCATIONS = [{"id": SHOP, "code": "SHOP", "name": "Shop", "kind": "shop", "isActive": True,
              "sirukWarehouseCode": "main", "armsoftStorage": "01", "supplierId": None, "connector": None}]
CREATE = ["locations", "create", "--code", "SH2", "--name", "Shop 2", "--kind", "shop"]


@pytest.fixture
def ops(ops_fake):
    ops_fake.on("GET", "/locations", LOCATIONS)
    ops_fake.on("POST", "/locations", {**LOCATIONS[0], "code": "SH2", "name": "Shop 2"})
    return ops_fake


def call(tool, args):
    """The tool's answer as the client sees it: one JSON text block per returned item."""
    res = asyncio.run(mcp.call_tool(tool, args))
    assert not res.is_error
    items = [json.loads(c.text) for c in res.content]
    return items if tool == "ops_commands" else items[0]


def writes(fc):
    return [c for c in fc.calls if c[0] != "GET"]


def test_the_server_lists_exactly_three_tools():
    names = {t.name for t in asyncio.run(mcp.list_tools())}
    assert names == {"ops_commands", "ops_read", "ops_write"}


def test_ops_commands_lists_ops_entries_and_hides_the_unreachable():
    rows = call("ops_commands", {})
    names = {r["name"] for r in rows}
    assert "ops locations create" in names and "ops goods list" in names
    assert all(n.startswith("ops ") for n in names)
    assert not {n for n in names if n.split()[1] in ("token", "api")}
    assert set(rows[0]) == {"name", "api", "tier", "roles", "help", "example"}
    assert [r["name"] for r in call("ops_commands", {"filter": "LOCATIONS CREATE"})] == ["ops locations create"]


def test_ops_read_runs_a_read_command_and_returns_its_json(ops):
    r = call("ops_read", {"argv": ["locations", "list"]})
    assert r["exit_code"] == 0 and r["data"] == LOCATIONS
    assert ops.calls == [("GET", "/locations", None)]


def test_ops_read_refuses_a_write_command_without_a_call(ops):
    r = call("ops_read", {"argv": CREATE})
    assert r["exit_code"] == 1 and "ops_write" in r["stderr"] and ops.calls == []


def test_ops_write_refuses_a_read_command(ops):
    r = call("ops_write", {"argv": ["locations", "list"]})
    assert r["exit_code"] == 1 and "ops_read" in r["stderr"] and ops.calls == []


def test_ops_write_without_a_code_is_a_dry_run(ops):
    r = call("ops_write", {"argv": CREATE})
    d = r["data"]
    assert r["exit_code"] == 0 and d["dry_run"] is True and d["tier"] == "draft"
    assert d["requests"][0]["method"] == "POST" and len(d["code"]) == 8 and d["summary"]
    assert writes(ops) == []


def test_ops_write_with_the_code_writes_once(ops):
    code = call("ops_write", {"argv": CREATE})["data"]["code"]
    r = call("ops_write", {"argv": CREATE, "confirm_code": code})
    assert r["exit_code"] == 0 and r["data"]["dry_run"] is False
    # create-location.dto.ts: code, name, kind
    assert writes(ops) == [("POST", "/locations", {"code": "SH2", "name": "Shop 2", "kind": "shop"})]


def test_ops_write_with_a_wrong_code_exits_1_and_writes_nothing(ops):
    r = call("ops_write", {"argv": CREATE, "confirm_code": "00000000"})
    assert r["exit_code"] == 1 and r["data"]["dry_run"] is True
    assert writes(ops) == []


def test_a_malformed_code_is_refused_before_any_call(ops):
    r = call("ops_write", {"argv": CREATE, "confirm_code": "--apply"})
    assert r["exit_code"] == 1 and ops.calls == []


def test_an_unknown_outcome_is_exit_3(ops):
    code = call("ops_write", {"argv": CREATE})["data"]["code"]
    ops.on("POST", "/locations", O.UnknownOutcome(0, "POST", "/locations", "timed out"))
    r = call("ops_write", {"argv": CREATE, "confirm_code": code})
    assert r["exit_code"] == 3 and "outcome unknown" in r["stderr"]
    assert r["data"]["failed"]["outcome_unknown"] is True


@pytest.mark.parametrize("tool,argv", [
    ("ops_read", ["token", "set"]),
    ("ops_write", ["token", "set"]),
    ("ops_read", ["api", "GET", "/documents"]),
    ("ops_write", ["api", "POST", "/documents", "{}"]),
    ("ops_write", ["ops", "api", "POST", "/documents", "{}"]),
    ("ops_write", [*CREATE, "--apply", "deadbeef"]),
    ("ops_write", [*CREATE, "--apply=deadbeef"]),
    ("ops_write", [*CREATE, "--ap", "deadbeef"]),
    ("ops_write", ["docs", "post", "DOC-1", "--a", "deadbeef"]),
    ("ops_write", ["docs", "post", "DOC-1", "--a=deadbeef"]),
    ("ops_write", ["docs", "post", "DOC-1", "--appl", "deadbeef"]),
    ("ops_read", ["report", "accountant", "--month", "2026-10", "-o", "CLAUDE.md"]),
    ("ops_read", ["report", "accountant", "--month", "2026-10", "-oCLAUDE.md"]),
    ("ops_read", ["report", "accountant", "--month", "2026-10", "-qo", "x"]),
    ("ops_read", ["report", "accountant", "--month", "2026-10", "--out", ".mcp.json"]),
    ("ops_read", ["report", "accountant", "--month", "2026-10", "--out=.mcp.json"]),
    ("ops_read", ["report", "accountant", "--month", "2026-10", "--ou", ".mcp.json"]),
    ("ops_read", ["report", "accountant", "--month", "2026-10", "--o=x"]),
    ("ops_read", ["locations", "list", "--no-pace"]),
    ("ops_read", ["locations", "list", "--no-pa"]),
    ("ops_read", ["locations", "list", "--apply", "deadbeef"]),
    ("ops_read", ["nothing", "here"]),
    ("ops_read", ["--json", "locations", "list"]),
    ("ops_read", ["admin", "show", "874"]),
    ("ops_read", []),
    ("ops_write", ["doctor"]),
])
def test_unreachable_argv_is_refused_with_zero_calls(ops, tool, argv):
    r = call(tool, {"argv": argv})
    assert r["exit_code"] == 1 and r["stderr"].startswith("refused:") and ops.calls == []


def test_a_leading_ops_is_tolerated(ops):
    assert call("ops_read", {"argv": ["ops", "locations", "list"]})["data"] == LOCATIONS


def test_nothing_reaches_the_real_stdout(ops, capfd):
    code = call("ops_write", {"argv": CREATE})["data"]["code"]
    call("ops_read", {"argv": ["locations", "list"]})
    call("ops_write", {"argv": CREATE, "confirm_code": code})
    call("ops_write", {"argv": CREATE, "confirm_code": "00000000"})
    call("ops_read", {"argv": ["nothing"]})
    assert capfd.readouterr().out == ""


def test_the_cli_does_not_import_the_server():
    from siruk import cli
    with open(cli.__file__, encoding="utf-8") as f:
        assert "ops_mcp" not in f.read()



def test_a_usage_error_is_a_refusal_not_an_api_error(ops):
    r = call("ops_write", {"argv": ["locations", "create"]})
    assert r["exit_code"] == 1 and r["stderr"].startswith("refused: usage:") and ops.calls == []


def test_an_upper_case_code_is_accepted(ops):
    code = call("ops_write", {"argv": CREATE})["data"]["code"]
    assert call("ops_write", {"argv": CREATE, "confirm_code": code.upper()})["exit_code"] == 0
    assert len(writes(ops)) == 1


def test_a_crash_during_the_apply_is_exit_3_with_the_captured_output(ops):
    code = call("ops_write", {"argv": CREATE})["data"]["code"]

    def boom(_):
        raise RuntimeError("disk on fire")
    ops.on("POST", "/locations", boom)
    r = call("ops_write", {"argv": CREATE, "confirm_code": code})
    assert r["exit_code"] == 3 and r["data"] is None and "outcome unknown" in r["stderr"]


def test_a_crash_without_a_code_stays_a_tool_error(ops):
    ops.on("GET", "/locations", lambda _: 1 / 0)
    with pytest.raises(Exception, match="crashed"):
        asyncio.run(mcp.call_tool("ops_write", {"argv": CREATE}))


def test_a_code_from_one_base_is_refused_on_another(ops):
    from ops_fakes import FakeOpsClient
    code = call("ops_write", {"argv": CREATE})["data"]["code"]
    other = FakeOpsClient(base="https://other.offline.test/api")
    other.on("GET", "/locations", LOCATIONS).on("POST", "/locations", LOCATIONS[0])
    O.set_default(other)
    r = call("ops_write", {"argv": CREATE, "confirm_code": code})
    assert r["exit_code"] == 1 and r["data"]["target"] == "https://other.offline.test/api"
    assert writes(other) == [] and writes(ops) == []


@pytest.mark.parametrize("before", [None, "0"])
def test_a_command_that_switches_pacing_off_leaves_the_environment_as_it_was(ops, monkeypatch, before):
    import os
    from siruk import ops_mcp
    if before is None:
        monkeypatch.delenv("SIRUK_NO_PACE", raising=False)
    else:
        monkeypatch.setenv("SIRUK_NO_PACE", before)

    def sets_it(argv):
        os.environ["SIRUK_NO_PACE"] = "1"
        raise SystemExit(0)
    monkeypatch.setattr(ops_mcp.cli, "main", sets_it)
    assert call("ops_read", {"argv": ["locations", "list"]})["exit_code"] == 0
    assert os.environ.get("SIRUK_NO_PACE") == before
