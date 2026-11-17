import io, json, urllib.error
import urllib.request

import pytest

from siruk import client as C
from siruk import config


def cfg(**over):
    c = config.load(env={"SIRUK_CONFIG": "nonexistent.json", "SIRUK_NO_PACE": "1"})
    c["retry"].update(over)
    return c


class Resp(io.BytesIO):
    def __init__(self, status, body):
        super().__init__(json.dumps(body).encode())
        self.status = status


def opener(seq, seen):
    def op(req, timeout=None):
        seen.append(req)
        status, body = seq.pop(0)
        if status >= 400:
            raise urllib.error.HTTPError(req.full_url, status, "x", {}, io.BytesIO(json.dumps(body).encode()))
        return Resp(status, body)
    return op


def make(seq, seen, **retry):
    sleeps = []
    c = C.Client(base="https://x.test/api/admin", token="T", opener=opener(seq, seen),
                 sleep=sleeps.append, cfg_loader=lambda: cfg(**retry))
    c.pacer = type("P", (), {"pace": lambda *a, **k: None})()
    return c, sleeps


def test_config_env_overrides_file_and_no_pace():
    c = config.load(env={"SIRUK_CONFIG": "nonexistent.json", "SIRUK_DELAY": "1.5", "SIRUK_RETRIES": "2"})
    assert c["request"]["delay_seconds"] == 1.5 and c["retry"]["attempts"] == 2
    # SIRUK_NO_PACE drops chunk pauses only; the hard floor (user 2026-11-12) always holds
    c = config.load(env={"SIRUK_CONFIG": "nonexistent.json", "SIRUK_NO_PACE": "1", "SIRUK_DELAY": "0", "SIRUK_MEDIA_DELAY": "0"})
    assert c["request"]["delay_seconds"] == 1.0 and c["media"]["delay_seconds"] == 2.5
    assert c["media"]["chunk_size"] == 0 and c["product"]["pause_seconds"] == 0


def test_floor_cannot_be_lowered_in_the_file(tmp_path):
    p = tmp_path / "c.json"
    p.write_text(json.dumps({"request": {"delay_seconds": 0, "min_delay_seconds": 0},
                             "media": {"delay_seconds": 0, "min_delay_seconds": 0}}))
    c = config.load(env={"SIRUK_CONFIG": str(p)})
    assert c["request"]["delay_seconds"] == 1.0 and c["media"]["delay_seconds"] == 2.5


def test_headers_and_retry_then_ok():
    seen = []
    c, sleeps = make([(503, {}), (200, {"data": 1})], seen)
    assert c.get("/products/1", lang="hy") == {"data": 1}
    assert len(seen) == 2 and sleeps == [2.0]
    h = dict(seen[0].header_items())
    assert h["Authorization"] == "Bearer T" and h["Content-language"] == "hy"
    assert "Mozilla" in h["User-agent"]  # the WAF 403s Python-urllib


def test_401_raises_with_hint_and_no_retry():
    seen = []
    c, _ = make([(401, {"message": "Unauthenticated."})], seen)
    with pytest.raises(C.ApiError) as e:
        c.get("/account")
    assert e.value.status == 401 and "token" in str(e.value) and len(seen) == 1


def test_bulk_post_is_never_retried():
    seen = []
    c, _ = make([(503, {})], seen)
    with pytest.raises(C.ApiError):
        c.post("/products/bulk", {"products": []})
    assert len(seen) == 1


def test_pacer_shares_lib_sh_state_format(tmp_path):
    sleeps = []
    p = C.Pacer(cfg_loader=lambda: config.load(env={"SIRUK_CONFIG": "nonexistent.json"}),
                sleep=sleeps.append, cache=str(tmp_path))
    p.pace("api")
    last, count = p.read_state("api")
    assert count == 1 and last > 0
    raw = (tmp_path / ".pace-api").read_text().split()
    assert len(raw) == 2 and raw[0].isdigit()  # "<ms> <count>", what lib.sh writes
    p.pace("api")
    assert p.read_state("api")[1] == 2 and sleeps  # second call waits ≥ delay


# ------------------------------------------------------------ redirects ----
LOCATION = "https://elsewhere.test/api/admin/products/1/?sig=SECRET&token=T"


def redirecting(status, seen, as_error):
    """An opener that answers `status` with a Location to another host (raised, or returned)."""
    def op(req, timeout=None):
        seen.append(req)
        if as_error:
            raise urllib.error.HTTPError(req.full_url, status, "x", {"Location": LOCATION}, io.BytesIO(b""))
        r = Resp(status, {})
        r.headers = {"Location": LOCATION}
        return r
    return op


def redirected_client(status, seen, as_error):
    c, _ = make([], seen)
    c.opener = redirecting(status, seen, as_error)
    return c


