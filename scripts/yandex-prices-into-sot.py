#!/usr/bin/env python3
"""Add the Yandex price proposal to final/siruk-source-of-truth.xlsx (columns L–U of
the first sheet, plus a "Yandex pricing" settings sheet). Re-runnable: it rewrites
those columns and that sheet each time and leaves everything else alone.

Every cell holds a plain value (no formulas: viewers that don't recalculate show
formula cells empty). The rule, with the settings sheet's values:
  a checked Zoovet match ("same"): max(floor(Zoovet price × (1 − undercut)), floor price)
  otherwise:                       max(ceiling(Siruk price × (1 + uplift)), floor price)
  floor price = ceiling(cost ÷ (1 − commission − minimum margin)), all to 50 ֏.
To change the rule, edit the yellow cells on "Yandex pricing" and re-run: the
script reads them back from the file.

  uv run --no-sync --with openpyxl python scripts/yandex-prices-into-sot.py
"""
import json, math, os, re
import openpyxl
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.formatting.formatting import ConditionalFormattingList
from openpyxl.formatting.rule import FormulaRule

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOT = os.path.join(ROOT, 'final', 'siruk-source-of-truth.xlsx')
SHORT = os.path.join(ROOT, 'final', 'yandex', 'siruk-yandex-prices-short.xlsx')
CACHE = os.path.join(ROOT, '.siruk-cache', 'yandex')
SETTINGS = [
    ('Yandex commission', 0.20, 'placeholder until the contract rate is known (user 2026-11-02: keep 20%)'),
    ('Undercut vs Zoovet on Yandex', 0.05, "how much cheaper than Zoovet's Yandex price"),
    ('Minimum net margin after commission', 0.15, 'floor price = cost ÷ (1 − commission − this)'),
    ('Uplift on the Siruk price when Zoovet has no such item', 0.14,
     "Zoovet's Yandex prices are a median 1.20× our Siruk prices; 1.20 × (1 − 5%) ≈ +14%"),
    ('Round to (֏)', 50, ''),
]
HEAD = ['Zoovet Yandex item', 'Zoovet Yandex price (AMD)', 'Suggested Yandex price (AMD)', 'vs Zoovet %',
        'Price basis', 'Match check', 'Match note', 'Net after Yandex commission (AMD)',
        'Net margin % on Yandex', 'vs Siruk price %']
WIDTH = dict(L=55, M=12, N=13, O=10, P=26, Q=11, R=34, S=14, T=11, U=10)


