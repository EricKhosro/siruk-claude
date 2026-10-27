"""The admin JSON API client — the Python twin of scripts/lib.sh `api`.

Same token lookup, same config.json knobs, and the SAME pacing state files
(.siruk-cache/.pace-<channel>, "<last ms> <count>"), so a run that mixes bash
scripts and `siruk` commands still keeps one request budget against the server.
Retries network errors and retry_on_status with exponential backoff; a POST to
/products/bulk is never retried (each item is a full write).
"""
import json, os, random, sys, time, urllib.error, urllib.parse, urllib.request, uuid

from siruk import config


class ApiError(Exception):
    def __init__(self, status, method, path, body=""):
        self.status, self.method, self.path, self.body = status, method, path, body
        super().__init__(self._text())

    def data(self):
        try:
            return json.loads(self.body)
        except (TypeError, ValueError):
            return None

    def _text(self):
        d = self.data()
        msg = (d or {}).get("message") if isinstance(d, dict) else None
        errs = (d or {}).get("errors") if isinstance(d, dict) else None
        out = f"HTTP {self.status} {self.method} {self.path}"
        if msg:
            out += f": {msg}"
        if errs:
            out += " " + json.dumps(errs, ensure_ascii=False)[:800]
        elif not msg and self.body:
            out += f": {str(self.body)[:300]}"
        if self.status in (401, 403):
            out += " → token expired or WAF-blocked; refresh it (`siruk token set`, scripts/README.md)"
        return out


# ------------------------------------------------------------------ pacing ----
def _now_ms():
    return int(time.time() * 1000)


class Pacer:
    """lib.sh `pace`: ≥delay between requests (+jitter), a pause after every chunk."""

    def __init__(self, cfg_loader=config.load, sleep=time.sleep, cache=config.CACHE):
        self.cfg_loader, self.sleep, self.cache = cfg_loader, sleep, cache

    def state_path(self, channel):
        return os.path.join(self.cache, f".pace-{channel}")

    def read_state(self, channel):
        try:
            with open(self.state_path(channel)) as f:
                last, count = (f.read().split() + ["0", "0"])[:2]
            return int(last) if last.isdigit() else 0, int(count) if count.isdigit() else 0
        except OSError:
            return 0, 0

    def pace(self, channel="api", log=None):
        cfg = self.cfg_loader()
        if channel == "product":
            self.sleep(max(0, float(cfg["product"]["pause_seconds"])))
            return
        sec = cfg["media"] if channel == "media" else cfg["request"]
        delay, jitter = float(sec["delay_seconds"]), float(sec["jitter_seconds"])
        chunk, pause = int(float(sec["chunk_size"])), float(sec["chunk_pause_seconds"])
        last, count = self.read_state(channel)
        now = _now_ms()
        if now - last > float(cfg["request"]["idle_reset_seconds"]) * 1000:
            count = 0  # a long quiet gap means a new run started
        count += 1
        wait = max(0, last + delay * 1000 - now)
        if jitter > 0:
            wait += random.randrange(int(jitter * 1000) or 1)
        if chunk > 0 and count > chunk:
            wait += pause * 1000
            count = 1
            if log:
                log(f"… chunk of {chunk} {channel} requests done — pausing {pause:g}s")
        if wait > 0:
            self.sleep(wait / 1000)
        os.makedirs(self.cache, exist_ok=True)
        with open(self.state_path(channel), "w") as f:
            f.write(f"{_now_ms()} {count}\n")


