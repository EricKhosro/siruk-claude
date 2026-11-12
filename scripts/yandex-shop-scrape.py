#!/usr/bin/env python3
"""Read a rival shop's whole Yandex Eats catalogue (names, prices, sizes, categories).

The storefront's own public API, no login needed:
  POST https://eats.yandex.com/api/v2/menu/goods  {"slug", "latitude", "longitude", "maxDepth"}
    → the category tree (items in a category come only as a preview there)
  same call + "category_uid": "<id>" → every item of that category and its children

  python3 scripts/yandex-shop-scrape.py zoovetam
  → .siruk-cache/yandex/<slug>-items.json and .csv (one row per item)

Yerevan coordinates by default; --lat/--lon for another delivery point.
"""
import argparse, csv, json, os, sys, time, urllib.error, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, '.siruk-cache', 'yandex')
URL = 'https://eats.yandex.com/api/v2/menu/goods?auto_translate=false'


def goods(slug, lat, lon, category=None, tries=3):
    body = {'slug': slug, 'maxDepth': 100, 'latitude': lat, 'longitude': lon}
    if category:
        body['category_uid'] = str(category)
    req = urllib.request.Request(URL, json.dumps(body).encode(), {
        'Content-Type': 'application/json', 'User-Agent': 'Mozilla/5.0', 'Accept-Language': 'hy'})
    for a in range(tries):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.load(r)['payload']
        except urllib.error.HTTPError as e:
            if e.code == 404:                       # an empty category answers 404
                return {'categories': []}
            if a == tries - 1:
                raise
            time.sleep(2 * (a + 1))
        except Exception:
            if a == tries - 1:
                raise
            time.sleep(2 * (a + 1))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('slug', help='shop slug from the eats.yandex.com/…/retail/<slug> url')
    ap.add_argument('--lat', type=float, default=40.177642)
    ap.add_argument('--lon', type=float, default=44.512519)
    a = ap.parse_args()

    cats = goods(a.slug, a.lat, a.lon)['categories']
    by_id = {c['id']: c for c in cats}

    def path(cid):
        p, c = [], by_id.get(cid)
        while c:
            p.insert(0, c['name'].strip())
            c = by_id.get(c['parentId'])
        return ' > '.join(p)

    items = {}
    for c in cats:
        if c['slug'] == 'skidki-i-aktsii':          # promo shelf repeats other items
            continue
        for cc in goods(a.slug, a.lat, a.lon, c['id'])['categories']:
            for it in cc.get('items') or []:
                k = it.get('public_id') or it['uid']
                row = items.setdefault(k, {
                    'id': k, 'name': it['name'], 'price': it.get('decimalPrice'),
                    'promo_price': it.get('decimalPromoPrice') or '', 'weight': it.get('weight') or '',
                    'price_per_kg': (it.get('weight_data') or {}).get('price_per_kg', ''),
                    'available': it.get('available'), 'description': (it.get('description') or '').strip(),
                    'picture': (it.get('picture') or {}).get('url', ''), 'categories': []})
                p = path(cc['id'])
                if p not in row['categories']:
                    row['categories'].append(p)
        time.sleep(1.5)
        print(f"{len(items):5} items after {c['name'].strip()}", file=sys.stderr)

    os.makedirs(OUT, exist_ok=True)
    rows = list(items.values())
    json.dump(rows, open(os.path.join(OUT, f'{a.slug}-items.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    with open(os.path.join(OUT, f'{a.slug}-items.csv'), 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, [k for k in rows[0] if k != 'description'], extrasaction='ignore')
        w.writeheader()
        for r in rows:
            w.writerow({**r, 'categories': ' | '.join(r['categories'])})
    print(f'{len(rows)} items → {OUT}/{a.slug}-items.json / .csv')


if __name__ == '__main__':
    main()
