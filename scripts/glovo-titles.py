#!/usr/bin/env python3
"""Glovo Armenian titles — build the review sheet, then apply the approved titles.

  python3 scripts/glovo-titles.py sheet                 # .siruk-cache/glovo/names/out-*.jsonl → final/glovo/siruk-glovo-titles.xlsx
  python3 scripts/glovo-titles.py apply [--sku …] [--apply]

The proposals follow the Zoovet-style pattern (reference/glovo/portal.md):
  <Brand> <Line> <what it is> <flavour -ով> <for whom … համար>, <size>

`sheet` checks every proposal:
  - the brand comes first,
  - every number of the current title is kept,
  - no «Brand», ≤ 110 characters,
  - which words were dropped / added.

`apply` reads the sheet. It sends column "Your correction" when filled, else "Proposed"
— only on rows whose "Approve" column is y/yes/1/✓. It renames on Glovo in two steps
(Glovo's anti-hijacking check refuses a brand move plus new words in one change):
  1. the current words with the brand moved to the front (no «»),
  2. the final title.
Each step sends `original` (the live state). Dry run unless --apply.
Log: runs/<date>/glovo-titles.csv.
"""
import argparse, datetime, glob, importlib.util, json, os, re, sys, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NAMES = os.path.join(ROOT, '.siruk-cache', 'glovo', 'names')
SHEET = os.path.join(ROOT, 'final', 'glovo', 'siruk-glovo-titles.xlsx')
HEAD = ['SKU', 'Brand', 'Product (Siruk, en)', 'Variant', 'Current Glovo title (hy)', 'Proposed title (hy)',
        'Check', 'Flag', 'Note', 'Words dropped', 'Words added', 'Your correction', 'Approve (y)']

spec = importlib.util.spec_from_file_location('gp', os.path.join(ROOT, 'scripts', 'glovo-portal.py'))
gp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gp)


def words(t):
    return [w for w in re.findall(r'[\w\'’&+.-]+', (t or '').lower().replace('«', ' ').replace('»', ' ')) if w not in '.-']


def numbers(t):
    return sorted(re.findall(r'\d+(?:\.\d+)?', (t or '').replace(',', '.')))


def check(cur, new, brand):
    p = []
    if not new:
        return ['empty']
    if brand and not new.lower().startswith(brand.lower()):
        p.append('brand not first')
    if brand and f'«{brand.lower()}»' in new.lower():
        p.append('brand in «»')
    nc, nn = set(numbers(cur)), set(numbers(new))       # a size printed twice may now appear once
    lost = nc - nn
    if lost:
        p.append('number lost: ' + ' '.join(sorted(lost)))
    extra = nn - nc
    if extra:
        p.append('new number: ' + ' '.join(sorted(set(extra))))
    if len(new) > 110:
        p.append(f'{len(new)} chars')
    return p


