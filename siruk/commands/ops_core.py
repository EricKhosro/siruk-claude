"""`siruk ops doctor | token set | whoami | api` — the person's key, never a password.

The token is an `ops_…` API key bound to one person, or a JWT; both go as Bearer. Nothing here
prints it, and `token set` takes it from stdin only so it never lands in a shell history.
"""
import base64, datetime, json, os, re, sys, urllib.parse

from siruk import client as _admin, config, output
from siruk.ops import client as _ops, guard
from siruk.payload import PayloadError

METHODS = ("GET", "POST", "PUT", "PATCH", "DELETE")
# A write the typed commands guard with extra checks: the raw call must not skip them.
USE_TYPED = ((re.compile(r"/hafo/reorder/list/[^/]+/accept"), "siruk ops reorder accept"),
             (re.compile(r"/einvoices/pull"), "siruk ops einvoices pull"),
             (re.compile(r"/outbox/[^/]+/resend"), "siruk ops outbox resend"),
             (re.compile(r"/stock/open-bag"), "siruk ops open-bag"),
             (re.compile(r"/documents"), "siruk ops docs new"),
             (re.compile(r"/documents/[^/]+/post"), "siruk ops docs post"),
             (re.compile(r"/web-orders/[^/]+/picking"), "siruk ops orders accept"),
             (re.compile(r"/web-orders/[^/]+/pack"), "siruk ops orders pack"),
             (re.compile(r"/web-orders/[^/]+/ship"), "siruk ops orders ship"),
             (re.compile(r"/web-orders/[^/]+/damaged"), "siruk ops orders damaged"),
             (re.compile(r"/web-orders/[^/]+/gifts"), "siruk ops orders gift add"),
             (re.compile(r"/web-orders/[^/]+/gifts/[^/]+"), "siruk ops orders gift rm"),
             (re.compile(r"/settings/[^/]+"), "siruk ops settings set"),
             (re.compile(r"/users"), "siruk ops staff add"),
             (re.compile(r"/users/[^/]+"), "siruk ops staff set"),
             (re.compile(r"/tills/[^/]+"), "siruk ops tills set"),
             (re.compile(r"/catalog/auto-sync"), "siruk ops catalog auto-sync"),
             (re.compile(r"/services"), "siruk ops services add"),
             (re.compile(r"/services/[^/]+"), "siruk ops services set"),
             (re.compile(r"/shop-promotions"), "siruk ops promotions add"),
             (re.compile(r"/shop-promotions/[^/]+"), "siruk ops promotions set"))
SECRET_KEY = re.compile(r"password|pin", re.I)


def _has_secret_key(x):
    if isinstance(x, dict):
        return any(SECRET_KEY.search(str(k)) or _has_secret_key(v) for k, v in x.items())
    return isinstance(x, list) and any(_has_secret_key(v) for v in x)


def _kind(tok):
    return "key" if tok.startswith("ops_") else "JWT" if tok.count(".") == 2 else "unknown"


def _jwt_expiry(tok):
    """exp of a JWT read from its payload, not verified; None when it has none."""
    try:
        seg = tok.split(".")[1]
        exp = json.loads(base64.urlsafe_b64decode(seg + "=" * (-len(seg) % 4))).get("exp")
        return datetime.datetime.fromtimestamp(int(exp), datetime.timezone.utc)
    except (IndexError, ValueError, TypeError, OverflowError, OSError):
        return None


def _key_facts(me):
    k = (me or {}).get("apiKey")
    k = k if isinstance(k, dict) else {}
    scopes = k.get("scopes")
    scopes = [scopes] if isinstance(scopes, str) else [str(x) for x in scopes] if isinstance(scopes, list) else []
    return {"name": k.get("name"), "prefix": (k.get("prefix") or "")[:12] or None, "scopes": scopes}


