#!/usr/bin/env python3
"""Submit NEW products to Glovo's review (createSimpleProductBatch), from a Pelican-style sheet,
and afterwards check what Glovo's team did with them.

  uv run --no-sync --with openpyxl python scripts/glovo-add-products.py <sheet.xlsx> \
      --brand YOKO --category 7145 [--also YOKO-1627:7078] [--out <dir>] [--batch N/SIZE] [--apply]
  uv run --no-sync --with openpyxl python scripts/glovo-add-products.py <sheet.xlsx…> --review [--apply]

--review (2026-11-12): Glovo's team accepts or rejects each case by hand within hours, and edits what it
accepts. For every row of the sheet(s), review reads the case result (Added Products, listProductJobs)
and the live store in hy and en. It reports:
  - rows that are not live: rejected, or still in review (Glovo gives no reason);
  - a Glovo-made twin under a zero-stripped SKU;
  - a price or category set that is not ours;
  - a changed hy or en title.
Rejected rows that are not live go to <sheet dir>/glovo-retry-<date>.xlsx, ready to send again.
With --apply, review restores our price and categories, each as its own update (a combined update
answers unexpected_error). Titles are only reported: Glovo's title guards refuse most rewrites
(portal.md).

The sheet ("Glovo products", or the first sheet) has the Pelican columns: A sku, C title,
E description, F price. Optional per row (2026-11-12, mixed-brand batches): K brand, L vendor
category ids ("20620+20619"); they override --brand / --category, which are then not needed. The photo for each row is <sheet dir>/<sku>.jpg (500x500 JPEG).

Every title must be in Zoovet's pattern (user 2026-11-05 / 2026-11-09): the brand first,
Latin, no «», and pass glovo-titles.py check() (no number lost, <= 110 chars). A row that
fails stops the run. Without --apply this is a dry run: it prints the rows and, with --out,
writes the exact request (glovo-request-exact.json), a readable copy
(glovo-request-readable.json) and a photo preview (glovo-request-preview.html) for the user.
Nothing is live until Glovo approves; validateProductsRequest is not a real check.
"""
import argparse, base64, datetime, html, importlib.util, json, os, re, sys, time

import openpyxl

HERE = os.path.dirname(os.path.abspath(__file__))


def load(name, file):
    spec = importlib.util.spec_from_file_location(name, os.path.join(HERE, file))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


# Never in a Glovo title or description (user 2026-11-12): լակոտ is an insult in Armenian for a puppy —
# write «շան ձագ»; plus the obvious Russian / English ones.
BAD_WORDS = ['լակոտ', 'сука', 'суки', 'сучк', 'бляд', 'блят', 'хуй', 'хуё', 'пизд', 'ебат', 'ебан', 'дерьм', 'говн',
             'bitch', 'fuck', 'shit', 'bastard']


# What the portal's own Add Product page sends (AddProductsV4 → createSimpleProductBatch, read from its JS 2026-11-12).
# The cases it opens show under Store Management → Actions Overview → Added Products, where Glovo's team reviews them.
# createProductsRequest (MUTATION below, used until 2026-11-12) answered "ok" and filed cases nobody at Glovo could see.
SIMPLE = """mutation($r: CreateSimpleProductBatchPayload!){
  createSimpleProductBatch(productsRequest:$r){
    __typename
    ... on SimpleProductBatchSuccess { message caseId }
    ... on SimpleProductBatchValidationError { csvValidationErrors { error message column }
                                               productValidationErrors { barcode errors index } } } }"""


