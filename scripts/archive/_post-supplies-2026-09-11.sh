#!/usr/bin/env bash
# Waits for the Supplies import (trixie-plan re-run + mrfresh-plan), then runs
# the end-of-run checks over just the products those two runs created.
cd "$(dirname "$0")/.."
RUN=runs/2026-09-11
while ! grep -q "=== MRFRESH DONE" $RUN/import-mrfresh.log 2>/dev/null; do sleep 60; done

ids=$(python3 -c "
import json
new=set()
for f,cats in (('trixie',{69,70,71,72,73,74,76,77,78,79,81}),('mrfresh',None)):
    plan=json.load(open('.siruk-cache/%s-plan.json'%f))
    state=json.load(open('.siruk-cache/%s-plan.state.json'%f))
    slugs={p['slug'] for p in plan['products'] if cats is None or p['category_ids'][0] in cats}
    new|={v['id'] for s,v in state['done'].items() if s in slugs}
print(','.join(str(i) for i in sorted(new)))")
n=$(echo "$ids" | tr ',' '\n' | wc -l | tr -d ' ')
echo "=== POST $(date) — $n products in the new Supplies leaves"
echo "$ids" > $RUN/supplies-product-ids.txt

echo "--- backfill translations"; scripts/backfill-translations.py --only "$ids" > $RUN/supplies-backfill.txt 2>&1; tail -5 $RUN/supplies-backfill.txt
echo "--- verify translations"; scripts/verify-translations.py > $RUN/supplies-verify-translations.txt 2>&1; head -6 $RUN/supplies-verify-translations.txt
echo "--- verify media"; scripts/verify-media.sh $(echo "$ids" | tr ',' ' ') > $RUN/supplies-verify-media.txt 2>&1; tail -5 $RUN/supplies-verify-media.txt
echo "--- feature image audit"; scripts/feature-image.py --only "$ids" > $RUN/supplies-feature-audit.txt 2>&1; tail -8 $RUN/supplies-feature-audit.txt
echo "--- hafo price check"; scripts/check-hafo-prices.py --only "$ids" > $RUN/supplies-price-check.txt 2>&1; tail -6 $RUN/supplies-price-check.txt
echo "=== POST DONE $(date)"
