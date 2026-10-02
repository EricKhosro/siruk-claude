# Royal Canin import — production (2026-09-30)

Source: `Price Royal Canin Nor _ SIRUK.xlsx`, the 52 rows with a number in column E. Sale price = column C `Վաճառքի Գին`, cost = column B, column D `Վաճառքի Գին կիլոգրամով` = the loose price (see below). Stock 10 each (by-weight variants: 10 kg = 10,000 g). Content, photos and barcodes: royalcanin.com (UK; Malta for Sterilised Loaf and the Sterilised 37 15 kg barcode).

**39 products · 91 variants · 6 rows not imported.** Imported: 39/39 (product ids 1229–1267).

## Column D — the loose variant
- **Dry food**: every bag also gets a **by-weight** variant (`sale_mode: weight`): price = column D per kg, the customer buys whole kilograms (minimum 1 kg, step 1 kg — user, 2026-10-01); cost = column B ÷ bag kg; stock 10 kg. SKU = bag barcode + `-KG`.
- **Wet food**: D (750) is below our cost per kg (7,500 ÷ 1.02 kg), so it is the price of **one 85 g pouch** — a single-pouch pack variant at 750, cost 7,500 ÷ 12 = 625, stock 10. SKU = the single pouch's own barcode where royalcanin.com lists it, else the 12-pack barcode + `-1`.
- The backend allows one by-weight variant per option combination (all loose food shares the size "by weight"), so a line whose bags differ only in size gets one loose variant, not one per bag. In this batch every dry product has one bag, so each gets exactly one.

