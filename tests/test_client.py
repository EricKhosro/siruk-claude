import io, json, urllib.error

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
    c = config.load(env={"SIRUK_CONFIG": "nonexistent.json", "SIRUK_NO_PACE": "1"})
    assert c["request"]["delay_seconds"] == 0 and c["media"]["chunk_size"] == 0 and c["product"]["pause_seconds"] == 0


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
