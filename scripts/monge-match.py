#!/usr/bin/env python3
"""Match our products to a monge.it product page and pull its official image.

monge.it's English catalogue is only partial, but product photography is the
same across locales, so we search the *whole* sitemap (all languages) and score
slugs on multilingual keyword overlap. Images are language-independent; the
English name still comes from our own catalogue, not from the matched page.

Usage: monge-match.py <urls-file> <spec.json> [--out out.json]
   spec.json: [{"key":"...", "must":[["pollo","chicken"],...], "nice":[...], "not":[...]}]
"""
import json, re, sys, urllib.request, urllib.parse

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")


def score(slug, spec):
    s = slug.lower()
    for group in spec.get("not", []):
        if any(w in s for w in group):
            return -1
    total = 0
    for group in spec.get("must", []):
        if not any(w in s for w in group):
            return -1
        total += 10
    for group in spec.get("nice", []):
        if any(w in s for w in group):
            total += 3
    # prefer English pages when several score the same
    if "/en/product/" in slug:
        total += 2
    return total - len(s) / 500.0


def og_image(url):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=45) as r:
            html = r.read().decode("utf-8", "replace")
    except Exception as e:
        return None, str(e)
    m = re.search(r'<meta property="og:image" content="([^"]+)"', html)
    if m:
        return m.group(1), None
    m = re.search(r'(https://www\.monge\.it/wp-content/uploads/[^"\' ]+\.(?:jpg|png))', html)
    return (m.group(1) if m else None), None


def main():
    urls = [u.strip() for u in open(sys.argv[1]) if u.strip()]
    specs = json.load(open(sys.argv[2]))
    out = []
    for sp in specs:
        ranked = sorted(((score(u, sp), u) for u in urls), reverse=True)
        best = [(sc, u) for sc, u in ranked if sc > 0][:3]
        rec = {"key": sp["key"], "candidates": [u for _, u in best]}
        if best:
            img, err = og_image(best[0][1])
            rec.update({"url": best[0][1], "image": img, "error": err})
        out.append(rec)
        print(f"{sp['key']:<44} {'OK ' if rec.get('image') else 'NO '} "
              f"{(rec.get('url') or '')[-62:]}", file=sys.stderr)
    o = sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else None
    js = json.dumps(out, ensure_ascii=False, indent=1)
    open(o, "w").write(js) if o else print(js)


if __name__ == "__main__":
    main()