| # | Product | id | Type | Categories | Variant | Sold as | Price | Cost | Barcode (SKU) |
|---|---|---|---|---|---|---|---|---|---|
| 1 | Maxi Adult 5+ | 1230 | Dry | [3] | 15 kg | pack | 45,500 | 39,500.0 | 3182550402316 |
| 1 | Maxi Adult 5+ | 1230 | Dry | [3] | By weight | loose / kg | 3,200 | 2,633 | — (3182550402316-KG) |
| 2 | Maxi Adult | 1229 | Dry | [3] | 15 kg | pack | 45,500 | 39,500.0 | 3182551055955 |
| 2 | Maxi Adult | 1229 | Dry | [3] | By weight | loose / kg | 3,200 | 2,633 | — (3182551055955-KG) |
| 3 | Maxi Puppy | 1231 | Dry | [3] | 15 kg | pack | 47,500 | 41,500.0 | 3182550402163 |
| 3 | Maxi Puppy | 1231 | Dry | [3] | By weight | loose / kg | 3,300 | 2,767 | — (3182550402163-KG) |
| 4 | Maxi Starter Mother & Babydog | 1232 | Dry | [3] | 15 kg | pack | 57,000 | 49,500.0 | 3182550778787 |
| 4 | Maxi Starter Mother & Babydog | 1232 | Dry | [3] | By weight | loose / kg | 3,950 | 3,300 | — (3182550778787-KG) |
| 5 | Medium Adult | 1233 | Dry | [3] | 15 kg | pack | 45,500 | 39,500.0 | 3182551055849 |
| 5 | Medium Adult | 1233 | Dry | [3] | By weight | loose / kg | 3,200 | 2,633 | — (3182551055849-KG) |
| 6 | Medium Puppy | 1234 | Dry | [3] | 15 kg | pack | 47,500 | 41,500.0 | 3182550402132 |
| 6 | Medium Puppy | 1234 | Dry | [3] | By weight | loose / kg | 3,300 | 2,767 | — (3182550402132-KG) |
| 7 | Mini Adult | 1235 | Dry | [3] | 8 kg | pack | 26,500 | 23,000.0 | 3182551055740 |
| 7 | Mini Adult | 1235 | Dry | [3] | By weight | loose / kg | 3,450 | 2,875 | — (3182551055740-KG) |
| 8 | Mini Puppy | 1236 | Dry | [3] | 8 kg | pack | 29,000 | 25,000.0 | 3182550793049 |
| 8 | Mini Puppy | 1236 | Dry | [3] | By weight | loose / kg | 3,750 | 3,125 | — (3182550793049-KG) |
| 9 | Mini Adult 8+ | 1237 | Dry | [3] | 8 kg | pack | 26,500 | 23,000.0 | 3182550831406 |
| 9 | Mini Adult 8+ | 1237 | Dry | [3] | By weight | loose / kg | 3,450 | 2,875 | — (3182550831406-KG) |
| 10 | Maxi Joint Care | 1238 | Dry | [3] | 10 kg | pack | 36,000 | 31,500.0 | 3182550893701 |
| 10 | Maxi Joint Care | 1238 | Dry | [3] | By weight | loose / kg | 3,800 | 3,150 | — (3182550893701-KG) |
| 11 | Mini Starter Mother & Babydog | 1239 | Dry | [3] | 8 kg | pack | 35,000 | 30,500.0 | 3182550932691 |
| 11 | Mini Starter Mother & Babydog | 1239 | Dry | [3] | By weight | loose / kg | 4,600 | 3,812 | — (3182550932691-KG) |
| 12 | Fit 32 | 1240 | Dry | [10] | 15 kg | pack | 53,500 | 46,500.0 | — (RC-FIT-32-15000G) |
| 12 | Fit 32 | 1240 | Dry | [10] | By weight | loose / kg | 3,700 | 3,100 | — (RC-FIT-32-15000G-KG) |
| 13 | Kitten | 1241 | Dry | [10] | 10 kg | pack | 39,500 | 34,500.0 | 3182550702973 |
| 13 | Kitten | 1241 | Dry | [10] | By weight | loose / kg | 4,150 | 3,450 | — (3182550702973-KG) |
| 14 | Sterilised 37 | 1242 | Dry | [10] | 15 kg | pack | 60,000 | 52,000.0 | 3182550777308 |
| 14 | Sterilised 37 | 1242 | Dry | [10] | By weight | loose / kg | 4,150 | 3,467 | — (3182550777308-KG) |
| 15 | Hairball Care | 1243 | Dry | [10] | 10 kg | pack | 39,500 | 34,500.0 | 3182550721424 |
| 15 | Hairball Care | 1243 | Dry | [10] | By weight | loose / kg | 4,150 | 3,450 | — (3182550721424-KG) |
| 16 | Hypoallergenic Cat | 1244 | Dry | [10] | 4.5 kg | pack | 22,000 | 19,000.0 | 3182550939560 |
| 16 | Hypoallergenic Cat | 1244 | Dry | [10] | By weight | loose / kg | 5,000 | 4,222 | — (3182550939560-KG) |
| 17 | Urinary S/O Cat | 1245 | Dry | [10] | 7 kg | pack | 29,000 | 25,000.0 | 3182550859554 |
| 17 | Urinary S/O Cat | 1245 | Dry | [10] | By weight | loose / kg | 4,300 | 3,571 | — (3182550859554-KG) |
| 18 | Hypoallergenic Dog | 1246 | Dry | [3, 5] | 14 kg | pack | 60,500 | 52,500.0 | 3182550939904 |
| 18 | Hypoallergenic Dog | 1246 | Dry | [3, 5] | By weight | loose / kg | 4,500 | 3,750 | — (3182550939904-KG) |
| 19 | Gastrointestinal Dog | 1247 | Dry | [3, 5] | 15 kg | pack | 65,000 | 56,500.0 | 3182550905695 |
| 19 | Gastrointestinal Dog | 1247 | Dry | [3, 5] | By weight | loose / kg | 4,500 | 3,767 | — (3182550905695-KG) |
| 20 | Urinary S/O Dog | 1248 | Dry | [3, 5] | 13 kg | pack | 56,500 | 49,000.0 | 3182550896856 |
| 20 | Urinary S/O Dog | 1248 | Dry | [3, 5] | By weight | loose / kg | 4,500 | 3,769 | — (3182550896856-KG) |
| 21 | Renal Dog | 1249 | Dry | [3, 5] | 14 kg | pack | 60,500 | 52,500.0 | 3182550842556 |
| 21 | Renal Dog | 1249 | Dry | [3, 5] | By weight | loose / kg | 4,500 | 3,750 | — (3182550842556-KG) |
| 22 | Hepatic Dog | 1250 | Dry | [3, 5] | 12 kg | pack | 52,000 | 45,000.0 | 3182550771740 |
| 22 | Hepatic Dog | 1250 | Dry | [3, 5] | By weight | loose / kg | 4,500 | 3,750 | — (3182550771740-KG) |
| 23 | Gastrointestinal Puppy | 1251 | Dry | [3, 5] | 10 kg | pack | 45,000 | 39,000.0 | 3182550771047 |
| 23 | Gastrointestinal Puppy | 1251 | Dry | [3, 5] | By weight | loose / kg | 4,700 | 3,900 | — (3182550771047-KG) |
| 24 | Hair & Skin Care Thin Slices | 1252 | Wet | [11] | In Gravy 12 × 85 g | pack | 8,600 | 7,500.0 | 9003579308929 |
| 24 | Hair & Skin Care Thin Slices | 1252 | Wet | [11] | In Gravy 85 g | single pouch | 750 | 625 | — (9003579308929-1) |
| 24 | Hair & Skin Care Thin Slices | 1252 | Wet | [11] | In Jelly 12 × 85 g | pack | 8,600 | 7,500.0 | 9003579311721 |
| 24 | Hair & Skin Care Thin Slices | 1252 | Wet | [11] | In Jelly 85 g | single pouch | 750 | 625 | — (9003579311721-1) |
| 25 | Sensitivity Control Chicken with Rice | 1253 | Wet | [11] | Chicken 12 × 85 g | pack | 8,600 | 7,500.0 | 9003579011423 |
| 25 | Sensitivity Control Chicken with Rice | 1253 | Wet | [11] | Chicken 85 g | single pouch | 750 | 625 | 9003579011430 |
| 26 | Digestive Care Thin Slices in Gravy | 1254 | Wet | [11] | 12 × 85 g | pack | 8,600 | 7,500.0 | 9003579309537 |
| 26 | Digestive Care Thin Slices in Gravy | 1254 | Wet | [11] | 85 g | single pouch | 750 | 625 | — (9003579309537-1) |
| 27 | Instinctive Thin Slices | 1255 | Wet | [11] | In Gravy 12 × 85 g | pack | 8,600 | 7,500.0 | 9003579308936 |
| 27 | Instinctive Thin Slices | 1255 | Wet | [11] | In Gravy 85 g | single pouch | 750 | 625 | — (9003579308936-1) |
| 27 | Instinctive Thin Slices | 1255 | Wet | [11] | In Jelly 12 × 85 g | pack | 8,600 | 7,500.0 | 9003579309513 |
| 27 | Instinctive Thin Slices | 1255 | Wet | [11] | In Jelly 85 g | single pouch | 750 | 625 | — (9003579309513-1) |
| 28 | Kitten Wet | 1256 | Wet | [11] | In Gravy 12 × 85 g | pack | 8,600 | 7,500.0 | 10030111604351 |
| 28 | Kitten Wet | 1256 | Wet | [11] | In Gravy 85 g | single pouch | 750 | 625 | — (10030111604351-1) |
| 28 | Kitten Wet | 1256 | Wet | [11] | In Jelly 12 × 85 g | pack | 8,600 | 7,500.0 | 9003579311714 |
| 28 | Kitten Wet | 1256 | Wet | [11] | In Jelly 85 g | single pouch | 750 | 625 | — (9003579311714-1) |
| 28 | Kitten Wet | 1256 | Wet | [11] | Loaf 12 × 85 g | pack | 8,600 | 7,500.0 | 9003579003848 |
| 28 | Kitten Wet | 1256 | Wet | [11] | Loaf 85 g | single pouch | 750 | 625 | — (9003579003848-1) |
| 29 | Instinctive 7+ Chunks in Gravy | 1257 | Wet | [11] | 12 × 85 g | pack | 8,600 | 7,500.0 | 9003579310168 |
| 29 | Instinctive 7+ Chunks in Gravy | 1257 | Wet | [11] | 85 g | single pouch | 750 | 625 | — (9003579310168-1) |
| 30 | Light Weight Care Thin Slices | 1258 | Wet | [11] | In Gravy 12 × 85 g | pack | 8,600 | 7,500.0 | 9003579308769 |
| 30 | Light Weight Care Thin Slices | 1258 | Wet | [11] | In Gravy 85 g | single pouch | 750 | 625 | — (9003579308769-1) |
| 30 | Light Weight Care Thin Slices | 1258 | Wet | [11] | In Jelly 12 × 85 g | pack | 8,600 | 7,500.0 | 9003579311738 |
| 30 | Light Weight Care Thin Slices | 1258 | Wet | [11] | In Jelly 85 g | single pouch | 750 | 625 | — (9003579311738-1) |
| 31 | Ageing 12+ Chunks in Jelly | 1259 | Wet | [11] | 12 × 85 g | pack | 8,600 | 7,500.0 | 9003579050057 |
| 31 | Ageing 12+ Chunks in Jelly | 1259 | Wet | [11] | 85 g | single pouch | 750 | 625 | — (9003579050057-1) |
| 32 | Sterilised Wet | 1260 | Wet | [11] | In Jelly 12 × 85 g | pack | 8,600 | 7,500.0 | 9003579311776 |
| 32 | Sterilised Wet | 1260 | Wet | [11] | In Jelly 85 g | single pouch | 750 | 625 | — (9003579311776-1) |
| 32 | Sterilised Wet | 1260 | Wet | [11] | Loaf 12 × 85 g | pack | 8,600 | 7,500.0 | 9003579003916 |
| 32 | Sterilised Wet | 1260 | Wet | [11] | Loaf 85 g | single pouch | 750 | 625 | 9003579003923 |
| 33 | Urinary S/O Morsels in Gravy | 1261 | Wet | [11] | 12 × 85 g | pack | 8,600 | 7,500.0 | 9003579010044 |
| 33 | Urinary S/O Morsels in Gravy | 1261 | Wet | [11] | 85 g | single pouch | 750 | 625 | 9003579010051 |
| 34 | Renal Thin Slices in Gravy | 1262 | Wet | [11] | Chicken 12 × 85 g | pack | 8,600 | 7,500.0 | 9003579000458 |
| 34 | Renal Thin Slices in Gravy | 1262 | Wet | [11] | Chicken 85 g | single pouch | 750 | 625 | 9003579000465 |
| 34 | Renal Thin Slices in Gravy | 1262 | Wet | [11] | Fish 12 × 85 g | pack | 8,600 | 7,500.0 | 9003579000519 |
| 34 | Renal Thin Slices in Gravy | 1262 | Wet | [11] | Fish 85 g | single pouch | 750 | 625 | 9003579000526 |
| 35 | Urinary Care in Gravy | 1263 | Wet | [11] | 12 × 85 g | pack | 8,600 | 7,500.0 | 9003579000366 |
| 35 | Urinary Care in Gravy | 1263 | Wet | [11] | 85 g | single pouch | 750 | 625 | — (9003579000366-1) |
| 36 | Sensory Smell Chunks in Gravy | 1264 | Wet | [11] | 12 × 85 g | pack | 8,600 | 7,500.0 | 9003579018514 |
| 36 | Sensory Smell Chunks in Gravy | 1264 | Wet | [11] | 85 g | single pouch | 750 | 625 | — (9003579018514-1) |
| 37 | Sensory Taste Chunks in Gravy | 1265 | Wet | [11] | 12 × 85 g | pack | 8,600 | 7,500.0 | 9003579018866 |
| 37 | Sensory Taste Chunks in Gravy | 1265 | Wet | [11] | 85 g | single pouch | 750 | 625 | — (9003579018866-1) |
| 38 | Sensory Feel Morsels in Gravy | 1266 | Wet | [11] | 12 × 85 g | pack | 8,600 | 7,500.0 | 9003579018941 |
| 38 | Sensory Feel Morsels in Gravy | 1266 | Wet | [11] | 85 g | single pouch | 750 | 625 | — (9003579018941-1) |
| 39 | Mother & Babycat Ultra Soft Mousse | 1267 | Wet | [11] | Mousse 12 × 195 g | pack | 2,300 | 2,000.0 | 9003579311660 |

