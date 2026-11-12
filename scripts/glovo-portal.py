#!/usr/bin/env python3
"""Glovo Partner portal (portal.glovoapp.com) — read and update our Glovo catalogue.

The portal is Delivery Hero's partner portal. Its catalogue runs on a GraphQL API,
catalog-vss-api-eu.deliveryhero.io/graphql, which answers a plain script with the
portal's Bearer token (no bot check on this host; the orders API is behind one).
Notes: reference/glovo/portal.md.

Token: .glovo-token (gitignored), captured from the built-in browser where the user
is signed in: the `accessToken` cookie of portal.glovoapp.com. It lives 4 h. We never
refresh it from here (the refresh token rotates and is tied to the browser's device
token, so refreshing it outside the browser could sign the user out); the browser
keeps itself signed in, so re-capture it there (skill glovo-portal → Token).

Every write is a DRY RUN unless --apply. Writes are paced (config: PACE seconds).

  python3 scripts/glovo-portal.py whoami
  python3 scripts/glovo-portal.py dump                     # → .siruk-cache/glovo/portal-products.json
  python3 scripts/glovo-portal.py find 4020
  python3 scripts/glovo-portal.py categories
  python3 scripts/glovo-portal.py prices [--sheet final/glovo/siruk-glovo-products.xlsx] [--sku 4020 …] [--apply]
  python3 scripts/glovo-portal.py fix-skus [--apply]           # 11137 → 011137 (Excel ate the zeros)
  python3 scripts/glovo-portal.py set-price 4020 9800 [--apply]
  python3 scripts/glovo-portal.py set-active 4020 4026 --off [--apply]
  python3 scripts/glovo-portal.py stock Scale/armsoft-turnover-<date>.xlsx Scale/armsoft-export-<date>.xml \
      [--out final/glovo/glovo-availability-<date>.xlsx] [--on] [--apply]

`prices` compares the live Glovo price with column F (Price) of the Glovo sheet,
matched by SKU (column A), and updates the differences. A change of more than
±40 % is refused without --force (a wrong SKU match or a typo, not a price policy).
"""
import argparse, base64, csv, datetime, json, os, sys, time, urllib.error, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOKEN_FILE = os.path.join(ROOT, '.glovo-token')
CACHE = os.path.join(ROOT, '.siruk-cache', 'glovo')
DUMP = os.path.join(CACHE, 'portal-products.json')
SHEET = os.path.join(ROOT, 'final', 'glovo', 'siruk-glovo-products.xlsx')
API = 'https://catalog-vss-api-eu.deliveryhero.io/graphql'
PACE = 1.5            # seconds between writes
MAX_JUMP = 0.40        # refuse a price change larger than this share without --force

Q_PRODUCTS = '''query GetProducts($filter: ProductFilter!, $page: PageInput!) {
  products(filter: $filter, page: $page) {
    items { sku name price originalPrice active globalId internalId categoryIds categoryNames
            pieceBarcodes firstImage maximumSalesQuantity isWeighted lastModified }
    pagedResult { itemCount pageSize }
  }
}'''
Q_CATEGORIES = '''query ProductCategories($filter: CategoryFilter!, $page: PageInput) {
  categories(filter: $filter, page: $page) {
    items { id internalId name parentId }
    pagedResult { itemCount pageSize }
  }
}'''
M_UPDATE = '''mutation updateProduct($productUpdate: ProductUpdate!) {
  product(productUpdate: $productUpdate) {
    active price sku maximumSalesQuantity validationErrors { code message }
  }
}'''


def load_token():
    if not os.path.exists(TOKEN_FILE):
        sys.exit('no .glovo-token — capture it from the built-in browser (skill glovo-portal → Token)')
    t = json.load(open(TOKEN_FILE))
    payload = json.loads(base64.urlsafe_b64decode(t['access_token'].split('.')[1] + '=='))
    left = payload['exp'] - time.time()
    if left < 60:
        sys.exit(f'Glovo token expired {-left / 60:.0f} min ago — re-capture it from the built-in browser '
                 '(skill glovo-portal → Token)')
    t['_payload'], t['_left'] = payload, left
    return t


