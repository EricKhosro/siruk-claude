#!/usr/bin/env python3
"""Open every image link in the Glovo workbook and prove it serves a 500×500 picture.

    scripts/check-glovo-links.py                       # final/glovo/siruk-glovo-products.xlsx
    scripts/check-glovo-links.py --xlsx path.xlsx
    scripts/check-glovo-links.py --retries 3 --workers 8

Reads column D of every data row, downloads each distinct link (the workbook repeats
one link across variants), and checks: HTTP 200, an image content type, a JPEG/PNG
that decodes, and — by default — exactly 500×500 px (the template's square).
Prints a summary, plus one line per failing link (with the skus that use it), and
exits 1 when anything fails. Read-only: it never touches Siruk or the workbook.
"""
import argparse, collections, io, sys, time, urllib.error, urllib.request
import concurrent.futures as cf

import openpyxl
from PIL import Image

UA = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36')


def rows(path):
    ws = openpyxl.load_workbook(path, read_only=True).active
    out = []
    for r in ws.iter_rows(min_row=3, max_col=4, values_only=True):
        if r[0] and r[3]:
            out.append((r[0], r[3]))
    return out


def check(url, retries, side):
    err = ''
    for attempt in range(retries):
        t = time.time()
        try:
            req = urllib.request.Request(url, headers={'User-Agent': UA})
            with urllib.request.urlopen(req, timeout=40) as r:
                body = r.read()
                ctype = r.headers.get('content-type', '')
                code = r.status
            if code != 200:
                err = f'HTTP {code}'
            elif not ctype.startswith('image/'):
                err = f'content-type {ctype}'
            else:
                size = Image.open(io.BytesIO(body)).size
                if side and size != (side, side):
                    return url, False, f'{size[0]}×{size[1]} not {side}×{side}', round(time.time() - t, 1)
                return url, True, f'{size[0]}×{size[1]} · {len(body) // 1024} KB', round(time.time() - t, 1)
        except urllib.error.HTTPError as e:
            err = f'HTTP {e.code}'
        except Exception as e:
            err = type(e).__name__ + ': ' + str(e)[:80]
        if attempt + 1 < retries:
            time.sleep(2 * (attempt + 1))
    return url, False, err, 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--xlsx', default='final/glovo/siruk-glovo-products.xlsx')
    ap.add_argument('--workers', type=int, default=8)
    ap.add_argument('--retries', type=int, default=3)
    ap.add_argument('--side', type=int, default=500, help='required square side (0 = any size)')
    ap.add_argument('--json', help='write the per-link results here')
    a = ap.parse_args()

    data = rows(a.xlsx)
    users = collections.defaultdict(list)
    for sku, url in data:
        users[url].append(sku)
    urls = list(users)
    print(f'{len(data)} rows, {len(urls)} distinct links — checking with {a.workers} workers', flush=True)

    bad, done = [], 0
    with cf.ThreadPoolExecutor(a.workers) as ex:
        futs = [ex.submit(check, u, a.retries, a.side) for u in urls]
        for f in cf.as_completed(futs):
            url, ok, info, secs = f.result()
            done += 1
            if not ok:
                bad.append((url, info, users[url]))
            if done % 100 == 0:
                print(f'  {done}/{len(urls)} checked, {len(bad)} failing', flush=True)

    if a.json:
        import json
        json.dump({u: {'ok': u not in {b[0] for b in bad}} for u in urls}, open(a.json, 'w'), indent=1)

    print(f'\n{len(urls) - len(bad)}/{len(urls)} links OK, {len(bad)} failing')
    for url, info, skus in bad[:50]:
        print(f'  FAIL {url} — {info} — skus {", ".join(skus[:5])}')
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