## Not imported
- row 82: no cost / sale price in the file (Indoor 27 10+2 kg promo bag) — not imported (user, 2026-09-30)
- row 66: Indoor 27 Home Life 10kg → 'Indoor 27' — skipped on the user's instruction (2026-10-01)
- row 54: Medium starter 15 kg → 'Medium Starter Mother & Babydog' — skipped on the user's instruction (2026-10-01)
- row 144: Cardiac dog 14kg → 'Cardiac Dog' — skipped on the user's instruction (2026-10-01)
- row 155: Mobility C2P+ 12KG → 'Mobility Support Dog' — skipped on the user's instruction (2026-10-01)
- row 158: SKIN CARE 11KG → 'Skin Care Dog' — skipped on the user's instruction (2026-10-01)

## Decisions and notes
- Gravy / jelly / loaf of one recipe are one product with a texture variant each (Hair & Skin, Instinctive, Kitten, Light Weight Care, Sterilised); Renal chicken + fish are one product with a flavour variant each.
- Loaf: there is no Loaf texture value, so loaf variants use **Pate** (Royal Canin's loaf is a pâté; the Russian label is «паштет»); the variant label says "Loaf".
- Sensory Smell / Taste / Feel: the file doesn't say gravy or jelly — imported as **gravy**, Royal Canin's default.
- Row 188 Mother & Babycat: corrected 2026-10-01 to ONE 195 g can at 2,300 (cases of 12 are sold one by one). The 12 × 85 g case variants on 1252–1266 were retired (stock 0, delete pending) — runs/2026-10-01-rc/single-pouch.py.
- Row 58 Fit 32 15 kg: no barcode published for the 15 kg bag (royalcanin.com lists 2 / 4 / 10 kg) — SKU `RC-FIT-32-15000G`.
- Row 194 'Instinctive 12+ jelly' = Royal Canin product 4153, sold in the UK as 'Ageing 11+ in jelly' (same product id); its photo and text say 11+. Named 'Ageing 12+ Chunks in Jelly'.
- Veterinary dry foods for dogs also go in Dog › Food › Health Condition (5); cats have no such leaf.
- Feeding guides are not in royalcanin.com's page data, so feeding instructions are empty.
- Royal Canin's page data had CMS labels in some bullets ("4B- Nutrient 1-Fop", "Claim 1 - … Long Text") — stripped. Gastrointestinal Dog and Gastrointestinal Puppy carried cat wording copied from the cat pages — corrected to dog/puppy in all three languages. Cardiac Dog's broken "IRIS stage 3 or stage" is left as Royal Canin wrote it.
- Product 1229 (Maxi Adult): its first upload attempt stopped at the duplicate-name guard (a **Monge** product is also named "Maxi Adult"); the 10 photos uploaded then were reused, not uploaded twice. Same-name products of other brands are fine.
- By-weight variants sell in whole kilograms: minimum 1 kg, step 1 kg (user, 2026-10-01). The first 7 (products 1229–1235) were created with 500 g / 100 g before that rule and were corrected to 1 kg / 1 kg the same day.
- Maxi Joint Care (Royal Canin page): 2 of its 6 gallery entries had no image URL — imported with the 4 real photos.
- Translations (ru / hy): worth a native speaker's look at vet terms (metabolisable energy, zootechnical additives, green-lipped mussel, IBD/EPI abbreviations in Armenian).

## Verification on production (2026-10-01)
- All 39 products / 91 variants match the plan: prices, costs, categories, product type, stock (10; by-weight 10,000 g), by-weight rules 1 kg / 1 kg, photos on every variant; the storefront API returns every variant.
- Photos: 370 distinct images, 0 broken (`scripts/verify-media.sh`).
- Translations: every description is in ru and hy (`scripts/verify-translations.py`). 16 product names are flagged as identical to English — intended: Royal Canin line names ("Maxi Adult", "Fit 32", "Sterilised 37") stay in Latin on Russian and Armenian packs too.
