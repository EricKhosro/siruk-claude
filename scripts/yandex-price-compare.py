#!/usr/bin/env python3
"""Match a rival's Yandex Eats items to Siruk variants and suggest a Yandex price.

Inputs (both cached):
  .siruk-cache/yandex/<slug>-items.json   scripts/yandex-shop-scrape.py <slug>
  .siruk-cache/yandex/siruk-ru.json       siruk export --lang ru --format json -o …

A rival item matches a Siruk variant when the brand agrees, the pack size
agrees (when both state one; a 1 kg loose rival item only meets our -KG
variant) and the Russian name words overlap. Each rival item goes to at most
one variant, best score first. Matches are candidates for a human check, not
identities (reference/zoovet.md): the confidence column says how sure.

  python3 scripts/yandex-price-compare.py zoovetam   → .siruk-cache/yandex/<slug>-matches.json
"""
import json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, '.siruk-cache', 'yandex')

BRAND_FORMS = {
    'Royal Canin': ['royal canin', 'роял канин'], 'Derevenskie Lakomstva': ['деревенские лакомства', 'derevenskie'],
    'Club 4 Paws': ['club 4 paws', 'club4paws', '4 лапы', 'клуб 4'], 'Versele-Laga': ['versele', 'версел'],
    'Iv San Bernard': ['iv san bernard', 'san bernard'], 'Mr. Fresh': ['mr.fresh', 'mr. fresh', 'mr fresh', 'мистер фреш'],
    'Ferma Kota Fedora': ['ферма кота', 'ferma kota'], 'Rolf Club': ['rolf', 'рольф'], 'Myau': ['мяу', 'myau'],
    'Mnyams': ['мнямс', 'mnyams'], 'Gav!': ['гав!', 'gav!'], 'Pro Plan': ['pro plan', 'proplan', 'про план'],
    'Eco-Premium': ['eco-premium', 'eco premium', 'эко премиум'], 'Special Dog': ['special dog'],
    'Trixie': ['trixie', 'трикси'], 'Monge': ['monge', 'монже'], 'Gemon': ['gemon', 'гемон'], 'Beaphar': ['beaphar', 'беафар'],
    'Acana': ['acana', 'акана'], 'Orijen': ['orijen', 'ориджен'], '8in1': ['8in1', '8 in 1'], 'Felix': ['felix', 'феликс'],
    'Simba': ['simba', 'симба'], 'GoSi': ['gosi', 'госи'], 'Kaskad': ['kaskad', 'каскад'], 'Inspector': ['inspector', 'инспектор'],
    'Gelmintal': ['gelmintal', 'гельминтал'], 'Insectal': ['insectal', 'инсектал'], 'flexi': ['flexi', 'флекси'],
    'Cliny': ['cliny', 'клини'], 'Lechat': ['lechat', 'лешат'], 'Comfy': ['comfy', 'комфи'], 'Pchelodar': ['пчелодар', 'pchelodar'],
    'Kotoffey': ['kotoffey', 'котофей'], 'INABA': ['inaba', 'инаба'], 'Petmil': ['petmil'], 'KorMell': ['kormell', 'кормел'],
    'Ok-Lock': ['ok-lock'], 'Mooor': ['mooor'], 'My Love': ['my love'], 'Justin': ['justin'], 'Inteko': ['inteko', 'интеко'],
    'Dogman': ['dogman', 'догман'],
}
UNITS = {'кг': 1000, 'kg': 1000, 'կգ': 1000, 'г': 1, 'гр': 1, 'g': 1, 'գ': 1,
         'л': 1000, 'l': 1000, 'լ': 1000, 'мл': 1, 'ml': 1, 'մլ': 1}
SIZE_RE = re.compile(r'(\d+(?:[.,]\d+)?)\s*(кг|kg|կգ|гр|г|g|գ|мл|ml|մլ|л|l|լ)(?![a-zа-яա-ֆ])', re.I)
STOP = set('для с и в на со из по от без к у the and with for of a in'.split())
LOOSE = re.compile(r'развес|քաշով', re.I)


def sizes(text):
    return {round(float(n.replace(',', '.')) * UNITS[u.lower()]) for n, u in SIZE_RE.findall(text or '')}


def words(text, drop):
    t = re.sub(r'[#№]\s*\d+', ' ', (text or '').lower().replace('ё', 'е'))
    t = SIZE_RE.sub(' ', t)
    out = set()
    for w in re.findall(r'[a-zа-яա-ֆ]+|\d+', t):
        if w in STOP or len(w) < 2 or w in drop:
            continue
        out.add(w[:5])
    return out


