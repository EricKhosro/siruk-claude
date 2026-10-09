# Sourcing a correct photo — instructions (no API writes; no google-lens.py)

Production pet shop; warehouse staff pick by the photo. Each item in your list (`need-photo.json`
rows given to you) needs a photo that shows EXACTLY that item: brand, line, flavour/recipe,
lifestage, colour, and the PACK SIZE / count printed or otherwise unambiguous.

Project rules: /Users/conceptmacmini01/Documents/Projects/Siruk-claude/CLAUDE.md rule 7 and
reference/image-sources.md (read "Keyed is necessary, not sufficient", "One gallery per size",
"Barcode lookup", "Fallback sites"), reference/brand-sites.md for the brand's row, and
scripts/README.md for the lookup scripts (trixie-image.sh, trixie-es.py, trixiecz-index.py,
tiierisch-index.py, barcode-lookup.py, 4lapy-lookup.py, ean-image-lookup.py, zoovet-lookup.py,
nemo-lookup.py, image-search.py / web-image-lookup.py). WebSearch / WebFetch / curl are fine.
Do NOT run scripts/google-lens.py (one headed browser — the lead runs it). Brand sites are
read-only. No API calls to Siruk.

## Accept a photo only when
- it is keyed (our article / EAN in the file name or on the page, or the brand's own page for that
  exact recipe+size), AND
- you downloaded it and LOOKED at it (Read tool): the pack visibly shows the right flavour / colour
  / size (read the printed weight!), clean, unwatermarked, product alone for a lead, ≥ 500 px.
- Shops reuse one stock photo for every flavour/size — a page printing our EAN can still show the
  wrong pack. Reject it.
If nothing qualifies, say so — never pick a near-miss. A photo of the item that does not print the
size is acceptable only if no size-printed one exists AND the shape/format unambiguously matches
that size (say why).

## Output
Save accepted files to `found/<sku>/<n>-<short-source>.<ext>` (n = gallery order, 1 = lead) and
write `found/<group>.json`:
```json
[{"product_id":"964","sku":"5431112","status":"found|not-found",
  "images":[{"file":"found/5431112/1-zooplus.jpg","url":"https://…","source":"zooplus.de",
             "keyed_by":"EAN 0064992543112 on page","seen":"Acana Ranchlands bag, NET WEIGHT 11.4 kg printed"}],
  "tried":"brand site (only 6 kg), barcode-lookup, 4lapy …", "lens_hint":"best query for Google/Lens if not found"}]
```
Finish with: found / not-found counts and the not-found list with your best Google/Lens query each.