def main():
    matches = {m['variant_id']: m for m in json.load(open(os.path.join(CACHE, 'zoovetam-matches.json'), encoding='utf-8'))['matches']}
    verdicts = json.load(open(os.path.join(CACHE, 'zoovetam-verdicts.json'), encoding='utf-8'))

    wb = openpyxl.load_workbook(SOT)
    ws = wb.worksheets[0]

    settings = [list(r) for r in SETTINGS]
    if 'Yandex pricing' in wb.sheetnames:            # keep the user's edits to the yellow cells
        old = wb['Yandex pricing']
        for i, row in enumerate(settings, start=2):
            if isinstance(old[f'B{i}'].value, (int, float)):
                row[1] = old[f'B{i}'].value
        del wb['Yandex pricing']
    comm, under, minm, upl, rnd = (r[1] for r in settings)
    up = lambda x: math.ceil(round(x / rnd, 6)) * rnd
    down = lambda x: math.floor(round(x / rnd, 6)) * rnd
    st = wb.create_sheet('Yandex pricing')
    st.append(['Setting', 'Value', 'Note'])
    for row in settings:
        st.append(row)
    for i in range(2, 2 + len(settings)):
        st[f'B{i}'].fill = PatternFill('solid', fgColor='FFF2CC')
        st[f'B{i}'].number_format = '0%' if isinstance(st[f'B{i}'].value, float) else '0'
    for c in 'ABC':
        st[f'{c}1'].font = Font(bold=True)
    st.append([])
    st.append(['Zoovet prices come from its Yandex Eats store (eats.yandex.com/en-am/retail/zoovetam), read 2026-11-02. '
               'A Zoovet price is used only where the match check says "same".'])
    st.column_dimensions['A'].width = 52
    st.column_dimensions['C'].width = 80

    for k, name in enumerate(HEAD):
        c = ws.cell(1, 12 + k, name)
        c.font = Font(bold=True)
        c.alignment = Alignment(wrap_text=True, vertical='top')
    for col, w in WIDTH.items():
        ws.column_dimensions[col].width = w

    n = {'zoovet': 0, 'uplift': 0}
    for r in range(2, ws.max_row + 1):
        for col in WIDTH:
            ws[f'{col}{r}'] = None
        m = re.search(r'/dp/(\d+)', ws[f'H{r}'].value or '')
        mm = matches.get(int(m.group(1))) if m else None
        same = False
        if mm and mm.get('rival_name'):
            vv = verdicts.get(str(mm['variant_id']), {})
            ws[f'L{r}'] = mm['rival_name']
            ws[f'M{r}'] = float(mm['rival_price'])
            ws[f'Q{r}'] = vv.get('verdict', 'unchecked')
            ws[f'R{r}'] = vv.get('note', '')
            same = vv.get('verdict') == 'same'
        cost, price = ws[f'D{r}'].value or 0, ws[f'C{r}'].value or 0
        floor = up(cost / (1 - comm - minm)) if cost else 0
        if same:
            rival = float(mm['rival_price'])
            want = down(rival * (1 - under))
            sug = max(want, floor)
            basis = 'under Zoovet' if want >= floor else 'minimum margin (Zoovet too cheap)'
            ws[f'O{r}'] = round(sug / rival - 1, 4)
            n['zoovet'] += 1
        else:
            want = up(price * (1 + upl))
            sug = max(want, floor)
            basis = 'Siruk price + uplift' if want >= floor else 'minimum margin'
            n['uplift'] += 1
        net = sug * (1 - comm) - cost
        ws[f'N{r}'], ws[f'P{r}'], ws[f'S{r}'] = sug, basis, round(net)
        ws[f'T{r}'] = round(net / sug, 4) if sug else None
        ws[f'U{r}'] = round(sug / price - 1, 4) if price else None
        for col in 'MNS':
            ws[f'{col}{r}'].number_format = '#,##0'
        for col in 'OTU':
            ws[f'{col}{r}'].number_format = '0.0%'
        for col in 'LMNOPQRSTU':
            ws[f'{col}{r}'].font = Font(bold=col == 'N')

    last = ws.max_row
    ws.auto_filter.ref = f'A1:U{last}'
    keep = ConditionalFormattingList()                 # drop this script's earlier colour rules, keep any others
    for rng in ws.conditional_formatting:
        if not re.match(r'[L-U]2:', str(rng.sqref)):
            for rule in rng.rules:
                keep.add(str(rng.sqref), rule)
    ws.conditional_formatting = keep
    ws.conditional_formatting.add(f'N2:N{last}', FormulaRule(formula=['LEFT($P2,7)="minimum"'], fill=PatternFill('solid', fgColor='F8CBAD')))
    ws.conditional_formatting.add(f'N2:N{last}', FormulaRule(formula=['$P2="under Zoovet"'], fill=PatternFill('solid', fgColor='E2F0D9')))
    wb.save(SOT)
    print(f'{last - 1} rows: {n["zoovet"]} priced against Zoovet, {n["uplift"]} on the Siruk price + uplift → {SOT}')

    # The short list the user asked for (2026-11-02): name, variant, Siruk price, suggested, Zoovet (checked matches only), link.
    # PM 2026-11-02: plus Siruk margin and Yandex margin (after commission), sorted by Siruk margin, highest first.
    sw = openpyxl.Workbook()
    sh = sw.active
    sh.title = 'Yandex prices'
    sh.append(['Product name on Siruk', 'Variant', 'Siruk price (AMD)', 'Siruk margin %',
               'Suggested Yandex price (AMD)', f'Yandex margin % (after {comm:.0%} commission)',
               'Zoovet Yandex price (AMD)', 'Siruk link'])
    for c in sh[1]:
        c.font = Font(bold=True)
        c.alignment = Alignment(wrap_text=True, vertical='top')
    rows = []
    for r in range(2, last + 1):
        cost, price = ws[f'D{r}'].value or 0, ws[f'C{r}'].value or 0
        rows.append([ws[f'A{r}'].value, ws[f'B{r}'].value, ws[f'C{r}'].value,
                     round((price - cost) / price, 4) if price and cost else None,
                     ws[f'N{r}'].value, ws[f'T{r}'].value if cost else None,
                     ws[f'M{r}'].value if ws[f'Q{r}'].value == 'same' else None, ws[f'H{r}'].value])
    rows.sort(key=lambda x: (x[3] is None, -(x[3] or 0)))   # no cost → last
    for row in rows:
        sh.append(row)
        i = sh.max_row
        for col in 'CEG':
            sh[f'{col}{i}'].number_format = '#,##0'
        for col in 'DF':
            sh[f'{col}{i}'].number_format = '0.0%'
        sh[f'E{i}'].font = Font(bold=True)
        if row[7]:
            sh[f'H{i}'].hyperlink = row[7]
            sh[f'H{i}'].style = 'Hyperlink'
    for k, w in dict(A=38, B=30, C=12, D=10, E=14, F=14, G=14, H=55).items():
        sh.column_dimensions[k].width = w
    sh.freeze_panes = 'A2'
    sh.auto_filter.ref = f'A1:H{sh.max_row}'
    sh.row_dimensions[1].height = 32
    os.makedirs(os.path.dirname(SHORT), exist_ok=True)
    sw.save(SHORT)
    print(f'short list → {SHORT}')


if __name__ == '__main__':
    main()
