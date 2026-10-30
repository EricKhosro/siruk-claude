import asyncio

import pytest

from siruk import cli


def test_global_flags_work_before_and_after_the_subcommand():
    p = cli.build_parser()
    a = p.parse_args(["-q", "show", "874"])
    b = p.parse_args(["show", "874", "-q", "--json"])
    assert a.quiet and not a.json and b.quiet and b.json


def test_cli_dry_run_writes_nothing(fake, capsys):
    with pytest.raises(SystemExit) as e:
        cli.main(["-q", "set-variant", "874", "387957", '{"price": 2200}', "--dry-run"])
    assert e.value.code == 0 and not fake.writes
    assert "2100 → 2200" in capsys.readouterr().out


def test_cli_refusal_exit_code(fake):
    with pytest.raises(SystemExit) as e:
        cli.main(["-q", "set-variant", "874", "387957", '{"price": 1000}', "--dry-run"])
    assert e.value.code == 1


def test_mcp_write_tools_default_to_dry_run(fake):
    pytest.importorskip("mcp")
    from siruk.mcp_server import mcp
    from siruk import client as _client
    _client.set_default(fake)

    async def go():
        names = {t.name for t in await mcp.list_tools()}
        assert {"find_products", "add_variant", "update_variant", "stock_receive"} <= names
        assert not names & {"delete_product", "api", "raw_api"}
        await mcp.call_tool("update_variant", {"product_id": 874, "sku": "387957", "patch": {"price": 2200}})
        assert not fake.writes
        with pytest.raises(Exception, match="below cost"):
            await mcp.call_tool("update_variant", {"product_id": 874, "sku": "387957",
                                                   "patch": {"price": 1000}, "confirm": True})
        assert not fake.writes
    asyncio.run(go())


def test_tui_opens_product_and_editor(fake, monkeypatch):
    pytest.importorskip("textual")
    from siruk.tui import app as tui
    from siruk.tui.editors import ConfirmScreen, VariantEditor
    monkeypatch.setattr(tui._client, "set_default", lambda c: None)  # keep the fake
    monkeypatch.setattr(tui.refdata, "ids", lambda kind: [])
    monkeypatch.setattr(tui.refdata, "product_type", lambda tid: fake.get("/attribute-families/2")["data"])
    monkeypatch.setattr(tui.stock, "movements", lambda vid: [])

    async def go():
        app = tui.SirukApp()
        async with app.run_test(size=(160, 45)) as pilot:
            app.load_product(874)
            await pilot.pause(0.5)
            assert app.query_one("#variants").row_count == 2
            await pilot.press("e")
            await pilot.pause(0.5)
            assert isinstance(app.screen, VariantEditor)
            app.screen.query_one("#f-price").value = "2200"
            await pilot.press("ctrl+s")
            await pilot.pause(0.5)
            assert isinstance(app.screen, ConfirmScreen)
            await pilot.press("escape")
            await pilot.press("escape")
            await pilot.pause(0.2)
        assert not fake.writes
    asyncio.run(go())
