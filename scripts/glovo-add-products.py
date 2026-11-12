#!/usr/bin/env python3
"""Submit NEW products to Glovo's review (createProductsRequest), from a Pelican-style sheet.

  uv run --no-sync --with openpyxl python scripts/glovo-add-products.py <sheet.xlsx> \
      --brand YOKO --category 7145 [--also YOKO-1627:7078] [--out <dir>] [--apply]

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
import argparse, base64, html, importlib.util, json, os, sys, time

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
    ap.add_argument('sheet')
    ap.add_argument('--brand', help='brand as it must open every title (Latin); column K overrides it per row')
    ap.add_argument('--category', help='vendor category id for every row; column L ("7069+7148") overrides it per row')
    ap.add_argument('--also', nargs='*', default=[], help='SKU:catid extra categories')
    ap.add_argument('--out', help='dir for the request files (default: the sheet dir)')
    ap.add_argument('--batch', help='N/SIZE: send only the N-th slice of SIZE rows (1-based). A 51-row, 2.4 MB request was '
                                    'refused VENDOR_RATE_LIMITED on 2026-11-12; 12 rows (~0.5 MB) went through on 2026-11-09')
    ap.add_argument('--legacy', action='store_true',
                    help='old createProductsRequest route — its cases are invisible to Glovo (2026-11-12); do not use')
    ap.add_argument('--apply', action='store_true')
    a = ap.parse_args()

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


if __name__ == '__main__':
    main()
