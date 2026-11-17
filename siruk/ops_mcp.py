"""`siruk-ops` MCP server — every `siruk ops` command through three tools (stdio).

A thin layer over the CLI: the command manifest says what exists and its tier, `siruk.cli.main` runs
it in-process. A write is a dry run until the caller passes the code the dry run printed, so the guard's
rules are the CLI's own. Never reachable: `ops token`, `ops api`, anything that is not an ops command,
and any argv that carries `--apply` (the code goes only through `confirm_code`).
"""
import functools, io, json, os, re, sys, threading
from contextlib import redirect_stderr, redirect_stdout

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations

from siruk import cli

INSTRUCTIONS = """Siruk Ops (stock, till, receiving) through the `siruk ops` CLI. Start with ops_commands to see
what exists; argv is the command without the leading `ops`, e.g. ["goods", "show", "SKU"].
- Who owns what: the server runs as the person whose Ops key it holds, so a command works only if that
  person has one of its roles (the owner passes every role check); this server never holds more than that key.
- ops_read runs read commands only. ops_write runs everything else and is a dry run until you pass the code:
  call it without confirm_code, show the user the summary, the requests, the target and the tier, and only
  after their yes call it again with the code from that dry run. Never reuse a code for a different plan:
  if the state changed the code is refused (exit 1) and the new plan is returned.
- Tiers: draft (editable or deletable afterwards) < irreversible (posts stock or money) < real-world (reaches
  siruk or a third party). A real-world write needs the owner's yes each time, never a standing one.
- Every call returns {exit_code, data, stderr}: 0 ok, 1 refused by a rule, 2 API error, 3 outcome unknown.
  On 3 do not repeat the write: check the state with the command named in stderr first.
- Admin and catalogue work (products, prices, translations, media) belongs to the `siruk` server, not this one.
- Deliberately absent: `ops token`, `ops api`, `--apply` (the code goes only in confirm_code), `-o/--out`
  (a downloaded file lands in the default runs/<date>/ folder) and `--no-pace`."""

mcp = MCPServer("siruk-ops", title="Siruk Ops", instructions=INSTRUCTIONS)

READ = ToolAnnotations(read_only_hint=True, open_world_hint=True)
WRITE = ToolAnnotations(read_only_hint=False, destructive_hint=True, idempotent_hint=False, open_world_hint=True)

BLOCKED = ("token", "api")
CODE = re.compile(r"[0-9a-f]{8}")
_LOCK = threading.Lock()  # stdout, stderr and stdin are process-wide while a command runs


@functools.cache
def _manifest() -> tuple:
    return tuple(r for r in cli.build_parser().parse_args(["commands"]).manifest if r["backend"] == "ops")


def _refused(why):
    return {"exit_code": 1, "data": None, "stderr": f"refused: {why}"}


def _forbidden(token):
    """The flags this server never passes on: --apply, -o/--out (a caller-chosen file path) and --no-pace
    (it would switch pacing off for the whole process). Prefix forms count: argparse expands them."""
    head = token.split("=", 1)[0]
    if head.startswith("--"):
        return len(head) >= 3 and any(f.startswith(head) for f in ("--apply", "--out", "--no-pace"))
    return bool(re.match(r"-[A-Za-z]*o", token))


def _match(argv):
    """(entry, command words, rest) or (None, refusal reason, None)."""
    if not isinstance(argv, list) or not argv or not all(isinstance(t, str) for t in argv):
        return None, "argv must be a non-empty list of strings", None
    words = argv[1:] if argv[0] == "ops" else list(argv)
    if not words:
        return None, "argv names no command", None
    if words[0] in BLOCKED:
        return None, f"`ops {words[0]}` is not available here; use the CLI", None
    if any(_forbidden(t) for t in words):
        return None, ("--apply (use confirm_code), -o/--out (files go to the default runs/<date>/ folder) "
                      "and --no-pace are never passed in argv"), None
    by_name = {r["name"]: r for r in _manifest()}
    for k in range(len(words), 0, -1):
        hit = by_name.get("ops " + " ".join(words[:k]))
        if hit:
            return hit, words[:k], words[k:]
    return None, "not an ops command; see ops_commands", None


def _run(cmd, rest, extra=()):
    out, err = io.StringIO(), io.StringIO()
    code = 0
    with _LOCK, redirect_stdout(out), redirect_stderr(err):
        stdin, sys.stdin = sys.stdin, io.StringIO()  # stdin is the MCP channel: a command must never read it
        pace = os.environ.get("SIRUK_NO_PACE")  # some commands switch pacing off for the whole process
        try:
            cli.main(["-q", "ops", *cmd, "--json", *extra, *rest])
        except SystemExit as e:
            code = e.code if isinstance(e.code, int) else (0 if e.code is None else 1)
            if isinstance(e.code, str):
                err.write(e.code + "\n")
        except Exception as e:
            if not extra:
                raise ToolError(f"the command crashed: {type(e).__name__}") from None
            code = 3
            err.write("crashed during the write; outcome unknown — check before repeating\n")
        finally:
            sys.stdin = stdin
            if pace is None:
                os.environ.pop("SIRUK_NO_PACE", None)
            else:
                os.environ["SIRUK_NO_PACE"] = pace
    text = out.getvalue().strip()
    try:
        data = json.loads(text) if text else None
    except ValueError:
        data = text
    stderr = err.getvalue().strip()
    if code == 2 and stderr.startswith("usage:"):
        return _refused(stderr)
    return {"exit_code": code, "data": data, "stderr": stderr}


@mcp.tool(annotations=READ)
def ops_commands(filter: str = "") -> list:
    """The ops commands: name, api, tier, roles, help, example. filter: a case-insensitive text
    matched against name, endpoints and help. Tier "read" goes through ops_read, every other tier through ops_write."""
    f = filter.strip().lower()
    keep = ("name", "api", "tier", "roles", "help", "example")
    return [{k: r[k] for k in keep} for r in _manifest()
            if r["name"].split()[1] not in BLOCKED and
            (not f or f in " ".join([r["name"], r["help"], *r["api"]]).lower())]


@mcp.tool(annotations=READ)
def ops_read(argv: list[str]) -> dict:
    """Run a read command, e.g. ["goods", "list", "--q", "royal"]; argv is `siruk ops <argv>` without
    "ops". Returns {exit_code, data (the command's --json), stderr}. Refuses a command that writes."""
    entry, cmd, rest = _match(argv)
    if not entry:
        return _refused(cmd)
    if entry["tier"] != "read":
        return _refused(f"`{entry['name']}` is tier {entry['tier']}; use ops_write")
    return _run(cmd, rest)


@mcp.tool(annotations=WRITE)
def ops_write(argv: list[str], confirm_code: str = "") -> dict:
    """Run a command that writes. Without confirm_code it is a dry run: data holds the summary, requests,
    target, tier and the code, and nothing is sent. Show that to the user; after their yes call again with
    the same argv and confirm_code set to that code. Exit 3 means the outcome is unknown: check before repeating."""
    entry, cmd, rest = _match(argv)
    if not entry:
        return _refused(cmd)
    if entry["tier"] == "read":
        return _refused(f"`{entry['name']}` only reads; use ops_read")
    code = confirm_code.strip().lower()
    if code and not CODE.fullmatch(code):
        return _refused("confirm_code is the 8-character code a dry run printed")
    return _run(cmd, rest, ("--apply", code) if code else ())


def main():
    mcp.run("stdio")


if __name__ == "__main__":
    main()