@pytest.mark.parametrize("as_error", [True, False])
@pytest.mark.parametrize("status", [301, 302, 303, 307])
@pytest.mark.parametrize("call", [
    lambda c: c.request("POST", "/products/1", {"a": 1}),
    lambda c: c.request("GET", "/products/1"),
    lambda c: c.download("/export/products"),
])
def test_a_redirect_raises_after_one_call_and_names_only_host_and_path(call, status, as_error):
    seen = []
    c = redirected_client(status, seen, as_error)
    with pytest.raises(C.ApiError) as e:
        call(c)
    assert len(seen) == 1 and e.value.status == status
    text = str(e.value)
    assert "not followed" in text and "SIRUK_API" in text
    assert "elsewhere.test/api/admin/products/1/" in text
    assert "SECRET" not in text and "sig=" not in text and "?" not in text.split("redirected")[1]


def test_a_redirect_is_not_retried_even_if_configured():
    seen = []
    c, sleeps = make([], seen, retry_on_status=[301, 503])
    c.opener = redirecting(301, seen, True)
    with pytest.raises(C.ApiError):
        c.get("/products/1")
    with pytest.raises(C.ApiError):
        c.download("/export/products")
    assert len(seen) == 2 and sleeps == []


def test_a_relative_location_is_reported_by_path():
    seen = []
    c, _ = make([], seen)
    def op(req, timeout=None):
        raise urllib.error.HTTPError(req.full_url, 302, "x", {"Location": "/login?next=/a"}, io.BytesIO(b""))
    c.opener = op
    with pytest.raises(C.ApiError) as e:
        c.get("/products/1")
    assert str(e.value).endswith(": /login")


@pytest.mark.parametrize("location", ["http://[x/p?q=1", "https://h:abc/p?q=1"])
def test_a_malformed_location_is_still_an_api_error(location):
    seen = []
    c, _ = make([], seen)
    def op(req, timeout=None):
        raise urllib.error.HTTPError(req.full_url, 301, "x", {"Location": location}, io.BytesIO(b""))
    c.opener = op
    for call in (lambda: c.get("/products/1"), lambda: c.download("/export/products")):
        with pytest.raises(C.ApiError) as e:
            call()
        assert e.value.status == 301 and "q=1" not in str(e.value)


def test_default_opener_does_not_follow_redirects():
    c = C.Client(base="https://x.test/api/admin", token="T")
    handlers = c.opener.__self__.handlers
    assert any(isinstance(h, C._NoRedirect) for h in handlers)
    assert not any(type(h) is urllib.request.HTTPRedirectHandler for h in handlers)


def test_default_opener_against_a_local_stub_stops_at_the_redirect(monkeypatch):
    import http.server, threading
    monkeypatch.setenv("NO_PROXY", "127.0.0.1,localhost")
    hits = []

    class H(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            hits.append((self.path, self.headers.get("Authorization")))
            if self.path.startswith("/start"):
                self.send_response(302)
                self.send_header("Location", f"http://localhost:{self.server.server_port}/landed?sig=SECRET")
                self.end_headers()
            else:
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"{}")

        do_POST = do_GET

        def log_message(self, *a):
            pass

    srv = http.server.HTTPServer(("127.0.0.1", 0), H)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    try:
        c = C.Client(base=f"http://127.0.0.1:{srv.server_port}", token="T",
                     sleep=lambda s: None, cfg_loader=lambda: cfg())
        c.pacer = type("P", (), {"pace": lambda *a, **k: None})()
        with pytest.raises(C.ApiError) as e:
            c.request("POST", "/start", {"a": 1})
        with pytest.raises(C.ApiError):
            c.download("/start")
        assert e.value.status == 302 and "localhost" in str(e.value) and "SECRET" not in str(e.value)
        assert [p for p, _ in hits] == ["/start", "/start"]   # /landed was never requested
        assert c.url_status(f"http://127.0.0.1:{srv.server_port}/start") == 200   # no token: follows
        assert hits[-1] == ("/landed?sig=SECRET", None)
    finally:
        srv.shutdown()
        srv.server_close()


def test_url_status_returns_the_final_status_of_a_redirecting_url():
    seen = []
    c, _ = make([(404, {})], seen)   # the injected opener stands for one that followed the 301
    assert c.url_status("https://cdn.test/a.webp") == 404
    assert "Authorization" not in dict(seen[0].header_items())


def test_url_status_default_follows_and_request_default_does_not():
    c = C.Client(base="https://x.test", token="T")
    assert c._follow is urllib.request.urlopen and c.opener is not urllib.request.urlopen
    assert C.Client(opener=print)._follow is print and C.Client(opener=print).opener is print
