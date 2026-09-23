#!/usr/bin/env python3
"""Re-upload and relink a named list of broken media ids.

`verify-media.sh --fix` does this for a whole catalogue, but each broken media
costs it a full retry ladder against a 500ing endpoint. When the broken ids are
already known, this repairs just those: find the variant carrying the id,
re-upload from the source url recorded in the run's plan state, and swap the id
in place with set-variant.sh.

    scripts/repair-media.py <product-id>... --ids 10317,10320
"""
import argparse, json, os, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, ".siruk-cache")
RUN = os.path.join(ROOT, "runs", "2026-09-15")


def sh(args, timeout=600):
    r = subprocess.run(args, capture_output=True, text=True, cwd=ROOT, timeout=timeout)
    return r.returncode, r.stdout.strip(), r.stderr.strip()


def api(path):
    _, out, _ = sh([os.path.join(ROOT, "scripts/api.sh"), "GET", path])
    i = out.find("{")
    return json.loads(out[i:]) if i >= 0 else {}


def source_urls():
    """media id -> the url it was uploaded from, across this run's plans."""
    out = {}
    for p in ("trixie-5", "8in1", "wetfood", "rest"):
        f = os.path.join(RUN, f"plan-{p}.state.json")
        if os.path.exists(f):
            for url, mid in json.load(open(f)).get("media", {}).items():
                out[mid] = url
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("products", nargs="+", type=int)
    ap.add_argument("--ids", required=True, help="comma-separated broken media ids")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    broken = {int(x) for x in a.ids.split(",")}
    src = source_urls()
    fixed, failed = [], []
    for pid in a.products:
        d = (api(f"/products/{pid}").get("data") or {})
        for v in d.get("variants") or []:
            ids = [m["id"] if isinstance(m, dict) else m for m in (v.get("images") or [])]
            hit = [i for i in ids if i in broken]
            if not hit:
                continue
            new = list(ids)
            for old in hit:
                url = src.get(old)
                if not url:
                    failed.append((pid, v["sku"], old, "no recorded source url"))
                    continue
                if a.dry_run:
                    print(f"DRY {pid}/{v['sku']}: {old} -> re-upload {url[:70]}")
                    continue
                rc, out, err = sh([os.path.join(ROOT, "scripts/upload-media.sh"), url])
                mid = next((int(t) for t in out.split() if t.isdigit()), None)
                if rc or not mid:
                    failed.append((pid, v["sku"], old, (err or out)[-160:]))
                    continue
                new[new.index(old)] = mid
                fixed.append((pid, v["sku"], old, mid))
            if not a.dry_run and new != ids:
                payload = json.dumps({"images": new})
                rc, out, err = sh([os.path.join(ROOT, "scripts/set-variant.sh"),
                                   str(pid), str(v["sku"]), payload])
                if rc:
                    failed.append((pid, v["sku"], "relink", (err or out)[-160:]))
    for f in fixed:
        print(f"fixed  product {f[0]} sku {f[1]}: media {f[2]} -> {f[3]}")
    for f in failed:
        print(f"FAILED product {f[0]} sku {f[1]}: {f[2]} — {f[3]}")
    print(f"{len(fixed)} repaired, {len(failed)} failed", file=sys.stderr)


main()
