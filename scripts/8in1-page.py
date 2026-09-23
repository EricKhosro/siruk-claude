#!/usr/bin/env python3
"""Read one 8in1.eu product page: name, pack size, bullets, composition, images.

8in1.eu prints no article number, so a page is only usable when hafo (which IS
keyed to the article) names the same line, flavour and pack — see rule 7.

    scripts/8in1-page.py <slug> [<slug> ...]
"""
import html, json, re, subprocess, sys

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")
BASE = "https://www.8in1.eu"


def text(x):
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", x)).split())


def page(slug):
    url = f"{BASE}/en/products/{slug}"
    t = subprocess.run(["curl", "-sL", "-A", UA, url], capture_output=True,
                       text=True, timeout=90).stdout
    t = re.sub(r"<script.*?</script>", "", t, flags=re.S)
    h1 = re.search(r"<h1[^>]*>(.*?)</h1>", t, flags=re.S)
    i = t.find("<h1")
    seg = t[i:i + 9000] if i >= 0 else t
    body = text(seg)
    # bullets sit between the <h1> and the pack size; "Details" starts the prose
    bullets = [b.strip() for b in re.findall(r"\|\s*([A-Z][^|]{6,110}?)\s*\|",
                                             html.unescape(re.sub(r"<[^>]+>", "|", seg)))]
    det = body.find("Details")
    prose = body[det + 7:det + 1400] if det >= 0 else ""
    comp = re.search(r"(?:Composition|Ingredients)\s*:?\s*(.{0,600})", body, flags=re.I)
    sizes = sorted(set(re.findall(r"\b(\d+\s?g(?:\s*/\s*\d+\s?ct)?)\b", body)))
    # the product's own photos carry 8in1's internal item code (TH…/TR…);
    # everything else under /fileadmin/pictures/ is a category banner
    imgs = sorted({BASE + m for m in re.findall(r'"(/fileadmin/[^"]+\.(?:png|jpg))"', t)
                   if re.search(r"csm_T[HR]\d+", m)})
    return {"url": url, "name": text(h1.group(1)) if h1 else "",
            "pack_sizes_seen": sizes[:8], "bullets": bullets[:12],
            "composition": comp.group(1)[:400] if comp else "",
            "description": prose, "images": imgs}


for s in sys.argv[1:]:
    print(json.dumps(page(s), ensure_ascii=False, indent=1))
