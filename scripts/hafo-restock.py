#!/usr/bin/env python3
"""What to order from hafo, and how many: ArmSoft stock + sales speed + what is already on the way.

    uv run --no-sync --with openpyxl python scripts/hafo-restock.py \
        --now Scale/armsoft-turnover-<today>.xlsx --before Scale/armsoft-turnover-<~14 days ago>.xlsx \
        --pending runs/<today>/hafo-pending.json [--cover 14] [--siruk <export.json>] \
        --out final/hafo/hafo-restock-<today>.xlsx --cart runs/<today>/hafo-cart.json

Inputs
  --now / --before  ArmSoft "Ապրանքների շրջանառություն", period from 01/01/01, "Բացված ըստ
                    գործողությունների" ticked (armsoft-app → Stock / turnover). The date in each file
                    name (YYYY-MM-DD) gives the window; --days overrides it.
  --pending         hafo orders placed but not yet received in ArmSoft, as
                    [{"order": 12126, "sku": "MG 006147", "qty": 1, "unit": "հատ"|"կգ."}, …]
                    (read from hafo.am/my-orders/<id> in the built-in browser; skill hafo-restock).
                    A "կգ." line is kilos (a bag ordered by weight).
  --siruk           the Siruk catalogue export (siruk export --format json); default
                    .siruk-cache/glovo/siruk-export.json.
  hafo's live stock comes from .siruk-cache/hafo-watch/snapshot.json (hafo-watch.py crawl).

Per ArmSoft good that hafo sells (matched Siruk variant → hafo row by EAN, else article code):
  rate     = sold in the window ÷ days   (sold = Վաճառքներ + Վաճառք (Մանրածախ) − Վերադարձներ)
  have     = ArmSoft stock + what is on the way (open hafo orders)
  need     = rate × cover − have; pieces → ceil(need), bags (per-kg goods) → ceil(need ÷ bag kg)
  ORDER    = need capped at hafo's stock
Groups:
  A  sells, runs short within --cover days → order
  B  out of stock and nothing on the way, sold before but not in the window → 1, optional (not in the cart)
  S  a toy / accessory / grooming / litter / treat in the same Siruk category leaf as something
     on the way (a similar item is coming) → not in the cart (food and supplements never)
  D  hafo has none right now
  (goods with enough stock, or never sold and in stock, are not listed)
Royal Canin and anything hafo doesn't carry never match a hafo row, so they are listed apart
("not on hafo") when they run short. Nothing here orders anything: --cart only writes the
plan (hafo url, row id, quantity) the skill puts in the basket after the user's yes.
"""
import argparse, datetime as dt, json, math, os, re, sys

import openpyxl
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SNAP = os.path.join(ROOT, '.siruk-cache', 'hafo-watch', 'snapshot.json')
SIRUK = os.path.join(ROOT, '.siruk-cache', 'glovo', 'siruk-export.json')


def turnover(path):
    rows = list(openpyxl.load_workbook(path, read_only=True, data_only=True).worksheets[0].iter_rows(values_only=True))
    hi = next(i for i, r in enumerate(rows) if r and any(str(c or '').strip() == 'Կոդ' for c in r))
    h = [str(c or '').strip() for c in rows[hi]]
    out = {}
    for r in rows[hi + 1:]:
        if not r[0]:
            continue
        d = dict(zip(h, r))
        f = lambda k: float(d.get(k) or 0)
        out[str(r[0]).strip()] = {
            'name': d.get('Անվանում') or '', 'kg': str(d.get('Չափման միավոր') or '').strip() == 'կգ',
            'stock': f('Վերջնական քանակ'),
            'sold': f('Վաճառքներ/Քանակ ելք') + f('Վաճառք (Մանրածախ)/Քանակ ելք') - f('Վերադարձներ/Քանակ մուտք')}
    return out


def file_date(p):
    m = re.search(r'(\d{4}-\d{2}-\d{2})', os.path.basename(p))
    return dt.date.fromisoformat(m.group(1)) if m else None


def art(s):
    return re.sub(r'\s+', '', str(s or '')).upper()


