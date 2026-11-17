"""`siruk admin api METHOD PATH [body] [--lang]` — a raw admin call: GET free, writes through the guard.

A write is a dry run until `--apply <code>`, and only paths the admin policy allows are sent.
"""
from siruk import client as _client, output
from siruk.admin import guard
from siruk.payload import PayloadError

METHODS = ("GET", "POST", "PUT", "PATCH", "DELETE")


def cmd_api(a):
    method, path = a.method.upper(), a.path
    if method not in METHODS or not path.startswith("/"):
        raise PayloadError(f"usage: admin api {'|'.join(METHODS)} /path [body]")
    if method == "GET":
        output.dump(_client.default().get(path, lang=a.lang))
        return 0
    body = None
    if a.body:
        from siruk.cli import _load_json
        try:
            body = _load_json(a.body)
        except (OSError, ValueError) as e:
            raise PayloadError(f"the body is not JSON: {e}")
    return guard.run(a, steps=[guard.Step(method, path, body)], summary=f"raw {method} {path}",
                     tier="irreversible", verify=f"siruk admin api GET {path}", lang=a.lang)


def register(reg):
    p = reg.command(("admin", "api"), cmd_api, "raw admin call: GET free, writes only in the allowed areas",
                    api=["GET /*", "POST|PUT|PATCH|DELETE /<allowed area>/*"], tier="irreversible",
                    roles="per endpoint", example="siruk admin api GET /brands")
    p.add_argument("method", metavar="METHOD")
    p.add_argument("path")
    p.add_argument("body", nargs="?", help="JSON (file, '-' or inline)")
    p.add_argument("--lang", choices=["en", "ru", "hy"], help="Content-Language for the call")
