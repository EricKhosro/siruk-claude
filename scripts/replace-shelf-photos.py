#!/usr/bin/env python3
"""Put the shelf-pack photo first on each variant, in Siruk and on Glovo (2026-11-11).

    python3 scripts/replace-shelf-photos.py <picks.json> [--apply] [--only N ...]

picks.json: [{"n", "file", "page_url", ...}] joined with runs/2026-11-10/shelf-answers.json
(n -> product id, variant ids, our current first photo). Per variant: the new photo is
uploaded into the folder our current photo lives in (alt "{Brand} {Name}"), put first,
and our current first photo (the other pack edition) is removed; the rest of the gallery
is kept. Then the Glovo product with the variant's SKU gets the same photo
(scripts/glovo-set-image.py). Dry run without --apply. Log: runs/<date>/shelf-photos.csv.
"""
import argparse, csv, datetime, json, os, subprocess, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)

def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    return r.returncode, r.stdout, r.stderr

def api_get(path):
    _, out, _ = run(['bash', 'scripts/api.sh', 'GET', path])
    d = json.loads(out[out.find('{'):]); return d.get('data', d)

ap = argparse.ArgumentParser(); ap.add_argument('picks'); ap.add_argument('--apply', action='store_true')
ap.add_argument('--only', nargs='*', type=int); ap.add_argument('--no-glovo', action='store_true')
ap.add_argument('--glovo-python', default=sys.executable)
a = ap.parse_args()
ans = {x['n']: x for x in json.load(open('runs/2026-11-10/shelf-answers.json'))}
brands = {b['id']: b['name'] for b in json.loads(run(['uv', 'run', '--no-sync', 'siruk', 'ids', 'brands', '--json'])[1])}
log = []
for p in json.load(open(a.picks)):
    n = p['n']
    if a.only and n not in a.only: continue
    x = ans[n]; prod = api_get(f"/products/{x['pid']}")
    alt = f"{brands.get(prod.get('brand_id'), '')} {prod['name']}".strip()
    targets = [v for v in prod['variants'] if v['id'] in x['vids']]
    for v in targets:
        media = v.get('images_media') or []
        old = [m['id'] for m in media if m.get('originalUrl') == x['ours']]
        folder = next((m['directory'] for m in media if m['id'] in old), media[0]['directory'] if media else None)
        print(f"{n}  product {x['pid']}  {v['sku']}  {alt}\n    gallery {v['images']}  remove {old}  folder {folder}\n    new  {p['file']}")
        if not old:
            print('    SKIP: our current photo is no longer on this variant'); log.append((n, x['pid'], v['sku'], '', 'skipped: photo already changed', '')); continue
        if not a.apply: continue
        rc, out, err = run(['uv', 'run', '--no-sync', 'siruk', 'media', 'upload', p['file'], '--folder', folder, '--alt', alt, '-y', '--json'])
        mid = json.loads(out[out.find('{'):])['id']
        gallery = [mid] + [i for i in v['images'] if i not in old]
        rc, out, err = run(['uv', 'run', '--no-sync', 'siruk', 'set-variant', str(x['pid']), v['sku'], json.dumps({'images': gallery}), '-y'])
        siruk_ok = rc == 0 and 'written' in out
        url = api_get(f'/medias/{mid}').get('originalUrl', '')
        glovo = 'not sent'
        if not a.no_glovo and siruk_ok:
            rc, gout, gerr = run([a.glovo_python, 'scripts/glovo-set-image.py', v['sku'], url, '--apply'])
            glovo = 'ok' if rc == 0 and 'glovo.dhmedia.io' in gout.split('after:')[-1] else ('not on Glovo' if 'StopIteration' in gerr else 'FAILED ' + (gerr or gout)[-200:])
        print(f'    siruk {"ok" if siruk_ok else "FAILED " + (err or out)[-200:]}  media {mid}  glovo {glovo}')
        log.append((n, x['pid'], v['sku'], mid, 'ok' if siruk_ok else 'FAILED', glovo))
if a.apply:
    path = f'runs/{datetime.date.today()}/shelf-photos.csv'; os.makedirs(os.path.dirname(path), exist_ok=True)
    new = not os.path.exists(path)
    with open(path, 'a', newline='') as f:
        w = csv.writer(f)
        if new: w.writerow(['n', 'product_id', 'sku', 'media_id', 'siruk', 'glovo'])
        w.writerows(log)
    print('log ->', path)
