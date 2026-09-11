#!/usr/bin/env python3
"""Replace hafo images with official brand-site images.

hafo.am is our identity lookup only — product photography must come from the
brand's own site. This clears every existing variant image and re-attaches only
images resolved from an official source, leaving the rest empty so they show up
in the run's follow-up CSV rather than shipping someone else's photo.
"""
import json, subprocess, sys, os, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Loaded from .siruk-cache/official-map.json (monge.shop, matched by EAN) and
# merged over the static table below.
import os as _os
_MAP = {}
_f = _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))),
                   ".siruk-cache/official-map.json")
if _os.path.exists(_f):
    _MAP = json.load(open(_f))

OFFICIAL = {
 # TRIXIE — cdn.trixie.de, keyed by the article number printed on the pack
 "4020Tx":  "https://cdn.trixie.de/assets/img/1600mx1200m/PHO_PAC_CLIP_4020-1_%23SALL_%23AWK_%23V1.jpg",
 "40121Tx": "https://cdn.trixie.de/assets/img/1600mx1200m/PHO_PRO_CLIP_40121-1_%23SALL_%23AWK_%23V1.jpg",
 "40397Tx": "https://cdn.trixie.de/assets/img/1600mx1200m/PHO_PRO_CLIP_40397-5_%23SALL_%23AWK_%23V1.jpg",
 "42404Tx": "https://cdn.trixie.de/assets/img/1600mx1200m/PHO_PAC_CLIP_42404-1_%23SALL_%23AWK_%23V1.jpg",
 # MONGE — monge.it, filename verified to name the same line, flavour and pack
 "011257": "https://www.monge.it/wp-content/uploads/2016/04/monge_cane_secco_all_breeds_puppy_e_junior_agnello_con_riso.jpg",
 "011407": "https://www.monge.it/wp-content/uploads/2023/09/Extra-Small-Puppy-and-Junior-Rich-in-Chicken_800g_8009470011402.jpg",
 "011477": "https://www.monge.it/wp-content/uploads/2016/04/monge_cane_secco_extra_small_adult_agnello_riso_e_patate.jpg",
 "012087": "https://www.monge.it/wp-content/uploads/2020/02/monge_gatto_secco_bwild_sterilised_tonno_con_piselli.jpg",
 "012067": "https://www.monge.it/wp-content/uploads/2020/02/monge_gatto_secco_bwild_large_breed_bufalo_con_patate_e_lenticchie.jpg",
 # TRIXIE 5 l litter: EAN 4011905-04026-4 gives article 4026, not 40261
 "40261Tx": "https://cdn.trixie.de/assets/img/1600mx1200m/PHO_PAC_CLIP_4026-1_%23SALL_%23AWK_%23V1.jpg",
}

# monge.shop wins wherever it has an EAN-exact hit: it is the brand's own shop
# and the match needed no name guessing at all.
ABOUT = {}
for _k, _v in _MAP.items():
    if _v.get("image"):
        OFFICIAL[_k] = _v["image"]
    if _v.get("about"):
        ABOUT[_k] = _v["about"]


def sh(cmd, **kw):
    return subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, **kw)


def get(pid):
    r = sh([f"{ROOT}/scripts/api.sh", "GET", f"/products/{pid}"])
    i = r.stdout.find("{")
    return json.loads(r.stdout[i:])["data"] if i >= 0 else None


def upload(url):
    r = sh([f"{ROOT}/scripts/upload-media.sh", url])
    ids = re.findall(r"media(?:\s+id)?\s*[:=]?\s*(\d+)", r.stdout, re.I)
    if not ids:
        ids = re.findall(r"\b(\d{3,6})\b", r.stdout.strip().splitlines()[-1] if r.stdout.strip() else "")
    return int(ids[-1]) if ids else None


def main():
    pids = [int(x) for x in sys.argv[1:]] or list(range(160, 199))
    cache, changed, cleared, attached = {}, 0, 0, 0
    for pid in pids:
        d = get(pid)
        if not d:
            continue
        touched = False
        for v in d.get("variants", []):
            sku = v.get("sku")
            want = OFFICIAL.get(sku)
            if want:
                if want not in cache:
                    cache[want] = upload(want)
                    print(f"  uploaded {sku:<9} -> media {cache[want]}")
                new = [cache[want]] if cache[want] else []
                if new: attached += 1
            else:
                new = []          # drop the hafo image, leave it empty
                if v.get("images"): cleared += 1
            if (v.get("images") or []) != new:
                v["images"] = new; touched = True
            about = ABOUT.get(sku)
            if about and v.get("about_this_item") != about:
                v["about_this_item"] = about; touched = True
        if not touched:
            continue
        body = {k: d[k] for k in ("name","slug","brand_id","attribute_family_id",
                                  "is_best_seller","is_on_sale") if k in d}
        body["category_ids"] = [c["id"] if isinstance(c, dict) else c
                                for c in (d.get("categories") or d.get("category_ids") or [])]
        body["variants"] = d["variants"]
        if d.get("meta"): body["meta"] = d["meta"]
        r = sh([f"{ROOT}/scripts/api.sh", "PUT", f"/products/{pid}", "-"], input=json.dumps(body))
        ok = "HTTP 200" in (r.stdout.splitlines()[0] if r.stdout else "")
        print(f"{pid:<4} {d['name'][:44]:<44} {'ok' if ok else 'FAILED ' + r.stdout[:120]}")
        changed += ok
    print(f"\n{changed} products updated — {cleared} hafo images removed, {attached} official images attached")


if __name__ == "__main__":
    main()
