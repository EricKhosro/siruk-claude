#!/usr/bin/env python3
"""Fold second-pass matches (a by-hand / agent search of the rival items the first
pass left over) into <slug>-matches.json and <slug>-verdicts.json.

  .siruk-cache/yandex/pass2-*.json   [{"zid": rival item id, "vid": Siruk variant id, "note": "..."}]

A pair is skipped when its variant already has a "same" match or its rival item is
already used by one. Backs both files up to *.pre-pass2.json first (once).

  python3 scripts/yandex-merge-pass2.py zoovetam
"""
import glob, json, os, shutil, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, '.siruk-cache', 'yandex')


def main():
    slug = sys.argv[1] if len(sys.argv) > 1 else 'zoovetam'
    mp, vp = os.path.join(CACHE, f'{slug}-matches.json'), os.path.join(CACHE, f'{slug}-verdicts.json')
    for p in (mp, vp):
        b = p.replace('.json', '.pre-pass2.json')
        if not os.path.exists(b):
            shutil.copy(p, b)
    data, verdicts = json.load(open(mp, encoding='utf-8')), json.load(open(vp, encoding='utf-8'))
    items = {z['id']: z for z in json.load(open(os.path.join(CACHE, f'{slug}-items.json'), encoding='utf-8'))}
    by_vid = {m['variant_id']: m for m in data['matches']}
    same = lambda m: verdicts.get(str(m['variant_id']), {}).get('verdict') == 'same'
    used = {m['rival_id'] for m in data['matches'] if m.get('rival_name') and same(m)}

    added, skipped = 0, []
    for f in sorted(glob.glob(os.path.join(CACHE, 'pass2-*.json'))):
        if f.endswith('pass2-input.json'):
            continue
        for p in json.load(open(f, encoding='utf-8')):
            m, z = by_vid.get(int(p['vid'])), items.get(p['zid'])
            if not m or not z or same(m) or p['zid'] in used:
                skipped.append((os.path.basename(f), p['zid'], p['vid']))
                continue
            m.update({'rival_id': z['id'], 'rival_name': z['name'], 'rival_price': z['price'],
                      'rival_promo': z['promo_price'], 'rival_category': ' | '.join(z['categories']),
                      'score': None, 'size_ok': None, 'confidence': 'pass 2'})
            verdicts[str(m['variant_id'])] = {'verdict': 'same', 'note': 'pass 2: ' + p.get('note', '')}
            used.add(z['id'])
            added += 1
    data['rival_unmatched'] = [z for z in data['rival_unmatched'] if z['id'] not in used]
    json.dump(data, open(mp, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    json.dump(verdicts, open(vp, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'added {added} matches; skipped {len(skipped)}: {skipped[:10]}')
    print(f'"same" matches now: {sum(1 for v in verdicts.values() if v["verdict"] == "same")}')


if __name__ == '__main__':
    main()
