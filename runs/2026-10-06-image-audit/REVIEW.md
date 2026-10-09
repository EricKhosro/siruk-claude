# Image review — instructions for one batch (read-only)

Context: Siruk pet shop, PRODUCTION catalogue. Warehouse staff now pick orders by looking at the
product photo, so every photo must show EXACTLY the product of its variant: same brand, same line,
same flavour/recipe, same lifestage, same colour, same pack size. A wrong photo = a wrong item shipped.

Input: `batches/batch-NN.json` — products → variants (label, size_label, option attributes, sku =
article code, hafo's Armenian title/variant name and EAN as identity hints) → images (pos, local
file path, file name, dims). Output: `verdicts/batch-NN.json`.

## How to look
- Open EVERY image with the Read tool (the `local` path). Same `md5` inside one product = same
  picture: you may look once, but judge it for EACH variant it is attached to.
- Read what is printed on the pack: brand, line, flavour, lifestage, weight/volume, count, colour.
  Compare with the variant: product name + label + size_label + options + hafo hints
  (Armenian: կգ=kg, գ=g, լ=l, մլ=ml, հավ=chicken, տավար=beef, ձուկ/սաղմոն=fish/salmon, գառ=lamb,
  հնդկահավ=turkey, ճագար=rabbit, լաքոտ=puppy, ձագ=kitten).
- Sibling variants that differ by flavour/colour/size must NOT show the same picture as their lead
  (pos 0). Exception: a `-KG` sku (1 kg loose-sale twin) legitimately reuses its bag's gallery.
- pos 0 must be a clean packshot of the product alone (no animal/hand/scene/group of products).
- Secondary images (pos ≥ 1): back of pack, kibble close-up, infographic, feeding table of the SAME
  line are fine; another size's or another flavour's/colour's pack is not.
- A hafo watermark (hafo.am logo across the photo) is a known placeholder — mark `hafo-placeholder`
  (still judge whether it shows the right product in `seen`).

## Verdict per (variant, image)
`ok` | `wrong-product` (different product/line/brand) | `wrong-flavour` | `wrong-size` |
`wrong-colour` | `wrong-lifestage` | `not-packshot-lead` (pos 0 only: right product, but not a clean
shot) | `hafo-placeholder` | `unclear` (pack does not show enough to confirm — say what is missing) |
`broken` (file unreadable/blank).
Be strict: if the pack visibly says a different flavour or size, it is wrong even if it "looks
similar". If the pack prints no size and the size can't be told from the picture, use `ok` only when
everything else matches and the line has a single size, otherwise `unclear`.

## Output format (JSON array, one entry per image placement)
```json
[{"product_id":"1320","variant_id":1998,"sku":"PM902085","label":"Chicken 11 kg","pos":0,
  "media":"14824","verdict":"ok","seen":"Myau Adult chicken bag, 11 kg printed"}]
```
`seen` = short factual description of what is printed/shown (always fill it).
Also write a summary at the end of your reply: counts per verdict and the list of non-ok rows.
Do not write anything to the API. Do not modify any file except your verdicts file.

## If an image does not display
If a Read returns no picture (e.g. "[media removed]", an empty result, or only text), you have NOT
seen it. Never write a verdict from the file name or from memory. Re-open it; if it still does not
display, convert a copy to JPEG in your scratchpad (`sips -s format jpeg -Z 1200 <file> --out <scratch>/x.jpg`)
and Read that. If it still fails, write verdict `not-seen` for it. At the end, state explicitly how
many images you actually saw.
