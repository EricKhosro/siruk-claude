"""Price/identity lookups — thin adapters over the existing scripts (reuse, not
a port): hafo-lookup.py (article code → hafo product + variant price),
zoovet-lookup.py and nemo-lookup.py (name search; never confirmed — a human
confirms identity, CLAUDE.md 2b).
"""
import importlib.util, io, json, os, sys
from contextlib import redirect_stdout

from siruk.config import ROOT

_mods = {}


def _script(name):
    if name not in _mods:
        path = os.path.join(ROOT, "scripts", f"{name}.py")
        spec = importlib.util.spec_from_file_location(name.replace("-", "_"), path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _mods[name] = mod
    return _mods[name]


def hafo(code, name=""):
    """{confirmed, price_source, price, hafo_id, brand, title_hy, skus, …} — see reference/hafo.md."""
    return _script("hafo-lookup").lookup(code, name)


def _run_main(name, argv):
    """Run a lookup script's argparse main() in-process and parse its JSON stdout."""
    mod = _script(name)
    old = sys.argv
    buf = io.StringIO()
    try:
        sys.argv = [name] + argv
        with redirect_stdout(buf):
            mod.main()
    finally:
        sys.argv = old
    out = buf.getvalue()
    i = min([x for x in (out.find("{"), out.find("[")) if x >= 0], default=-1)
    return json.loads(out[i:]) if i >= 0 else {"raw": out}


def zoovet(search=None, brand=None, url=None, limit=10):
    argv = ["--limit", str(limit)]
    if search:
        argv += ["--search", search]
    if brand:
        argv += ["--brand", brand]
    if url:
        argv = ["--url", url]
    return _run_main("zoovet-lookup", argv)


def nemo(search=None, brand=None, url=None, limit=10):
    argv = ["--limit", str(limit)]
    if search:
        argv += ["--search", search]
    if brand:
        argv += ["--brand", brand]
    if url:
        argv = ["--url", url]
    return _run_main("nemo-lookup", argv)
