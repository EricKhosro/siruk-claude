#!/usr/bin/env python3
"""Glovo prices of record → column F of final/glovo/siruk-glovo-products.xlsx.

  uv run --no-sync --with openpyxl python scripts/glovo-prices-into-sheet.py harvest   # re-read Zoovet's Glovo store
  uv run --no-sync --with openpyxl python scripts/glovo-prices-into-sheet.py fill      # dry run: what would change
  uv run --no-sync --with openpyxl python scripts/glovo-prices-into-sheet.py fill --write

Then push with `scripts/glovo-portal.py prices` (skill /glovo-portal).

The rule (user 2026-11-06, "make sure everything is even a little under zoovet"):
  1. base = the Yandex/Glovo price, column N of final/siruk-source-of-truth.xlsx
     (scripts/yandex-prices-into-sot.py: 5% under Zoovet's *Yandex* price, else Siruk + 14%).
  2. Where the same item is on Zoovet's *Glovo* store (state/glovo-zoovet-matches.csv, checked
     matches) and base ≥ Zoovet's Glovo price, the price becomes Zoovet's Glovo price minus a
     little: rounded down to 50 ֏ below it (900 → 850, 980 → 950). Royal Canin included — the
     Yandex rule's Royal Canin exemption does not apply on Glovo.
  3. Never at a loss: if that price leaves nothing after the 20% commission
     (price × 0.8 ≤ cost) the base stays and the row is reported.
  4. A Zoovet price under 40% of ours is a per-kg / per-piece price (big Monge bags, single sticks):
     not compared, the base stays.

Zoovet's Glovo store: store 452954, branch address 712865 — the branch customers see as open.
(The address-less site shows branch 761345, closed, with another catalogue and lower prices.)
Customer API, no login, pages are 0-based (reference/glovo/portal.md → storefront API).
"""
import argparse, csv, json, math, os, re, sys, time, urllib.error, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOT = os.path.join(ROOT, 'final', 'siruk-source-of-truth.xlsx')
SHEET = os.path.join(ROOT, 'final', 'glovo', 'siruk-glovo-products.xlsx')
MATCHES = os.path.join(ROOT, 'state', 'glovo-zoovet-matches.csv')
CACHE = os.path.join(ROOT, '.siruk-cache', 'glovo')
ZOOVET = os.path.join(CACHE, 'zoovet-glovo-open.json')
EXPORT = os.path.join(CACHE, 'siruk-export.json')
STORE, ADDRESS = 452954, 712865
COMMISSION, ROUND, PER_UNIT = 0.20, 50, 0.40
H = {'glovo-app-platform': 'web', 'glovo-app-type': 'customer', 'glovo-language-code': 'hy',
     'glovo-location-city-code': 'YRV', 'glovo-api-version': '14', 'glovo-app-version': '7',
     'User-Agent': 'Mozilla/5.0'}


def get(url):
    for k in range(8):
        try:
            return json.loads(urllib.request.urlopen(urllib.request.Request(url, headers=H), timeout=40).read())
        except urllib.error.HTTPError as e:
            if e.code in (429, 503):           # Glovo rate-limits fast readers
                time.sleep(15 * (k + 1)); continue
            raise
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            time.sleep(10 * (k + 1))
    sys.exit('gave up: ' + url)


def cmd_harvest(a):
    base = f'https://api.glovoapp.com'
    menu = get(f'{base}/v3/stores/{STORE}/addresses/{ADDRESS}/node/store_menu')
    sections = []
    def walk(es):
        for e in es:
            m = re.search(r's\.(\d+)$', e['action']['data']['path'])
            if not e['elements'] and m:
                sections.append((e['name'], m.group(1)))
            walk(e['elements'])
    walk(menu['data']['elements'])
    out = {}
    for name, sid in sections:
        seen, page = set(), 0
        while page < 200:
            j = get(f'{base}/v4/stores/{STORE}/addresses/{ADDRESS}/content/partial?component=section&id={sid}&page={page}')
            tiles = [x['data'] for g in j['data']['body'] for x in g['data'].get('elements', []) if x['type'] == 'PRODUCT_TILE']
            new = [t for t in tiles if t['externalId'] not in seen]
            if not new:
                break
            for t in new:
                seen.add(t['externalId'])
                out.setdefault(t['externalId'], {'name': t['name'], 'price': t.get('price'), 'section': name,
                                                 'out_of_stock': t.get('outOfStock'), 'promotions': t.get('promotions') or [],
                                                 'description': t.get('description', '')})
            page += 1
            time.sleep(1.5)
        print(f'{name}: {len(seen)}', flush=True)
    os.makedirs(CACHE, exist_ok=True)
    json.dump(out, open(ZOOVET, 'w'), ensure_ascii=False)
    print(f'{len(out)} Zoovet Glovo products → {ZOOVET}')