def main():
    slug = sys.argv[1] if len(sys.argv) > 1 else 'zoovetam'
    rival = json.load(open(os.path.join(CACHE, f'{slug}-items.json'), encoding='utf-8'))
    ours = json.load(open(os.path.join(CACHE, 'siruk-ru.json'), encoding='utf-8'))
    en = {r['variant_id']: r for r in json.load(open(os.path.join(CACHE, 'siruk-en.json'), encoding='utf-8'))}

    for z in rival:
        low = z['name'].lower()
        z['brand'] = next((b for b, forms in BRAND_FORMS.items() if any(f in low for f in forms)), None)
        w = z['weight'] if z['weight'] not in ('1 գ', '1 g') else ''
        z['sizes'] = sizes(z['name']) | sizes(w)
        z['loose'] = bool(LOOSE.search(z['name'])) or (bool(z.get('price_per_kg')) and z['sizes'] == {1000})
        drop = {f[:5] for f in BRAND_FORMS.get(z['brand'], []) for f in f.split()}
        z['words'] = words(z['name'], drop)

    pairs = []
    for i, s in enumerate(ours):
        loose = s['sku'].upper().endswith(('-KG', '-100G'))
        total = (s['content'] or 0) * (s['pack_count'] or 1)
        ssz = {round(s['content'])} if s['content'] else set()
        if total:
            ssz.add(round(total))
        ssz |= sizes(s['variant_name']) | sizes(s['size'])
        drop = {f[:5] for f in BRAND_FORMS.get(s['brand'], [s['brand'].lower()]) for f in f.split()}
        e = en.get(s['variant_id'], {})
        opts = ' '.join(re.sub(r'^[^:]*:', '', o) for o in re.split(r',\s*(?=[^,:]+:)', (s['options'] or '') + ', ' + (e.get('options') or '')))
        sw = words(' '.join([s['product_name'], e.get('product_name', ''), opts, s['variant_name'] or '',
                             s['categories'] or '', e.get('categories') or '', s['product_type'] or '']), drop)
        if not sw:
            continue
        for j, z in enumerate(rival):
            if z['brand'] != s['brand']:
                continue
            if loose != z['loose']:
                continue
            size_ok = None
            if ssz and z['sizes']:
                size_ok = any(abs(a - b) <= max(2, 0.02 * a) for a in ssz for b in z['sizes'])
                if not size_ok:
                    continue
            if not z['words']:
                continue
            score = len(sw & z['words']) / len(z['words'])     # how much of the rival's wording we cover
            if score >= 0.34:
                pairs.append((score + (0.15 if size_ok else 0), score, size_ok, i, j))

    pairs.sort(reverse=True)
    used_s, used_z, match = set(), set(), {}
    for rank, score, size_ok, i, j in pairs:
        if i in used_s or j in used_z:
            continue
        used_s.add(i); used_z.add(j)
        conf = 'high' if score >= 0.6 and size_ok else 'medium' if score >= 0.45 and size_ok is not False else 'low'
        match[i] = {'rival_id': rival[j]['id'], 'rival_name': rival[j]['name'], 'rival_price': rival[j]['price'],
                    'rival_promo': rival[j]['promo_price'], 'rival_category': ' | '.join(rival[j]['categories']),
                    'score': round(score, 2), 'size_ok': size_ok, 'confidence': conf}

    out = []
    for i, s in enumerate(ours):
        out.append({**{k: s[k] for k in ('product_id', 'variant_id', 'sku', 'brand', 'product_name', 'variant_name', 'options',
                                          'categories', 'product_type', 'barcode', 'price', 'cost_price', 'stock_status',
                                          'is_purchasable', 'is_discontinued')}, **match.get(i, {})})
    unmatched = [z for j, z in enumerate(rival) if j not in used_z]
    json.dump({'matches': out, 'rival_unmatched': [{k: z[k] for k in ('id', 'name', 'price', 'promo_price', 'weight', 'categories', 'brand')}
                                                     for z in unmatched]},
              open(os.path.join(CACHE, f'{slug}-matches.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    from collections import Counter
    print(Counter(m.get('confidence', 'none') for m in out), f'rival items unmatched: {len(unmatched)}',
          f'rival items with a Siruk brand: {sum(1 for z in rival if z["brand"])}/{len(rival)}')


if __name__ == '__main__':
    main()