TOKEN = None


def vendor():
    return {'platformVendorId': TOKEN['platform_vendor_id'], 'globalEntityId': TOKEN['global_entity_id']}


def gql(query, variables, tries=3):
    """tries=1 for a mutation that must never run twice (createProductsRequest): a retry after a 5xx could
    file it again. (Glovo files three identical review cases per call anyway — seen with one attempt, 2026-11-12.)"""
    body = json.dumps({'query': query, 'variables': variables}).encode()
    req = urllib.request.Request(API, body, {
        'Authorization': 'Bearer ' + TOKEN['access_token'],
        'Content-Type': 'application/json; charset=utf-8',
        'x-client-source': 'one-web',
        'Origin': 'https://portal.glovoapp.com',
        'User-Agent': 'siruk-glovo-client'})
    for attempt in range(tries):
        try:
            with urllib.request.urlopen(req, timeout=60) as f:
                d = json.load(f)
            if d.get('errors'):
                raise RuntimeError(json.dumps(d['errors'], ensure_ascii=False)[:600])
            return d['data']
        except urllib.error.HTTPError as e:
            if e.code == 401:
                sys.exit('401 from Glovo — token expired or revoked; re-capture it (skill glovo-portal → Token)')
            if e.code >= 500 and attempt < tries - 1:
                time.sleep(2 * (attempt + 1)); continue
            raise RuntimeError(f'HTTP {e.code}: {e.read()[:400]!r}')


def all_products(search=''):
    out, page = [], 1
    while True:
        d = gql(Q_PRODUCTS, {'filter': {'vendorIdentifier': vendor(), 'locale': 'en', 'searchTerm': search,
                                        'active': None, 'brandIds': [], 'categoryIds': []},
                             'page': {'pageNumber': page, 'pageSize': 100}})['products']
        out += d['items']
        total = d['pagedResult']['itemCount']
        if not d['items'] or len(out) >= total:
            return out
        page += 1


def update(sku, fields, apply):
    v = {'productUpdate': dict(fields, sku=sku, vendorIdentifier=vendor())}
    if not apply:
        return None
    r = gql(M_UPDATE, v)['product']
    time.sleep(PACE)
    if r.get('validationErrors'):
        raise RuntimeError(f'{sku}: {r["validationErrors"]}')
    return r


