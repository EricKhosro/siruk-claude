#!/usr/bin/env python3
"""Glovo prices → ArmSoft price type 02 ("Glovo"), as an import XML.

ArmSoft price type 01 is the shop / siruk.am price. Glovo charges ~20 %
commission, so the Glovo price is higher; a Glovo sale is rung up with the
buyer "Glovo", whose contract carries price type 02 (user, 2026-11-09).

  uv run --no-sync --with openpyxl python scripts/armsoft-glovo-prices.py \
      <armsoft-prices.xlsx> [--glovo .siruk-cache/glovo/portal-products.json] \
      [--siruk runs/<date>/siruk-export.json] [--date 2026-11-09] --out <file.xml>

Inputs: the ArmSoft price list export (navigator գներ, from 01/01/01), the
live Glovo catalogue (`glovo-portal.py dump`) and the Siruk export
(`siruk export --format json`). Glovo SKU = Siruk variant SKU →
accounting_code (= ArmSoft good) + unit:
  <sku>-KG   → 303 (kg), price as is
  <sku>-100G → 303 (kg), price × 10 (ArmSoft/scale keep it per kg)
  else       → the unit whose 01 price = the Siruk price (004 stick packs,
               003 bags); failing that 001, then 003.
Writes a CSV report next to the XML: every row, plus what was skipped and why.
"""
import argparse, csv, json, os, sys
from collections import defaultdict
from xml.sax.saxutils import escape
import openpyxl

ap = argparse.ArgumentParser()
ap.add_argument('armsoft_prices')
ap.add_argument('--glovo', default='.siruk-cache/glovo/portal-products.json')
ap.add_argument('--siruk', required=True)
ap.add_argument('--date', required=True)
ap.add_argument('--price-type', default='02')
ap.add_argument('--out', required=True)
a = ap.parse_args()

units = defaultdict(dict)  # code -> unit -> latest 01 price
latest = {}
for r in openpyxl.load_workbook(a.armsoft_prices, read_only=True).active.iter_rows(min_row=3, values_only=True):
    if not r[1] or r[5] != '01':
        continue
    k = (r[1], r[7])
    if k not in latest or r[0] >= latest[k]:
        latest[k] = r[0]
        units[r[1]][r[7]] = float(r[10])

g = json.load(open(a.glovo, encoding='utf-8'))
glovo = g if isinstance(g, list) else g['items']
siruk = {r['sku']: r for r in json.load(open(a.siruk, encoding='utf-8'))}

rows, out, skipped = [], {}, []
for it in glovo:
    sku, gp = it['sku'], it['price']
    v = siruk.get(sku)
    note = ''
    if not v:
        skipped.append((sku, it['name'], gp, 'no Siruk variant with this SKU')); continue
    acc = v.get('accounting_code')
    if not acc or acc not in units:
        skipped.append((sku, it['name'], gp, f'no ArmSoft good / 01 price for accounting code {acc!r}')); continue
    have = units[acc]
    if sku.endswith('-100G'):
        unit, factor = '303', 10
    elif sku.endswith('-KG'):
        unit, factor = '303', 1
    elif [u for u, x in have.items() if abs(x - v['price']) < 0.005]:
        # the unit whose shop price is the Siruk price (004 packs of sticks, 003 bags)
        m = [u for u, x in have.items() if abs(x - v['price']) < 0.005]
        unit, factor = ('001' if '001' in m else sorted(m)[0]), 1
    elif '001' in have:
        unit, factor = '001', 1
    elif '003' in have:
        unit, factor = '003', 1
    else:
        skipped.append((sku, it['name'], gp, f'ArmSoft {acc} has no 001/003 price (units {sorted(have)})')); continue
    if unit not in have:
        skipped.append((sku, it['name'], gp, f'ArmSoft {acc} has no {unit} price')); continue
    p01 = have[unit]
    p02 = round(gp * factor, 2)
    sp = v['price'] * factor
    if abs(p01 - sp) > 0.005:
        note = f'ArmSoft 01 {p01:g} != Siruk {sp:g}'
    if p02 < p01:
        note = (note + '; ' if note else '') + 'Glovo price below 01'
    key = (acc, unit)
    if key in out and abs(out[key][0] - p02) > 0.005:
        skipped.append((sku, it['name'], gp, f'{acc}/{unit} already gets {out[key][0]:g} from {out[key][1]}')); continue
    out[key] = (p02, sku)
    rows.append([acc, unit, sku, it['name'], v['product_name'], v['size'], p01, p02, round(p02 / p01 - 1, 3) if p01 else '', it['active'], note])

with open(a.out, 'w', encoding='utf-8') as f:
    f.write('<?xml version="1.0" encoding="utf-8"?>\n<Exchange xmlns="http://www.armsoft.am/Accountant/6.0">\n')
    for (acc, unit), (p, _) in sorted(out.items()):
        f.write('<Prices xmlns:i="http://www.w3.org/2001/XMLSchema-instance">'
                f'<Code>{escape(acc)}</Code><PriceType>{a.price_type}</PriceType><Unit>{unit}</Unit>'
                f'<Date>{a.date}T00:00:00</Date><CurrencyCode>AMD</CurrencyCode>'
                f'<Price>{p:.4f}</Price><Comment></Comment></Prices>\n')
    f.write('</Exchange>\n')
rep = os.path.splitext(a.out)[0] + '.csv'
with open(rep, 'w', encoding='utf-8-sig', newline='') as f:
    w = csv.writer(f)
    w.writerow(['armsoft code', 'unit', 'glovo sku', 'glovo name', 'siruk name', 'size', 'price 01 (shop)', 'price 02 (glovo)', 'markup', 'glovo active', 'note'])
    w.writerows(sorted(rows))
    w.writerow([])
    w.writerow(['SKIPPED'])
    for s in skipped: w.writerow(['', '', *s])
print(f'{len(out)} prices → {a.out}; report {rep}; skipped {len(skipped)}')
notes = [r for r in rows if r[-1]]
print(f'{len(notes)} rows with a note:')
for r in notes[:40]: print('  ', r[0], r[1], r[2], r[4], r[5], r[6], r[7], '|', r[-1])
for s in skipped[:40]: print('  SKIP', s)
