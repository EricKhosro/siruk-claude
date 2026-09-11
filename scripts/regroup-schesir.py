#!/usr/bin/env python3
"""Replay the corrected Schesir plan onto the live catalogue.

The first import grouped products with `scripts/plan-schesir.py` before it was
fixed, so pack weight, texture and any `&`-joined flavor acted as *product*
discriminators instead of variant axes. That left one range spread over several
products (the 113 g and 283 g training snacks; the Born Carnivore flavors) and,
where a merge had been hand-patched, variant labels that no longer told the
siblings apart ("255 g" three times).

This walks the fixed plan and, for every planned product:

  * picks the live product already holding the most of its SKUs as the target,
  * moves the other products' variants onto it (their bodies are copied intact —
    same media ids, copy, prices — only the label and attributes are recomputed),
  * renames the product and its slug to the planned name,
  * deletes the emptied products.

Variants already on the target keep their `id`, so their storefront rows
survive; absorbed ones are appended without an `id` and get a fresh one.

    scripts/regroup-schesir.py            # show what would change
    scripts/regroup-schesir.py --apply    # do it
"""
import argparse
import importlib
import json
import re
import sys

sys.path.insert(0, 'scripts')
imp = importlib.import_module('import-schesir')

PLAN = '.siruk-cache/schesir-plan-fixed.json'
BACKUP = '.siruk-cache/schesir-regroup-backup.json'
BRAND_SLUG = 'schesir'


def api(method, path, payload=None):
    return imp.api(method, path, payload)


def get_product(pid):
    _, d = api('GET', f'/products/{pid}')
    return d.get('data', {})


def slugify(s):
    return re.sub(r'-+', '-', re.sub(r'[^a-z0-9]+', '-', s.lower())).strip('-')


def variant_body(var):
    """A re-postable variant, minus the server-derived read-only fields."""
    return {k: v for k, v in var.items()
            if k not in ('attribute_values', 'attributes')}


SIZE_RE = re.compile(r'\b\d+(?:[.,]\d+)?\s*(?:g|kg)\b', re.I)
TEXTURE_RE = re.compile(
    r'\b(?:in\s+)?(?:Broth|Jelly|Paté|Pate|Mousse(?:\s*(?:&|and)\s*Shreds)?|'
    r'Gravy|Cream|Soup|Natural)\b', re.I)


planner = importlib.import_module('plan-schesir')
FLAVOR_RE = re.compile(
    r'\b(?:' + '|'.join(sorted({re.escape(f) for f in planner.FLAVOR_MAP.values()},
                               key=len, reverse=True)) + r')\b', re.I)