def runlog(name, header, rows):
    d = os.path.join(ROOT, 'runs', datetime.date.today().isoformat())
    os.makedirs(d, exist_ok=True)
    p = os.path.join(d, name)
    new = not os.path.exists(p)
    with open(p, 'a', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        if new:
            w.writerow(header)
        w.writerows(rows)
    return p


def cmd_whoami(a):
    p = TOKEN['_payload']
    n = gql(Q_PRODUCTS, {'filter': {'vendorIdentifier': vendor(), 'locale': 'en', 'searchTerm': '', 'active': None,
                                    'brandIds': [], 'categoryIds': []}, 'page': {'pageNumber': 1, 'pageSize': 1}})
    print(json.dumps({'email': p['metadata'].get('email'), 'vendors': p['metadata'].get('platforms'),
                      'token_minutes_left': round(TOKEN['_left'] / 60),
                      'products_on_glovo': n['products']['pagedResult']['itemCount']}, indent=1))


def cmd_dump(a):
    items = all_products()
    os.makedirs(CACHE, exist_ok=True)
    json.dump({'saved': datetime.datetime.now().isoformat(timespec='seconds'), 'items': items},
              open(DUMP, 'w'), ensure_ascii=False, indent=1)
    act = sum(1 for i in items if i['active'])
    print(f'{len(items)} products ({act} active, {len(items) - act} inactive) → {DUMP}')


def cmd_find(a):
    for i in all_products(a.text):
        print(json.dumps({k: i[k] for k in ('sku', 'name', 'price', 'originalPrice', 'active', 'categoryNames',
                                            'pieceBarcodes', 'internalId')}, ensure_ascii=False))


def cmd_categories(a):
    d = gql(Q_CATEGORIES, {'filter': {'vendorIdentifier': vendor(), 'locale': a.locale, 'leavesOnly': False},
                           'page': {'pageNumber': 1, 'pageSize': 500}})['categories']
    for c in d['items']:
        print(c['internalId'], c['id'], c['parentId'] or '-', c['name'], sep='\t')


def sheet_prices(path):
    import openpyxl
    ws = openpyxl.load_workbook(path, read_only=True, data_only=True).worksheets[0]
    out = {}
    for r in ws.iter_rows(min_row=3, values_only=True):
        if r[0] is not None and isinstance(r[5], (int, float)):
            out[str(r[0]).strip()] = (float(r[5]), r[2])
    return out


SIRUK_EXPORT = os.path.join(CACHE, 'siruk-export.json')


def siruk_names():
    """sku → 'product name variant' (English) from a Siruk catalogue export, refreshed daily."""
    if not os.path.exists(SIRUK_EXPORT) or time.time() - os.path.getmtime(SIRUK_EXPORT) > 86400:
        import subprocess
        subprocess.run(['uv', 'run', '--no-sync', 'siruk', 'export', '-q', '--format', 'json', '-o', SIRUK_EXPORT],
                       cwd=ROOT, check=True, stdout=subprocess.DEVNULL)
    return {str(r['sku']): f"{r['product_name']} {r['variant_name']} {r.get('brand') or ''}"
            for r in json.load(open(SIRUK_EXPORT))}


def match_skus(live, ours):
    """Glovo sku → our sku. Glovo stores many SKUs with the leading zeros stripped (011137 → 11137:
    the onboarding sheet went through Excel), so match on the sku without leading zeros, and when two
    of ours collide there (12767 vs 012767) pick the one whose Siruk name shares most words with the
    Glovo name. Returns (mapping, ambiguous)."""
    import re
    from collections import defaultdict
    norm = defaultdict(list)
    for s in ours:
        norm[s.lstrip('0')].append(s)
    words = lambda x: set(re.findall(r'[a-z0-9]+', x.lower()))
    names, out, amb = None, {}, []
    for g, item in live.items():
        cands = norm.get(g.lstrip('0'), [])
        if len(cands) == 1:
            out[g] = cands[0]
        elif len(cands) > 1:
            names = names or siruk_names()
            score = sorted(((len(words(item['name']) & words(names.get(c, ''))), c) for c in cands), reverse=True)
            if score[0][0] > score[1][0]:
                out[g] = score[0][1]
            else:
                amb.append((g, item['name'], cands))
    return out, amb


def cmd_prices(a):
    want = sheet_prices(a.sheet)
    live = {i['sku']: i for i in all_products()}
    m, amb = match_skus(live, want)
    if a.sku:
        m = {g: o for g, o in m.items() if g in a.sku or o in a.sku}
    changes, refused = [], [(g, f'ambiguous: {n[:40]} could be {c}') for g, n, c in amb]
    skus = sorted(m)
    for s in skus:
        old, new = live[s]['price'], want[m[s]][0]
        if s != m[s]:
            live[s]['name'] += f'  [our sku {m[s]}]'
        if abs(old - new) < 0.5:
            continue
        if new <= 0 or (old and abs(new / old - 1) > MAX_JUMP and not a.force):
            refused.append((s, f'{old:.0f} → {new:.0f} is a {new / old - 1:+.0%} jump (--force to allow)')); continue
        changes.append((s, live[s]['name'], old, new))
    print(f'{len(changes)} price changes, {len(skus) - len(changes) - len(refused)} already right, '
          f'{len(refused)} skipped' + ('' if a.apply else '  (DRY RUN — add --apply)'))
    for c in changes[:15]:
        print(f'  {c[0]:>14}  {c[2]:>8.0f} → {c[3]:>8.0f}  {c[1][:60]}')
    if len(changes) > 15:
        print(f'  … {len(changes) - 15} more')
    for r in refused[:20]:
        print('  skip', *r)
    missing_on_glovo = sorted(set(want) - set(m.values()))
    if missing_on_glovo and not a.sku:
        print(f'{len(missing_on_glovo)} sheet SKUs are not on Glovo (new products — add them through the portal): '
              + ', '.join(missing_on_glovo[:12]) + (' …' if len(missing_on_glovo) > 12 else ''))
    if not a.apply:
        return
    done, failed = [], []
    for i, (s, name, old, new) in enumerate(changes, 1):
        try:
            r = update(s, {'price': new}, True)
            done.append((datetime.datetime.now().isoformat(timespec='seconds'), s, name, old, r['price']))
        except Exception as e:
            failed.append((s, str(e)[:200]))
        if i % 100 == 0:
            print(f'  {i}/{len(changes)}')
    p = runlog('glovo-prices.csv', ['time', 'sku', 'name', 'old price', 'new price'], done)
    print(f'updated {len(done)}, failed {len(failed)} → {p}')
    for f in failed[:20]:
        print('  FAIL', *f)


M_SKU = '''mutation UpdateSKU($vendorIdentifier: VendorIdentifier!, $oldSku: String!, $newSku: String!) {
  productUpdateSKU(vendorIdentifier: $vendorIdentifier, oldSku: $oldSku, newSku: $newSku) { status }
}'''


def cmd_fix_skus(a):
    """Rename zero-stripped Glovo SKUs back to ours (11137 → 011137) so they match exactly."""
    want = sheet_prices(a.sheet)
    live = {i['sku']: i for i in all_products()}
    m, amb = match_skus(live, want)
    todo = [(g, o, live[g]['name']) for g, o in sorted(m.items()) if g != o and o not in live]
    print(f'{len(todo)} Glovo SKUs to restore' + ('' if a.apply else '  (DRY RUN — add --apply)'))
    for t in todo[:15]:
        print(f'  {t[0]:>14} → {t[1]:<14} {t[2][:60]}')
    for g, n, c in amb:
        print('  ambiguous, left alone:', g, n[:50], c)
    if not a.apply:
        return
    rows = []
    for g, o, name in todo:
        try:
            st = gql(M_SKU, {'vendorIdentifier': vendor(), 'oldSku': g, 'newSku': o})['productUpdateSKU']['status']
        except Exception as e:
            st = 'ERROR ' + str(e)[:150]
        time.sleep(PACE)
        rows.append((datetime.datetime.now().isoformat(timespec='seconds'), g, o, name, st))
    p = runlog('glovo-skus.csv', ['time', 'old sku', 'new sku', 'name', 'status'], rows)
    print(f'{sum(r[4] == "UPDATE_SUCCESS" for r in rows)}/{len(rows)} UPDATE_SUCCESS → {p}')


def cmd_set_price(a):
    live = {i['sku']: i for i in all_products(a.sku)}
    if a.sku not in live:
        sys.exit(f'{a.sku} is not on Glovo')
    old = live[a.sku]['price']
    print(f'{a.sku} {live[a.sku]["name"]}: {old:.0f} → {a.price:.0f}' + ('' if a.apply else '  (DRY RUN — add --apply)'))
    if old and abs(a.price / old - 1) > MAX_JUMP and not a.force:
        sys.exit(f'refused: a {a.price / old - 1:+.0%} jump (--force to allow)')
    if a.apply:
        r = update(a.sku, {'price': a.price}, True)
        runlog('glovo-prices.csv', ['time', 'sku', 'name', 'old price', 'new price'],
               [(datetime.datetime.now().isoformat(timespec='seconds'), a.sku, live[a.sku]['name'], old, r['price'])])
        print('done:', r)


def cmd_set_active(a):
    on = a.on
    rows = []
    for s in a.skus:
        hit = [i for i in all_products(s) if i['sku'] == s]
        if not hit:
            print(f'{s}: not on Glovo'); continue
        i = hit[0]
        if i['active'] == on:
            print(f'{s}: already {"active" if on else "inactive"}'); continue
        print(f'{s} {i["name"][:60]}: {"inactive → active" if on else "active → inactive"}'
              + ('' if a.apply else '  (DRY RUN — add --apply)'))
        if a.apply:
            r = update(s, {'active': on}, True)
            rows.append((datetime.datetime.now().isoformat(timespec='seconds'), s, i['name'], r['active'], a.note or ''))
    if rows:
        print('→', runlog('glovo-availability.csv', ['time', 'sku', 'name', 'active', 'note'], rows))


M_DELETE = '''mutation($r: DeleteProductRequest!){ deleteProduct(deleteProductRequest:$r){ status reason } }'''


def cmd_delete(a):
    """Delete one product from our Glovo store for good (2026-11-12: Glovo staff's wrong merge 12007).
    Permanent: the user confirms each one. A product that is only sold out is switched off, not deleted.
    Refuses a SKU that is one of ours in Siruk, and an active product."""
    hit = [i for i in all_products(a.sku) if i['sku'] == a.sku]
    if not hit:
        sys.exit(f'{a.sku}: not on Glovo')
    i = hit[0]
    print(f'{a.sku}  internal id {i["internalId"]}  price {i["price"]:.0f}  active {i["active"]}  {i["categoryNames"]}\n  {i["name"]}')
    if a.sku in siruk_names():
        sys.exit('refused: this SKU is one of our Siruk variants — switch it off instead (set-active --off)')
    if i['active']:
        sys.exit('refused: switch it off first (set-active --off), then delete')
    if not a.apply:
        sys.exit('DRY RUN — a delete cannot be undone; on the user\'s yes add --apply')
    r = gql(M_DELETE, {'r': {'productInternalId': int(i['internalId']), 'vendorIdentifier': vendor()}}, tries=1)['deleteProduct']
    print('→', r)
    print(runlog('glovo-deleted.csv', ['time', 'sku', 'internal id', 'name', 'price', 'note', 'status', 'reason'],
                 [(datetime.datetime.now().isoformat(timespec='seconds'), a.sku, i['internalId'], i['name'], i['price'],
                   a.note or '', r['status'], r['reason'])]))
    left = [x for x in all_products(a.sku) if x['sku'] == a.sku]
    print('still listed!' if left else 'gone from the store')


MAX_OFF_SHARE = 0.25   # refuse to switch off more than this share of the store without --force


def armsoft_stock(turnover, goods_xml):
    """ArmSoft code → {unit_kg, stock, bag} from the turnover export + goods XML (sealed-stock-report.py)."""
    import importlib.util
    spec = importlib.util.spec_from_file_location('ssr', os.path.join(ROOT, 'scripts', 'sealed-stock-report.py'))
    ssr = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ssr)
    goods, turn = ssr.load_goods(goods_xml), ssr.load_turnover(turnover)
    ssr.fold_duplicates(turn)
    return {c: {'kg': t['unit'] == 'կգ', 'stock': round(t['stock'], 3),
                'bag': goods.get(c, {}).get('pack', 0) if t['unit'] == 'կգ' else 0} for c, t in turn.items()}


