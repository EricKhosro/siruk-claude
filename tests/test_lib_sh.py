"""scripts/lib.sh `api` and upload-media.sh `post_media` must fail on a 3xx, naming only the
Location's host and path — the bash twin of the Python client's no-redirect rule."""
import http.server, shutil, subprocess, threading
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
pytestmark = pytest.mark.skipif(not (shutil.which("bash") and shutil.which("curl") and shutil.which("jq")),
                                reason="bash, curl and jq are needed")
LOCATION = "http://user:pw@elsewhere.test/p?sig=SECRET#frag"


@pytest.fixture
def stub():
    hits = []

    class H(http.server.BaseHTTPRequestHandler):
        def do_POST(self):
            self.rfile.read(int(self.headers.get("Content-Length") or 0))
            hits.append((self.command, self.path))
            self.send_response(302)
            self.send_header("Location", LOCATION)
            self.send_header("Content-Length", "0")
            self.end_headers()

        do_GET = do_POST

        def log_message(self, *a):
            pass

    srv = http.server.HTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield srv, hits
    srv.shutdown()
    srv.server_close()


def run_bash(script, srv, tmp_path):
    tok = tmp_path / "token"
    tok.write_text("throwaway")
    env = {"PATH": "/usr/bin:/bin:/usr/local/bin:/opt/homebrew/bin", "HOME": str(tmp_path),
           "SIRUK_API": f"http://127.0.0.1:{srv.server_port}/api/admin", "SIRUK_TOKEN_FILE": str(tok),
           "SIRUK_CONFIG": str(tmp_path / "none.json"), "SIRUK_NO_PACE": "1", "NO_PROXY": "127.0.0.1"}
    pre = f"source {ROOT}/scripts/lib.sh; CACHE={tmp_path}/cache; mkdir -p \"$CACHE\"; "
    return subprocess.run(["bash", "-c", pre + script], env=env, capture_output=True, text=True, timeout=60)


def check(r, hits):
    assert r.returncode != 0 and len(hits) == 1
    assert "redirected, not followed" in r.stderr and "SIRUK_API" in r.stderr
    assert "elsewhere.test/p" in r.stderr
    for leaked in ("SECRET", "sig=", "pw", "frag", "user"):
        assert leaked not in r.stderr.replace("SIRUK_API", "")


def test_api_fails_on_a_redirect_and_names_only_host_and_path(stub, tmp_path):
    srv, hits = stub
    r = run_bash("api POST /x /dev/null", srv, tmp_path)
    check(r, hits)
    assert r.stdout == ""


def test_post_media_fails_on_a_redirect_and_names_only_host_and_path(stub, tmp_path):
    srv, hits = stub
    fn = subprocess.run(["sed", "-n", "/^post_media() {/,/^}/p", str(ROOT / "scripts/upload-media.sh")],
                        capture_output=True, text=True).stdout
    assert fn.startswith("post_media()")
    img = tmp_path / "a.jpg"
    img.write_bytes(b"x")
    r = run_bash(f"tok=T path={img} name=a.jpg info='{{}}' dims=; {fn}\npost_media", srv, tmp_path)
    check(r, hits)
    assert r.stdout == ""


def test_api_still_returns_the_body_of_a_200(tmp_path):
    class H(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'{"data":1}')

        def log_message(self, *a):
            pass

    srv = http.server.HTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        r = run_bash("api GET /x", srv, tmp_path)
    finally:
        srv.shutdown()
        srv.server_close()
    assert r.returncode == 0 and r.stdout.strip() == '{"data":1}'
