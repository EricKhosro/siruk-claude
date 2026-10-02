#!/usr/bin/env python3
"""Index every production media record (id → originalUrl, filename, directory) by listing
each media-library folder (GET /medias?directory=…&acceptTypes=…, siruk-web MediaController::index's shape).
Read-only. → media-index.json"""
import json, os, sys, urllib.parse
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
os.environ.update(SIRUK_API="https://api.siruk.am/api/admin",
                  SIRUK_TOKEN_FILE=os.path.join(ROOT, ".siruk-token-prod"))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from siruk_payload import api  # noqa: E402
TYPES = urllib.parse.quote("image/jpeg,image/png,image/webp,image/gif,image/svg+xml,image/avif", safe="")
import subprocess
_r = subprocess.run([os.path.join(ROOT, "scripts/api.sh"), "GET", "/media-folders"], capture_output=True, text=True)
tree = json.loads(_r.stdout[_r.stdout.find("["):])   # a bare JSON array, not {data: …}
paths = [""]
def walk(nodes):
    for n in nodes:
        paths.append(n["path"]); walk(n.get("children") or [])
walk(tree)
idx = {}
for d in paths:
    page = 1
    while True:
        r = api("GET", f"/medias?directory={urllib.parse.quote(d, safe='')}&acceptTypes={TYPES}&page={page}")
        for m in r.get("data") or []:
            idx[m["id"]] = {k: m.get(k) for k in ("originalUrl", "url", "filename", "extension", "directory", "dimensions")}
        last = (r.get("meta") or {}).get("last_page") or 1
        if page >= last:
            break
        page += 1
print(len(paths), "folders", len(idx), "media")
json.dump(idx, open(os.path.join(HERE, "media-index.json"), "w"), indent=0)