# ------------------------------------------------------------------ client ----
class Client:
    def __init__(self, base=None, token=None, log=None, opener=None, pacer=None,
                 sleep=time.sleep, cfg_loader=config.load):
        self.base = (base or config.api_base()).rstrip("/")
        self._token = token
        self.log = log or (lambda msg: None)
        self.opener = opener or urllib.request.urlopen
        self.sleep = sleep
        self.cfg_loader = cfg_loader
        self.pacer = pacer or Pacer(cfg_loader=cfg_loader, sleep=sleep)

    # -- plumbing
    def token(self):
        tok = self._token or config.token()
        if not tok:
            raise ApiError(0, "-", "-", f"no token: set SIRUK_TOKEN or write {config.token_file()} "
                                        "(`siruk token set`)")
        return tok

    def _retryable(self, status, cfg):
        if status == 0:
            return bool(cfg["retry"]["retry_on_network_error"])
        return status in cfg["retry"]["retry_on_status"]

    def _backoff(self, attempt, cfg):
        r = cfg["retry"]
        w = float(r["backoff_seconds"]) * float(r["backoff_factor"]) ** (attempt - 1)
        return max(0.0, min(w, float(r["max_backoff_seconds"])))

    def _send(self, req, timeout):
        """→ (status, body text). status 0 = network error."""
        try:
            with self.opener(req, timeout=timeout) as resp:
                return resp.status, resp.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode("utf-8", "replace")
        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as e:
            return 0, f"network error: {e}"

    def request(self, method, path, body=None, lang=None, retry=None, timeout=None,
                channel="api", raw_body=None, content_type=None):
        """JSON in, parsed JSON out (None for an empty 204). Raises ApiError on a final ≥400."""
        cfg = self.cfg_loader()
        method = method.upper()
        url = self.base + path
        headers = {"Authorization": f"Bearer {self.token()}", "Accept": "application/json",
                   "User-Agent": config.UA}
        data = raw_body
        if body is not None:
            data = json.dumps(body, ensure_ascii=False).encode("utf-8")
            headers["Content-Type"] = "application/json"
        elif content_type:
            headers["Content-Type"] = content_type
        lang = lang or os.environ.get("SIRUK_LANG")
        if lang:
            headers["Content-Language"] = lang
        if retry is None:
            retry = not (method == "POST" and path.startswith("/products/bulk"))
        attempts = max(1, int(float(cfg["retry"]["attempts"]))) if retry else 1
        timeout = timeout or float(cfg["request"]["timeout_seconds"])
        attempt = 1
        while True:
            self.pacer.pace(channel, self.log)
            req = urllib.request.Request(url, data=data, method=method, headers=headers)
            status, text = self._send(req, timeout)
            if (status == 0 or status >= 400) and self._retryable(status, cfg) and attempt < attempts:
                wait = self._backoff(attempt, cfg)
                self.log(f"HTTP {status:03d}  {method} {path} — retrying in {wait:g}s "
                         f"(attempt {attempt}/{attempts})")
                self.sleep(wait)
                attempt += 1
                continue
            break
        self.log(f"HTTP {status:03d}  {method} {path}")
        if status == 0 or status >= 400:
            raise ApiError(status, method, path, text)
        if not text.strip():
            return None
        try:
            return json.loads(text)
        except ValueError:
            raise ApiError(status, method, path, f"not JSON: {text[:300]}")

    def get(self, path, lang=None, **kw):
        return self.request("GET", path, lang=lang, **kw)

    def post(self, path, body=None, **kw):
        return self.request("POST", path, body=body, **kw)

    def put(self, path, body=None, **kw):
        return self.request("PUT", path, body=body, **kw)

    def delete(self, path, **kw):
        return self.request("DELETE", path, **kw)

    def upload(self, path, filename, content, fields, mime="application/octet-stream"):
        """multipart/form-data: one `file` part + plain string fields (POST /medias)."""
        boundary = uuid.uuid4().hex
        # same part order as upload-media.sh's curl -F: file, then fileInfo
        parts = [f'--{boundary}\r\nContent-Disposition: form-data; name="file"; '
                 f'filename="{filename}"\r\nContent-Type: {mime}\r\n\r\n'.encode() + content + b"\r\n"]
        for k, v in fields.items():
            parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n'
                         .encode() + str(v).encode("utf-8") + b"\r\n")
        parts.append(f"--{boundary}--\r\n".encode())
        return self.request("POST", path, raw_body=b"".join(parts), channel="media",
                            content_type=f"multipart/form-data; boundary={boundary}")

    def download(self, path, timeout=None):
        """GET a file endpoint (an .xlsx export) → (bytes, filename or None). Same auth, pacing
        and retries as request(); raises ApiError on a final ≥400."""
        cfg = self.cfg_loader()
        url = self.base + path
        headers = {"Authorization": f"Bearer {self.token()}", "Accept": "*/*", "User-Agent": config.UA}
        attempts = max(1, int(float(cfg["retry"]["attempts"])))
        timeout = timeout or float(cfg["request"]["timeout_seconds"])
        for attempt in range(1, attempts + 1):
            self.pacer.pace("api", self.log)
            req = urllib.request.Request(url, headers=headers)
            try:
                with self.opener(req, timeout=timeout) as resp:
                    data = resp.read()
                    disp = resp.headers.get("Content-Disposition", "") if resp.headers else ""
                self.log(f"HTTP {resp.status}  GET {path}  ({len(data)} bytes)")
                name = disp.split("filename=")[-1].strip('"; ') if "filename=" in disp else None
                return data, name
            except urllib.error.HTTPError as e:
                status, text = e.code, e.read().decode("utf-8", "replace")
            except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as e:
                status, text = 0, f"network error: {e}"
            if not (self._retryable(status, cfg) and attempt < attempts):
                self.log(f"HTTP {status:03d}  GET {path}")
                raise ApiError(status, "GET", path, text)
            wait = self._backoff(attempt, cfg)
            self.log(f"HTTP {status:03d}  GET {path} — retrying in {wait:g}s (attempt {attempt}/{attempts})")
            self.sleep(wait)

    def url_status(self, url):
        """HTTP status of a plain GET on a storage url (no auth). 0 = no answer."""
        cfg = self.cfg_loader()
        self.pacer.pace("api", self.log)
        req = urllib.request.Request(url, headers={"User-Agent": config.UA})
        status, _ = self._send(req, float(cfg["request"]["timeout_seconds"]))
        return status

    def paginate(self, path, lang=None, max_pages=200):
        """Every item of a paginated list endpoint ({data, meta.last_page})."""
        sep = "&" if "?" in path else "?"
        page, out = 1, []
        while page <= max_pages:
            r = self.get(f"{path}{sep}page={page}", lang=lang) or {}
            out += r.get("data") or []
            meta = r.get("meta") or {}
            last = meta.get("last_page") or r.get("last_page") or 1
            if page >= last:
                break
            page += 1
        return out


def stderr_log(msg):
    print(msg, file=sys.stderr)


def quote(s):
    return urllib.parse.quote(str(s), safe="")


_default = None


def default():
    """Process-wide client (quiet). The CLI swaps in a logging one."""
    global _default
    if _default is None:
        _default = Client()
    return _default


def set_default(client):
    global _default
    _default = client
