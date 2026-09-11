#!/usr/bin/env bash
# Finish the 2026-09-11 import: brand-site images only (no hafo — rule 7a),
# then every end-of-run check, the CSVs and the report.
cd "$(dirname "$0")/.."
RUN=runs/2026-09-11
export SIRUK_MEDIA_DELAY=0.5 SIRUK_CHUNK_PAUSE=6
echo "=== IMAGES $(date)"
scripts/enrich-images.py --apply >> $RUN/image-apply.log 2>&1
unset SIRUK_MEDIA_DELAY SIRUK_CHUNK_PAUSE
ids=$(python3 -c "
import json
ids=[]
for f in ('trixie','monge','small'):
    s=json.load(open('.siruk-cache/%s-plan.state.json'%f)); ids+=[v['id'] for v in s['done'].values()]
print(','.join(str(i) for i in sorted(set(ids))))")
echo "$ids" > $RUN/new-product-ids.txt
echo "=== POST $(date) — $(echo $ids | tr ',' ' ' | wc -w | tr -d ' ') products"
echo "--- backfill translations"; scripts/backfill-translations.py --only "$ids" > $RUN/backfill.txt 2>&1; tail -4 $RUN/backfill.txt
echo "--- verify translations"; scripts/verify-translations.py --only "$ids" > $RUN/verify-translations.txt 2>&1; head -6 $RUN/verify-translations.txt
echo "--- verify media"; scripts/verify-media.sh $(echo $ids | tr ',' ' ') > $RUN/verify-media.txt 2>&1; tail -6 $RUN/verify-media.txt
echo "--- feature image audit"; scripts/feature-image.py --only "$ids" --sheet --out $RUN > $RUN/feature-audit.txt 2>&1; tail -8 $RUN/feature-audit.txt
echo "--- hafo price check"; scripts/check-hafo-prices.py --only "$ids" > $RUN/price-check.txt 2>&1; tail -6 $RUN/price-check.txt
echo "--- csvs + report"; scripts/_write-run-csvs.py 2026-09-11 small-plan.json; scripts/_write-report-2026-09-11.py
echo "=== FINISH DONE $(date)"
