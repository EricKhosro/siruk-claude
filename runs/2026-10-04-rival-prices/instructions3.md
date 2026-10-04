# Pass 3 — zoovet.am + nemo.am price for items siruk.am sells at hafo.am's price

READ-ONLY on every site: never add to cart, log in, or submit a form.
Work in `W:\work\concept-studio\siruk-claude\runs\2026-10-04-rival-prices`; set `PYTHONUTF8=1` for every python call.

Helper (`python rival.py` prints its docstring):
- `python rival.py zoovet "<terms>"`: zoovet.am. Searches today's brand lists plus zoovet's live search. Names are Russian/English. All terms must match; `a|b` means any-of.
- `python rival.py zoovet-page <url>`: a zoovet product page. Returns the name, price, OPTIONS (size → price, e.g. 'На развес, 1 кг' → 5700, 'Упак (8 кг)' → 43500) and stock.
- `python rival.py nemo "<terms>"`: nemo.am. Searches today's brand lists plus nemo's live search. Names are Armenian/English, often without the brand.
- `python rival.py nemo-page <url>`: a nemo product page. Returns the name, price, old price, stock and manufacturer.
- `python rival.py hafo-sku "<text>"`: hafo rows. For reference only: hafo's own Armenian name and the barcode.

**Context.** Each variant in your batch file (`batches3/batch-NN.json`) is sold on siruk.am and on hafo.am. It was matched to hafo by article code; `hafo_match` gives hafo's Armenian row name, which describes the exact item. For each variant we need the SAME item's current price on zoovet.am AND on nemo.am.

**Identity.** "The same item" means EVERY axis matches:
- brand;
- product line;
- lifestage / breed size;
- flavour / recipe / texture (gravy vs jelly vs pâté vs chunks);
- pack size and count: 85 g ≠ 100 g, 400 g ≠ 415 g, a 4 × 15 g multipack ≠ one 15 g, 7 pcs ≠ 1;
- for toys, accessories, collars and pipettes: size, colour, length, weight band ("for dogs 10–20 kg") and model.

A same-line item in another size, flavour, colour or weight band is NOT a match. Mark it found=false and name the nearest candidate in the evidence.

zoovet sometimes recycles a URL slug from another product, so trust the page's name and description, not the slug. nemo names often omit the brand, so open the page and check the manufacturer and description.

**Kinds.** A kind "1 kg" variant is 1 kg of the bag (`bag_label`) sold loose. A rival matches it only if it sells that exact food per 1 kg / loose:
- zoovet: the option 'На развес, 1 кг', or a listing '… на развес 1 кг';
- nemo: a listing '(կիլոգրամով)' or '1 կգ' of that exact line.

**Price.**
- Take the price for our exact pack/option as the rival's PRODUCT PAGE shows it today. Confirm it on the page; on zoovet, pick the option for our size.
- If the page shows a discount: `price` = what customers pay now, `old_price` = the struck-through price.
- An out-of-stock listing still counts (`in_stock`=false).

**Search.** `candidate_hints` are HINTS ONLY and often wrong. Always search yourself as well, with several spellings:
- the English line name;
- Russian;
- Armenian words from `register_name_hy` and `hafo_match.row_name`;
- the size, e.g. `85|85 г|85գ`;
- the article number / EAN;
- the brand's list.

**Output.** Write the file you are told to write: JSON `{"results":[...]}`, one entry per variant in the batch (all of them, same `variant_id`s):

```json
{"variant_id": 123,
 "zoovet": {"found": true, "url": "...", "price": 1850, "old_price": null, "name": "...", "in_stock": true, "evidence": "why every axis matches / searches tried"},
 "nemo":   {"found": false, "evidence": "searches tried; nearest candidate"},
 "confidence": "high|medium|low"}
```

Then reply with a single line: the file path and counts (found zoovet / found nemo).
