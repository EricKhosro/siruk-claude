# 2026-08-13 — Schesir import (sheet "Royal Canin 1")

Source: `csv/Vendors_Siruk - Royal Canin 1.csv`, Schesir rows only.
Catalogue went from **73 → 125 products**; Schesir now has **56**.

## Result

| | |
|---|---|
| Priced Schesir rows | 129 |
| Rows imported | **96** |
| Rows not imported (no live site match) | 33 |
| Products created | 53 |
| Products updated | 4 (99, 100, 101, 102) |
| Products renamed afterwards | 46 |
| Images uploaded | 252 |
| Images verified readable | **252 / 252** |
| Page-fetch failures | 0 |

Every image was re-fetched from its `/storage/...` url after the run and returned
HTTP 200 — no repeat of the media-621 dead-image class of bug.

## How rows were matched

Not by name. Schesir image filenames embed the article code
(`…/ITA_21112001_MAIN_….jpg`), so the sheet's `Կոդ` matches on the **full 8-digit
code**. A code claimed by more than one product is dropped rather than guessed —
an ambiguous match is worse than none.

An earlier 7-digit-prefix version produced silent false matches (all four
`BAG DRY MAINTENANCE` bags resolved to one handle). Full-code-only costs 4
matches and removes the whole class of error.

## Grouping

Flavor is a variant axis, so the flavors of one format collapse into one product
(shelf test, CLAUDE.md). Product identity = species + line + texture + container
+ pack size. Species comes from the site tags (`Gatto`/`Cane`) and **splits
products** — `chicken-fillets-in-jelly-150g-in-can` is dog food despite sitting
beside cat rows in the sheet. Container comes from the site handle
(`…-in-can` / `…-in-pouch`), which is reliable where the vendor string often
omits it.

Content per variant: description + tag bullets, Composition + Nutritional
additives, Feeding recommendation + Storage — pulled from the product page's
`<details class="cc-accordion-item">` blocks over plain curl, no browser.

## Pricing

- Wet/treat rows → `pricing_type: fixed`, price straight from `R/Price` (the
  single retail unit; the leading `12X`/`6X` case pack is stripped).
- Dry bags → `pricing_type: per_kg`, `price_per_kg = R/Price ÷ pack weight`,
  `price` forced to 0 because the API ignores it. Verified: 24500 ÷ 12 kg =
  2041.67/kg → 2041.67 × 12 = **24500.04**, i.e. the pack price is reproduced to
  four hundredths of an AMD. The sheet's own `PRICE/KG` column (2150) is a
  rounded vendor figure and was deliberately **not** used.
- `product-weight` is omitted on `per_kg` variants (the admin derives it from
  pack weight). Flavor is what makes those variants unique, so no collision.

## Attribute values created (32) — approved by the user

Without these the API rejects same-attribute variants, which would have blocked
17 variant pairs.

- **Flavor (11)**: Anchovies, Surimi, Seabass, Ham, Egg, Fish, Prawns, Squid,
  Papaya, Pineapple, Peas
- **Food Texture (2)**: Broth, Mousse & Shreds
- **Product Weight (19)**: 40 g, 70 g, 80 g, 90 g, 113 g, 115 g, 140 g, 145 g,
  160 g, 165 g, 225 g, 250 g, 255 g, 283 g, 285 g, 300 g, 340 g, 960 g, 3.4 kg

The sheet's `Carrots` was mapped to the existing `Carrot` — no new value.

⚠️ **One flavor id per variant.** Schesir names read `<base> with <qualifier>`,
so the **qualifier** is stored (`Tuna with Anchovies` → Anchovies), because that
is what distinguishes the variant from its siblings. A tuna product therefore is
not findable under a `Tuna` flavor filter. This is the multi-value attribute
question already open in CLAUDE.md.

## Repairs after the bulk run

The first pass derived names from site titles and left artefacts. 46 were
renamed; single-variant products now take the site's own title (a real product
name) instead of a reconstruction, which had produced nonsense like
`Classic Chicken with Small Puppy 2kg`.

| Was | Now |
|---|---|
| `in Jelly 85g` | `Tuna in Jelly 85g` |
| `Peas 85g` | `Tuna with Peas in Jelly 85g` |
| `Medium Puppy Puppy/Kitten 12kg` | `Medium Puppy Chicken 12kg` |
| `G Multipack 300g` | `Chicken Fillets with Duck in Cooking Water 300g` |
| `150g` | `Chicken Fillets 150g` |

Four groups had wrongly split and were merged:

- **131 → 132** Silver mousse: the chicken pouch row carries no pack size, so it
  became its own product. Merged as a flavor variant; 131 deleted.
- **111** the 2 kg Small Adult range lost its Lamb bag — the sheet writes
  `SMALL MAINT LAMB` where the others say `SMALL MAINTENANCE`. Added.
- **153 + 154** Born Carnivore 255 g flavors were three products; now one with
  three variants. 154 deleted, and the row that had 422'd on a duplicate slug is
  in.

⚠️ Both merges initially failed: I added a SKU while the old product still owned
it, and the delete ran afterwards, briefly orphaning two variants. Re-added and
verified — 132 has 2 variants, 153 has 3.

## Not imported — 33 rows

These have prices but no product on the live site, so there is no image,
description or composition to attach. Rather than invent them they are listed
here. Most are ranges Schesir no longer sells.

| Group | Codes |
|---|---|
| Multipack Can 8x6x50g | 01064126, 01064129, 01064135, 01064145, 01064146 |
| Can 24x140g | 01064601 |
| Dry 10 kg / 1.5 kg bags | 02044210, 02044213, 02044214, 02044215, 02044739, 02044742, 02044745 |
| Grill 70 g (wholefood + paté) | 21110103, 21110202, 21110303, 21141003, 21141203 |
| After Dark variety packs | 21119904, 21139904 |
| Tuna jelly 140 g | 21126004, 21126104, 21126304, 21126804 |
| Tuna jelly pouch 85 g | 21223004, 21223504 |
| After Dark mousse chicken/duck | 21232404 |
| Soup 40 g | 21254004, 21254104, 21254204, 21254304 |
| Training snack 113 g / fish oil 250 ml | 26261604, 27990106 |

Note **26261604** is already live as product 101 (created in an earlier run) —
only its price refresh is outstanding.

## Flagged for the user

1. **Cat treats have no category.** The tree is `Dog > Treat` only, so the Stix
   90 g pouches and the mixed-flavor snack were filed under `Cat` (id 8). Two
   products affected. Add a `Cat > Treat` category and I'll re-file them.
2. **Product 99's default variant changed.** The PUT rebuilt the variant list and
   `Tuna & Anchovies` is now default rather than plain `Tuna`. Cosmetic, easily
   flipped if you'd rather the plain tuna lead.
3. **`Broth 85g` and `Jelly 150g`** are thin names — those ranges genuinely have
   no identity beyond flavor on the site, and flavor belongs to the variants.
4. Leonardo (id 11) and Stuzzy (id 12) still share the Schesir/Agras placeholder
   logo (media 61).

## Reusable pieces

- `scripts/normalize-vendor-csv.py` — all 5 sheet layouts → canonical rows
- `scripts/plan-schesir.py` — code matching + product/variant grouping
- `scripts/import-schesir.py` — content, media, attributes, create/update
- `scripts/fix-schesir-names.py`, `scripts/fix-schesir-leftovers.py` — repairs

The plan/import split is worth keeping for the other brands: `--dry-run` showed
the flavor-collision bug and the bad names before anything was written.