def merged_name(live_name, plan_name, sizes_vary, textures_vary,
                flavors_vary=False):
    """Name for a product that just absorbed another.

    The live names were already cleaned up by `fix-schesir-names.py`, so they
    beat the raw plan names and are kept — but a name that states an axis which
    now VARIES across the variants is wrong ("Snack Flavored 283g" once a 113 g
    variant joins it). Strip just those axes; if nothing identifying survives,
    fall back to the planned name.
    """
    n = live_name or ''
    if textures_vary:
        n = TEXTURE_RE.sub(' ', n)
    if sizes_vary:
        n = SIZE_RE.sub(' ', n)
    if flavors_vary:
        n = FLAVOR_RE.sub(' ', n)
    n = re.sub(r'\s*[-–]\s*$', '', re.sub(r'\s+', ' ', n)).strip(' -–,')
    # "85g" or "" left over means the live name carried no identity of its own
    if not re.search(r'[A-Za-z]', SIZE_RE.sub('', n)):
        return plan_name
    return n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true')
    ap.add_argument('--only', help='substring of the planned product name')
    args = ap.parse_args()

    plan = json.load(open(PLAN))
    menu = json.load(open(imp.MENU))

    # live Schesir catalogue: sku -> (product_id, variant dict)
    live_sku, live_prod = {}, {}
    for page in range(1, 12):
        _, d = api('GET', f'/products?page={page}')
        rows = d.get('data', [])
        if not rows:
            break
        for row in rows:
            if row.get('brand') != 'Schesir':
                continue
            full = get_product(row['id'])
            live_prod[row['id']] = full
            for var in full.get('variants', []):
                live_sku[str(var.get('sku'))] = (row['id'], var)

    print(f'live Schesir products: {len(live_prod)}   variants: {len(live_sku)}')
    if args.apply:
        json.dump(live_prod, open(BACKUP, 'w'), ensure_ascii=False, indent=1)
        print(f'backed every one of them up to {BACKUP}')
    print()

    # Resolve every planned product to the live product holding most of its
    # SKUs, then bucket by that target. Two planned products CAN land on the
    # same live one — `fix-schesir-leftovers.py` already merged a few ranges by
    # hand that the plan still separates (product 111's Lamb bag). PUT replaces
    # the whole variants array, so writing them one at a time would make the
    # second call silently delete the first call's variants.
    buckets = {}
    for p in plan:
        if args.only and args.only.lower() not in p['name'].lower():
            continue
        owners = {}
        for v in p['variants']:
            hit = live_sku.get(str(v['sku']))
            if hit:
                owners.setdefault(hit[0], []).append(v['sku'])
        if not owners:
            continue
        target = max(owners, key=lambda pid: len(owners[pid]))
        b = buckets.setdefault(target, {'plans': [], 'absorb': []})
        b['plans'].append(p)
        b['absorb'] += [pid for pid in owners if pid != target]

    changed = deleted = relabelled = 0
    for target, bucket in buckets.items():
        plans = bucket['plans']
        absorb = [a for a in dict.fromkeys(bucket['absorb']) if a != target]
        p = max(plans, key=lambda x: len(x['variants']))   # names the product
        kind = imp.kind_of(p)
        cur = live_prod[target]
        # Only a merge can invalidate the existing name; leave every other
        # product's name (and slug, and therefore its storefront url) alone.
        all_planned = [(pp, v) for pp in plans for v in pp['variants']]
        if absorb:
            sizes = {v['unit_g'] for _, v in all_planned}
            textures = {v.get('texture') or '' for _, v in all_planned}
            flavors = {v.get('flavor') or '' for _, v in all_planned}
            name = merged_name(cur.get('name'), p['name'],
                               len(sizes) > 1, len(textures) > 1,
                               len(flavors) > 1)
        else:
            name = cur.get('name')
        slug = (slugify(f'{BRAND_SLUG} {name}')
                if name != cur.get('name') else cur.get('slug'))

        variants, seen_default, claimed = [], False, set()
        for i, (pp, v) in enumerate(all_planned):
            hit = live_sku.get(str(v['sku']))
            if not hit:
                continue                       # never imported; leave it alone
            owner, var = hit
            body = variant_body(var)
            if owner != target:
                body.pop('id', None)           # recreate it on the target
            body['name'] = v['label']
            body['attribute_value_ids'] = imp.attrs_for(pp, v, menu,
                                                        imp.kind_of(pp))
            body['sort_order'] = i
            body['is_default'] = not seen_default
            seen_default = True
            claimed.add(str(v['sku']))
            variants.append(body)

        # A PUT deletes any variant missing from the payload, so carry over
        # every live variant on the target the plan does not mention.
        for var in cur.get('variants', []):
            if str(var.get('sku')) not in claimed:
                body = variant_body(var)
                body['sort_order'] = len(variants)
                body['is_default'] = not seen_default
                seen_default = True
                variants.append(body)
                print(f'    .. keeping unplanned live variant {var.get("sku")}'
                      f' "{var.get("name")}" on #{target}')

        if not variants:
            continue

        # the API refuses two variants with the same attribute combination
        combos = {}
        for var in variants:
            combos.setdefault(
                tuple(sorted(var['attribute_value_ids'].items())), []
            ).append(var['sku'])
        dupes = [v for v in combos.values() if len(v) > 1]

        old_labels = [var.get('name') for var in cur.get('variants', [])]
        new_labels = [var['name'] for var in variants]
        renaming = cur.get('name') != name
        merging = bool(absorb)
        if not (renaming or merging or old_labels != new_labels):
            continue

        print(f'#{target} "{cur.get("name")}" -> "{name}"'
              f'{"  (slug " + slug + ")" if renaming else ""}')
        if absorb:
            print('    absorbs ' + ', '.join(
                f'#{a} "{live_prod[a].get("name")}"' for a in absorb))
        for var in variants:
            tag = 'keep' if var.get('id') else 'NEW '
            print(f'    {tag} {var["sku"]:10s} {var["name"]:26s} '
                  f'attrs={var["attribute_value_ids"]}')
        if dupes:
            print(f'    !! duplicate attribute combos {dupes} — SKIPPED')
            continue

        body = dict(name=name, slug=slug,
                    category_ids=cur.get('category_ids') or [],
                    brand_id=cur.get('brand_id'),
                    attribute_family_id=cur.get('attribute_family_id'),
                    is_best_seller=cur.get('is_best_seller', False),
                    is_on_sale=cur.get('is_on_sale', False),
                    variants=variants)

        if not args.apply:
            changed += 1
            deleted += len(absorb)
            continue

        # SKUs are unique catalogue-wide, so the absorbed products must go
        # BEFORE the target can claim their SKUs ("SKU ... is already in use by
        # another variant"). Their full bodies are already in memory and were
        # written to the backup file above, so a failed PUT is recoverable.
        gone = []
        for a in absorb:
            st, r = api('DELETE', f'/products/{a}')
            if not any(f'HTTP {c}' in st for c in (200, 202, 204)):
                print(f'    !! DELETE {a} -> {st or "no status"}: '
                      f'{json.dumps(r)[:200]}')
            else:
                gone.append(a)
                deleted += 1
                print(f'    deleted #{a}')
        if len(gone) != len(absorb):
            print('    !! not every source product went away — skipping the '
                  'PUT so nothing is half-merged')
            continue

        st, resp = api('PUT', f'/products/{target}', body)
        if 'HTTP 200' not in st:
            print(f'    !! PUT {st or "no status"}: {json.dumps(resp)[:300]}')
            if gone:
                print(f'    !! #{gone} are already deleted — restore them from '
                      f'{BACKUP}')
            continue
        after = get_product(target)
        got = {str(v.get('sku')) for v in after.get('variants', [])}
        want = {str(v['sku']) for v in variants}
        if not want <= got:
            print(f'    !! verify failed, missing {sorted(want - got)} '
                  f'(restore from {BACKUP})')
            continue
        changed += 1
        relabelled += len(variants)
        print(f'    OK  #{target} now "{after.get("name")}" '
              f'with {len(after.get("variants", []))} variants')

    verb = 'would change' if not args.apply else 'changed'
    print(f'\n{verb} {changed} products; '
          f'{"would delete" if not args.apply else "deleted"} {deleted}')
    if imp.missing_vocab:
        print('wanted but missing vocabulary: '
              + json.dumps({k: sorted(v) for k, v in imp.missing_vocab.items()}))


if __name__ == '__main__':
    main()
