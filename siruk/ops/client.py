"""The Siruk Ops API client — `Authorization: Bearer <ops_… key or JWT>`, never a password.

Same pacing state, config.json knobs and retry maths as siruk.client, on its own channel
("ops"). A GET retries network errors and retry_on_status; a write makes exactly ONE
attempt: if its answer never arrives the outcome is unknown and the caller must look
before repeating (the server's idempotency keys make a deliberate repeat safe).
"""
import http.client, json, sys, time, urllib.error, urllib.parse, urllib.request

from siruk import config
from siruk.client import ApiError, Pacer

CHANNEL = "ops"
PUBLIC = ("/health",)   # answers without a token, so `ops doctor` can still reach it
GATEWAY_GAVE_UP = (502, 504)   # a proxy's answer says nothing about whether the write ran
class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """A redirect would replay the request, with the token, somewhere the caller never named."""

    def redirect_request(self, *a, **kw):
        return None


_open = urllib.request.build_opener(_NoRedirect).open
NETWORK = (urllib.error.URLError, TimeoutError, ConnectionError, OSError, http.client.HTTPException)


class OpsError(ApiError):
    """body is Ops' `{message, error, details | statusCode}`; message may be a list (validation)."""

    @property
    def code(self):
        d = self.data()
        return d.get("error") if isinstance(d, dict) else None

    @property
    def details(self):
        d = self.data()
        return d.get("details") if isinstance(d, dict) else None

    def _text(self):
        d = self.data()
        d = d if isinstance(d, dict) else {}
        msg = d.get("message")
        if isinstance(msg, list):
            msg = "; ".join(str(m) for m in msg)
        out = f"HTTP {self.status} {self.method} {self.path}" if self.status else f"{self.method} {self.path}"
        if msg:
            out += f": {msg}"
        elif self.body and not d:
            out += f": {str(self.body)[:300]}"
        if d.get("error") and d.get("error") != msg:
            out += f" [{d['error']}]"
        if d.get("details"):
            out += " " + json.dumps(d["details"], ensure_ascii=False, default=str)[:800]
        if self.status in (401, 403):
            out += " → token missing, expired or without the scope; see `siruk ops doctor`"
        return out


class UnknownOutcome(OpsError):
    """A write whose answer never arrived (or arrived unreadable): it may or may not have run."""


