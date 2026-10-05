# Fallback import + image audit — 2026-10-02 (production)

Input: the 51 register rows + 6 Royal Canin rows that `runs/2026-10-02-final` listed as not imported.
New step used: Google search with the result pages read in the headed Chrome
(`scripts/google-lens.py` `search` + `page` jobs; `reference/image-sources.md` → "Texts when the brand has no page").

## Outcome

| | Rows |
|---|---|
| Imported now | **13** — 7 new products, 6 variants on live products |
| Were already live (register never linked them) | 6 — 01365–01368, 01370, 01371 = Trixie 50540/5105/5108/6000/60146/60795 (products 1223–1228), from sirook.pdf 2026-09-28 |
| Genuinely not importable | **38** — `not-imported.csv` |

### Created / added

| Register | Code | Product | Variant | Price | Source |
|---|---|---|---|---|---|
| 00291 | 61001K | 1325 Dogman Litter Tray | 42.5 × 31 × 8 cm | 1950 | kaskad-pet.ru (art. 09307018) — "no source" in earlier runs |
| 00289 | 09307034 | 1324 Kaskad Litter Tray with Mesh | 37 × 28 × 6 cm | 2150 | kaskad-pet.ru |
| 00290 | 09307016 | 1323 Kaskad Small Deep Litter Tray with Grid | 30 × 22 × 4.5 cm | 1500 | kaskad-pet.ru |
| 01096 | 00012105 | 1322 Kaskad Classic Double Leather Collar with Rhinestones | 12 mm, 20–24 cm | 2150 | kaskad-pet.ru |
| 01047 | 00012007 | 1149 Classic Leather Collar with Braid (+variant) | 12 mm, 20–24 cm | 1000 | kaskad-pet.ru |
| 01005 | 26445251 | 1290 Prong Collar (+variant) | 2.5 mm, 45 cm | 4750 | kaskad-pet.ru |
| 01006 | 26460321 | 1290 Prong Collar (+variant) | 3.5 mm, 60 cm | 6900 | kaskad-pet.ru |
| 01007 | 26465401 | 1290 Prong Collar (+variant) | 4 mm, 65 cm | 6100 | kaskad-pet.ru |
| 00116 | 10201 | 1110 Beaphar Flea & Tick Collar for Cats (+variant) | 35 cm, green | 2200 | EAN 8711231102013 pages (biostyle, e-zoo.by photo named by EAN) |
| 00118 | REG00118 | 1110 Beaphar Flea & Tick Collar for Cats (+variant) | 35 cm, blue | 2200 | zoovet.am (confirmed by hand) |
| 00170 | 63245PCHL | 1327 Pchelodar Cleaning Paw Spray | 125 ml | 1800 | Google → biostyle.biz (art. 1041, EAN 4607145632453); photo eapteka.ru |
| 00033 | REG00033 | 1328 My Love Junior Dry Dog Food (new brand My Love, 47) | Chicken 11 kg + 1 kg pack | 13000 / 1200 | EAN 4820269143074 pages (e-fresh.gr packshot, emag.ro) — brand created on user approval |
| 00171 | 63243PCHL | 1326 Pchelodar Antiskolzin Anti-Slip Paw Spray | 125 ml | 2100 | Google → biostyle.biz (art. 1004); photo agrobioprom.ru (maker) |

Prices: the PM's register (rule 2c). Stock 10. en/ru/hy shipped (bulk create / set-translation).
Vocabulary: `size` values 880–885 (prong collar and tray sizes). Media check: 0 broken.

## Image audit (user report: Myau flavours all showed the beef bag)

`runs/2026-10-02-audit/` — every variant whose photos came from runs 2026-10-01-fix, 2026-10-02-found and
2026-10-02-images: 97 products, 371 photos, each looked at (4 parallel reviewers) + an identical-file check.
323 ok. Fixed on production (galleries.py, read back, 0 mismatches):

- 1320 Myau Adult Dry Cat Food — Chicken/Rabbit led with the meat bag → miau.ua's own flavour packshots
  (300 g pack: the 11 kg front prints no flavour; logged "other size"); Meat-Rice-Veg → miau.ua's 11 kg pack.
- 804 Trixie Premium Adjustable Lead — apple and lilac led with the aqua lead → trixie.es packshots in their colour.
- 1291 Club 4 Paws — 900 g / 300 g promo shots removed from the 14 kg variants.
- 1150 flexi New Neon — neon-yellow close-up removed from the orange/blue/pink/green variants.
- 636 Mini Adult 800 g — 3 kg bag shots removed; 730 Iv San Bernard Lemon 300 ml — other-size group shot removed.

Still open (in `state/open-items.csv`): 804 coral (no coral photo anywhere), 804 colour labels, 1050 veal-vs-beef
label, 1284 bells collar photo, Monge Best-for-Breeders 15 kg sacks (no recipe on the sack), 324 Wild Game 1230 g
and 639 Lamb 800 g (known since 2026-10-01; every shop reuses the other size's photo).

Workflow fix: `reference/image-sources.md` and the google-lens skill now require reading the flavour/colour/size
on the pack; new `scripts/variant-image-audit.py` flags sibling variants that share a picture.
