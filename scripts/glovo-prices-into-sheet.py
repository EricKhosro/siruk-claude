#!/usr/bin/env python3
"""Glovo prices of record → column F of final/glovo/siruk-glovo-products.xlsx.

  uv run --no-sync --with openpyxl python scripts/glovo-prices-into-sheet.py harvest   # re-read Zoovet's Glovo store
  uv run --no-sync --with openpyxl python scripts/glovo-prices-into-sheet.py fill      # dry run: what would change
  uv run --no-sync --with openpyxl python scripts/glovo-prices-into-sheet.py fill --write

Then push with `scripts/glovo-portal.py prices` (skill /glovo-portal).

The rule (user 2026-11-15 evening; replaces the +14 % base and the 50–200 ֏ tiers;
reference/glovo/portal.md → "New rule"):
  1. Default: Siruk price ÷ 0.8 (= +25 %), rounded UP to 50 ֏. Glovo keeps 20 % of its price,
     so a Glovo sale earns the shop profit.
  2. Where the same item is on Zoovet's *Glovo* store, in stock (state/glovo-zoovet-matches.csv,
     checked matches; the lowest if several): 50 ֏ under Zoovet's Glovo price zp — zp − 50
     rounded DOWN to 50 ֏, or to 10 ֏ when that would open a gap over 100 ֏. Up or down from
     the default, Royal Canin included.
  3. Floor: never below Siruk + 15 %, rounded UP to 50 ֏ — below that we stop following Zoovet
     (the floor wins even when it ends above Zoovet).
  4. A Zoovet price under 40 % of our Siruk price is per kg / per piece (big Monge bags, single
     sticks): not compared, the default stays.
Siruk price and cost come from the export (.siruk-cache/glovo/siruk-export.json, `siruk export
--format json`); final/siruk-source-of-truth.xlsx column N (the Yandex price) is no longer read.
`fill` also writes runs/<date>/glovo-undercut-dryrun.csv: one line per matched row.

Zoovet's Glovo store: store 452954, branch address 712865 — the branch customers see as open.
(The address-less site shows branch 761345, closed, with another catalogue and lower prices.)
Customer API, no login, pages are 0-based (reference/glovo/portal.md → storefront API).
"""
import argparse, csv, json, math, os, re, sys, time, urllib.error, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHEET = os.path.join(ROOT, 'final', 'glovo', 'siruk-glovo-products.xlsx')
MATCHES = os.path.join(ROOT, 'state', 'glovo-zoovet-matches.csv')
CACHE = os.path.join(ROOT, '.siruk-cache', 'glovo')
ZOOVET = os.path.join(CACHE, 'zoovet-glovo-open.json')
EXPORT = os.path.join(CACHE, 'siruk-export.json')
STORE, ADDRESS = 452954, 712865
COMMISSION, ROUND, PER_UNIT = 0.20, 50, 0.40
MARKUP, FLOOR = 1 / 0.8, 1.15          # default Siruk ÷ 0.8; floor Siruk + 15 %
UNDER, MAX_GAP, FINE_ROUND = 50, 100, 10
WILD = 0.40                            # |zp / default − 1| above this → flagged as a likely wrong match


def up50(x):
    return int(math.ceil(round(x / ROUND, 6)) * ROUND)


def under_zoovet(zp):
    """zp − 50 rounded down to 50 ֏, or to 10 ֏ when the 50 ֏ step would open a gap over 100 ֏."""
    p = math.floor(round((zp - UNDER) / ROUND, 6)) * ROUND
    if zp - p > MAX_GAP:
        p = math.floor(round((zp - UNDER) / FINE_ROUND, 6)) * FINE_ROUND
    return int(p)