def cmd_sheet(a):
    import openpyxl
    from openpyxl.styles import Alignment, Font, PatternFill
    inp, out = {}, {}
    for f in sorted(glob.glob(os.path.join(NAMES, 'in-*.jsonl'))):
        for line in open(f, encoding='utf-8'):
            r = json.loads(line); inp[r['sku']] = r
    for f in sorted(glob.glob(os.path.join(NAMES, 'out-*.jsonl'))):
        for line in open(f, encoding='utf-8'):
            if line.strip():
                r = json.loads(line); out[r['sku']] = r
    missing = [s for s in inp if s not in out]
    wb = openpyxl.Workbook(); ws = wb.active; ws.title = 'Titles'
    ws.append(HEAD)
    for c in ws[1]:
        c.font = Font(bold=True); c.alignment = Alignment(wrap_text=True, vertical='top')
    n = {'ok': 0, 'check': 0, 'flag': 0}
    for s, r in inp.items():
        o = out.get(s, {})
        new = (o.get('proposed_hy') or '').strip()
        cur = r['current_hy']
        probs = check(cur, new, r.get('brand'))
        cw, nw = words(cur), words(new)
        dropped = [w for w in dict.fromkeys(cw) if w not in nw]
        added = [w for w in dict.fromkeys(nw) if w not in cw]
        ws.append([s, r.get('brand'), r.get('product_en'), r.get('variant_en'), cur, new or '(missing)',
                   '; '.join(probs), o.get('flag', ''), o.get('note', ''), ' '.join(dropped), ' '.join(added), '', ''])
        i = ws.max_row
        if probs:
            n['check'] += 1
            ws[f'G{i}'].fill = PatternFill('solid', fgColor='F8CBAD')
        if o.get('flag'):
            n['flag'] += 1
            ws[f'H{i}'].fill = PatternFill('solid', fgColor='FFF2CC')
        if not probs and not o.get('flag'):
            n['ok'] += 1
        ws[f'F{i}'].font = Font(bold=True)
        for col in 'L', 'M':
            ws[f'{col}{i}'].fill = PatternFill('solid', fgColor='E2F0D9')
    for k, w in dict(A=14, B=14, C=34, D=20, E=60, F=70, G=22, H=30, I=30, J=22, K=26, L=60, M=10).items():
        ws.column_dimensions[k].width = w
    ws.freeze_panes = 'F2'
    ws.auto_filter.ref = f'A1:M{ws.max_row}'
    rd = wb.create_sheet('Read me')
    for line in [
        'New Armenian Glovo titles, Zoovet-style pattern:',
        '<Brand> <Line> <what it is> <flavour -ով> <for whom … համար>, <size>',
        '',
        'Proposed title = the suggestion. Check (red) = an automatic check failed: brand not first, a number lost or added, too long.',
        'Flag (yellow) = the writer was unsure or the data disagree; read those first.',
        'Words dropped / added = difference against today\'s title (Glovo rejects titles that look like another product).',
        'To change a title: type it in "Your correction". To send a row: put y in "Approve".',
        'Nothing is sent to Glovo until you approve; then: python3 scripts/glovo-titles.py apply --apply',
    ]:
        rd.append([line])
    rd.column_dimensions['A'].width = 120
    os.makedirs(os.path.dirname(SHEET), exist_ok=True)
    wb.save(SHEET)
    print(f'{len(inp)} rows ({len(missing)} without a proposal): {n["ok"]} clean, {n["check"]} fail a check, '
          f'{n["flag"]} flagged → {SHEET}')


CACHE = {}


def preload():
    """All products in hy_AM and en_AM in one paged read (instead of two searches per product)."""
    q = '''query($f:ProductFilter!,$p:PageInput!){products(filter:$f,page:$p){items{sku name price active imageUrls categoryIds maximumSalesQuantity internalId} pagedResult{itemCount}}}'''
    for loc in ('hy_AM', 'en_AM'):
        page, got = 1, {}
        while True:
            d = gp.gql(q, {'f': {'vendorIdentifier': gp.vendor(), 'locale': loc, 'searchTerm': '', 'active': None,
                                 'brandIds': [], 'categoryIds': []}, 'p': {'pageNumber': page, 'pageSize': 100}})['products']
            for i in d['items']:
                got[i['sku']] = i
            if not d['items'] or len(got) >= d['pagedResult']['itemCount']:
                break
            page += 1
        CACHE[loc] = got


def live_state(sku):
    if CACHE:
        return CACHE['hy_AM'].get(sku), CACHE['en_AM'].get(sku)
    V = gp.vendor()
    q = '''query($f:ProductFilter!,$p:PageInput!){products(filter:$f,page:$p){items{sku name price active imageUrls categoryIds maximumSalesQuantity internalId}}}'''
    def get(loc):
        d = gp.gql(q, {'f': {'vendorIdentifier': V, 'locale': loc, 'searchTerm': sku, 'active': None, 'brandIds': [],
                             'categoryIds': []}, 'p': {'pageNumber': 1, 'pageSize': 20}})['products']['items']
        hit = [i for i in d if i['sku'] == sku]
        return hit[0] if hit else None
    hy, en = get('hy_AM'), get('en_AM')
    return hy, en