MUTATION = """mutation($v: VendorIdentifier!, $r: ProductsRequest!){
  createProductsRequest(vendorIdentifier:$v, productsRequest:$r){
    __typename
    ... on CreateProductsRequestSuccessful { status }
    ... on CreateProductsRequestErrorDuplicatesFound { products { __typename
          ... on DuplicateMasterProduct { barcode name requestId status createdAt image } } } } }"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('sheet', nargs='+', help='one sheet to send; with --review, every sheet that was sent')
    ap.add_argument('--brand', help='brand as it must open every title (Latin); column K overrides it per row')
    ap.add_argument('--category', help='vendor category id for every row; column L ("7069+7148") overrides it per row')
    ap.add_argument('--also', nargs='*', default=[], help='SKU:catid extra categories')
    ap.add_argument('--out', help='dir for the request files (default: the sheet dir)')
    ap.add_argument('--batch', help='N/SIZE: send only the N-th slice of SIZE rows (1-based). A 51-row, 2.4 MB request was '
                                    'refused VENDOR_RATE_LIMITED on 2026-11-12; 12 rows (~0.5 MB) went through on 2026-11-09')
    ap.add_argument('--legacy', action='store_true',
                    help='old createProductsRequest route — its cases are invisible to Glovo (2026-11-12); do not use')
    ap.add_argument('--review', action='store_true', help='check the sent rows against the case results and the live store')
    ap.add_argument('--apply', action='store_true')
    a = ap.parse_args()
    if a.review:
        return review(a)
    if len(a.sheet) > 1:
        sys.exit('send one sheet at a time')
    a.sheet = a.sheet[0]

    gt = load('gt', 'glovo-titles.py')
    gp = load('gp', 'glovo-portal.py')
    gp.TOKEN = gp.load_token()
    names = {}
    for c in gp.gql(gp.Q_CATEGORIES, {'filter': {'vendorIdentifier': gp.vendor(), 'locale': 'hy', 'leavesOnly': False},
                                      'page': {'pageNumber': 1, 'pageSize': 500}})['categories']['items']:
        names[str(c['id'])] = c['name']
        names.setdefault(str(c['internalId']), c['name'])

    wb = openpyxl.load_workbook(a.sheet, data_only=True)
    ws = wb['Glovo products'] if 'Glovo products' in wb.sheetnames else wb.worksheets[0]
    d = os.path.dirname(os.path.abspath(a.sheet))
    extra = {}
    for s in a.also:
        sku, cid = s.rsplit(':', 1)
        extra.setdefault(sku, []).append(cid)

    products, bad = [], []
    for r in ws.iter_rows(min_row=2, values_only=True):
        sku = r[0]
        if not sku or str(sku).startswith('sku'):
            continue
        sku, title, desc, price = str(sku), r[2], r[4], r[5]
        brand = (r[10] if len(r) > 10 and r[10] else None) or a.brand
        row_cats = str(r[11]).split('+') if len(r) > 11 and r[11] else ([a.category] if a.category else [])
        if not brand or not row_cats:
            bad.append(f'{sku}: no brand (--brand / column K) or no category (--category / column L)')
            continue
        probs = gt.check(title, title, brand)
        low = f'{title} {desc or ""}'.lower()
        probs += [f'rude word "{w}"' for w in BAD_WORDS if w in low]
        if probs:
            bad.append(f'{sku}: {", ".join(probs)} | {title}')
        title_en = r[12] if len(r) > 12 and r[12] else None     # column M: Armenia requires hy AND en titles
        if not a.legacy and not title_en:
            bad.append(f'{sku}: no English title (column M) — Glovo Armenia requires hy and en')
        if title_en:
            probs_en = [f'rude word "{w}" (en)' for w in BAD_WORDS if w in title_en.lower()]
            if probs_en:
                bad.append(f'{sku}: {", ".join(probs_en)} | {title_en}')
        img = open(os.path.join(d, f'{sku}.jpg'), 'rb').read()
        cats = row_cats + extra.get(sku, [])
        products.append({'sku': sku, 'name': title, 'price': float(price), 'description': desc,
                         # a zero-padded scale PLU / internal code (00000108) is no EAN: Glovo's master catalogue
                         # has other shops' goods under those numbers and refuses the whole batch (2026-11-12)
                         'barcode': (str(r[1]) if r[1] and not str(r[1]).startswith('0000') else None),
                         'requestId': 'siruk-' + sku,
                         'imagesEncoded': ['data:image/jpeg;base64,' + base64.b64encode(img).decode()],   # plain base64 -> dhis_upload.parsing_error
                         'categoryList': [{'id': c, 'name': names.get(c, '')} for c in cats],
                         'title_en': title_en})
    if bad:
        sys.exit('titles not in Zoovet\'s pattern (brand first, no «»):\n  ' + '\n  '.join(bad))
    missing = sorted({c['id'] for p in products for c in p['categoryList'] if not c['name']})
    if names and missing:
        sys.exit(f'unknown vendor category ids: {missing} (glovo-portal.py categories --locale hy)')
    if a.batch:
        n, size = map(int, a.batch.split('/'))
        products = products[(n - 1) * size:n * size]
        if not products:
            sys.exit(f'batch {a.batch}: no rows')

    for p in products:
        print(p['sku'], int(p['price']), '+'.join(c['id'] for c in p['categoryList']), '|', p['name'])
    print(f'{len(products)} products')

    out = a.out or d
    if a.legacy:
        req = {'query': MUTATION, 'variables': {'v': gp.vendor(), 'r': {'products': [
            {k: v for k, v in p.items() if k != 'title_en'} for p in products]}}}
    else:
        req = {'query': SIMPLE, 'variables': {'r': {'simpleProducts': [{
            'name': [{'locale': 'hy', 'name': p['name']}, {'locale': 'en', 'name': p['title_en']}],
            'description': [{'locale': 'hy', 'name': p['description']}] if p['description'] else [],
            'barcode': p['barcode'].zfill(14) if p['barcode'] else None,     # the portal pads to 14 digits
            'imagesEncoded': p['imagesEncoded'], 'sku': p['sku'], 'brand': None, 'activeness': True,
            'price': p['price'], 'isSoldByWeight': False, 'weighableSoldByPiece': False,
            'categories': [{'id': c['id'], 'locale': 'hy_AM', 'name': c['name']} for c in p['categoryList']],
            'vendorsIdentifier': [gp.vendor()]} for p in products]}}}
    json.dump(req, open(os.path.join(out, 'glovo-request-exact.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    short = json.loads(json.dumps(req))
    for p in short['variables']['r'].get('products') or short['variables']['r']['simpleProducts']:
        p['imagesEncoded'] = [f"<{p['sku']}.jpg, {len(p['imagesEncoded'][0])} base64 chars>"]
    json.dump(short, open(os.path.join(out, 'glovo-request-readable.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    rows = ''.join(
        f'<tr><td><img src="{p["imagesEncoded"][0]}"></td><td>{p["sku"]}</td>'
        f'<td>{html.escape(p["name"])}</td><td>{html.escape(p["description"] or "")}</td><td>{int(p["price"])}</td>'
        f'<td>{"<br>".join(html.escape(c["id"] + " " + c["name"]) for c in p["categoryList"])}</td>'
        f'<td>{p["barcode"] or "none"}</td></tr>' for p in products)
    open(os.path.join(out, 'glovo-request-preview.html'), 'w', encoding='utf-8').write(
        '<!doctype html><meta charset="utf-8"><title>Glovo new products</title><style>body{font-family:sans-serif;margin:16px}'
        'table{border-collapse:collapse}td,th{border:1px solid #ccc;padding:6px;vertical-align:top;font-size:14px}img{width:160px}</style>'
        f'<h2>{len(products)} new products for Glovo review</h2><table><tr><th>Photo</th><th>SKU</th><th>Title</th>'
        f'<th>Description</th><th>Price</th><th>Categories</th><th>Barcode</th></tr>{rows}</table>')
    print(f'request files → {out}')

    if not a.apply:
        sys.exit('dry run - show the user the request files, then --apply')
    time.sleep(3)   # right after the categories call Glovo answers VENDOR_RATE_LIMITED (2026-11-12); nothing is filed then
    print(json.dumps(gp.gql(req['query'], req['variables'], tries=1), ensure_ascii=False, indent=1))   # never retried: a retry could file it again


Q_JOBS = """query($f: ProductJobsFilter!, $p: PageInput!){ listProductJobs(filter:$f, page:$p){
  jobs { caseId status createdAt itemsTruncated items { sku status title } } } }"""
Q_LIVE = """query($f: ProductFilter!, $p: PageInput!){ products(filter:$f, page:$p){
  items { sku name price active categoryIds categoryNames } pagedResult { itemCount } } }"""


def numbers(t):
    return {float(n.replace(',', '.')) for n in re.findall(r'\d+(?:[.,]\d+)?', t)}


def species(t):
    t = t.lower()
    return {k for k, w in {'dog': r'\b(dogs?|pupp(y|ies))\b', 'cat': r'\b(cats?|kittens?)\b'}.items() if re.search(w, t)}


def en_off(theirs, ours):
    """Glovo's moderators restyle nearly every en title ("Yoko Dried Bull Pizzle S 40g"), drop "1 pc" or "ø 17 cm".
    Worth a look only when they add or change a number (23410 "7pcs" for 1 pc) or name another species."""
    a, b = species(theirs), species(ours)
    return bool(numbers(theirs) - numbers(ours)) or bool(a and b and a != b)


def sheet_rows(path):
    wb = openpyxl.load_workbook(path, data_only=True)
    ws = wb['Glovo products'] if 'Glovo products' in wb.sheetnames else wb.worksheets[0]
    hdr = None
    for r in ws.iter_rows(min_row=1, values_only=True):
        if hdr is None:
            hdr = r
            continue
        if r[0] and not str(r[0]).startswith('sku'):
            yield hdr, r


def review(a):
    gp = load('gp', 'glovo-portal.py')
    gp.TOKEN = gp.load_token()
    sent, src = {}, {}
    for path in a.sheet:
        for hdr, r in sheet_rows(path):
            sku = str(r[0])
            sent[sku] = {'hy': r[2], 'price': float(r[5]), 'en': r[12] if len(r) > 12 else None,
                         'cats': sorted(str(r[11]).split('+')) if len(r) > 11 and r[11] else None, 'row': r}
            src[sku] = (path, hdr)

    # the case results (Added Products): the newest job item per SKU. Glovo gives no rejection reason.
    job, page = {}, 1
    while True:
        js = gp.gql(Q_JOBS, {'f': {'vendorIdentifier': gp.vendor(), 'locale': 'en', 'includeItems': True,
                                   'itemPageSize': 100}, 'p': {'pageNumber': page, 'pageSize': 20}})['listProductJobs']['jobs']
        for j in js:
            if j['itemsTruncated']:
                print(f'warning: case {j["caseId"]} lists only part of its items')
            for i in j['items']:
                if i['sku'] in sent and (i['sku'] not in job or j['createdAt'] > job[i['sku']][0]):
                    job[i['sku']] = (j['createdAt'], i['status'], j['caseId'])
        if len(js) < 20:
            break
        page += 1
        time.sleep(gp.PACE)

    def live(locale):
        out, page = {}, 1
        while True:
            d = gp.gql(Q_LIVE, {'f': {'vendorIdentifier': gp.vendor(), 'locale': locale, 'searchTerm': '', 'active': None,
                                      'brandIds': [], 'categoryIds': []}, 'p': {'pageNumber': page, 'pageSize': 100}})['products']
            out.update({i['sku']: i for i in d['items']})
            if not d['items'] or len(out) >= d['pagedResult']['itemCount']:
                return out
            page += 1
            time.sleep(gp.PACE)
    hy = live('hy_AM')
    time.sleep(gp.PACE)
    en = live('en_AM')
    stripped = {}
    for s in hy:
        stripped.setdefault(s.lstrip('0'), []).append(s)

    ours = set(gp.siruk_names())     # our own SKUs: 4097 and 004097 are two real goods, not a twin
    report, fixes, retry, restyled = [], [], [], []
    now = datetime.datetime.now().isoformat(timespec='seconds')
    for sku, w in sent.items():
        st = job.get(sku, (None, 'NO CASE', ''))
        # Glovo's staff sometimes create our goods by hand from old onboarding rows, under a zero-stripped SKU
        # (12767 / 012767, 2026-11-12), and once merged two goods into one (12007)
        twins = [s for s in stripped.get(sku.lstrip('0'), []) if s != sku and s not in ours]
        h, e, issues = hy.get(sku), en.get(sku), []
        if twins:
            issues.append(f'twin under SKU {", ".join(twins)}: check it with glovo-portal.py find')
        if not h:
            issues.append(f'NOT LIVE (case {st[1]})')
            if st[1].startswith('FAIL') and not twins:
                retry.append(sku)
        else:
            if not h['active']:
                issues.append('switched off')
            if abs(float(h['price']) - w['price']) > 0.5:
                if float(h['price']) and abs(w['price'] / float(h['price']) - 1) > gp.MAX_JUMP:
                    issues.append(f'price {h["price"]:.0f}, ours {w["price"]:.0f}: over ±40 %, a wrong merge? check by hand')
                else:
                    issues.append(f'price {h["price"]:.0f} → {w["price"]:.0f}')
                    fixes.append((sku, 'price', {'price': w['price']}))
            if w['cats'] and sorted(map(str, h['categoryIds'])) != w['cats']:
                issues.append(f'categories {h["categoryIds"]} → {"+".join(w["cats"])}')
                fixes.append((sku, 'categories', {'categoryInternalIds': w['cats']}))
            if w['hy'] and h['name'] != w['hy']:
                issues.append(f'hy title now "{h["name"]}"')
            if w['en'] and e and e['name'] != w['en']:
                if en_off(e['name'], w['en']):
                    issues.append(f'en title now "{e["name"]}" (ours "{w["en"]}")')
                else:
                    restyled.append(sku)
        report.append((sku, st[1], st[2], '; '.join(issues) or 'ok'))

    for r in report:
        if r[3] != 'ok':
            print(f'{r[0]:14} {r[1]:10} {r[3]}')
    ok = sum(r[3] == 'ok' for r in report)
    print(f'\n{len(report)} rows: {ok} ok, {len(report) - ok} to look at; '
          f'{len(fixes)} price/category fixes, {len(retry)} to send again; '
          f'{len(restyled)} en titles restyled by Glovo (same numbers, left as they are)')
    gp.runlog('glovo-review.csv', ['time', 'sku', 'case status', 'case', 'finding'], [(now,) + r for r in report])

    if retry:
        by_sheet = {}
        for sku in retry:
            by_sheet.setdefault(src[sku], []).append(sent[sku]['row'])
        for (path, hdr), rows in by_sheet.items():
            out = os.path.join(os.path.dirname(os.path.abspath(path)), f'glovo-retry-{datetime.date.today().isoformat()}.xlsx')
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = 'Glovo products'
            ws.append(list(hdr))
            for r in rows:
                ws.append(list(r))
            wb.save(out)
            print(f'rejected and not live → {out}\n  look at why first (photo, title, a twin by name), then send that sheet')
    if fixes and not a.apply:
        print('dry run: --apply restores our price and categories')
    elif fixes:
        log = []
        for sku, what, fields in fixes:
            try:
                gp.update(sku, fields, True)
                log.append((now, sku, f'review: {what} {fields}', 'ok'))
            except RuntimeError as ex:
                log.append((now, sku, f'review: {what} {fields}', str(ex)[:200]))
            print(*log[-1][1:])
        print(gp.runlog('glovo-fixes.csv', ['time', 'sku', 'change', 'status'], log))


if __name__ == '__main__':
    main()
