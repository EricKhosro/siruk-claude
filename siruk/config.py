"""config.json + env, read the same way scripts/lib.sh reads them.

Defaults mirror lib.sh's _CFG_DEFAULTS; config.json is deep-merged over them and
re-read on every call (edit it mid-run, no restart). Env wins over the file:
SIRUK_DELAY, SIRUK_CHUNK_SIZE, SIRUK_CHUNK_PAUSE, SIRUK_MEDIA_DELAY,
SIRUK_RETRIES, SIRUK_TIMEOUT, MAX_PX; SIRUK_NO_PACE=1 turns all waiting off.
"""
import copy, json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, ".siruk-cache")
DEFAULT_API = "https://api.siruk.am/api/admin"
# brand CDNs and the API's WAF refuse urllib's default agent (403 on Python-urllib)
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

DEFAULTS = {
    "request": {"delay_seconds": 0.6, "jitter_seconds": 0.3, "chunk_size": 15,
                "chunk_pause_seconds": 5, "idle_reset_seconds": 120,
                "timeout_seconds": 60, "connect_timeout_seconds": 15},
    "retry": {"attempts": 4, "backoff_seconds": 2, "backoff_factor": 2,
              "max_backoff_seconds": 30,
              "retry_on_status": [408, 425, 429, 500, 502, 503, 504],
              "retry_on_network_error": True},
    "media": {"delay_seconds": 2, "jitter_seconds": 0.5, "chunk_size": 5,
              "chunk_pause_seconds": 15, "max_pixels": 2000,
              "verify": {"enabled": True, "wait_seconds": 2, "attempts": 3,
                         "delete_broken": True, "retry_upload": True, "upload_attempts": 2}},
    "product": {"pause_seconds": 3},
    "bulk": {"max_per_request": 25, "timeout_seconds": 300},
}

ENV_NUM = {  # env var → (section, key)
    "SIRUK_DELAY": ("request", "delay_seconds"),
    "SIRUK_CHUNK_SIZE": ("request", "chunk_size"),
    "SIRUK_CHUNK_PAUSE": ("request", "chunk_pause_seconds"),
    "SIRUK_MEDIA_DELAY": ("media", "delay_seconds"),
    "SIRUK_RETRIES": ("retry", "attempts"),
    "SIRUK_TIMEOUT": ("request", "timeout_seconds"),
    "MAX_PX": ("media", "max_pixels"),
}


def _merge(base, over):
    for k, v in over.items():
        if k.startswith("_"):
            continue
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            _merge(base[k], v)
        else:
            base[k] = v
    return base


def config_path():
    return os.environ.get("SIRUK_CONFIG") or os.path.join(ROOT, "config.json")


def load(env=None):
    """The effective config: defaults ← config.json ← env."""
    env = os.environ if env is None else env
    cfg = copy.deepcopy(DEFAULTS)
    path = env.get("SIRUK_CONFIG") or os.path.join(ROOT, "config.json")
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as f:
                _merge(cfg, json.load(f))
        except (OSError, ValueError):
            print(f"⚠ {path} is not valid JSON — falling back to built-in defaults", file=sys.stderr)
    for var, (sec, key) in ENV_NUM.items():
        if env.get(var) not in (None, ""):
            try:
                cfg[sec][key] = float(env[var])
            except ValueError:
                pass
    if env.get("SIRUK_NO_PACE") == "1":
        for sec in ("request", "media"):
            cfg[sec].update(delay_seconds=0, jitter_seconds=0, chunk_size=0)
        cfg["product"]["pause_seconds"] = 0
    return cfg


def api_base(env=None):
    env = os.environ if env is None else env
    return (env.get("SIRUK_API") or DEFAULT_API).rstrip("/")


def token_file(env=None):
    env = os.environ if env is None else env
    return env.get("SIRUK_TOKEN_FILE") or os.path.join(ROOT, ".siruk-token")


def token(env=None):
    """SIRUK_TOKEN, else the token file (whitespace stripped). None when neither exists."""
    env = os.environ if env is None else env
    if env.get("SIRUK_TOKEN"):
        return env["SIRUK_TOKEN"].strip()
    path = token_file(env)
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return "".join(f.read().split()) or None


def is_production(env=None):
    return "demo" not in api_base(env)
