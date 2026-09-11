#!/usr/bin/env python3
"""Fetch neoterica.ru brand listings (all pages) and product pages; parse name,
images (544x600 renditions), description, composition and instructions.
    scripts/neoterica-fetch.py --brands rolfclub-3d,inspector,... --out .siruk-cache/neoterica/pages.json
"""
import hashlib, html, json, os, re, subprocess, sys, time
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, ".siruk-cache", "neoterica")
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
BASE = "https://neoterica.ru"


def get(url):
    os.makedirs(CACHE, exist_ok=True)
    p = os.path.join(CACHE, hashlib.sha1(url.encode()).hexdigest() + ".html")
    if os.path.exists(p):
        return open(p, encoding="utf-8", errors="ignore").read()
    for i in range(3):
        r = subprocess.run(["curl", "-sS", "-A", UA, "-L", "--max-time", "60", url], capture_output=True, text=True)
        if r.returncode == 0 and len(r.stdout) > 3000:
            open(p, "w", encoding="utf-8").write(r.stdout); time.sleep(0.7); return r.stdout
        time.sleep(2)
    return ""


def clean(s):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s or ""))).strip()


def listing(brand):
    links, page = [], 1
    while page < 15:
        h = get(f"{BASE}/brands/{brand}" + (f"?page={page}" if page > 1 else ""))
        found = [l for l in dict.fromkeys(re.findall(r'href="(/products/[^"#?]+)"', h)) if l not in links]
        if not found:
            break
        links += found; page += 1
    return links


def parse(url, h):
    out = {"url": url}
    m = re.search(r"<h1[^>]*>(.*?)</h1>", h, re.S); out["name"] = clean(m.group(1)) if m else ""
    imgs = [u for u in dict.fromkeys(re.findall(r'/sitefiles/fx/544x600/Items/[^"\']+\.(?:jpg|png|jpeg)', h))]
    out["images"] = [BASE + u for u in imgs]
    txt = clean(h)
    out["text"] = txt[:6000]
    for key, rx in (("composition", r"(?:Состав|Действующее вещество|Действующие вещества)[:\s]+(.*?)(?=\s(?:Показания|Способ применения|Применение|Дозировка|Противопоказания|Форма выпуска|Условия хранения|Срок годности|$))"),
                    ("usage", r"(?:Способ применения и дозы|Способ применения|Применение|Дозировка)[:\s]+(.*?)(?=\s(?:Противопоказания|Побочные|Условия хранения|Срок годности|Форма выпуска|$))"),
                    ("description", r"(?:Описание|Показания к применению|Показания)[:\s]+(.*?)(?=\s(?:Состав|Действующее|Способ применения|Применение|$))")):
        m = re.search(rx, txt, re.S)
        out[key] = m.group(1).strip()[:2500] if m else ""
    return out


def index(out):
    """name from <title>, 544x600 images, article codes found in image filenames, plain text."""
    for u, p in out.items():
        h = get(u)
        t = re.search(r"<title>(.*?)</title>", h, re.S)
        p["name"] = html.unescape(t.group(1)).split("✅")[0].strip() if t else p.get("name", "")
        imgs = []
        for m in re.findall(r'/sitefiles/(?:fx/544x600/)?Items/([^"\']+\.(?:png|jpg|jpeg))', h):
            u2 = BASE + "/sitefiles/fx/544x600/Items/" + m
            if u2 not in imgs:
                imgs.append(u2)
        p["images"] = imgs
        p["codes"] = sorted({c for f in imgs for c in re.findall(r"([A-Z]\d{3})", f.rsplit("/", 1)[-1])})
        p["text"] = clean(re.sub(r"<(script|style).*?</\1>", " ", h, flags=re.S))[:6000]
    return out


def main():
    outp = sys.argv[sys.argv.index("--out") + 1]
    out = json.load(open(outp)) if os.path.exists(outp) else {}
    if "--urls" in sys.argv:
        for u in json.load(open(sys.argv[sys.argv.index("--urls") + 1])):
            if u in out:
                continue
            h = get(u)
            if h:
                out[u] = parse(u, h); out[u]["brand"] = sys.argv[sys.argv.index("--brand-name") + 1] if "--brand-name" in sys.argv else "?"
                print("  ", out[u]["name"][:70], file=sys.stderr)
        index(out); json.dump(out, open(outp, "w"), ensure_ascii=False, indent=1); return
    if "--reindex" in sys.argv:
        index(out); json.dump(out, open(outp, "w"), ensure_ascii=False, indent=1); print("reindexed", len(out)); return
    brands = sys.argv[sys.argv.index("--brands") + 1].split(",")
    for b in brands:
        links = listing(b)
        print(b, len(links), file=sys.stderr)
        for l in links:
            u = BASE + l
            if u in out:
                continue
            h = get(u)
            if not h:
                continue
            out[u] = parse(u, h); out[u]["brand"] = b
            print("  ", out[u]["name"][:70], len(out[u]["images"]), file=sys.stderr)
    index(out)
    json.dump(out, open(outp, "w"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
