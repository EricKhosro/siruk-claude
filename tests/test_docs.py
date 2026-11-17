"""The AI-facing docs carry no credential, and every command line in the recipes parses.
Offline: nothing here calls an API."""
import os, re, shlex

import pytest

from siruk import cli

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB = os.path.join(os.path.dirname(ROOT), "siruk-web")
OWN = ["CLAUDE.md", "reference/siruk-cli.md", "reference/ops.md", "reference/workflows.md", "reference/admin-api.md",
       ".claude/skills/ops-receiving/SKILL.md", ".claude/skills/ops-stock/SKILL.md", ".claude/skills/ops-goods/SKILL.md",
       ".claude/skills/add-products/SKILL.md", ".opencode/commands/ops-receiving.md", ".opencode/commands/ops-stock.md",
       ".opencode/commands/ops-goods.md", "tests/test_docs.py", "tests/test_docs_manifest.py", "scripts/update-cli-reference.py"]
SIBLING = [os.path.join(WEB, p) for p in ("docs/README.md", "ops/docs/GUIDE.md")]

JWT = re.compile(r"eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]*")
KEY = re.compile(r"\b(?:ops_|sk_)[A-Za-z0-9_-]{20,}")
LOGIN_PAIR = re.compile(r"`[^`\s]+@[^`\s]+` / `[^`]+`")


def _files():
    return [os.path.join(ROOT, p) for p in OWN] + [p for p in SIBLING if os.path.exists(p)]


def _hits(text):
    return [name for name, rx in (("jwt", JWT), ("key", KEY), ("login pair", LOGIN_PAIR)) if rx.search(text)]


def test_the_patterns_catch_what_they_are_for():
    segment = "x" * 12
    assert _hits("Bearer " + "eyJ" + segment + "." + segment + "." + segment) == ["jwt"]
    assert _hits("ops" + "_" + "a1b2c3d4e5f6g7h8i9j0k1") == ["key"]
    assert _hits("sk" + "_" + "a1b2c3d4e5f6g7h8i9j0k1") == ["key"]
    assert _hits("`" + "me" + "@" + "example.com` / `" + "pw` ") == ["login pair"]
    assert _hits("an `ops_…` key, `office:read`, `task_list`, a.b.c") == []


@pytest.mark.parametrize("path", _files(), ids=lambda p: os.path.relpath(p, os.path.dirname(ROOT)))
def test_no_credential_in_the_docs(path):
    with open(path, encoding="utf-8") as f:
        assert _hits(f.read()) == []


def _recipe_commands():
    with open(os.path.join(ROOT, "reference", "workflows.md"), encoding="utf-8") as f:
        fenced = re.findall(r"```sh\n(.*?)```", f.read(), re.S)
    return [shlex.split(l)[1:] for block in fenced for l in block.splitlines() if l.startswith("siruk ")]


def test_every_recipe_line_parses():
    lines = _recipe_commands()
    assert len(lines) > 40
    parser = cli.build_parser()
    for argv in lines:
        parser.parse_args(argv)
