"""The scripts that fetch a product themselves hand on its flat website price, on both server models.

The price-types product is conftest.PT_PRODUCT (siruk-web SingleProductResource::typePrices: `prices` rows, no flat
`price`); the legacy one is conftest.PRODUCT. Scripts are loaded by path and every subprocess call is faked.
"""
import builtins, copy, importlib.util, json, os, subprocess, sys

import pytest
from conftest import PRODUCT, PT_PRODUCT

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SNAPSHOT = os.path.join(ROOT, ".siruk-cache", "catalogue-snapshot.json")


def load(name):
    """Execute scripts/<name>.py as a module; sys.path is put back (the scripts prepend to it)."""
    path = os.path.join(ROOT, "scripts", name + ".py")
    spec = importlib.util.spec_from_file_location(name.replace("-", "_"), path)
    mod = importlib.util.module_from_spec(spec)
    saved = list(sys.path)
    try:
        spec.loader.exec_module(mod)
    finally:
        sys.path[:] = saved
    return mod


@pytest.fixture
def api_sh(monkeypatch):
    """Every `bash scripts/api.sh GET /products/<id>` answers the product in `served`; nothing else may run."""
    served = {}

    def run(cmd, **kw):
        assert cmd[0] == "bash" and cmd[1].endswith("scripts/api.sh") and cmd[2] == "GET", cmd
        pid = int(cmd[3].rsplit("/", 1)[1])
        return subprocess.CompletedProcess(cmd, 0, json.dumps({"data": copy.deepcopy(served[pid])}), "")

    monkeypatch.setattr(subprocess, "run", run)
    return served


def website(product):
    return {v["sku"]: next(r["price"] for r in v["prices"] if r["price_type_code"] == "website")
            for v in product["variants"]}


def prices_by_sku(variants):
    return {v["sku"]: v["price"] for v in variants}


def run_dump(tmp_path, monkeypatch, api_sh, product):
    mod = load("dump-products")
    api_sh[product["id"]] = product
    monkeypatch.setattr(mod, "OUT", str(tmp_path))
    mod.main(["--ids", str(product["id"])])
    return json.load(open(tmp_path / f"{product['id']}.json"))


def run_snapshot(tmp_path, monkeypatch, api_sh, product, fake):
    api_sh[product["id"]] = product
    real = builtins.open
    out = str(tmp_path / "snapshot.json")
    # the script runs main() on import and writes to the real snapshot: send that one file to tmp_path
    monkeypatch.setattr(builtins, "open", lambda f, *a, **kw: real(out if f == SNAPSHOT else f, *a, **kw))
    monkeypatch.setattr(sys, "argv", ["catalogue-snapshot.py", "--refresh", "--ids", str(product["id"])])
    load("catalogue-snapshot")
    monkeypatch.setattr(builtins, "open", real)
    return json.load(open(out))[str(product["id"])]


def run_report(tmp_path, monkeypatch, api_sh, product):
    state = {"done": {"a-product": {"id": product["id"]}}}
    (tmp_path / "plan-rest.state.json").write_text(json.dumps(state))
    # the script reads each variant's `stock`, which the shared fixture (an ops-ledger shape) does not carry
    api_sh[product["id"]] = {**product, "variants": [{**v, "stock": v["available_quantity"]} for v in product["variants"]]}
    monkeypatch.setattr(sys, "argv", ["write-run-report.py", str(tmp_path)])
    load("write-run-report")
    return json.load(open(tmp_path / "created.json"))[0]


def test_dump_products_writes_the_flat_website_price(tmp_path, monkeypatch, api_sh, fake_pt):
    saved = run_dump(tmp_path, monkeypatch, api_sh, PT_PRODUCT)
    assert prices_by_sku(saved["variants"]) == website(PT_PRODUCT) == {"387957": 2100, "387967": 2100}
    assert [r["price_type_code"] for r in saved["variants"][0]["prices"]] == ["website", "store"]


def test_dump_products_legacy_is_unchanged(tmp_path, monkeypatch, api_sh, fake):
    saved = run_dump(tmp_path, monkeypatch, api_sh, PRODUCT)
    assert saved == PRODUCT
    assert open(tmp_path / "874.json").read() == json.dumps(PRODUCT, ensure_ascii=False)


def test_catalogue_snapshot_carries_the_flat_website_price(tmp_path, monkeypatch, api_sh, fake_pt):
    entry = run_snapshot(tmp_path, monkeypatch, api_sh, PT_PRODUCT, fake_pt)
    assert prices_by_sku(entry["variants"]) == website(PT_PRODUCT)


def test_catalogue_snapshot_legacy_is_unchanged(tmp_path, monkeypatch, api_sh, fake):
    entry = run_snapshot(tmp_path, monkeypatch, api_sh, PRODUCT, fake)
    assert prices_by_sku(entry["variants"]) == {"387957": 2100, "387967": 2100}
    assert entry["variants"][0]["cost_price"] == 1300 and entry["variants"][0]["stock"] == 10


def test_write_run_report_reads_the_flat_website_price(tmp_path, monkeypatch, api_sh, fake_pt):
    row = run_report(tmp_path, monkeypatch, api_sh, PT_PRODUCT)
    assert prices_by_sku(row["variants"]) == website(PT_PRODUCT)


def test_write_run_report_legacy_is_unchanged(tmp_path, monkeypatch, api_sh, fake):
    row = run_report(tmp_path, monkeypatch, api_sh, PRODUCT)
    assert prices_by_sku(row["variants"]) == {"387957": 2100, "387967": 2100}