def variant_need(v, st):
    """(needed stock in ArmSoft's main unit, what it means) for one Siruk variant, or (None, why)."""
    sku = str(v['sku'])
    if not st['kg']:
        return (None, 'per-kg variant on a piece good') if sku.endswith(('-KG', '-100G')) else (1, '1 in stock')
    if sku.endswith('-KG'):
        return 1, '1 kg loose (open + sealed)'
    if sku.endswith('-100G'):
        return 0.1, '100 g loose (open + sealed)'
    if st['bag']:
        return st['bag'], f'1 sealed {st["bag"]:g} kg bag'
    return None, 'kg good with no bag unit in ArmSoft'


def cmd_stock(a):
    """Glovo availability from ArmSoft stock: a bag needs a sealed bag, 1 kg / 100 g needs that much loose
    (open bag + sealed ones), anything else needs 1 in stock. Off by default; --on also switches back on."""
    import openpyxl
    from openpyxl.styles import Font, PatternFill
    stock = armsoft_stock(a.turnover, a.goods)
    siruk_names()                                   # refreshes the Siruk export if older than a day
    ours = {str(r['sku']): r for r in json.load(open(SIRUK_EXPORT, encoding='utf-8'))}
    live = {i['sku']: i for i in all_products()}
    m, amb = match_skus(live, ours)
    rows, off, on = [], [], []
    for g, item in sorted(live.items(), key=lambda kv: kv[1]['name']):
        o = m.get(g)
        v = ours.get(o)
        code = (v or {}).get('accounting_code') or ''
        code = code.strip()
        st = stock.get(code, {'kg': False, 'stock': 0, 'bag': 0}) if code else None
        if not v:
            need, why, avail = None, 'no Siruk variant with this SKU', None
        elif not code:
            need, why, avail = None, 'Siruk variant has no ArmSoft code', None
        else:
            if code not in stock and (v.get('measure_type') == 'mass' and str(o).endswith(('-KG', '-100G'))):
                st = {'kg': True, 'stock': 0, 'bag': 0}
            need, why = variant_need(v, st)
            avail = None if need is None else st['stock'] >= need - 1e-6
            if code not in stock:
                why += ' — never stocked in ArmSoft'
        sealed = math_floor(st['stock'] / st['bag']) if st and st['bag'] and st['stock'] > 0 else None
        action = ''
        if avail is False and item['active']:
            action = 'OFF'; off.append(g)
        elif avail is True and not item['active']:
            # --on-codes (a posted receipt's goods) switches on only those; --on switches on everything in stock
            want_on = a.on or (a.on_codes and code in a.on_codes)
            action = 'ON' if want_on else 'back in stock (use --on)'
            if want_on:
                on.append(g)
        rows.append([g, o or '', item['name'], code, (st or {}).get('stock'), 'kg' if st and st['kg'] else 'pcs' if st else '',
                     (st or {}).get('bag') or '', sealed, round(st['stock'] - sealed * st['bag'], 3) if sealed is not None else '',
                     why, need, {True: 'yes', False: 'NO', None: '?'}[avail], 'on' if item['active'] else 'off', action])
    n_act = sum(1 for i in live.values() if i['active'])
    print(f'{len(live)} Glovo products ({n_act} on). ArmSoft: {sum(1 for r in rows if r[11] == "NO")} not available, '
          f'{sum(1 for r in rows if r[11] == "?")} unknown (left alone).')
    print(f'switch OFF: {len(off)}' + (f', switch ON: {len(on)}' if a.on or a.on_codes else
          f'; {sum(1 for r in rows if r[13].startswith("back"))} are off on Glovo but in stock (not touched without --on)')
          + ('' if a.apply else '  (DRY RUN — add --apply)'))
    for r in rows:
        if r[13] in ('OFF', 'ON'):
            print(f'  {r[13]:<3} {r[0]:>14}  {r[3]:<5} stock {r[4]!s:<7} {r[5]:<3} need {r[10]!s:<5} {r[2][:55]}')
    for g, n, c in amb:
        print('  ambiguous SKU, left alone:', g, n[:50], c)
    if a.out:
        wb = openpyxl.Workbook(); ws = wb.active; ws.title = 'Glovo availability'
        ws.append(['Glovo SKU', 'Siruk SKU', 'Glovo name', 'ArmSoft code', 'Stock', 'Unit', 'Bag kg', 'Sealed bags',
                   'Open bag left', 'Rule', 'Needs', 'Available', 'Glovo now', 'Action'])
        for c in ws[1]:
            c.font = Font(bold=True, color='FFFFFF'); c.fill = PatternFill('solid', fgColor='1F4E78')
        for r in sorted(rows, key=lambda r: ({'OFF': 0, 'ON': 1}.get(r[13], 2 if r[13] else 3), r[2])):
            ws.append(r)
            if r[13]:
                ws.cell(ws.max_row, 14).fill = PatternFill('solid', fgColor='F8CBAD' if r[13] == 'OFF' else 'C6EFCE')
        for j, w in enumerate([15, 17, 60, 9, 8, 5, 7, 8, 9, 40, 6, 9, 8, 22], start=1):
            ws.column_dimensions[openpyxl.utils.get_column_letter(j)].width = w
        ws.freeze_panes = 'D2'; ws.auto_filter.ref = ws.dimensions
        wb.save(a.out)
        print('→', a.out)
    if len(off) > MAX_OFF_SHARE * max(n_act, 1) and not a.force:
        sys.exit(f'refused: {len(off)} of {n_act} active products would go off — check the export (--force to allow)')
    if not a.apply:
        return
    log, failed = [], []
    for g, act in [(g, False) for g in off] + [(g, True) for g in on]:
        try:
            r = update(g, {'active': act}, True)
            log.append((datetime.datetime.now().isoformat(timespec='seconds'), g, live[g]['name'], r['active'],
                        a.note or ('ArmSoft stock: ' + ('none left' if not act else 'back in stock'))))
        except Exception as e:
            failed.append((g, str(e)[:200]))
    p = runlog('glovo-availability.csv', ['time', 'sku', 'name', 'active', 'note'], log)
    print(f'switched {len(log)}, failed {len(failed)} → {p}')
    for f in failed:
        print('  FAIL', *f)


