#!/usr/bin/env python3
"""Submit NEW products to Glovo's review (createProductsRequest), from a Pelican-style sheet.

  uv run --no-sync --with openpyxl python scripts/glovo-add-products.py <sheet.xlsx> \
      --brand YOKO --category 7145 [--also YOKO-1627:7078] [--out <dir>] [--apply]

The sheet ("Glovo products", or the first sheet) has the Pelican columns: A sku, C title,
E description, F price. The photo for each row is <sheet dir>/<sku>.jpg (500x500 JPEG).

Every title must be in Zoovet's pattern (user 2026-11-05 / 2026-11-09): the brand first,
Latin, no «», and pass glovo-titles.py check() (no number lost, <= 110 chars). A row that
fails stops the run. Without --apply this is a dry run: it prints the rows and, with --out,
writes the exact request (glovo-request-exact.json), a readable copy
(glovo-request-readable.json) and a photo preview (glovo-request-preview.html) for the user.
Nothing is live until Glovo approves; validateProductsRequest is not a real check.
"""
import argparse, base64, html, importlib.util, json, os, sys

import openpyxl

HERE = os.path.dirname(os.path.abspath(__file__))


def load(name, file):
    spec = importlib.util.spec_from_file_location(name, os.path.join(HERE, file))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


MUTATION = """mutation($v: VendorIdentifier!, $r: ProductsRequest!){
  createProductsRequest(vendorIdentifier:$v, productsRequest:$r){
    __typename
    ... on CreateProductsRequestSuccessful { status }
    ... on CreateProductsRequestErrorDuplicatesFound { products { __typename } } } }"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('sheet')
    ap.add_argument('--brand', required=True, help='brand as it must open every title (Latin)')
    ap.add_argument('--category', required=True, help='vendor category id for every row')
    ap.add_argument('--also', nargs='*', default=[], help='SKU:catid extra categories')
    ap.add_argument('--out', help='dir for the request files (default: the sheet dir)')
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
        probs = gt.check(title, title, a.brand)
        if probs:
            bad.append(f'{sku}: {", ".join(probs)} | {title}')
        img = open(os.path.join(d, f'{sku}.jpg'), 'rb').read()
        cats = [a.category] + extra.get(sku, [])
        products.append({'sku': sku, 'name': title, 'price': float(price), 'description': desc,
                         'barcode': (str(r[1]) if r[1] else None), 'requestId': 'siruk-' + sku,
                         'imagesEncoded': ['data:image/jpeg;base64,' + base64.b64encode(img).decode()],   # plain base64 -> dhis_upload.parsing_error
                         'categoryList': [{'id': c, 'name': names.get(c, '')} for c in cats]})
    if bad:
        sys.exit('titles not in Zoovet\'s pattern (brand first, no «»):\n  ' + '\n  '.join(bad))
    missing = sorted({c['id'] for p in products for c in p['categoryList'] if not c['name']})
    if names and missing:
        sys.exit(f'unknown vendor category ids: {missing} (glovo-portal.py categories --locale hy)')

    for p in products:
        print(p['sku'], int(p['price']), '+'.join(c['id'] for c in p['categoryList']), '|', p['name'])
    print(f'{len(products)} products')

    out = a.out or d
    req = {'query': MUTATION, 'variables': {'v': gp.vendor(), 'r': {'products': products}}}
    json.dump(req, open(os.path.join(out, 'glovo-request-exact.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    short = json.loads(json.dumps(req))
    for p in short['variables']['r']['products']:
        p['imagesEncoded'] = [f"<{p['sku']}.jpg, {len(p['imagesEncoded'][0])} base64 chars>"]
    json.dump(short, open(os.path.join(out, 'glovo-request-readable.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    rows = ''.join(
        f'<tr><td><img src="data:image/jpeg;base64,{p["imagesEncoded"][0]}"></td><td>{p["sku"]}</td>'
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
    print(json.dumps(gp.gql(MUTATION, req['variables']), ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