def glovo_price(siruk, zp=None):
    """(price, rule) for one variant; zp = Zoovet's in-stock Glovo price of a checked match."""
    default, floor = up50(siruk * MARKUP), up50(siruk * FLOOR)
    if zp is None:
        return default, 'default'
    if zp < PER_UNIT * siruk:
        return default, 'default (Zoovet price is per kg / piece)'
    want = under_zoovet(zp)
    if want < floor:
        return floor, 'floor: Siruk + 15% (Zoovet is cheaper)'
    return want, f'{zp - want:.0f} under Zoovet'
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
    json.dump(out, open(ZOOVET, 'w', encoding='utf-8'), ensure_ascii=False)
    print(f'{len(out)} Zoovet Glovo products → {ZOOVET}')


def cmd_fill(a):
    import openpyxl
    export = json.load(open(EXPORT, encoding='utf-8'))
    siruk = {str(v['sku']): v.get('price') for v in export if v.get('sku')}
    cost = {str(v['sku']): v.get('cost_price') or 0 for v in export if v.get('sku')}
    brand = {str(v['sku']): v.get('brand') or '' for v in export if v.get('sku')}
    zoovet = json.load(open(ZOOVET, encoding='utf-8'))
    zmatch = {}
    for m in csv.DictReader(open(MATCHES, encoding='utf-8')):
        z = zoovet.get(m['zoovet_code'])
        if z and z.get('price') and not z.get('out_of_stock'):
            zmatch.setdefault(m['sku'], []).append((float(z['price']), m['zoovet_code']))

    wb = openpyxl.load_workbook(SHEET)
    ws = wb.worksheets[0]
    changes, nobase, wild, log, losses = [], [], [], [], []
    rules = {}
    for row in ws.iter_rows(min_row=3):
        sku = str(row[0].value).strip() if row[0].value is not None else ''
        if not sku:
            continue
        old = row[5].value
        sp = siruk.get(sku)
        if not sp:
            nobase.append(sku); continue
        zp, code = min(zmatch[sku]) if sku in zmatch else (None, '')
        price, rule = glovo_price(sp, zp)
        key = '50–100 under Zoovet' if 'under Zoovet' in rule else rule
        rules[key] = rules.get(key, 0) + 1
        c = cost.get(sku, 0)
        if price * (1 - COMMISSION) <= c:
            losses.append((sku, brand.get(sku), sp, price, c))
        if zp is not None:
            if abs(zp / up50(sp * MARKUP) - 1) > WILD and zp >= PER_UNIT * sp:
                wild.append((sku, brand.get(sku), sp, zp, code))
            log.append(dict(sku=sku, brand=brand.get(sku), cost=c, siruk_price=sp, sheet_price=old,
                            zoovet_glovo_price=zp, zoovet_code=code, new_price=price, rule=rule,
                            gap=round(zp - price), net_at_new=round(price * (1 - COMMISSION) - c)))
        if old != price:
            changes.append((sku, old, price, sp, zp, rule))
            if a.write:
                row[5].value = price
    for s_, o, p, b, z, r in changes:
        print(f'{s_:>18} {o!s:>8} → {p:>8}   Siruk {b:>8}   Zoovet Glovo {z if z else "-":>8}   {r}')
    print(f'{len(changes)} changes in column F; rules used: {rules}; {len(nobase)} SKUs not in the export (left as is)')
    for s_, br, sp, p, c in losses:
        print(f'  AT A LOSS after the 20% commission: {s_} {br}  Siruk {sp}, Glovo {p}, cost {c}')
    for s_, br, b, z, code in wild:
        print(f'  CHECK THE MATCH (Zoovet {z / b - 1:+.0%} vs our Siruk price): {s_} {br}  Siruk {b}, Zoovet {z} {code}')
    out = os.path.join(ROOT, 'runs', time.strftime('%Y-%m-%d'), 'glovo-undercut-dryrun.csv')
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.DictWriter(f, fieldnames=list(log[0]) if log else ['sku'])
        w.writeheader(); w.writerows(log)
    print(f'{len(log)} matched rows → {out}')
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
