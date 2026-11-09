Add 12 new YOKO dog treats to Siruk's Glovo store, then give them their Glovo price in ArmSoft.

Everything you need is in `final/glovo/yoko-2026-11-09/yoko-glovo-2026-11-09.xlsx`:
- Sheet **Glovo products**: one row per product in Glovo's Pelican template columns (SKU, Armenian title, description, price, availability 1, Section 1/2). Column D (image link) is empty. Column K has the local 500×500 white-square photo for each row (`final/glovo/yoko-2026-11-09/<sku>.jpg`).
- Sheet **Price check**: how each price was set. 9 rows are 50 ֏ under Zoovet's Glovo price, read 2026-11-09. Brain M, Dried Capelin and Bull Testicles aren't on Zoovet's Glovo, so they get 2,700 like the other YOKO items that cost the same. Every row makes a profit after Glovo's ~20 % fee.
- Sheet **ArmSoft price 02**: ArmSoft code → Glovo price (unit 001, price type 02).

These are new products. None of the 12 SKUs (YOKO-1625 … YOKO-1636) is on Glovo yet, and the brand YOKO is new to the store. On Siruk they are products 1461–1468 (brand id 54).

Steps:
1. Read `.claude/skills/glovo-portal/SKILL.md` and `reference/glovo/portal.md`. Get a fresh token (`python3 scripts/glovo-portal.py whoami`; if it has expired, open portal.glovoapp.com in the built-in browser and the user signs in).
2. Check that none of the SKUs is on Glovo yet: `glovo-portal.py find YOKO`.
3. Photos: upload each `<sku>.jpg` to postimages.org from a real Chrome page context, with *Do not resize* and *No expiration* (`reference/glovo/README.md` → "Image hosting"). Put each Direct link in column D.
4. Add the 12 products. Adding new products isn't scripted yet (glovo-portal skill §6). Either the portal's Add Products / bulk upload with this sheet, which goes through Glovo's review, or explore `createProductsRequest` / `createSimpleProductBatch` first. Write down what you learn, dated, in `reference/glovo/portal.md`. Before anything goes live, show the user the dry run or exactly what will be submitted, and get a yes.
5. Once they are live, set each one active, then check the prices: `glovo-portal.py prices --sku YOKO-1625 …` should show 0 changes against the sheet. Glovo may strip or alter SKUs; check that they stayed exactly `YOKO-16xx`.
6. ArmSoft price type 02 (the till's Glovo buyer 000008): import the 11 new 02 prices for codes 1626–1636, plus 1625 at 1,550. Build an XML like `final/armsoft-2026-11-09/glovo-prices-02.xml` from the "ArmSoft price 02" sheet and import it (armsoft-app skill).
7. Add the 12 rows to `final/glovo/siruk-glovo-products.xlsx` (the Glovo sheet of record). The Zoovet matches are already in `state/glovo-zoovet-matches.csv`.

Stock: ArmSoft has 1625 × 7, 1628 × 10 and 2 each of the rest, so all 12 can be switched on.
