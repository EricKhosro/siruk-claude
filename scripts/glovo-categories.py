#!/usr/bin/env python3
"""Glovo vendor categories: audit every product on our Glovo store against what it is in Siruk, and fix them.

What a product IS comes from Siruk: its category leaves (+ product type, + the Material option for bowls).
reference/glovo/category-map.json turns those into the Glovo VENDOR categories of our store (the 75-category
tree from `glovo-portal.py categories`), with both names beside every id. A dual-species product (Siruk
leaves under Dog and Cat) gets both species' categories. Notes: reference/glovo/portal.md → 2026-11-15.

  python scripts/glovo-categories.py audit [--refresh]
      reads .siruk-cache/glovo/portal-products.json (--refresh re-dumps it from Glovo), the Glovo category
      tree, .siruk-cache/glovo/siruk-export.json (siruk export) and the Siruk category tree; writes
      runs/<today>/glovo-categories-plan.csv and glovo-categories-breakdown.csv, prints the before/after
      product-type breakdown per Glovo category.
  python scripts/glovo-categories.py apply [--plan …csv] [--sku a b] [--limit N] [--include-approximate] [--apply]
      one paced category update per `change` row (and `approximate` with --include-approximate).
      DRY RUN unless --apply. Re-reads Glovo first and skips a row whose categories changed since the audit.
      Backs up the before-state to glovo-categories-before.json next to the plan (first state per SKU is kept),
      logs every result to glovo-categories.csv there.
  python scripts/glovo-categories.py apply --restore [--sku …] [--limit N] [--apply]
      puts the backed-up categories back.

Plan actions: ok · change · approximate (the fix uses a closest-fit Glovo category, look first) ·
ambiguous (no or contradictory Siruk data, SKU collision, a skip-listed SKU) · no-siruk-match.
A category update is its own call: {sku, vendorIdentifier, productInternalId, categoryInternalIds}, never
combined with price or titles (a combined update answers unexpected_error, portal.md 2026-11-12).
"""
import argparse, collections, csv, datetime, importlib.util, json, os, re, subprocess, sys, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location('gp', os.path.join(ROOT, 'scripts', 'glovo-portal.py'))
gp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gp)

MAP = os.path.join(ROOT, 'reference', 'glovo', 'category-map.json')
DUMP = gp.DUMP
GCATS = os.path.join(gp.CACHE, 'vendor-categories.json')
SIRUK_EXPORT = gp.SIRUK_EXPORT
SIRUK_CATS = os.path.join(gp.CACHE, 'siruk-categories-en.json')
MAX_CATS = 5          # the portal form allows up to 5 categories per product
PACE = 1.0            # seconds between Glovo writes
READ_PACE = 0.5       # seconds between Glovo read pages
TODAY = datetime.date.today().isoformat()
PLAN_COLS = ['sku', 'glovo name', 'active', 'siruk sku', 'siruk product id', 'siruk product name', 'siruk leaves',
             'siruk product type', 'current ids', 'current names', 'expected ids', 'expected names', 'action', 'reason']


def jload(p):
    with open(p, encoding='utf-8') as f:
        return json.load(f)


def jsave(p, d):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, 'w', encoding='utf-8') as f:
        json.dump(d, f, ensure_ascii=False, indent=1)


def ids(s):
    return [int(x) for x in str(s).split('+') if x.strip()]


def live_products():
    """All products on our Glovo store, paged with a pause (the read gp.all_products does, paced)."""
    out, page = [], 1
    while True:
        d = gp.gql(gp.Q_PRODUCTS, {'filter': {'vendorIdentifier': gp.vendor(), 'locale': 'hy', 'searchTerm': '',
                                              'active': None, 'brandIds': [], 'categoryIds': []},
                                   'page': {'pageNumber': page, 'pageSize': 100}})['products']
        out += d['items']
        if not d['items'] or len(out) >= d['pagedResult']['itemCount']:
            return out
        page += 1
        time.sleep(READ_PACE)


