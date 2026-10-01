#!/usr/bin/env python3
"""Fetch mapped royalcanin.com/uk pages with headless Chrome (own profiles), keep productData.response."""
import json, os, re, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor
R = os.path.dirname(os.path.abspath(__file__))
S = "/private/tmp/claude-501/-Users-conceptmacmini01-Documents-Projects-Siruk-claude/9757426a-8c71-478a-9cfa-a0164dd86bb2/scratchpad"
CH = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
m = json.load(open(f"{R}/map.json"))
def get(item):
    (key, slug), slot = item
    out = f"{R}/pages/{key}.json"
    if os.path.exists(out):
        return key, "cached"
    prof = f"{S}/chrome-prof-{slot}"
    for attempt in range(2):
        p = subprocess.Popen([CH, "--headless=new", "--disable-gpu", f"--user-data-dir={prof}", "--virtual-time-budget=20000",
                              "--dump-dom", f"https://www.royalcanin.com/uk/{slug}"], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        try:
            html, _ = p.communicate(timeout=90)
        except subprocess.TimeoutExpired:
            p.kill(); html = p.communicate()[0]
        h = html.decode("utf-8", "ignore")
        mm = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', h, re.S)
        if mm:
            d = json.loads(mm.group(1))["props"]["pageProps"].get("productData", {}).get("response")
            if d:
                d["_url"] = f"https://www.royalcanin.com/uk/{slug}"
                json.dump(d, open(out, "w"), ensure_ascii=False)
                return key, "ok"
        time.sleep(3)
    return key, "FAILED"
items = [(kv, i % 2) for i, kv in enumerate(sorted(m.items()))]
with ThreadPoolExecutor(2) as ex:
    for key, st in ex.map(get, items):
        print(key, st, flush=True)