def ean(s):
    s = re.sub(r'\D', '', str(s or ''))
    return s.lstrip('0') if len(s) >= 8 else ''


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--now', required=True)
    ap.add_argument('--before', required=True)
    ap.add_argument('--days', type=float)
    ap.add_argument('--pending', help='open hafo order lines (json)')
    ap.add_argument('--siruk', default=SIRUK)
    ap.add_argument('--cover', type=float, default=14, help='days of sales to have on hand (default 14)')
    ap.add_argument('--out', required=True)
    ap.add_argument('--cart', help='write the A-group basket plan here')
    a = ap.parse_args()

    days = a.days or ((file_date(a.now) - file_date(a.before)).days if file_date(a.now) and file_date(a.before) else None)
    if not days or days <= 0:
        sys.exit('window unknown: name the turnover files …-YYYY-MM-DD… or pass --days')
    now, before = turnover(a.now), turnover(a.before)
    snap = json.load(open(SNAP, encoding='utf-8'))
    fetched = snap['fetched']
    hrows = snap['rows']
    h_ean, h_art = {}, {}
    for k, r in hrows.items():
        if ean(r.get('barcode')):
            h_ean.setdefault(ean(r['barcode']), r)
        h_art[art(k)] = r
    siruk = [v for v in json.load(open(a.siruk, encoding='utf-8'))
             if v.get('accounting_code') and not str(v.get('sku', '')).endswith(('-KG', '-100G'))]

    # ArmSoft code -> (Siruk variant, hafo row)
    goods = {}
    for v in siruk:
        code = str(v['accounting_code']).strip()
        h = h_ean.get(ean(v.get('barcode'))) or h_art.get(art(v.get('sku')))
        how = 'EAN' if h_ean.get(ean(v.get('barcode'))) else ('article' if h else '')
        if code not in goods or (h and not goods[code][1]):
            goods[code] = (v, h, how)

    # what is on the way, per ArmSoft code (in ArmSoft units: pieces, or kg for per-kg goods)
    pending = json.load(open(a.pending, encoding='utf-8')) if a.pending else []
    by_hafo = {}
    for code, (v, h, _) in goods.items():
        if h:
            by_hafo[art(h['sku'])] = code
    incoming, incoming_leaves, unmatched = {}, set(), []
    for p in pending:
        code = by_hafo.get(art(p['sku']))
        if not code:
            unmatched.append(p)
            continue
        v = goods[code][0]
        q = float(p['qty'])
        if now.get(code, {}).get('kg') and 'կգ' not in str(p.get('unit', '')):
            q *= (v.get('content') or 0) / 1000 or 1          # bags ordered as pieces -> kg
        incoming[code] = incoming.get(code, 0) + q
        incoming_leaves.update(v.get('category_ids') or [])

    lines = []
    for code, t in now.items():
        g = goods.get(code)
        if not g:
            continue
        v, h, how = g
        if v.get('is_discontinued'):
            continue
        sold = t['sold'] - before.get(code, {}).get('sold', 0)
        rate = max(sold, 0) / days
        inc = incoming.get(code, 0)
        have = t['stock'] + inc
        bag = (v.get('content') or 0) / 1000 if t['kg'] else 0
        need = rate * a.cover - have
        unit = f'bag {bag:g} kg' if bag else 'pcs'
        n = math.ceil(need / bag) if bag and need > 0 else (math.ceil(need) if need > 0 else 0)
        group, why = None, ''
        if n > 0:
            group, why = 'A', f'{rate * 7:.1f}/week, {have:g} on hand + on the way'
        elif have <= 0 and t['sold'] > 0:
            group, n, why = 'B', 1, 'out, sold before, not in the last window'
        if not group:
            continue
        leaves = set(v.get('category_ids') or [])
        # "similar is on the way" only for things one can stand in for another (toys, accessories,
        # grooming, litter, treats) — a different food or supplement is never a substitute
        swappable = (v.get('product_type') or '') not in ('Dry Food', 'Wet Food', 'Supplements')
        if inc <= 0 and swappable and leaves & incoming_leaves and group in ('A', 'B'):
            group, why = 'S', 'a similar item (same category) is on the way — ' + why
        if not h:
            group = 'C'
        hq = h['qty'] if h else None
        order = 0 if group in ('S', 'C') else (min(n, int(hq)) if hq is not None else n)
        if h and hq is not None and hq <= 0 and group in ('A', 'B'):
            group, order = 'D', 0
        cost = v.get('cost_price') or 0
        unit_cost = cost * bag if bag and str(v.get('measure_type')) == 'mass' and (v.get('content') or 0) < 2000 else cost
        lines.append({'group': group, 'code': code, 'brand': v.get('brand') or '', 'product': v.get('product_name') or '',
                      'size': v.get('size') or (f'{bag:g} kg' if bag else ''), 'armsoft': t['name'],
                      'stock': round(t['stock'], 3), 'unit': 'kg' if t['kg'] else 'pcs', 'incoming': round(inc, 3),
                      'sold_window': round(sold, 3), 'per_week': round(rate * 7, 2), 'suggested': n, 'order_unit': unit,
                      'hafo_sku': (h or {}).get('sku', ''), 'match': how, 'hafo_qty': int(hq) if hq is not None else '',
                      'hafo_price': (h or {}).get('price', ''), 'order': order, 'why': why,
                      'url': (h or {}).get('url', ''), 'row_id': (h or {}).get('row_id', '')})

    order_key = {'A': 0, 'B': 1, 'S': 2, 'D': 3, 'C': 4}
    lines.sort(key=lambda r: (order_key[r['group']], -r['per_week'], r['brand'].lower(), r['product']))
    names = {'A': 'A. Order — runs short within the cover', 'B': 'B. Out, slow seller — 1, optional',
             'S': 'S. Similar item already on the way — skipped', 'D': 'D. hafo has none now',
             'C': 'C. Not on hafo — other supplier'}

    wb = openpyxl.Workbook()
    sm = wb.active
    sm.title = 'Summary'
    sm.append([f'hafo restock, {file_date(a.now)}: {days:g}-day sales window, cover {a.cover:g} days, hafo stock {fetched}'])
    sm.append(['Group', 'Lines', 'Order qty', 'hafo price total'])
    for g in 'ABSDC':
        rs = [r for r in lines if r['group'] == g]
        sm.append([names[g], len(rs), sum(r['order'] for r in rs),
                   sum((r['hafo_price'] or 0) * r['order'] for r in rs)])
    sm.append([])
    sm.append(['On the way (open hafo orders)', len(pending), 'lines', f'{len(unmatched)} not matched to an ArmSoft good'])
    sm.column_dimensions['A'].width = 52
    ws = wb.create_sheet('Suggestion')
    cols = [('Group', 'group', 34), ('ArmSoft code', 'code', 9), ('Brand', 'brand', 14), ('Product', 'product', 44),
            ('Size', 'size', 9), ('ArmSoft name', 'armsoft', 36), ('Stock', 'stock', 8), ('Unit', 'unit', 5),
            ('On the way', 'incoming', 9), (f'Sold last {days:g} days', 'sold_window', 10), ('Per week', 'per_week', 8),
            ('Suggested', 'suggested', 9), ('Order unit', 'order_unit', 11), ('ORDER', 'order', 8),
            ('hafo stock', 'hafo_qty', 8), ('hafo price', 'hafo_price', 9), ('hafo article', 'hafo_sku', 14),
            ('Matched by', 'match', 8), ('Why', 'why', 40), ('hafo link', 'url', 40)]
    ws.append([c[0] for c in cols])
    for c in ws[1]:
        c.font = Font(bold=True, color='FFFFFF')
        c.fill = PatternFill('solid', fgColor='1F4E78')
        c.alignment = Alignment(wrap_text=True)
    fill = {'A': 'C6EFCE', 'B': 'FFF2CC', 'S': 'D9D9D9', 'D': 'F8CBAD', 'C': 'DDEBF7'}
    for r in lines:
        ws.append([names[r['group']] if k == 'group' else r[k] for _, k, _ in cols])
        ws.cell(ws.max_row, 1).fill = PatternFill('solid', fgColor=fill[r['group']])
        ws.cell(ws.max_row, 14).font = Font(bold=True)
    for j, (_, _, w) in enumerate(cols, 1):
        ws.column_dimensions[get_column_letter(j)].width = w
    ws.freeze_panes = 'E2'
    ws.auto_filter.ref = ws.dimensions
    if pending:
        pw = wb.create_sheet('On the way')
        pw.append(['hafo order', 'hafo article', 'qty', 'unit', 'ArmSoft code'])
        for p in pending:
            pw.append([p.get('order'), p['sku'], p['qty'], p.get('unit', ''), by_hafo.get(art(p['sku']), 'not matched')])
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    wb.save(a.out)

    cart = [{'code': r['code'], 'product': r['product'], 'url': r['url'], 'row_id': r['row_id'], 'qty': r['order'],
             'hafo_sku': r['hafo_sku'], 'price': r['hafo_price']} for r in lines if r['group'] == 'A' and r['order'] > 0]
    if a.cart:
        os.makedirs(os.path.dirname(os.path.abspath(a.cart)), exist_ok=True)
        json.dump(cart, open(a.cart, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'{days:g}-day window, cover {a.cover:g} days, hafo stock {fetched}')
    for g in 'ABSDC':
        rs = [r for r in lines if r['group'] == g]
        print(f'  {names[g]}: {len(rs)} lines, {sum(r["order"] for r in rs)} to order, '
              f'~{sum((r["hafo_price"] or 0) * r["order"] for r in rs):,.0f} AMD at hafo prices')
    if unmatched:
        print(f'  {len(unmatched)} open-order lines not matched to an ArmSoft good: '
              + ', '.join(p['sku'] for p in unmatched[:10]))
    print('→', a.out + (f'  (basket plan: {len(cart)} lines → {a.cart})' if a.cart else ''))


if __name__ == '__main__':
    main()