def cmd_fill(a):
    import openpyxl
    down = lambda x: math.floor(round(x / ROUND, 6)) * ROUND
    export = json.load(open(EXPORT, encoding='utf-8'))
    sku_vid = {str(v['sku']): v['variant_id'] for v in export if v.get('sku')}
    cost = {str(v['sku']): v.get('cost_price') or 0 for v in export if v.get('sku')}
    brand = {str(v['sku']): v.get('brand') or '' for v in export if v.get('sku')}
    sot = openpyxl.load_workbook(SOT, read_only=True, data_only=True).worksheets[0]
    vid_n = {}
    for r in sot.iter_rows(min_row=2, values_only=True):
        m = re.search(r'/dp/(\d+)', r[7] or '')
        if m and isinstance(r[13], (int, float)):
            vid_n[int(m.group(1))] = r[13]
    zoovet = json.load(open(ZOOVET, encoding='utf-8'))
    zmatch = {}
    for m in csv.DictReader(open(MATCHES, encoding='utf-8')):
        z = zoovet.get(m['zoovet_code'])
        if z and z.get('price') and not z.get('out_of_stock'):
            zmatch.setdefault(m['sku'], []).append((float(z['price']), m['zoovet_code']))

    wb = openpyxl.load_workbook(SHEET)
    ws = wb.worksheets[0]
    changes, losses, per_unit, nobase, under = [], [], [], [], 0
    for row in ws.iter_rows(min_row=3):
        sku = str(row[0].value).strip() if row[0].value is not None else ''
        if not sku:
            continue
        old = row[5].value
        base = vid_n.get(sku_vid.get(sku))
        if base is None:
            nobase.append(sku); continue
        price = base
        if sku in zmatch:
            zp, code = min(zmatch[sku])
            if zp < PER_UNIT * base:
                per_unit.append((sku, base, zp, code))
            elif base >= zp:
                want = down(zp - 1)
                if want * (1 - COMMISSION) > cost.get(sku, 0):
                    price = want; under += 1
                else:
                    losses.append((sku, brand.get(sku), base, zp, cost.get(sku)))
        if old != price:
            changes.append((sku, old, price, base, zmatch.get(sku, [(None,)])[0][0]))
            if a.write:
                row[5].value = price
    for s, o, p, b, z in changes:
        print(f'{s:>18} {o!s:>8} → {p:>8}   base {b:>8}   Zoovet Glovo {z if z else "-"}')
    print(f'{len(changes)} changes in column F; {under} priced just under Zoovet Glovo; '
          f'{len(per_unit)} Zoovet per-kg/per-piece prices not compared; {len(nobase)} SKUs with no base price (left as is)')
    for s, br, b, z, c in losses:
        print(f'  CAN\'T BEAT Zoovet at a profit: {s} {br}  base {b}, Zoovet {z}, cost {c}')
    if a.write and changes:
        wb.save(SHEET)
        print(f'→ {SHEET}')
    elif changes:
        print('(dry run — add --write)')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(required=True)
    sp.add_parser('harvest', help="re-read Zoovet's Glovo store").set_defaults(f=cmd_harvest)
    p = sp.add_parser('fill', help='prices of record → column F of the Glovo sheet')
    p.add_argument('--write', action='store_true')
    p.set_defaults(f=cmd_fill)
    a = ap.parse_args()
    a.f(a)


if __name__ == '__main__':
    main()
