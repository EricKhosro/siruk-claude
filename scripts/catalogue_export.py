#!/usr/bin/env python3
"""The whole catalogue in one call: GET /products/export?format=json (siruk-web 2026-10-27).

One record per variant, in the requested language — 13 s for ~1,650 variants,
where scripts/dump-products.py needs ~1 h per language. The export gives every
field a per-product GET has for the jobs below, except that the variant's
attribute values come as one text ("Համ: Հավ, Տարիք: Չափահասներ"). products()
rebuilds them as GET /products/<id> gives them (attribute_value_labels:
attributeId, attributeName, role, valueId, label) from the live attribute list
and the product types, both in the same language.

    scripts/catalogue_export.py --lang hy           # -> .siruk-cache/live/export-hy.json
    scripts/catalogue_export.py --lang hy --check   # + compare with the dump-products.py copies

As a module: products(lang) -> ({product id: product}, {media id: original url}),
the product in the shape of GET /products/<id> for the fields the export carries.

Read-only: GET only.
"""
import argparse, glob, json, os, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIVE = os.path.join(ROOT, '.siruk-cache', 'live')


def api_get(path, lang):
    r = subprocess.run(['bash', os.path.join(ROOT, 'scripts/api.sh'), 'GET', path], capture_output=True,
                       text=True, encoding='utf-8', cwd=ROOT, timeout=300,
                       env=dict(os.environ, SIRUK_NO_PACE='1', SIRUK_LANG=lang))
    i = r.stdout.find('{')
    if i < 0:
        sys.exit(f'GET {path} failed: {r.stderr.strip()[-300:]}')
    return json.loads(r.stdout[i:])


def all_pages(path, lang):
    out, page = [], 1
    while True:
        d = api_get(f'{path}{"&" if "?" in path else "?"}page={page}', lang)
        out += d.get('data') or []
        if page >= (d.get('meta') or {}).get('last_page', 1):
            return out
        page += 1


def fetch(lang):
    """The export records, also saved to .siruk-cache/live/export-<lang>.json."""
    records = api_get(f'/products/export?lang={lang}&format=json', lang)['data']
    os.makedirs(LIVE, exist_ok=True)
    json.dump(records, open(os.path.join(LIVE, f'export-{lang}.json'), 'w', encoding='utf-8'), ensure_ascii=False)
    return records


def option_parser(lang):
    """A function: (options text, product type name) -> attribute_value_labels."""
    pairs = {}                                    # "Name: label" -> (attribute, value)
    for a in all_pages('/attributes?per_page=100', lang):
        for v in a.get('values') or []:
            pairs[f"{a['name']}: {v['label']}"] = (a, v)
    roles = {f['name']: {x['id']: x['role'] for x in f.get('attributes') or []}
             for f in all_pages('/attribute-families?per_page=100', lang)}
    longest = sorted(pairs, key=len, reverse=True)

    def parse(text, family):
        out, i, role = [], 0, roles.get(family, {})
        while text and i < len(text):
            # the longest known "Name: label" here that ends the text or is followed by ", "
            hit = next((p for p in longest if text.startswith(p, i) and text[i + len(p):i + len(p) + 2] in ('', ', ')), None)
            if not hit:
                raise ValueError(f'unknown attribute value at {text[i:]!r}')
            a, v = pairs[hit]
            out.append({'attributeId': a['id'], 'attributeName': a['name'], 'role': role.get(a['id']),
                        'valueId': v['id'], 'label': v['label']})
            i += len(hit) + 2
        return out
    return parse


def products(lang, records=None):
    records = records if records is not None else fetch(lang)
    parse = option_parser(lang)
    prods, media = {}, {}
    for r in records:
        p = prods.setdefault(r['product_id'], {
            'id': r['product_id'], 'name': r['product_name'], 'slug': r['slug'], 'brand_id': r['brand_id'],
            'category_ids': r['category_ids'] or [], 'attribute_family_name': r['product_type'],
            'is_discontinued': r['is_discontinued'], 'is_on_sale': r['is_on_sale'],
            'is_best_seller': r['is_best_seller'], 'variants': []})
        if r['variant_id'] is None:
            continue
        p['variants'].append({
            'id': r['variant_id'], 'sku': r['sku'], 'name': r['variant_name'], 'size_label': r['size'],
            'barcode': r['barcode'], 'accounting_code': r['accounting_code'], 'sale_mode': r['sale_mode'],
            'measure_type': r['measure_type'], 'content': r['content'], 'pack_count': r['pack_count'],
            'price': r['price'], 'compare_at_price': r['compare_at_price'], 'cost_price': r['cost_price'],
            'stock_status': r['stock_status'], 'available_quantity': r['available'],
            'is_purchasable': r['is_purchasable'], 'price_source_url': r['price_source_url'],
            'images': r['image_ids'] or [], 'about_this_item': r['about_this_item_html'],
            'attribute_value_labels': parse(r['options'] or '', r['product_type'])})
        media.update(zip(map(str, r['image_ids'] or []), r['image_urls'] or []))
    return prods, media


def check(prods, lang):
    """Field-by-field against the dump-products.py copies (.siruk-cache/live/products[-<lang>]/)."""
    d = os.path.join(LIVE, 'products' + ('' if lang == 'en' else f'-{lang}'))
    keys = ['sku', 'name', 'size_label', 'barcode', 'price', 'images', 'about_this_item', 'stock_status',
            'is_purchasable', 'pack_count']
    diffs, n = [], 0
    for f in glob.glob(os.path.join(d, '[0-9]*.json')):
        g = json.load(open(f, encoding='utf-8'))
        g = g.get('data', g)
        p = prods.get(g['id'])
        if not p:
            diffs.append((g['id'], '', 'product not in the export'))
            continue
        for k in ('name', 'brand_id', 'is_discontinued'):
            if g.get(k) != p.get(k):
                diffs.append((g['id'], '', k))
        if sorted(g.get('category_ids') or []) != sorted(p['category_ids']):
            diffs.append((g['id'], '', 'category_ids'))
        ev = {v['id']: v for v in p['variants']}
        for v in g.get('variants') or []:
            n += 1
            e = ev.get(v['id'])
            if not e:
                diffs.append((g['id'], v['sku'], 'variant not in the export'))
                continue
            for k in keys:
                a, b = v.get(k), e.get(k)
                if k == 'price':
                    a, b = float(a or 0), float(b or 0)
                if a != b:
                    diffs.append((g['id'], v['sku'], k))
            want = sorted((x['attributeId'], x['valueId'], x.get('role'), x['label']) for x in v.get('attribute_value_labels') or [])
            got = sorted((x['attributeId'], x['valueId'], x['role'], x['label']) for x in e['attribute_value_labels'])
            if want != got:
                diffs.append((g['id'], v['sku'], 'attribute_value_labels'))
    return n, diffs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--lang', default='en', choices=['en', 'ru', 'hy'])
    ap.add_argument('--check', action='store_true', help='compare with the dump-products.py copies')
    a = ap.parse_args()
    prods, media = products(a.lang)
    print(f'{sum(len(p["variants"]) for p in prods.values())} variants, {len(prods)} products, '
          f'{len(media)} images -> .siruk-cache/live/export-{a.lang}.json', file=sys.stderr)
    if a.check:
        n, diffs = check(prods, a.lang)
        print(f'{n} variants compared, {len(diffs)} differences', file=sys.stderr)
        for d in diffs:
            print(*d, sep='\t')


if __name__ == '__main__':
    main()
