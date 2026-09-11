#!/usr/bin/env python3
"""Find a product photo by EAN when the brand's own sites have none.

CLAUDE.md's fallback ladder ends with "a general web/image search for the exact
product", flagged as fallback. hornung-baushop.de (a German pet/hardware shop)
is the useful form of that: its search accepts an EAN-13 and it names every
image file after the EAN(s) of the article it shows —

    napf-nahrungsaufnahme-4047974251416-hornung-baushop.jpg
    napf-fuettern-4047974245354-4047974245361-4047974245378-hornung-baushop.jpg

so a hit is keyed to our own hafo row's barcode, not to a name. The product slug
comes back too, so the identification can be checked in words before anything is
written. Photos are TRIXIE's own, unwatermarked.

    scripts/ean-image-lookup.py <ean> [...]
    scripts/ean-image-lookup.py --from .siruk-cache/gap-barcodes.json --out out.json
"""
import json, re, subprocess, sys, time

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")
SEARCH = "https://hornung-baushop.de/search?search={ean}"


def get(url, timeout=60):
    r = subprocess.run(["curl", "-sSL", "-A", UA, "--max-time", str(timeout), url],
                       capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else ""


def lookup(ean):
    h = get(SEARCH.format(ean=ean))
    if not h:
        return {"ean": ean, "images": [], "note": "search failed"}
    imgs, seen = [], set()
    for u in re.findall(r'https://hornung-baushop\.de/media/[^"?\s]+?\.(?:jpg|jpeg|png|webp)', h):
        if ean in u and u not in seen:
            seen.add(u); imgs.append(u)
    slugs = []
    for s in re.findall(r'href="(https://hornung-baushop\.de/[a-z0-9-]+)"', h):
        if s not in slugs and "/search" not in s:
            slugs.append(s)
    return {"ean": ean, "images": imgs, "page": slugs[0] if slugs else None,
            "slug_words": slugs[0].rsplit("/", 1)[-1].replace("-", " ") if slugs else ""}


def main():
    if "--from" in sys.argv:
        src = json.load(open(sys.argv[sys.argv.index("--from") + 1]))
        out = {}
        for code, v in src.items():
            ean = v["barcode"] if isinstance(v, dict) else v
            r = lookup(ean)
            if r["images"]:
                out[code] = r
                print(f"{code:<10} {ean} {len(r['images'])} img  {r['slug_words'][:60]}", flush=True)
            else:
                print(f"{code:<10} {ean} -", flush=True)
            time.sleep(0.8)
        dest = sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else "/tmp/ean-images.json"
        json.dump(out, open(dest, "w"), indent=1)
        print(f"{len(out)}/{len(src)} resolved -> {dest}")
    else:
        print(json.dumps([lookup(a) for a in sys.argv[1:]], indent=1))


if __name__ == "__main__":
    main()
