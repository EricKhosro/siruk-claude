#!/usr/bin/env python3
"""Probe the TRIXIE CDN for EVERY image of an article number, not just the ones
the product page happens to list.

Why: trixie.de product pages show one gallery for a whole product family, so a
single-article variant often keeps only its own packshot (and pages exist for
only 529 of our 678 articles). The CDN, however, serves every shot under a
predictable name:

    https://cdn.trixie.de/assets/img/1600mx1200m/<PREFIX>_<article>-<n>_%23SALL_%23AWK_%23V1.jpg

with PREFIX one of PHO_PRO_CLIP (packshot), PHO_PAC_CLIP (pack),
PHO_PRO_DET_CLIP (detail), PHO_PRO_SET_CLIP (set), PHO_PRO_USE(_CLIP) (in use),
PHO_PRO_DOG/CAT(_CLIP) (lifestyle), PHO_PRO (plain), GRA_PRO (drawing), and
n = 1..14 (not contiguous — article 3271 only has -6).

Group shots (PHO_PRO_GROUP_CLIP_<a>-<b>-…) carry several article numbers and
cannot be probed; they still come from the page parser.

    scripts/trixie-cdn-sweep.py <article> [...]         # probe these
    scripts/trixie-cdn-sweep.py --plan trixie-plan.json # every article in a plan
    scripts/trixie-cdn-sweep.py --plan … --refresh      # ignore the cache

Result is merged into .siruk-cache/trixie-cdn-gallery.json ({article: [url…]},
ranked packshot, pack, detail/set, in-use, lifestyle, drawing).
"""
import json, os, re, subprocess, sys, tempfile, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, ".siruk-cache")
OUT = os.path.join(CACHE, "trixie-cdn-gallery.json")
BASE = "https://cdn.trixie.de/assets/img/1600mx1200m/"
TAIL = "_%23SALL_%23AWK_%23V1.jpg"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
PFX = ["PHO_PRO_CLIP", "PHO_PAC_CLIP", "PHO_PRO_DET_CLIP", "PHO_PRO_SET_CLIP", "PHO_PRO_USE_CLIP", "PHO_PRO_USE",
       "PHO_PRO_DOG_CLIP", "PHO_PRO_CAT_CLIP", "PHO_PRO_DOG", "PHO_PRO_CAT", "PHO_PRO", "GRA_PRO"]
RANK = {"PHO_PRO_CLIP": 1, "PHO_PAC_CLIP": 2, "PHO_PRO_DET_CLIP": 3, "PHO_PRO_SET_CLIP": 4,
        "PHO_PRO_USE_CLIP": 5, "PHO_PRO_USE": 5, "PHO_PRO_DOG_CLIP": 6, "PHO_PRO_CAT_CLIP": 6,
        "PHO_PRO_DOG": 6, "PHO_PRO_CAT": 6, "PHO_PRO": 3, "GRA_PRO": 7}
LO, HI = 1, 14          # index range (overridable: --range 15-26)
PARALLEL = 32


def rank(url):
    f = url.rsplit("/", 1)[-1]
    m = re.match(r"^([A-Z_]+?)_[0-9]", f)
    p = m.group(1) if m else ""
    n = int(re.search(r"-(\d+)_%23", f).group(1)) if re.search(r"-(\d+)_%23", f) else 99
    return (RANK.get(p, 8), n, f)


def sweep(articles, chunk=40, lo=None, hi=None):
    """HEAD every candidate URL with one parallel curl per chunk of articles."""
    found = {}
    for i in range(0, len(articles), chunk):
        batch = articles[i:i + chunk]
        with tempfile.NamedTemporaryFile("w", suffix=".curl", delete=False) as f:
            for a in batch:
                for p in PFX:
                    for n in range(lo or LO, (hi or HI) + 1):
                        f.write(f"url = {BASE}{p}_{a}-{n}{TAIL}\n")
            cfg = f.name
        r = subprocess.run(["curl", "-sS", "--head", "-Z", "--parallel-max", str(PARALLEL), "-A", UA,
                            "--max-time", "30", "-K", cfg, "-o", "/dev/null", "-w", "%{http_code} %{url}\n"],
                           capture_output=True, text=True, timeout=900)
        os.unlink(cfg)
        for line in r.stdout.splitlines():
            if not line.startswith("200 "):
                continue
            url = line[4:].strip()
            m = re.search(r"/(?:[A-Z_]+?)_(\d+)-\d+_%23", url)
            if m:
                found.setdefault(m.group(1), []).append(url)
        done = min(i + chunk, len(articles))
        print(f"  {done}/{len(articles)} articles, {sum(len(v) for v in found.values())} images", file=sys.stderr)
        time.sleep(1)
    return {a: sorted(set(u), key=rank) for a, u in found.items()}


def main():
    argv = sys.argv[1:]
    refresh = "--refresh" in argv
    argv = [a for a in argv if a != "--refresh"]
    lo, hi = LO, HI
    if "--range" in argv:
        i = argv.index("--range"); lo, hi = (int(x) for x in argv[i + 1].split("-")); del argv[i:i + 2]
        refresh = True          # a new index band must re-probe articles already cached
    if argv and argv[0] == "--plan":
        plan = json.load(open(os.path.join(CACHE, argv[1])))
        arts = []
        for p in plan["products"] + plan.get("blocked_no_category", []):
            for v in p["variants"]:
                arts.append(re.sub(r"[^0-9]", "", v.get("_code") or v["sku"]))
    else:
        arts = argv
    have = json.load(open(OUT)) if os.path.exists(OUT) else {}
    todo = sorted({a for a in arts if a and (refresh or a not in have)})
    print(f"{len(set(arts))} articles, {len(todo)} to probe", file=sys.stderr)
    if todo:
        for a, urls in sweep(todo, lo=lo, hi=hi).items():
            have[a] = sorted(set(have.get(a, []) + urls), key=rank)
        for a in todo:
            have.setdefault(a, [])
        json.dump(have, open(OUT, "w"), indent=0)
    n0 = [a for a in set(arts) if not have.get(a)]
    print(f"{len(have)} articles cached; {len(n0)} of this run's articles have NO CDN image")
    if len(n0) <= 60:
        print("  ", " ".join(sorted(n0)))


if __name__ == "__main__":
    main()
