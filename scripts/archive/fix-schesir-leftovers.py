#!/usr/bin/env python3
"""Repair the handful of Schesir products the bulk import got wrong.

1. Four multi-variant products whose names still begin "in " or are vague.
2. Products 131/132 — one Silver mousse line split in two because the vendor
   string for the chicken pouch carries no pack size.
3. Product 111 — the 2 kg Small Adult range lost its Lamb bag, because the sheet
   writes "SMALL MAINT LAMB" where the others say "SMALL MAINTENANCE".
4. Products 153/154 — the Born Carnivore 255 g flavors became separate products;
   one of them 422'd on a duplicate slug.

    scripts/fix-schesir-leftovers.py [--apply]
"""
import argparse
import json
import re
import subprocess
import sys

sys.path.insert(0, 'scripts')
import importlib
imp = importlib.import_module('import-schesir')


def api(method, path, payload=None):
    return imp.api(method, path, payload)


def get(pid):
    _, d = api('GET', f'/products/{pid}')
    return d.get('data', {})


def body_of(fd):
    b = {k: v for k, v in fd.items()
         if k not in ('createdAt', 'updatedAt', 'attribute_family_name', 'id')}
    b['variants'] = [{k: v for k, v in var.items()
                      if k not in ('attribute_values', 'attributes')}
                     for var in fd.get('variants', [])]
    return b


RENAMES = {
    99:  'Tuna in Jelly 85g',        # every variant is tuna + a qualifier
    109: 'Jelly 150g',               # mixed chicken and tuna bases
    113: 'Chicken Fillets 150g',     # chicken fillets with papaya/pineapple/apple
    118: 'Broth 85g',
    155: 'Born Carnivore Baby Kitten 255g',
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true')
    args = ap.parse_args()
    plan = json.load(open('.siruk-cache/schesir-plan.json'))
    cat = {}
    for ln in open('.siruk-cache/sources/schesir.jsonl', encoding='utf-8'):
        d = json.loads(ln)
        cat[d['handle']] = d
    media = imp.load_media_cache()
    menu = json.load(open('reference/attribute-values.json'))

    def build_variant(sku, flavor_id, sort, default=False):
        """Make a variant payload for a vendor sku from the plan + site data."""
        for p in plan:
            for v in p['variants']:
                if v['sku'] != sku:
                    continue
                site = cat.get(v['handle'] or '')
                if not site:
                    return None, f'{sku}: no site match'
                kind = imp.kind_of(p)
                sections = imp.fetch_page(site['handle'])
                about, ing, feed = imp.build_content(site, sections)
                imgs = imp.upload_images([i['src'] for i in site.get('images', [])[:3]],
                                         media, not args.apply)
                g = v['unit_g'] or 0
                a = imp.attrs_for(p, v, menu, kind)
                if flavor_id:
                    a['flavor'] = flavor_id
                var = dict(name=v['flavor'] if v['flavor'] != '(plain)'
                           else imp.weight_label(g),
                           about_this_item=about, ingredient_information=ing,
                           feeding_instructions=feed, sku=str(sku),
                           cost_price=v['cost'] or 0, compare_at_price=None,
                           min_allowed_price=0, weight=round(g / 1000, 3),
                           is_default=default, stock=10, vendor_stock=False,
                           sort_order=sort, images=imgs, attribute_value_ids=a)
                if kind == 'dry' and g:
                    var.update(pricing_type='per_kg', price=0,
                               price_per_kg=round(v['price'] / (g / 1000), 2))
                else:
                    var.update(pricing_type='fixed', price=v['price'])
                return var, None
        return None, f'{sku}: not in plan'

    acts = []

    # 1 — plain renames
    for pid, new in RENAMES.items():
        fd = get(pid)
        if not fd or fd.get('name') == new:
            continue
        acts.append(('rename', pid, fd.get('name'), new, lambda fd=fd, pid=pid, new=new:
                     api('PUT', f'/products/{pid}', {**body_of(fd), 'name': new})))

    # 2 — merge 131 (Silver chicken mousse, no size) into 132, then delete 131
    a, b = get(131), get(132)
    if a and b and a.get('variants'):
        v = dict(a['variants'][0])
        for k in ('attribute_values', 'attributes', 'id'):
            v.pop(k, None)
        v['weight'] = 0.08
        v['is_default'] = False
        v['sort_order'] = 1
        v.setdefault('attribute_value_ids', {})
        v['attribute_value_ids'] = {**a['variants'][0].get('attribute_value_ids', {}),
                                    'product-weight': menu['product-weight']['values']['80 g']}
        merged = body_of(b)
        merged['variants'].append(v)
        merged['name'] = 'Silver Senior in Mousse 80g Pouch'
        acts.append(('merge 131->132', 132, a.get('name'), merged['name'],
                     lambda merged=merged: api('PUT', '/products/132', merged)))
        acts.append(('delete 131', 131, a.get('name'), '-',
                     lambda: api('DELETE', '/products/131')))

    # 3 — the missing Lamb bag on product 111
    fd = get(111)
    if fd and not any(str(x.get('sku')) == '02055017' for x in fd.get('variants', [])):
        var, err = build_variant('02055017', menu['flavor']['values']['Lamb'],
                                 len(fd.get('variants', [])))
        if var:
            nb = body_of(fd)
            nb['variants'].append(var)
            acts.append(('add Lamb to 111', 111, fd.get('name'), '+02055017',
                         lambda nb=nb: api('PUT', '/products/111', nb)))
        else:
            print('  !', err)

    # 4 — Born Carnivore 255 g: one product, three flavors
    fd = get(153)
    if fd:
        keep = [v for v in body_of(fd)['variants'] if str(v.get('sku')) == '23380106']
        for v in keep:
            v['is_default'] = True
            v['sort_order'] = 0
            v.setdefault('attribute_value_ids', {})['flavor'] = menu['flavor']['values']['Egg']
        for i, (sku, fl) in enumerate([('23380206', 'Salmon'), ('23380306', 'Chicken')], 1):
            if any(str(v.get('sku')) == sku for v in keep):
                continue
            var, err = build_variant(sku, menu['flavor']['values'][fl], i)
            if var:
                keep.append(var)
            else:
                print('  !', err)
        nb = body_of(fd)
        nb['variants'] = keep
        nb['name'] = 'Born Carnivore 255g'
        acts.append(('rebuild 153 (BC 255g)', 153, fd.get('name'),
                     f'Born Carnivore 255g ({len(keep)}v)',
                     lambda nb=nb: api('PUT', '/products/153', nb)))
        acts.append(('delete 154 (folded in)', 154, 'Herring with Salmon 255g', '-',
                     lambda: api('DELETE', '/products/154')))

    for kind, pid, old, new, _ in acts:
        print(f'  {kind:26s} {pid:4d}  {old!r} -> {new!r}')
    if not args.apply:
        print('\n(dry run — pass --apply)')
        return
    ok = bad = 0
    for kind, pid, old, new, fn in acts:
        st, res = fn()
        good = 'HTTP 200' in st or 'HTTP 204' in st or 'HTTP 201' in st
        ok += good
        bad += not good
        print(f"{'OK  ' if good else 'FAIL'} {kind} {pid}"
              + ('' if good else f'  {json.dumps(res)[:200]}'))
    print(f'\nok={ok} failed={bad}')


if __name__ == '__main__':
    main()
