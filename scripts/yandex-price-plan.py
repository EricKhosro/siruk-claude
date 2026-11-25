#!/usr/bin/env python3
"""Yandex price plan: which Siruk variants go on Yandex and at what price (user 2026-11-18).

  uv run --no-sync --with openpyxl python scripts/yandex-price-plan.py [--date 2026-11-18]
  → final/yandex/yandex-plan-<date>.xlsx  (+ .siruk-cache/yandex/plan.json for the card builder)

The rule (user 2026-11-18, replaces column N of the source of truth and the Siruk-price rule):
  1. The product set is what is live on Glovo (the portal itself, `glovo-portal.py dump` →
     .siruk-cache/glovo/portal-products.json — never the sheet; user 2026-11-18), food and care only
     for now: a variant needs a real mass / volume (`measure_type` mass|volume and `content`).
     Piece goods (toys, collars, bowls …) wait: Yandex has no piece unit.
     Loose 1 kg / 100 g variants (-KG / -100G) are never sent (their barcode is a PLU).
  2. Price (user 2026-11-19, replaces "the live Glovo price"): `glovo_price()` of
     glovo-prices-into-sheet.py, run against Zoovet's YANDEX price, not its Glovo price:
     Siruk × 1.25 rounded up to 50 ֏ (Yandex keeps 20 %, so the net = the Siruk price); where Zoovet
     sells the same item on Yandex, in stock: 50–100 ֏ under Zoovet (up or down from +25 %), never
     below Siruk + 15 % (the user's pick for the clash, 2026-11-19). A Zoovet price under 40 % of our
     Siruk price is per kg / per piece and is not compared.
     A product switched off on Glovo goes up switched off on Yandex.
Zoovet's Yandex items: scripts/yandex-shop-scrape.py zoovetam → .siruk-cache/yandex/zoovetam-items.json.
Same item = a checked match: state/glovo-zoovet-matches.csv (zoovet code ↔ our SKU; Zoovet's
Yandex names end in "#<code>") or a "same" row of final/siruk-source-of-truth.xlsx (by item name).
"""
import argparse, csv, datetime, importlib.util, json, math, os, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, '.siruk-cache', 'yandex')
PORTAL = os.path.join(ROOT, '.siruk-cache', 'glovo', 'portal-products.json')
SOT = os.path.join(ROOT, 'final', 'siruk-source-of-truth.xlsx')
MATCHES = os.path.join(ROOT, 'state', 'glovo-zoovet-matches.csv')
FLOOR, PER_UNIT = 1.15, 0.40

spec = importlib.util.spec_from_file_location('gp', os.path.join(ROOT, 'scripts', 'glovo-prices-into-sheet.py'))
gp = importlib.util.module_from_spec(spec); spec.loader.exec_module(gp)
up50, under_zoovet, glovo_price = gp.up50, gp.under_zoovet, gp.glovo_price