def cmd_doctor(a):
    c = _ops.default()
    tok = c.token()
    info = {"api": c.base, "production": config.url_is_production(c.base),
            "token_file": config.ops_token_file(), "token": bool(tok)}
    try:
        h = c.get("/health") or {}
        info["health"] = "ok" if h.get("status") == "ok" else h
    except _admin.ApiError as e:
        info["health"] = f"error: {e}"
    ok = info["health"] == "ok"
    if tok:
        info["kind"] = _kind(tok)
        if info["kind"] == "JWT":
            exp = _jwt_expiry(tok)
            if exp:
                info["expires"] = exp.strftime("%Y-%m-%d %H:%M UTC") + (
                    " (EXPIRED)" if exp < datetime.datetime.now(datetime.timezone.utc) else "")
        try:
            me = c.get("/auth/me") or {}
            info["role"] = me.get("role")
            key = _key_facts(me)
            if key["prefix"]:
                info.update(key_name=key["name"], key_prefix=key["prefix"], key_scopes=key["scopes"])
        except _admin.ApiError as e:
            info["auth"], ok = f"error: {e}", False
    else:
        ok = False
    if a.json:
        output.dump(info)
    else:
        for k, v in info.items():
            print(f"{k:<12} {'yes' if v is True else 'no' if v is False else v}")
    return 0 if ok else 2


def cmd_token_set(a):
    if sys.stdin.isatty():
        print("refused: pipe the token in (e.g. `pbpaste | siruk ops token set`); it is never asked for "
              "on a terminal or taken from arguments", file=sys.stderr)
        return 1
    tok = "".join(sys.stdin.read().split())
    if _kind(tok) == "unknown":
        print("refused: that is neither an `ops_…` API key nor a JWT", file=sys.stderr)
        return 1
    me = _ops.default().with_token(tok).get("/auth/me") or {}
    path = config.ops_token_file()
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(tok + "\n")
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass
    key = _key_facts(me)
    who = f"{me.get('role')}" + (f", key {key['prefix']}…" if key["prefix"] else "")
    print(f"token ok for {who} — wrote {path}")
    if os.environ.get("SIRUK_OPS_TOKEN"):
        print("note: SIRUK_OPS_TOKEN is set and wins over the file", file=sys.stderr)
    return 0


def cmd_whoami(a):
    me = _ops.default().get("/auth/me") or {}
    if a.json:
        output.dump(me)
        return 0
    key = _key_facts(me)
    print(f"user     {me.get('userId')}\ncompany  {me.get('companyId')}\nrole     {me.get('role')}")
    if key["prefix"]:
        print(f"key      {key['name']} ({key['prefix']}…)  scopes: {', '.join(key['scopes']) or '-'}")
    return 0


def cmd_api(a):
    method, path = a.method.upper(), a.path
    if method not in METHODS or not path.startswith("/"):
        raise PayloadError(f"usage: ops api {'|'.join(METHODS)} /path [body]")
    if method == "GET":
        output.dump(_ops.default().get(path))
        return 0
    body = None
    if a.body:
        from siruk.cli import _load_json
        try:
            body = _load_json(a.body)
        except (OSError, ValueError) as e:
            raise PayloadError(f"the body is not JSON: {e}")
    plain = urllib.parse.unquote(re.split(r"[?#]", path)[0]).rstrip("/").lower()
    if (plain == "/users" or plain.startswith("/users/")) and _has_secret_key(body):
        raise PayloadError("passwords and PINs are set by the person in the Ops app, never from the CLI")
    for rx, command in USE_TYPED:
        if rx.fullmatch(plain):
            raise PayloadError(f"{method} {path} has its own checks: use `{command}`")
    return guard.run(a, steps=[guard.Step(method, path, body)], summary=f"raw {method} {path}",
                     tier="real-world", verify=f"siruk ops api GET {path}")


def register(reg):
    reg.command(("ops", "doctor"), cmd_doctor, "check the Ops API, the token and whose it is",
                api=["GET /health", "GET /auth/me"], example="siruk ops doctor")
    reg.command(("ops", "token", "set"), cmd_token_set, "store the Ops key or JWT read from stdin",
                api=["GET /auth/me"], example="pbpaste | siruk ops token set")
    reg.command(("ops", "whoami"), cmd_whoami, "the person and role the token belongs to",
                api=["GET /auth/me"], example="siruk ops whoami --json")
    p = reg.command(("ops", "api"), cmd_api, "raw Ops call: GET free, writes only in the allowed areas",
                    api=["GET /*", "POST|PUT|PATCH|DELETE /<allowed area>/*"], tier="real-world",
                    roles="per endpoint", example="siruk ops api GET /goods?q=royal")
    p.add_argument("method", metavar="METHOD")
    p.add_argument("path")
    p.add_argument("body", nargs="?", help="JSON (file, '-' or inline)")
