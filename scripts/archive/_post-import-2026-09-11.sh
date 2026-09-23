#!/usr/bin/env bash
# Waits for the three plan imports, then runs every end-of-run check and writes the report.
cd "$(dirname "$0")/.."
RUN=runs/2026-09-11
while ! grep -q "=== SMALL DONE" $RUN/import-small.log 2>/dev/null; do sleep 60; done
ids=$(python3 -c "
import json
ids=[]
for f in ('trixie','monge','small'):
    s=json.load(open('.siruk-cache/%s-plan.state.json'%f)); ids+=[v['id'] for v in s['done'].values()]
print(','.join(str(i) for i in sorted(set(ids))))")
echo "=== POST $(date) — $(echo $ids | tr ',' '\n' | wc -l | tr -d ' ') products"
echo "$ids" > $RUN/new-product-ids.txt
echo "--- enrich images (every source, article-keyed)"; scripts/enrich-images.py --build > $RUN/image-build.txt 2>&1; tail -3 $RUN/image-build.txt
scripts/enrich-images.py --apply > $RUN/image-apply.txt 2>&1; tail -3 $RUN/image-apply.txt
echo "--- backfill translations"; scripts/backfill-translations.py --only "$ids" > $RUN/backfill.txt 2>&1; tail -5 $RUN/backfill.txt
echo "--- verify translations"; scripts/verify-translations.py > $RUN/verify-translations.txt 2>&1; head -5 $RUN/verify-translations.txt
echo "--- verify media"; scripts/verify-media.sh $(echo $ids | tr ',' ' ') > $RUN/verify-media.txt 2>&1; tail -5 $RUN/verify-media.txt
echo "--- feature image audit"; scripts/feature-image.py --only "$ids" --sheet --out $RUN > $RUN/feature-audit.txt 2>&1; tail -8 $RUN/feature-audit.txt
echo "--- hafo price check"; scripts/check-hafo-prices.py --only "$ids" > $RUN/price-check.txt 2>&1; tail -5 $RUN/price-check.txt
echo "--- report"; scripts/_write-report-2026-09-11.py
echo "=== POST DONE $(date)"