def code_of(name):
    m = re.search(r'#\s*(\d{3,8})\s*$', name or '')
    return 'ME-' + m.group(1).zfill(8) if m else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--date', default=datetime.date.today().isoformat())
    a = ap.parse_args()
    import openpyxl

    dump = json.load(open(PORTAL, encoding='utf-8'))
    print('Glovo portal dump of', dump['saved'])
    glovo, active = {}, {}
    for it in dump['items']:
        s = str(it['sku']).strip()
        glovo[s], active[s] = float(it['price']), bool(it['active'])

    rows = json.load(open(os.path.join(CACHE, 'siruk-en.json'), encoding='utf-8'))
    by_sku = {r['sku']: r for r in rows}
    by_vid = {r['variant_id']: r for r in rows}

    zoo = json.load(open(os.path.join(CACHE, 'zoovetam-items.json'), encoding='utf-8'))
    z_by_code, z_by_name = {}, {}
    for z in zoo:
        p = float(z['promo_price'] or z['price'] or 0)
        item = {'name': z['name'], 'price': p, 'available': z['available']}
        c = code_of(z['name'])
        if c:
            z_by_code.setdefault(c, []).append(item)
        z_by_name.setdefault(z['name'].strip(), []).append(item)

    match = {}                                     # sku -> [(zoovet item, how)]
    for m in csv.DictReader(open(MATCHES, encoding='utf-8-sig')):
        for it in z_by_code.get(m['zoovet_code'], []):
            match.setdefault(m['sku'], []).append((it, 'glovo match ' + m['zoovet_code']))
    ws = openpyxl.load_workbook(SOT, read_only=True, data_only=True)['Source of truth']
    for r in ws.iter_rows(min_row=2, values_only=True):
        if not (r[11] and r[16] == 'same'):
            continue
        vid = re.search(r'/dp/(\d+)/', r[7] or '')
        v = by_vid.get(vid.group(1)) if vid else None
        if not v:
            continue
        c = code_of(r[11])
        its = z_by_code.get(c, []) if c else z_by_name.get(r[11].strip(), [])
        for it in its:
            if all(it is not x for x, _ in match.get(v['sku'], [])):
                match.setdefault(v['sku'], []).append((it, 'yandex match (source of truth)'))

    plan, skipped = [], []
    nozero = {}
    for s in by_sku:
        if s:
            nozero.setdefault(s.lstrip('0'), []).append(s)
    for gsku, gprice in glovo.items():
        sku = gsku if gsku in by_sku else (nozero.get(gsku.lstrip('0')) or [None])[0] if len(nozero.get(gsku.lstrip('0'), [])) == 1 else None
        if sku is None:
            skipped.append((gsku, '', 'Glovo SKU not found in Siruk')); continue
        v = by_sku.get(sku)
        if not v:
            skipped.append((sku, '', 'not in the Siruk export')); continue
        label = f"{v['brand']} {v['product_name']} — {v['variant_name']}"
        why, kind = None, 'pack'
        if sku.endswith(('-KG', '-100G')) or v['sale_mode'] != 'pack':
            kind = 'loose'                       # 1 kg / 100 g from an open bag: no barcode (user 2026-11-18: mirror Glovo)
        elif v['measure_type'] not in ('mass', 'volume') or v['content'] in (None, '', 'None'):
            kind = 'piece'                       # toy, bowl, bed…: measure "1 г" as Zoovet does (user 2026-11-18)
        if v['is_discontinued'] == 'True':
            why = 'discontinued'
        if why:
            skipped.append((sku, label, why)); continue
        siruk, cost = float(v['price']), float(v['cost_price'] or 0)
        zname, zp = '', None
        live = [(it, how) for it, how in match.get(sku, []) if it['available'] and it['price'] >= siruk * PER_UNIT]
        if live:
            it, how = min(live, key=lambda x: x[0]['price'])
            zname, zp = it['name'], it['price']
        price, rule = glovo_price(siruk, zp)       # the Glovo rule, against Zoovet's YANDEX price (user 2026-11-19)
        if zp is not None and not rule.startswith('default'):
            rule += f' ({how})'
        plan.append({'sku': sku, 'variant_id': v['variant_id'], 'product_id': v['product_id'], 'brand': v['brand'],
                     'product': v['product_name'], 'variant': v['variant_name'], 'categories': v['categories'],
                     'category_ids': v['category_ids'], 'measure_type': v['measure_type'], 'content': v['content'],
                     'pack_count': v['pack_count'], 'barcode': v['barcode'], 'siruk_price': siruk, 'cost': cost,
                     'glovo_price': gprice, 'zoovet_item': zname, 'zoovet_yandex_price': zp,
                     'yandex_price': int(price), 'rule': rule, 'stock_status': v['stock_status'],
                     'glovo_sku': gsku, 'glovo_active': active[gsku], 'kind': kind})

    json.dump(plan, open(os.path.join(CACHE, 'plan.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    wb = openpyxl.Workbook(); ws = wb.active; ws.title = 'Yandex prices'
    cols = ['sku', 'brand', 'product', 'variant', 'categories', 'siruk_price', 'cost', 'glovo_price',
            'zoovet_item', 'zoovet_yandex_price', 'yandex_price', 'rule', 'glovo_active']
    ws.append(['SKU', 'Brand', 'Product', 'Variant', 'Siruk category', 'Siruk price', 'Cost', 'Glovo price (live)',
               'Zoovet item on Yandex', 'Zoovet Yandex price', 'Yandex price', 'Why this price', 'On on Glovo'])
    for p in sorted(plan, key=lambda p: (p['rule'] == 'Glovo price', p['brand'], p['product'])):
        ws.append([p[c] for c in cols])
    ws2 = wb.create_sheet('Not sent yet'); ws2.append(['SKU', 'Product', 'Reason'])
    for s in skipped:
        ws2.append(list(s))
    for w in (ws, ws2):
        w.freeze_panes = 'A2'
        for col, width in zip('ABCDEFGHIJKL', (12, 16, 40, 22, 22, 10, 9, 10, 50, 10, 10, 40)):
            w.column_dimensions[col].width = width
    out = os.path.join(ROOT, 'final', 'yandex', f'yandex-plan-{a.date}.xlsx')
    wb.save(out)
    on_glovo = {p['sku'] for p in plan} | {s[0] for s in skipped}
    ws3 = wb.create_sheet('Siruk, not on Glovo'); ws3.append(['SKU', 'Product', 'Stock', 'Has g/ml size'])
    off = [r for r in rows if r['sku'] and r['sku'] not in on_glovo and not r['sku'].endswith(('-KG', '-100G'))
           and r['is_discontinued'] != 'True']
    for r in off:
        ws3.append([r['sku'], f"{r['brand']} {r['product_name']} — {r['variant_name']}", r['stock_status'],
                    'yes' if r['measure_type'] in ('mass', 'volume') and r['content'] not in ('', 'None', None) else 'no'])
    wb.save(out)
    from collections import Counter
    print(len(off), 'Siruk variants not on Glovo:', Counter((r['stock_status'], r['measure_type'] in ('mass', 'volume')) for r in off))
    print('switched off on Glovo:', sum(not p['glovo_active'] for p in plan))
    print(len(plan), 'to send,', len(skipped), 'not yet →', out)
    print(Counter(p['rule'].split(' (')[0] for p in plan)); print(Counter(p['kind'] for p in plan))
    print(Counter(s[2] for s in skipped))


if __name__ == '__main__':
    main()
