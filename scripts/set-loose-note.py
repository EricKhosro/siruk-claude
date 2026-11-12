#!/usr/bin/env python3
"""Put the "sold by weight" note at the top of every loose variant's text (user 2026-11-10).

Loose variant = SKU ending -KG (1 kg) or -100G (100 g). Siruk: about_this_item in en/ru/hy,
only on the loose variant (its bag keeps its text). Glovo: description hy_AM = note + the
sheet's description, en_AM = note (en descriptions were empty).

  python3 scripts/set-loose-note.py siruk [--apply] [--pid N …]
  python3 scripts/set-loose-note.py glovo [--apply] [--sku S …]

Skips a text that already holds the note. Dry run unless --apply.
"""
import argparse, importlib.util, json, os, sys, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

NOTE = {
    'en': 'Sold by weight: we open the original bag, weigh out exactly the amount you ordered, '
          'pack it in our own packaging and send it to you.',
    'ru': 'Продаётся на вес: мы вскрываем оригинальную упаковку, отвешиваем ровно столько, '
          'сколько вы заказали, упаковываем в нашу упаковку и отправляем вам.',
    'hy': 'Կշռով վաճառք․ մենք բացում ենք գործարանային փաթեթը, կշռում ենք ճիշտ այնքան, '
          'որքան պատվիրել եք, լցնում ենք մեր փաթեթավորման մեջ և ուղարկում Ձեզ։',
}
LOOSE = ('-KG', '-100G')


def with_note(text, lang):
    text = text or ''
    note = NOTE[lang]
    if note in text:
        return None
    if not text.strip():
        return note
    if text.lstrip().startswith('<'):
        return f'<p>{note}</p>' + text
    return note + '\n' + text


def cmd_siruk(a):
    from siruk import products, translations
    from siruk import client as C
    if a.pid:
        pids = a.pid
    else:
        out = os.path.join(ROOT, '.siruk-cache', 'loose-export.json')
        os.system(f'cd "{ROOT}" && uv run --no-sync siruk export -q --format json -o "{out}" >/dev/null')
        pids = sorted({r['product_id'] for r in json.load(open(out)) if r['sku'].endswith(LOOSE)})
    print(f'{len(pids)} products', file=sys.stderr)
    done = skipped = 0
    for pid in pids:
        got = {l: (C.default().get(f'/products/{pid}', lang=l) or {})['data'] for l in ('en', 'ru', 'hy')}
        loose = [v['sku'] for v in got['en']['variants'] if v['sku'].endswith(LOOSE)]
        for lang in ('en', 'ru', 'hy'):
            vs = {v['sku']: v for v in got[lang]['variants']}
            ens = {v['sku']: v for v in got['en']['variants']}
            patch = {}
            for sku in loose:
                cur = (vs.get(sku) or {}).get('about_this_item') or ''
                if lang != 'en' and not cur:
                    cur = ens[sku].get('about_this_item') or ''   # the locale has nothing yet
                new = with_note(cur, lang)
                if new is None:
                    skipped += 1
                    continue
                patch[sku] = new
            if not patch:
                continue
            print(f'{pid} [{lang}] ' + ', '.join(patch), file=sys.stderr)
            if not a.apply:
                continue
            if lang == 'en':
                for sku, new in patch.items():
                    products.update_variant(pid, sku, {'about_this_item': new})
            else:
                translations.set_translation(pid, lang, {'variants': {s: {'about_this_item': t} for s, t in patch.items()}})
            done += len(patch)
    print(f'{"written" if a.apply else "would write"} — skipped (already there) {skipped}, written {done}')


def cmd_glovo(a):
    spec = importlib.util.spec_from_file_location('gt', os.path.join(ROOT, 'scripts', 'glovo-titles.py'))
    gt = importlib.util.module_from_spec(spec); spec.loader.exec_module(gt)
    gp = gt.gp
    gp.TOKEN = gp.load_token()
    import openpyxl
    descs = {}
    for r in openpyxl.load_workbook(gp.SHEET, read_only=True).worksheets[0].iter_rows(min_row=3, values_only=True):
        if r[0] is not None:
            descs[str(r[0])] = r[4] or ''
    gt.preload()
    skus = a.sku or sorted(s for s in gt.CACHE['hy_AM'] if s.endswith(LOOSE))
    print(f'{len(skus)} loose products on Glovo', file=sys.stderr)
    rows, fails = [], 0
    for sku in skus:
        hy, en = gt.CACHE['hy_AM'].get(sku), gt.CACHE['en_AM'].get(sku)
        old = descs.get(sku, '')
        if NOTE['hy'] in old:
            continue
        new_hy = NOTE['hy'] + '\n\n' + old if old else NOTE['hy']
        T = [{'locale': 'hy_AM', 'value': hy['name']}, {'locale': 'en_AM', 'value': en['name']}]
        orig = {'active': hy['active'], 'categoryInternalIds': hy['categoryIds'],
                'descriptions': [{'locale': 'hy_AM', 'value': old}] if old else [],
                'images': hy['imageUrls'] or [], 'maximumSalesQuantity': hy['maximumSalesQuantity'] or 0,
                'price': hy['price'], 'sku': sku, 'titles': T}
        upd = {'sku': sku, 'vendorIdentifier': gp.vendor(), 'productInternalId': hy['internalId'],
               'descriptions': [{'locale': 'hy_AM', 'value': new_hy}, {'locale': 'en_AM', 'value': NOTE['en']}],
               'original': orig}
        status = 'dry run'
        if a.apply:
            try:
                r = gp.gql('mutation($u:ProductUpdate!){product(productUpdate:$u){validationErrors{code message}}}',
                           {'u': upd})['product']
                errs = (r or {}).get('validationErrors')
                status = '; '.join(f"{e['code']}: {e['message'][:160]}" for e in errs) if errs else 'ok'
            except Exception as e:
                status = f'error: {e}'[:300]
            time.sleep(gp.PACE)
        fails += status not in ('ok', 'dry run')
        print(sku, status, file=sys.stderr)
        rows.append([sku, hy['name'], status])
    if a.apply:
        gp.runlog('glovo-loose-note', ['sku', 'title_hy', 'status'], rows)
    print(f'{len(rows)} {"sent" if a.apply else "to send"}, {fails} failed')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    p = sub.add_parser('siruk'); p.add_argument('--apply', action='store_true'); p.add_argument('--pid', type=int, nargs='*')
    p.set_defaults(f=cmd_siruk)
    p = sub.add_parser('glovo'); p.add_argument('--apply', action='store_true'); p.add_argument('--sku', nargs='*')
    p.set_defaults(f=cmd_glovo)
    a = ap.parse_args()
    a.f(a)


if __name__ == '__main__':
    main()