def math_floor(x):
    import math
    return math.floor(x + 1e-6)


def main():
    global TOKEN
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    sub.add_parser('whoami').set_defaults(f=cmd_whoami)
    sub.add_parser('dump').set_defaults(f=cmd_dump)
    p = sub.add_parser('find'); p.add_argument('text'); p.set_defaults(f=cmd_find)
    p = sub.add_parser('categories'); p.add_argument('--locale', default='hy'); p.set_defaults(f=cmd_categories)
    p = sub.add_parser('prices'); p.add_argument('--sheet', default=SHEET); p.add_argument('--sku', nargs='*')
    p.add_argument('--apply', action='store_true'); p.add_argument('--force', action='store_true'); p.set_defaults(f=cmd_prices)
    p = sub.add_parser('fix-skus'); p.add_argument('--sheet', default=SHEET)
    p.add_argument('--apply', action='store_true'); p.set_defaults(f=cmd_fix_skus)
    p = sub.add_parser('set-price'); p.add_argument('sku'); p.add_argument('price', type=float)
    p.add_argument('--apply', action='store_true'); p.add_argument('--force', action='store_true'); p.set_defaults(f=cmd_set_price)
    p = sub.add_parser('set-active'); p.add_argument('skus', nargs='+')
    g = p.add_mutually_exclusive_group(required=True); g.add_argument('--on', action='store_true'); g.add_argument('--off', action='store_true')
    p.add_argument('--note'); p.add_argument('--apply', action='store_true'); p.set_defaults(f=cmd_set_active)
    p = sub.add_parser('delete', help='delete one product from the Glovo store (permanent; user confirms)')
    p.add_argument('sku'); p.add_argument('--note'); p.add_argument('--apply', action='store_true'); p.set_defaults(f=cmd_delete)
    p = sub.add_parser('stock', help='availability from an ArmSoft turnover export (sealed bags vs open)')
    p.add_argument('turnover'); p.add_argument('goods')
    p.add_argument('--on', action='store_true', help='also switch back on what is in stock again')
    p.add_argument('--on-codes', nargs='+', default=[], metavar='CODE',
                   help='switch back on only these ArmSoft codes (the goods of a receipt just posted)')
    p.add_argument('--out', help='review sheet (.xlsx)'); p.add_argument('--note')
    p.add_argument('--apply', action='store_true'); p.add_argument('--force', action='store_true'); p.set_defaults(f=cmd_stock)
    a = ap.parse_args()
    TOKEN = load_token()
    a.f(a)


if __name__ == '__main__':
    main()
