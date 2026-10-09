# Gallery fix planning — instructions (read-only, no API calls)

Context: production pet shop; warehouse staff pick orders by looking at a variant's photos, so every
photo on a variant must show THAT item (brand, line, flavour, lifestage, colour, pack size / count).
Input `plan-in/pN.json`: products whose galleries had at least one non-ok verdict; for each variant,
every current image (pos, media id, verdict, `seen` = what the reviewer saw, `local` file path).
Output `plan-out/pN.json`.

## Decide, per variant, the final gallery (ordered list of existing media ids)
1. KEEP only images that show this exact item. DROP every image with verdict wrong-product,
   wrong-flavour, wrong-size, wrong-colour, wrong-lifestage, and any image showing other products
   (range line-ups, cross-sell with dry/wet packs of other products, "other flavours" grids,
   multi-size group shots, wholesale cartons on a single unit). Also drop `unclear` secondaries
   unless the `seen` text clearly confirms this item.
2. LEAD (pos 0) = a clean shot of the item as the warehouse holds it: the PACK front for anything
   packaged (treats, food, litter, care products); the item alone for unpackaged goods (toys,
   collars, bowls). Pick the best ok image already in the gallery (prefer one that shows the
   flavour / size / article). Then OPEN that chosen lead image with the Read tool and confirm.
3. ACCEPTED without a new photo (policy):
   - The brand's own packshot prints no size, but nothing contradicts the size AND either this
     product has only one size of that line, or the item looks physically identical across sizes
     (Trixie collars / harnesses / leads / bowls / clothing in the same colour: one photo per colour
     is fine across sizes).
   - Royal Canin / Monge dry-bag packshots with no printed weight, when line + lifestage match.
   - A `-KG` sku (1 kg loose-sale twin) gets exactly the same gallery as its bag (sku without -KG).
4. NEW PHOTO NEEDED when, after dropping, no image correctly shows the item as the lead:
   wrong printed size (e.g. 6 kg bag on an 11.4 kg variant, 300 g on 11 kg, 2.5 kg on 800 g),
   wrong flavour/colour/product, a flavour that cannot be told from its sibling's lead (two flavours
   with the identical bag front), a 12 × 85 g case variant with only single-pouch photos, a
   multi-piece set shown as one piece with no set photo. Set "need" to a precise description of the
   photo required (brand, line, flavour, lifestage, size/count, colour) and keep in "gallery" only the
   correct remaining images (may be empty). Do not invent media ids.
5. QUESTION for the owner when the data itself looks wrong (label says purple but every brand photo
   of that article is lilac; product name says "with hood" but the article has none; brand on the
   pack differs from the product's brand). Put it in "question"; still give the safest gallery.

## Output format
```json
{"<product_id>": {"<sku>": {"gallery": [12345, 12348], "need": null, "question": null,
                            "why": "dropped 13342 (Loaf pouch on gravy variant); lead 13336 pack front gravy 85 g"}}}
```
Include EVERY variant of every product in your input (unchanged galleries too, so the plan is
complete). Media ids are integers. Finish your reply with: products, variants changed, variants
needing a new photo (sku + need), and questions.
