# Worker brief — turn prepared rows into cards

You fill **cards** for a batch of rows of one brand + type. You never write to
the admin: no `create-product.sh`, `add-variant.sh`, `upload-media.sh`,
`api.sh PUT/POST`, `set-translation.py`. Price, route, pack size and brand are
already decided in `rows.jsonl` — do not re-derive or change them.

Your prompt gives: the run folder `<run>` and the codes. **`rows.jsonl` wins over any
note in the prompt** — the prompt's hints are paraphrase; the row's CSV name is the fact.

**Keep your context small**: never print a whole page. Save it (`curl … > .siruk-cache/<code>.html`),
then grep/slice what you need (≤ 40 lines per look). WebFetch with a narrow prompt is fine.

**Identity**: a row with `hafo.confirmed: true` is already identified by its article code — you
only need images and texts for it, not a second identity proof. hafo's own text
(`hafo.title_hy`, `variant_name_hy`, and `content_html` in `<run>/hafo.json`) is a valid,
Armenian source. If nothing better exists, hafo's photo alone is acceptable (the validator WARNs,
the row goes on needs-image.csv) — do not hold a hafo-confirmed row just for want of photos.

## Read (only this)
1. Your rows: `grep -E '"code": "(C1|C2)"' <run>/rows.jsonl`
2. `reference/card-schema.md` — the exact card format.
3. The type entry in `reference/types.json`, and in `.claude/skills/<type>/SKILL.md`
   the sections on filing, attributes and variant axes.
4. The allowed values — only your family's attributes:
   `python3 -c "import json;m=json.load(open('reference/attribute-values.json'));f=json.load(open('.siruk-cache/live-ids.json'))['families']['<family id>']['attrs'];[print(c,'→',list(m[c]['values'])) for c in f if c in m]"`
5. The brand's line in `reference/brand-sites.md` (`grep -i <brand>`).
6. Lifestage/breed-size/texture words: the matching table in `reference/data-tables.md` (grep, don't read it all).

## Per row
1. **Find the product page**, first source that has it:
   brand site (and its other-country domains) → **barcode lookup**
   (`scripts/barcode-lookup.py --code <code> --name "<csv name>"`, then WebSearch the EAN in
   quotes; `reference/image-sources.md` → "Barcode lookup": name/texts/photos only from pages
   that print our exact EAN, never from a bot-walled or robots-excluded site, source kind
   `barcode`, and add a line to `<run>/barcode-sourced.csv`) → `scripts/4lapy-lookup.py --ean <EAN> --search "<latin words>"`
   (hafo `barcodes` in the row are EANs) → zoovet.am / nemo.am (`scripts/zoovet-lookup.py --search …`)
   → petshop.ru (texts only, never photos) → web search whose page or image file name carries our
   article code or EAN. Identity is confirmed only by the EAN or our article on the page, or by
   brand + line + lifestage + flavour + pack (+ size/colour) ALL matching. Unconfirmed → hold.
   Fetch with WebFetch/curl; in a browser use one `evaluate_script`, never `take_snapshot`.
2. **Save the raw page text** to `<run>/cards/<code>.source.txt` (plain text, as on the page, any
   language). Every attribute quote must be copied verbatim from it, the CSV name or hafo's text.
3. **Images**: every gallery image URL of that product (full size), in order. Download the one you
   put first (`curl -s -o .siruk-cache/<code>-first.jpg <url>`) and Read it: `packshot` only if it
   is the product alone on a plain background — no animal, hand, scene or group. Reorder if another
   image is the clean one. hafo's own photo is a watermarked placeholder: last, and only if nothing else.
4. **Same product?** For each `existing_candidates` id run `scripts/show-product.sh <id>`. It is
   the same product only when brand, line, lifestage, breed size, food form, diet and health claim
   all match and it differs only on the type's axes (pack, flavour, texture; size/colour for
   accessories) → `existing_id`. Otherwise a new product (`existing_id: null`).
5. **Card**: English `name` (no brand, no pack size, no flavour/colour), `label` = the axis
   (`Turkey in Gravy`, `M`, `42.5 × 31 × 8 cm`), `category_ids` = every leaf that fits from
   types.json (both species' mirror leaves only if the pack says both), attributes only with a
   verbatim quote — no quote, leave it out. `product-weight` whenever the row has a `pack` in kg/g.
   `texts.about_this_item` in English, faithful to the source (translate from Russian/Ukrainian if
   that is all there is), no claims the source doesn't make; ingredients/feeding for food.
   `price: {"source": "prepared"}` unless the row's route is `needs-price`.
   - **Packaging and colour are seen, not read**: when the page text doesn't say it, set them
     from the photo as `{"value": "Bag", "basis": "photo"}` (no quote). Every family that has
     `packaging` should get it — dry food is nearly always `Bag`; a 400 g tin is `Can`.
   - **The whole gallery**: every product image the page has (all angles, back of pack, detail
     shots), not just the first. One image from a brand site is almost always incomplete.
   - **Wrong type in the CSV**: if the page proves the CSV's category wrong (a "wet food" row that
     is dry kibble), set the right `type` and a `type_reason` quoting the proof — don't hold it.
6. **Validate**: `scripts/validate-card.py --run <run> <code>`. Fix every FAIL. If a FAIL can't be
   fixed honestly (no confirmed source, no image, value not in the menu), write the card as
   `{"code": …, "status": "hold", "hold_reason": "…"}` instead. WARN lines are fine — mention them.

## Reply
Only this, one line per code, nothing else:
`<code> PASS <≤12 words: source + anything the reviewer must look at>`
`<code> HOLD <≤12 words: why>`
