"""Rewrite the command table in reference/siruk-cli.md from `siruk commands --markdown`.

Only the text between the two markers changes. `--check` writes nothing and exits 1 when the file differs.
tests/test_docs_manifest.py calls generate() and block() from here, so there is one generator.
"""
import contextlib, io, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOC = os.path.join(ROOT, "reference", "siruk-cli.md")
START, END = "<!-- commands:start -->", "<!-- commands:end -->"


def generate():
    """The table `siruk commands --markdown` prints, without the trailing newline."""
    sys.path.insert(0, ROOT)
    from siruk import cli
    out, code = io.StringIO(), None
    with contextlib.redirect_stdout(out):
        try:
            cli.main(["-q", "commands", "--markdown"])
        except SystemExit as e:
            code = e.code
    if code not in (0, None) or not out.getvalue().strip():
        raise RuntimeError(f"`siruk commands --markdown` failed (exit {code})")
    return out.getvalue().strip()


def block(text):
    """What sits between the markers, stripped."""
    _, sep, rest = text.partition(START)
    body, end, _ = rest.partition(END)
    if not (sep and end):
        raise ValueError(f"reference/siruk-cli.md needs {START} and {END}")
    return body.strip()


def splice(text, table):
    head, _, rest = text.partition(START)
    _, _, tail = rest.partition(END)
    block(text)
    return f"{head}{START}\n{table}\n{END}{tail}"


def main(argv):
    with open(DOC, encoding="utf-8", newline="") as f:
        old = f.read()
    nl = "\r\n" if "\r\n" in old else "\n"
    new = splice(old.replace("\r\n", "\n"), generate()).replace("\n", nl)
    if new == old:
        return 0
    if "--check" in argv:
        print("reference/siruk-cli.md is out of date: run `python scripts/update-cli-reference.py`", file=sys.stderr)
        return 1
    with open(DOC, "w", encoding="utf-8", newline="") as f:
        f.write(new)
    print("updated reference/siruk-cli.md")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
