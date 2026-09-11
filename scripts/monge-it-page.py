#!/usr/bin/env python3
"""Fetch + parse a monge.it product page (any locale): name (h1), og:image and
gallery images, description paragraphs, composition, analytical constituents,
additives, feeding table text. Cached in .siruk-cache/mongeit-html/.

    scripts/monge-it-page.py --url <page> | --urls list.json --out pages.json
"""
import hashlib, html, json, os, re, subprocess, sys, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HTML_CACHE = os.path.join(ROOT, ".siruk-cache", "mongeit-html")
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")


def get(url):
    os.makedirs(HTML_CACHE, exist_ok=True)
    p = os.path.join(HTML_CACHE, hashlib.sha1(url.encode()).hexdigest() + ".html")
    if os.path.exists(p):
        return open(p, encoding="utf-8", errors="ignore").read(), True
    for i in range(3):
        r = subprocess.run(["curl", "-sS", "-A", UA, "-L", "--max-time", "40", url], capture_output=True, text=True)
        if r.returncode == 0 and len(r.stdout) > 5000:
            open(p, "w", encoding="utf-8").write(r.stdout)
            return r.stdout, False
        time.sleep(2 * (i + 1))
    return "", False


def clean(s):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s or ""))).strip()


def parse(url, h):
    out = {"url": url}
    m = re.search(r"<h1[^>]*>(.*?)</h1>", h, re.S)
    out["name"] = clean(m.group(1)) if m else ""
    og = re.search(r'property="og:image"\s+content="([^"]+)"', h) or re.search(r'content="([^"]+)"\s+property="og:image"', h)
    out["images"] = [og.group(1)] if og else []
    txt = clean(h)
    i = txt.find("Related Products")
    if i > 0:
        txt = txt[:i]
    nm = out["name"]
    j = txt.find(nm) if nm else -1
    body = txt[j + len(nm):] if j >= 0 else txt
    m = re.search(r"^\s*(?:\d+[.,]?\d*\s*(?:g|kg|ml|l)\s+)?(.*?)\s+Product Details", body, re.S)
    out["description"] = m.group(1).strip()[:2000] if m else ""
    if "{" in out["description"] or "wp-" in out["description"] or "sourceURL" in out["description"]:
        out["description"] = ""
    m = re.search(r"Instructions for use\s+Composition\s+(.*?)\s+Analytical components\s+(.*?)\s+Additives\s+(.*?)\s+Instructions for use\s+(.*)$", body, re.S)
    if not m:
        m = re.search(r"Composition\s+(.*?)\s+Analytical components\s+(.*?)\s+Additives\s+(.*?)\s+Instructions for use\s+(.*)$", body[body.find("Instructions for use") + 1:] if "Instructions for use" in body else body, re.S)
    if m:
        out["composition"], out["analytical"], out["additives"], out["feeding"] = [m.group(k).strip()[:2000] for k in (1, 2, 3, 4)]
    else:
        out["composition"] = out["analytical"] = out["additives"] = out["feeding"] = ""
    for k in ("description", "composition", "analytical", "additives", "feeding"):
        out[k] = re.sub(r"(Add to cart|Share|Print).*$", "", out[k]).strip()
    return out


def main():
    if "--url" in sys.argv:
        u = sys.argv[sys.argv.index("--url") + 1]
        h, _ = get(u); print(json.dumps(parse(u, h), ensure_ascii=False, indent=1)); return
    urls = json.load(open(sys.argv[sys.argv.index("--urls") + 1]))
    outp = sys.argv[sys.argv.index("--out") + 1]
    out = json.load(open(outp)) if os.path.exists(outp) else {}
    for i, u in enumerate(urls, 1):
        if u in out:
            continue
        h, cached = get(u)
        if not h:
            print(f"[{i}] FAILED {u}", file=sys.stderr); continue
        out[u] = parse(u, h)
        print(f"[{i}/{len(urls)}] {'cache' if cached else 'net'} {out[u]['name'][:60]} imgs={len(out[u]['images'])}", file=sys.stderr)
        if not cached:
            time.sleep(0.8)
    json.dump(out, open(outp, "w"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
