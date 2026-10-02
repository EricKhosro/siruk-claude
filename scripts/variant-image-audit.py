#!/usr/bin/env python3
"""Find variants that differ by flavour / colour / size but show the same picture
(reference/image-sources.md → "Keyed is necessary, not sufficient", user report 2026-10-02).

    scripts/variant-image-audit.py <product id> [...] [--out runs/<date>/variant-images.csv] [--download DIR]

Read-only. Per product it lists every variant's gallery and flags any media id or file
(md5 of the stored original) shared by two variants whose labels differ — the 1 kg twin
(<sku>-KG) is skipped, it shares its bag's gallery by design. A shared secondary image
can be fine (an infographic of the same line); a shared FIRST image never is, unless the
variants differ only in a size the photo cannot show. Identical files are only half the
check: a look-alike photo from another shop is a different file — look at each first image.
Uses SIRUK_API / SIRUK_TOKEN_FILE like scripts/api.sh.
"""
import argparse, collections, csv, hashlib, json, os, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def api(path):
    r = subprocess.run([os.path.join(ROOT, "scripts/api.sh"), "GET", path], capture_output=True, text=True, cwd=ROOT)
    t = r.stdout
    return json.loads(t[t.find("{"):])["data"]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("ids", nargs="+", type=int)
    ap.add_argument("--out")
    ap.add_argument("--download", default=os.path.join(ROOT, ".siruk-cache", "variant-images"))
    a = ap.parse_args()
    os.makedirs(a.download, exist_ok=True)
    media, rows, flags = {}, [], 0
    for pid in a.ids:
        p = api(f"/products/{pid}")
        by_key = collections.defaultdict(set)
        for v in p["variants"]:
            if v["sku"].endswith("-KG"):
                continue
            for i, mid in enumerate(v.get("images") or []):
                if mid not in media:
                    m = api(f"/medias/{mid}")
                    f = os.path.join(a.download, f"{mid}.{m.get('extension') or 'jpg'}")
                    if not os.path.exists(f):
                        subprocess.run(["curl", "-sL", "-o", f, m["originalUrl"]])
                    media[mid] = (m["filename"], hashlib.md5(open(f, "rb").read()).hexdigest(), f)
                fn, md5, local = media[mid]
                rows.append({"product_id": pid, "product": p["name"], "variant_id": v["id"], "sku": v["sku"],
                             "label": v["name"], "pos": i, "media": mid, "file": fn, "md5": md5, "local": local})
                by_key[md5].add((v["name"], i))
        for md5, uses in by_key.items():
            labels = {l for l, _ in uses}
            if len(labels) > 1:
                first = any(i == 0 for _, i in uses)
                flags += 1
                print(f"{pid} {p['name']}: same picture on {sorted(labels)}"
                      + ("  ← FIRST IMAGE" if first else "  (secondary)"))
    if a.out:
        with open(a.out, "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    print(f"{len(a.ids)} products, {len({r['variant_id'] for r in rows})} variants, {len(media)} media — "
          f"{flags} shared pictures; now look at every variant's first image ({a.download})")


if __name__ == "__main__":
    main()