def glovo_tree(refresh):
    if refresh or not os.path.exists(GCATS):
        gp.TOKEN = gp.TOKEN or gp.load_token()
        d = gp.gql(gp.Q_CATEGORIES, {'filter': {'vendorIdentifier': gp.vendor(), 'locale': 'hy', 'leavesOnly': False},
                                     'page': {'pageNumber': 1, 'pageSize': 500}})['categories']['items']
        jsave(GCATS, {'saved': datetime.datetime.now().isoformat(timespec='seconds'), 'items': d})
    return {int(c['internalId']): c for c in jload(GCATS)['items']}


def siruk_tree():
    """Siruk category id → ('Dog > Supplies > Beds', root id). One GET /categories, cached."""
    if not os.path.exists(SIRUK_CATS):
        out = subprocess.run([sys.executable, '-m', 'siruk', 'api', 'GET', '/categories?per_page=500'], cwd=ROOT,
                             check=True, capture_output=True, env=dict(os.environ, PYTHONUTF8='1')).stdout
        with open(SIRUK_CATS, 'wb') as f:
            f.write(out)
    path = {}

    def walk(n, trail, root):
        t = trail + [n['name']]
        path[n['id']] = (' > '.join(t), root or n['id'])
        for c in n.get('children') or []:
            walk(c, t, root or n['id'])
    for n in jload(SIRUK_CATS)['data']:
        walk(n, [], None)
    return path


def material(row):
    m = re.search(r'Material: ([^,]+)', row.get('options') or '')
    return m.group(1).strip() if m else ''


def expected_for(row, cmap, tree):
    """(ordered category ids, approximate?, notes, problems) for one Siruk variant."""
    exact, approx, alone, notes, problems = [], [], [], [], []
    ov = cmap.get('sku_overrides', {}).get(str(row.get('sku')))
    if ov:
        return list(ov['glovo']), bool(ov.get('approximate')), ['SKU override: ' + ov.get('note', '')], []
    for leaf in row.get('category_ids') or []:
        rule = cmap['leaves'].get(str(leaf))
        if not rule:
            problems.append(f'no mapping for Siruk leaf {leaf} {tree.get(leaf, ("?",))[0]}')
            continue
        bt = (rule.get('by_type') or {}).get(row.get('product_type') or '')
        r = dict(rule, **bt) if bt else rule
        cats = list(r['glovo'])
        if r.get('dish'):
            d = cmap['dish_by_material']
            cats.append(d.get(material(row), d['_default']))
        target = alone if r.get('only_if_alone') else approx if r.get('approximate') else exact
        for c in cats:
            if c not in target:
                target.append(c)
        if r.get('approximate'):
            notes.append(f'{leaf}→{"+".join(map(str, cats))} approximate: {r.get("note", "")}')
    for nr in cmap.get('name_rules', []):
        if set(nr['leaves']) & set(row.get('category_ids') or []) and re.search(nr['regex'], row.get('product_name') or '', re.I):
            exact += [c for c in nr['add'] if c not in exact]
    out = exact + [c for c in approx if c not in exact]
    if not out:
        out = alone
    elif alone:
        notes.append('catch-all ' + '+'.join(map(str, alone)) + ' dropped (product has real categories)')
    used_approx = any(c in approx or c in alone for c in out) and not all(c in exact for c in out)
    if len(out) > MAX_CATS:
        notes.append(f'{len(out)} categories cut to {MAX_CATS}: dropped {"+".join(map(str, out[MAX_CATS:]))}')
        out = out[:MAX_CATS]
    return out, used_approx, notes, problems


def cname(gcats, cmap, c):
    return (gcats.get(c) or {}).get('name') or cmap['glovo_categories'].get(str(c), {}).get('hy') or f'?{c}'