class OpsClient:
    def __init__(self, base=None, token=None, log=None, opener=None, pacer=None,
                 sleep=time.sleep, cfg_loader=config.load):
        self.base = (base or config.ops_api_base()).rstrip("/")
        self._token = token
        self.log = log or (lambda msg: None)
        self.opener = opener or _open
        self.sleep = sleep
        self.cfg_loader = cfg_loader
        self.pacer = pacer or Pacer(cfg_loader=cfg_loader, sleep=sleep)

    def with_token(self, token):
        """The same client speaking with another token (`ops token set` checks one before saving it)."""
        return OpsClient(self.base, token, self.log, self.opener, self.pacer, self.sleep, self.cfg_loader)

    # -- plumbing
    def token(self):
        return self._token or config.ops_token()

    def _headers(self, path, accept="application/json"):
        h = {"Accept": accept, "User-Agent": config.UA}
        tok = self.token()
        if tok:
            h["Authorization"] = f"Bearer {tok}"
        elif path.split("?")[0] not in PUBLIC:
            raise OpsError(0, "-", path, f"no Ops token: pipe one to `siruk ops token set` or set "
                                         f"SIRUK_OPS_TOKEN (file: {config.ops_token_file()})")
        return h

    def _url(self, path, params=None):
        if not str(path).startswith("/"):   # base + "@host/x" would send the token elsewhere
            raise OpsError(0, "-", str(path), "an Ops path starts with '/'")
        url = self.base + path
        if params:
            q = {k: ("true" if v is True else "false" if v is False else v)
                 for k, v in params.items() if v is not None}
            url += ("&" if "?" in path else "?") + urllib.parse.urlencode(q, doseq=True)
        return url

    def _retryable(self, status, cfg):
        if status == 0:
            return bool(cfg["retry"]["retry_on_network_error"])
        return status in cfg["retry"]["retry_on_status"]

    def _backoff(self, attempt, cfg):
        r = cfg["retry"]
        w = float(r["backoff_seconds"]) * float(r["backoff_factor"]) ** (attempt - 1)
        return max(0.0, min(w, float(r["max_backoff_seconds"])))

    def _send(self, req, timeout):
        """→ (status, body bytes, headers). status 0 = no answer (network error, timeout, cut connection)."""
        try:
            with self.opener(req, timeout=timeout) as resp:
                return resp.status, resp.read(), resp.headers
        except urllib.error.HTTPError as e:
            return e.code, e.read(), e.headers
        except NETWORK as e:
            return 0, f"network error: {e}".encode(), None

    def _once(self, method, path, params, body, cfg):
        data, headers = None, self._headers(path)
        if body is not None:
            data = json.dumps(body, ensure_ascii=False).encode("utf-8")
            headers["Content-Type"] = "application/json"
        self.pacer.pace(CHANNEL, self.log)
        req = urllib.request.Request(self._url(path, params), data=data, method=method, headers=headers)
        return self._send(req, float(cfg["request"]["timeout_seconds"]))

    def _retrying(self, method, path, params, accept=None):
        cfg = self.cfg_loader()
        attempts = max(1, int(float(cfg["retry"]["attempts"])))
        attempt = 1
        while True:
            self.pacer.pace(CHANNEL, self.log)
            headers = self._headers(path, accept or "application/json")
            req = urllib.request.Request(self._url(path, params), method=method, headers=headers)
            status, raw, hdrs = self._send(req, float(cfg["request"]["timeout_seconds"]))
            if (status == 0 or status >= 400) and self._retryable(status, cfg) and attempt < attempts:
                wait = self._backoff(attempt, cfg)
                self.log(f"HTTP {status:03d}  {method} {path} — retrying in {wait:g}s (attempt {attempt}/{attempts})")
                self.sleep(wait)
                attempt += 1
                continue
            self.log(f"HTTP {status:03d}  {method} {path}")
            if status == 0 or status >= 300:
                raise OpsError(status, method, path, raw.decode("utf-8", "replace"))
            return raw, hdrs

    # -- API
    def get(self, path, params=None):
        raw, _ = self._retrying("GET", path, params)
        text = raw.decode("utf-8", "replace")
        if not text.strip():
            return None
        try:
            return json.loads(text)
        except ValueError:
            raise OpsError(200, "GET", path, f"not JSON: {text[:300]}")

    def write(self, method, path, body=None):
        """One attempt, no retry. No answer → UnknownOutcome; an error answer → OpsError."""
        cfg = self.cfg_loader()
        method = method.upper()
        status, raw, _ = self._once(method, path, None, body, cfg)
        text = raw.decode("utf-8", "replace")
        self.log(f"HTTP {status:03d}  {method} {path}")
        if status == 0 or status in GATEWAY_GAVE_UP:
            raise UnknownOutcome(status, method, path, text)
        if status >= 300:   # a redirect was not followed: the target applied nothing
            raise OpsError(status, method, path, text)
        if not text.strip():
            return None
        try:
            return json.loads(text)
        except ValueError:
            raise UnknownOutcome(status, method, path, f"answered {status} but not JSON: {text[:300]}")

    def download(self, path, params=None):
        """GET a file endpoint → (bytes, filename or None)."""
        raw, hdrs = self._retrying("GET", path, params, accept="*/*")
        disp = hdrs.get("Content-Disposition", "") if hdrs else ""
        name = disp.split("filename=")[-1].strip('"; ') if "filename=" in disp else None
        return raw, name


def stderr_log(msg):
    print(msg, file=sys.stderr)


_default = None


def default():
    """Process-wide client (quiet). The command registrar gives it the stderr log."""
    global _default
    if _default is None:
        _default = OpsClient()
    return _default


def set_default(client):
    global _default
    _default = client