def rename(sku, title_hy, desc_hy, apply):
    hy, en = live_state(sku)
    if not hy:
        raise RuntimeError('not on Glovo')
    L = lambda h: [{'locale': 'hy_AM', 'value': h}, {'locale': 'en_AM', 'value': en['name']}]
    orig = {'active': hy['active'], 'categoryInternalIds': hy['categoryIds'],
            'descriptions': [{'locale': 'hy_AM', 'value': desc_hy}] if desc_hy else [],
            'images': hy['imageUrls'] or [], 'maximumSalesQuantity': hy['maximumSalesQuantity'] or 0,
            'price': hy['price'], 'sku': sku, 'titles': L(hy['name'])}
    if not apply:
        return hy['name']
    r = gp.gql('''mutation($u:ProductUpdate!){product(productUpdate:$u){validationErrors{code message}}}''',
               {'u': {'sku': sku, 'vendorIdentifier': gp.vendor(), 'productInternalId': hy['internalId'],
                      'titles': L(title_hy), 'original': orig}})['product']
    time.sleep(gp.PACE)
    if r and r.get('validationErrors'):
        raise RuntimeError('; '.join(f"{e['code']}: {e['message'][:160]}" for e in r['validationErrors']))
    if CACHE:
        CACHE['hy_AM'][sku]['name'] = title_hy      # the next step's `original` must be the new title
    return hy['name']


def step1(cur, brand):
    """Today's words, brand moved to the front, «» dropped around it."""
    rest = re.sub(r'\s*«\s*' + re.escape(brand) + r'\s*»\s*', ' ', cur, flags=re.I)
    rest = re.sub(r'\s+', ' ', rest).strip(' ,')
    return f'{brand} {rest}'


def cmd_apply(a):
    import openpyxl
    ws = openpyxl.load_workbook(SHEET, read_only=True, data_only=True)['Titles']
    rows = [dict(zip(HEAD, r)) for r in ws.iter_rows(min_row=2, values_only=True)]
    ok = lambda v: str(v or '').strip().lower() in ('y', 'yes', '1', '✓', 'x', 'այո')
    todo = [r for r in rows if ok(r['Approve (y)']) and (not a.sku or str(r['SKU']) in a.sku)]
    descs = {}
    wb = openpyxl.load_workbook(gp.SHEET, read_only=True).worksheets[0]
    for r in wb.iter_rows(min_row=3, values_only=True):
        if r[0] is not None:
            descs[str(r[0])] = r[4] or ''
    preload()
    print(f'{len(todo)} approved rows' + ('' if a.apply else '  (DRY RUN — add --apply)'))
    log = []
    for i, r in enumerate(todo, 1):
        s = str(r['SKU']); final = (r['Your correction'] or r['Proposed title (hy)'] or '').strip()
        if not final or final == '(missing)':
            continue
        try:
            cur, _ = live_state(s)
            cur = cur['name'] if cur else None
            if cur == final:
                log.append((s, cur, final, 'already')); continue
            if not a.apply:
                print(f'  {s}: {cur}  →  {final}'); continue
            mid = step1(cur, r['Brand'] or '')
            status = 'ok'
            if mid not in (cur, final):
                try:
                    rename(s, mid, descs.get(s), True)
                except RuntimeError as e:
                    status = 'step1 refused: ' + str(e)[:120]
            rename(s, final, descs.get(s), True)
            log.append((s, cur, final, status))
        except Exception as e:
            log.append((s, r['Current Glovo title (hy)'], final, 'FAILED ' + str(e)[:200]))
        if i % 50 == 0:
            print(f'  {i}/{len(todo)}')
    if a.apply:
        rows_out = [(datetime.datetime.now().isoformat(timespec='seconds'),) + x for x in log]
        p = gp.runlog('glovo-titles.csv', ['time', 'sku', 'old title', 'new title', 'status'], rows_out)
        bad = [x for x in log if x[3].startswith('FAILED')]
        print(f'renamed {sum(x[3] in ("ok",) or x[3].startswith("step1") for x in log)}, '
              f'already {sum(x[3] == "already" for x in log)}, failed {len(bad)} → {p}')
        for b in bad[:20]:
            print('  ', b[0], b[3])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    sub.add_parser('sheet').set_defaults(f=cmd_sheet)
    p = sub.add_parser('apply'); p.add_argument('--sku', nargs='*'); p.add_argument('--apply', action='store_true')
    p.set_defaults(f=cmd_apply)
    a = ap.parse_args()
    if a.cmd == 'apply':
        gp.TOKEN = gp.load_token()
    a.f(a)


if __name__ == '__main__':
    main()