def cmd_audit(a):
    cmap = jload(MAP)
    if a.refresh:
        gp.TOKEN = gp.load_token()
        items = live_products()
        jsave(DUMP, {'saved': datetime.datetime.now().isoformat(timespec='seconds'), 'items': items})
    dump = jload(DUMP)
    print(f'Glovo dump {dump["saved"]}: {len(dump["items"])} products')
    gcats = glovo_tree(a.refresh)
    missing = sorted({c for r in cmap['leaves'].values() for c in r['glovo'] + [x for b in (r.get('by_type') or {}).values()
                      for x in b['glovo']]} - set(gcats))
    if missing:
        sys.exit(f'category-map.json names Glovo categories that are not in our tree: {missing}')
    if not os.path.exists(SIRUK_EXPORT):
        sys.exit(f'no {SIRUK_EXPORT}: python -m siruk export --format json -o {SIRUK_EXPORT}')
    export = jload(SIRUK_EXPORT)
    print(f'Siruk export {datetime.datetime.fromtimestamp(os.path.getmtime(SIRUK_EXPORT)):%Y-%m-%d %H:%M}: {len(export)} variants')
    tree = siruk_tree()
    ours = {str(r['sku']): r for r in export if r.get('sku')}
    live = {i['sku']: i for i in dump['items']}
    # collisions are settled by name; use the export we loaded (gp's own helper would re-export through uv)
    gp.siruk_names = lambda: {s: f"{r['product_name']} {r['variant_name']} {r.get('brand') or ''}" for s, r in ours.items()}
    m, amb = gp.match_skus(live, ours)
    amb = {g: c for g, n, c in amb}
    kinds = {int(k): v['kind'] for k, v in cmap['glovo_categories'].items() if k.isdigit()}

    rows = []
    for g, item in sorted(live.items(), key=lambda kv: kv[1]['name']):
        cur = sorted(int(c) for c in item['categoryIds'])
        base = {'sku': g, 'glovo name': item['name'], 'active': 'on' if item['active'] else 'off',
                'current ids': '+'.join(map(str, cur)), 'current names': ' | '.join(cname(gcats, cmap, c) for c in cur)}
        o = m.get(g)
        if g in cmap.get('skip_skus', {}):
            rows.append(dict(base, **{'siruk sku': o or '', 'action': 'ambiguous', 'reason': 'skip-listed: ' + cmap['skip_skus'][g]}))
            continue
        if g in amb:
            rows.append(dict(base, **{'action': 'ambiguous', 'reason': f'SKU collision, could be Siruk {amb[g]}'}))
            continue
        if not o:
            rows.append(dict(base, **{'action': 'no-siruk-match', 'reason': 'no Siruk variant with this SKU (zeros stripped too)'}))
            continue
        r = ours[o]
        exp, used_approx, notes, problems = expected_for(r, cmap, tree)
        row = dict(base, **{
            'siruk sku': o if o != g else '', 'siruk product id': r['product_id'], 'siruk product name': r['product_name'],
            'siruk leaves': ' | '.join(f'{l} {tree.get(l, ("?",))[0]}' for l in r.get('category_ids') or []),
            'siruk product type': r.get('product_type') or '',
            'expected ids': '+'.join(map(str, sorted(exp))), 'expected names': ' | '.join(cname(gcats, cmap, c) for c in sorted(exp))})
        why = []
        if r.get('is_discontinued'):
            why.append('Siruk product is discontinued')
        allowed = cmap['type_kinds'].get(r.get('product_type') or '')
        if problems or not exp:
            row['action'], why = 'ambiguous', why + (problems or ['Siruk variant has no category leaf'])
        elif allowed and not any(kinds.get(c) in allowed for c in exp):
            row['action'] = 'ambiguous'
            why.append(f'Siruk type {r.get("product_type")} contradicts its leaves (→ {"+".join(kinds.get(c, "?") for c in exp)})')
        elif set(exp) == set(cur):
            row['action'] = 'ok'
        else:
            row['action'] = 'approximate' if used_approx else 'change'
            add, drop = sorted(set(exp) - set(cur)), sorted(set(cur) - set(exp))
            if drop:
                why.append('WRONG: remove ' + ', '.join(f'{c} {cname(gcats, cmap, c)}' for c in drop)
                           + ('; add ' + ', '.join(f'{c} {cname(gcats, cmap, c)}' for c in add) if add else ''))
            else:
                why.append('missing only: add ' + ', '.join(f'{c} {cname(gcats, cmap, c)}' for c in add))
        row['reason'] = '; '.join(why + notes)
        rows.append(row)

    d = os.path.join(ROOT, 'runs', TODAY)
    os.makedirs(d, exist_ok=True)
    plan = a.plan or os.path.join(d, 'glovo-categories-plan.csv')
    with open(plan, 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.DictWriter(f, PLAN_COLS)
        w.writeheader()
        w.writerows({k: r.get(k, '') for k in PLAN_COLS} for r in rows)
    acts = collections.Counter(r['action'] for r in rows)
    wrong = sum(1 for r in rows if r['action'] in ('change', 'approximate') and 'WRONG' in r['reason'])
    print(f'{len(rows)} products: ' + ', '.join(f'{k} {v}' for k, v in acts.most_common())
          + f'  ({wrong} of the change/approximate rows sit in a wrong category; the rest only miss one)')
    print('→', plan)
    breakdown(rows, gcats, cmap, os.path.join(os.path.dirname(plan), 'glovo-categories-breakdown.csv'))


def breakdown(rows, gcats, cmap, out):
    """Per Glovo category: Siruk product types in it now, and after the plan (change + approximate applied)."""
    before, after = collections.defaultdict(collections.Counter), collections.defaultdict(collections.Counter)
    removed = collections.Counter()
    for r in rows:
        t = r.get('siruk product type') or '(no Siruk match)'
        cur = ids(r['current ids'])
        new = ids(r['expected ids']) if r['action'] in ('change', 'approximate') else cur
        for c in cur:
            before[c][t] += 1
            if c not in new:
                removed[c] += 1
        for c in new:
            after[c][t] += 1
    lines = []
    for c in sorted(set(before) | set(after), key=lambda c: -sum(before[c].values())):
        b, n = before[c], after[c]
        fmt = lambda x: ', '.join(f'{k} {v}' for k, v in x.most_common()) or '-'
        lines.append((c, cname(gcats, cmap, c), sum(b.values()), sum(n.values()), removed[c], fmt(b), fmt(n)))
    with open(out, 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.writer(f)
        w.writerow(['glovo id', 'glovo name', 'products now', 'after plan', 'moved out', 'types now', 'types after'])
        w.writerows(lines)
    print('\nGlovo category: products now → after plan (moved out) | types now || types after')
    for c, nm, nb, na, rm, b, n in lines:
        print(f'{c:>6} {nm[:34]:<34} {nb:>4} → {na:>4} (-{rm:<3}) | {b} || {n}')
    print('→', out)


def plan_rows(path):
    with open(path, encoding='utf-8-sig') as f:
        return list(csv.DictReader(f))


def cmd_apply(a):
    plan = a.plan or os.path.join(ROOT, 'runs', TODAY, 'glovo-categories-plan.csv')
    d = os.path.dirname(os.path.abspath(plan))
    backup_p, log_p = os.path.join(d, 'glovo-categories-before.json'), os.path.join(d, 'glovo-categories.csv')
    backup = jload(backup_p) if os.path.exists(backup_p) else {}
    if a.restore and not backup:
        sys.exit(f'nothing to restore: no {backup_p}')
    gp.TOKEN = gp.load_token()
    print('reading the live store …')
    live = {i['sku']: i for i in live_products()}
    todo, skipped = [], []
    if a.restore:
        if not backup:
            sys.exit(f'nothing to restore: no {backup_p}')
        for sku, b in sorted(backup.items()):
            if a.sku and sku not in a.sku:
                continue
            i = live.get(sku)
            if not i:
                skipped.append((sku, 'not on Glovo any more')); continue
            if sorted(map(int, i['categoryIds'])) == sorted(b['categoryIds']):
                skipped.append((sku, 'already as backed up')); continue
            todo.append((sku, i, sorted(map(int, i['categoryIds'])), sorted(b['categoryIds']), 'restore'))
    else:
        want = {'change'} | ({'approximate'} if a.include_approximate else set())
        for r in plan_rows(plan):
            if r['action'] not in want or (a.sku and r['sku'] not in a.sku):
                continue
            i = live.get(r['sku'])
            if not i:
                skipped.append((r['sku'], 'not on Glovo any more')); continue
            now, cur, exp = sorted(map(int, i['categoryIds'])), sorted(ids(r['current ids'])), sorted(ids(r['expected ids']))
            if now == exp:
                skipped.append((r['sku'], 'already as planned')); continue
            if now != cur:
                skipped.append((r['sku'], f'changed since the audit ({r["current ids"]} → {"+".join(map(str, now))}): re-run audit')); continue
            todo.append((r['sku'], i, now, exp, r['action']))
    if a.limit:
        todo = todo[:a.limit]
    print(f'{len(todo)} category updates' + (' (restore)' if a.restore else '') + ('' if a.apply else '  (DRY RUN — add --apply)'))
    for sku, i, now, exp, act in todo[:25]:
        print(f'  {sku:>15}  {"+".join(map(str, now)):<12} → {"+".join(map(str, exp)):<18} {act:<11} {i["name"][:55]}')
    if len(todo) > 25:
        print(f'  … {len(todo) - 25} more')
    for s in skipped[:30]:
        print('  skip', *s)
    if not a.apply:
        return
    if not a.restore:
        for sku, i, now, exp, act in todo:          # keep the FIRST before-state we ever saw for a SKU
            backup.setdefault(sku, {'internalId': i['internalId'], 'name': i['name'], 'categoryIds': now,
                                    'categoryNames': i['categoryNames'],
                                    'saved': datetime.datetime.now().isoformat(timespec='seconds')})
        jsave(backup_p, backup)
        print('before-state →', backup_p)
    new = not os.path.exists(log_p)
    ok = failed = 0
    with open(log_p, 'a', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        if new:
            w.writerow(['time', 'mode', 'sku', 'name', 'before', 'sent', 'answer', 'status', 'validationErrors'])
        for n, (sku, i, now, exp, act) in enumerate(todo, 1):
            v = {'productUpdate': {'sku': sku, 'vendorIdentifier': gp.vendor(), 'productInternalId': int(i['internalId']),
                                   'categoryInternalIds': exp}}
            status, errs, got = 'ok', '', ''
            try:
                r = gp.gql(gp.M_UPDATE.replace('validationErrors', 'categoryInternalIds validationErrors'), v)['product']
                got = '+'.join(map(str, sorted(r.get('categoryInternalIds') or [])))
                if r.get('validationErrors'):
                    status, errs = 'refused', json.dumps(r['validationErrors'], ensure_ascii=False)
                elif got and got != '+'.join(map(str, exp)):
                    status = 'answer differs'
            except Exception as e:
                status, errs = 'error', str(e)[:300]
            ok += status == 'ok'
            failed += status != 'ok'
            w.writerow([datetime.datetime.now().isoformat(timespec='seconds'), act, sku, i['name'],
                        '+'.join(map(str, now)), '+'.join(map(str, exp)), got, status, errs])
            f.flush()
            if status != 'ok':
                print('  FAIL', sku, status, errs[:150])
            if n % 50 == 0:
                print(f'  {n}/{len(todo)}')
            time.sleep(PACE)
    print(f'{ok} updated, {failed} failed → {log_p}')
    print('re-run audit (with --refresh): the updated rows should now be ok')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    p = sub.add_parser('audit')
    p.add_argument('--refresh', action='store_true', help='re-read the store and the category tree from Glovo first')
    p.add_argument('--plan', help='where to write the plan CSV (default runs/<today>/glovo-categories-plan.csv)')
    p.set_defaults(f=cmd_audit)
    p = sub.add_parser('apply')
    p.add_argument('--plan')
    p.add_argument('--sku', nargs='*')
    p.add_argument('--limit', type=int)
    p.add_argument('--include-approximate', action='store_true')
    p.add_argument('--restore', action='store_true', help='put the backed-up categories back')
    p.add_argument('--apply', action='store_true')
    p.set_defaults(f=cmd_apply)
    a = ap.parse_args()
    a.f(a)


if __name__ == '__main__':
    main()
