"""The generated command table in reference/siruk-cli.md follows the CLI's own manifest.
Regenerate with `python scripts/update-cli-reference.py` when a command is added."""
import importlib.util, json, os

import pytest

from siruk import cli

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOC = os.path.join(ROOT, "reference", "siruk-cli.md")


def _script():
    spec = importlib.util.spec_from_file_location("update_cli_reference", os.path.join(ROOT, "scripts", "update-cli-reference.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _read():
    with open(DOC, encoding="utf-8") as f:
        return f.read()


def test_the_generated_block_equals_the_markdown_the_cli_prints(capsys):
    script = _script()
    with pytest.raises(SystemExit):
        cli.main(["-q", "commands", "--markdown"])
    assert script.block(_read()) == capsys.readouterr().out.strip() == script.generate()


def test_every_command_in_the_manifest_is_in_the_doc(capsys):
    with pytest.raises(SystemExit):
        cli.main(["-q", "commands", "--json"])
    names = [r["name"] for r in json.loads(capsys.readouterr().out)]
    text = _read()
    assert names and [n for n in names if f"`siruk {n}`" not in text] == []


def test_the_script_checks_and_rewrites_only_the_block(tmp_path, monkeypatch):
    script = _script()
    original = _read()
    start = original.index(script.START) + len(script.START)
    drifted = original[:start] + "\n| stale |\n" + original[original.index(script.END):]
    for text in (drifted, drifted.replace("\n", "\r\n")):
        doc = tmp_path / "siruk-cli.md"
        doc.write_bytes(text.encode())
        monkeypatch.setattr(script, "DOC", str(doc))
        assert script.main(["--check"]) == 1 and doc.read_bytes() == text.encode()
        assert script.main([]) == 0
        fixed = doc.read_bytes()
        assert script.main(["--check"]) == 0 and script.main([]) == 0 and doc.read_bytes() == fixed
        eol = "\r\n" if "\r\n" in text else "\n"
        assert fixed.decode().replace("\r\n", "\n").replace("\n", eol) == fixed.decode()
        assert fixed.decode().replace("\r\n", "\n") == original
