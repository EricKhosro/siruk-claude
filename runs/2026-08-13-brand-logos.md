# Every brand showed the same picture — cause and fix (2026-08-13)

**Reported:** brand images are wrong; all brands show one image, "it feels like
a fallback".

## It is not a fallback

The data really does say that. 12 of the 15 brands stored the **same** image id:

```
✗ media 61 is the logo of 12 brands: Acana, Belcando, Brit, Canvit, Farmina,
  Leonardo, Monge, Orijen, Royal Canin, Schesir, Stuzzy, Trixie
```

Only Bewi Dog (732), Bewi Cat (735) and Dogland (738) — created earlier the same
day — had their own logos. `GET /brands/<id>` agreed with the list endpoint, so
nothing was being substituted at render time.

And media **61** is not a logo at all any more: it is
`royal-canin-sterilised-regular-15kg-3.jpg`, created 13/08.

### Why that id changed meaning: media ids are recycled

`runs/2026-08-13-schesir-import.md` records media 61 as the **Schesir/Agras
logo** on 12/08. A scan of the whole library (ids 1–740, 644 live records) shows
what happened:

| id | filename | created |
|---|---|---|
| 55 | royal-canin-sterilised-regular-15kg-1.jpg | 11/08 |
| 58 | royal-canin-sterilised-regular-15kg-2.jpg | 11/08 |
| **61** | **royal-canin-sterilised-regular-15kg-3.jpg** | **13/08** |
| 62 | …-3.jpg-adminThumbnail | 13/08 |

Ids 61–62 are dated 13/08 but sit inside an 11/08 block: they were freed by a
delete and handed to a later upload. So the brands' shared placeholder quietly
turned into a Royal Canin bag.

**For the dev team:** media ids should not be reusable. Anything holding a media
reference (brand image, variant images) silently changes picture when an id is
recycled, with no error anywhere.

Also worth knowing: **one upload creates three media rows** — the original,
`<name>-adminThumbnail`, and `<name>-<hash>` (the webp the storefront serves).
`GET /medias/<id>.url` only ever returns the admin thumbnail.

## What was done

All 12 brands now have their own logo, each one **sourced from the brand's own
site and looked at before upload** (no URL-guessing — that is what produced the
shared placeholder in the first place).

| Brand | id | Source | Logo media | Size |
|---|---|---|---|---|
| Acana | 1 | inline `<svg class="AcanaLogo">` on acana.com | 1501 | 1200×420 |
| Belcando | 2 | belcando.com `bb-logo-tafel-mit-zunge.svg` | 1504 | 1200×746 |
| Brit | 3 | brit-petfood.com `logo-brit.png` | 1507 | 273×75 ⚠ |
| Canvit | 4 | canvit.cz `logo01.png` | 1510 | 264×60 ⚠ |
| Monge | 5 | monge.it `logo_blu.png` | 1513 | 199×55 ⚠ |
| Orijen | 6 | inline `<svg class="OrijenLogo">` on orijenpetfoods.com | 1516 | 1000×1000 |
| Royal Canin | 7 | Wikimedia Commons `Royal-Canin-Logo.svg` (1200px render) | 1519 | 1280×481 |
| Trixie | 8 | trixie.de `TRIXIE_LOGO_RGB_Rot_NEW2024.png` | 1522 | 600×317 |
| Farmina | 9 | farmina.com `logo-Farmina.png` | 1525 | 138×120 ⚠ |
| Schesir | 10 | schesir.com `Schesir-Logo-GREY.svg` | 1528 | 1200×338 |
| Leonardo | 11 | leonardo-catfood.com `bl-logo-cmyk-mit-zunge.svg` | 1531 | 1200×673 |
| Stuzzy | 12 | stuzzy.it `logo_footer.svg` | 1534 | 1200×524 |

Verification after the run:

```
15 brands: 0 with no logo, 0 with a dead logo, 0 sharing a logo with another brand
```

Every logo url returns 200, including the `/storage/webp/…` derivative the
storefront actually serves (the url family that was 404ing earlier today).

**Stuzzy no longer carries the Schesir placeholder** — the long-standing flag in
`CLAUDE.md` is resolved. Belcando/Leonardo and Schesir/Stuzzy are the sibling
pairs that get swapped; all four were checked by eye and are correct.

## Notes and leftovers

- ⚠ **Four low-res logos** — Brit (273×75), Canvit (264×60), Monge (199×55),
  Farmina (138×120). These are the biggest files those brands publish; I probed
  the obvious `@2x`/SVG/press variants and they 404. Monge and Farmina do have
  vector logos, but Monge's is white-on-transparent (invisible on white) and
  Farmina ships none. If the distributors can supply press-kit files, they will
  drop straight in with `scripts/set-brand-logo.sh <id> <file>`.
- Orijen's official vector is white artwork on a black plate. Rendered with the
  black background path hidden, giving the standard black wordmark on white —
  the vector is the brand's own, only the background layer was suppressed.
- Royal Canin publishes no downloadable logo on royalcanin.com; the Wikimedia
  Commons file is the official mark, rendered at 1200 px. Swap it if Mars sends
  a press-kit file.

## Tooling added

| Script | Purpose |
|---|---|
| `scripts/verify-media.sh --brands` | catches all three failure modes: no logo, dead logo, **several brands sharing one media** |
| `scripts/set-brand-logo.sh <id> <file\|url\|mediaId>` | replaces a logo keeping name/slug/meta; refuses an image another brand uses; verifies the new url |
| `scripts/rasterize-svg.sh <svg> [width]` | official-vector → tight PNG (headless Chrome). `qlmanage` pads or clips, so it is not usable here |

`scripts/fetch-logo.sh` + looking at every candidate stays the rule; see the
`/create-brand` skill, which now documents the SVG-only and white-logo traps.
