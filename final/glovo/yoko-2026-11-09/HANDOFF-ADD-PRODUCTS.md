# YOKO × 12 — handoff: add the products on Glovo

2026-11-09. This picks up the original `HANDOFF.md` at step 4. Steps 3, 6 (XML
built, not imported) and 7 are done; the Glovo submission is not.

> **Update 2026-11-09 16:45:** titles rewritten in Zoovet's pattern (brand first, no «»),
> e.g. `YOKO չորացրած տավարի թոք փոքր ցեղատեսակի շների համար, 40 գ`. Submit with
> `scripts/glovo-add-products.py final/glovo/yoko-2026-11-09/yoko-glovo-2026-11-09.xlsx --brand YOKO --category 7145 --also YOKO-1627:7078 [--apply]`
> instead of the inline Option A script below.

## What is already done

| Step | State |
|---|---|
| 1. Token, skill, reference read | done — `whoami` OK, `find YOKO` → **0 rows**, none of the 12 SKUs is on Glovo |
| 2. No YOKO on Glovo | confirmed 2026-11-09 |
| 3. Photos on postimages.org | **done**, all 12 uploaded from a real Chrome page context, *Do not resize* + *No expiration*, each verified `500×500` and byte-identical to the local file |
| 4. Add the 12 products | **NOT DONE** — needs a signed-in portal session; everything is prepared below |
| 5. Set active + `prices` check | waits on 4 |
| 6. ArmSoft price type 02 | XML **built**: `final/armsoft-2026-11-09/glovo-prices-02-yoko-1625-1636.xml` (12 rows, unit 001, type 02, date 2026-11-09) — **not imported** |
| 7. Sheet of record | **done**: 12 rows appended to `final/glovo/siruk-glovo-products.xlsx` (rows 1641–1652) |

Column D of `yoko-glovo-2026-11-09.xlsx` is filled with the links below.

## The 12 rows (ready to submit)

| SKU | Price | Category (vendor id) | Image link (direct, 500×500) |
|---|---|---|---|
| YOKO-1625 | 1550 | 7145 Անուշեղեն Շների Համար | https://i.postimg.cc/YS8C85SV/YOKO-1625.jpg |
| YOKO-1626 | 2300 | 7145 Անուշեղեն Շների Համար | https://i.postimg.cc/CdyhzYvk/YOKO-1626.jpg |
| YOKO-1627 | 2700 | 7145 + 7078 Անուշեղեն Կատուների Համար | https://i.postimg.cc/fW1mx9pX/YOKO-1627.jpg |
| YOKO-1628 | 2700 | 7145 Անուշեղեն Շների Համար | https://i.postimg.cc/gc18vZQH/YOKO-1628.jpg |
| YOKO-1629 | 2700 | 7145 Անուշեղեն Շների Համար | https://i.postimg.cc/qBWy83Sw/YOKO-1629.jpg |
| YOKO-1630 | 2700 | 7145 Անուշեղեն Շների Համար | https://i.postimg.cc/RC2KcHyP/YOKO-1630.jpg |
| YOKO-1631 | 2700 | 7145 Անուշեղեն Շների Համար | https://i.postimg.cc/NfTTb0v4/YOKO-1631.jpg |
| YOKO-1632 | 2700 | 7145 Անուշեղեն Շների Համար | https://i.postimg.cc/28vvT5Nc/YOKO-1632.jpg |
| YOKO-1633 | 2300 | 7145 Անուշեղեն Շների Համար | https://i.postimg.cc/L6ffvsMS/YOKO-1633.jpg |
| YOKO-1634 | 2300 | 7145 Անուշեղեն Շների Համար | https://i.postimg.cc/m2MMVrGr/YOKO-1634.jpg |
| YOKO-1635 | 2700 | 7145 Անուշեղեն Շների Համար | https://i.postimg.cc/YCHFPwpq/YOKO-1635.jpg |
| YOKO-1636 | 2300 | 7145 Անուշեղեն Շների Համար | https://i.postimg.cc/htBmYqSj/YOKO-1636.jpg |

Titles, descriptions and Armenian sizes are in the `Glovo products` sheet of
`yoko-glovo-2026-11-09.xlsx` — use them verbatim (`name` = the title column).

**Why 7145 and not the sheet's section name.** The sheet's `Section 1`
(`Ոսկորներ, ջիլեր և բնական հյուրասիրություններ շների համար`) is a Pelican/Glovo
taxonomy name that **does not exist** in our vendor category tree (75 categories;
`glovo-portal.py categories --locale hy`). The tree has `7145 Անուշեղեն Շների
Համար` (dog treats) and `26752 Ոսկորներ և ձողիկներ` (bones/sticks). Every dried
meat/freeze-dried treat already on Glovo — Derevenskie Lakomstva, Trixie
freeze-dried, 8in1 — sits in `7145`; only dental bones/sticks sit in `26752`.
So 7145 for the 11 dog treats and 7145 + 7078 for the capelin (sold for cats too).
Still put the section name in the sheet's H/I columns for the Pelican upload.

## Option A — catalogue API (what to try first)

`createProductsRequest` files a review case; nothing is live until Glovo approves.
Access facts (dated 2026-11-09, also in `reference/glovo/portal.md`):
`ProductRequest` = `{sku, name, price, description, barcode, requestId,
imagesEncoded, categoryList}`; `imagesEncoded` takes **plain base64 JPEG** (no
`data:` prefix); `categoryList` = `[{id, name}]` of the **vendor** category.

`validateProductsRequest` is **not** a real validator — it answers `ok` for a
bogus category id, an empty category list and an SKU that already exists. Do not
trust it as a dry run; it only proves the payload parses.

Run this from the repo root with a fresh token (`python scripts/glovo-portal.py
whoami`). It is a dry run without `--apply`: it prints exactly what will be sent.

```python
# scripts/tmp-add-yoko.py — delete after use
import base64, json, sys, importlib.util, openpyxl
spec = importlib.util.spec_from_file_location("gp", "scripts/glovo-portal.py")
gp = importlib.util.module_from_spec(spec); spec.loader.exec_module(gp)
gp.TOKEN = gp.load_token()

CAT = {"7145": "Անուշեղեն Շների Համար", "7078": "Անուշեղեն Կատուների Համար"}
cats = {"YOKO-1627": ["7145", "7078"]}          # capelin: dogs + cats
ws = openpyxl.load_workbook(
    "final/glovo/yoko-2026-11-09/yoko-glovo-2026-11-09.xlsx", data_only=True)["Glovo products"]
products = []
for r in ws.iter_rows(min_row=2, values_only=True):
    if not r[0]: continue
    sku, title, desc, price = r[0], r[2], r[4], r[5]
    img = open(f"final/glovo/yoko-2026-11-09/{sku}.jpg", "rb").read()
    products.append({
        "sku": sku, "name": title, "price": float(price), "description": desc,
        "barcode": None, "requestId": "siruk-" + sku,
        "imagesEncoded": [base64.b64encode(img).decode()],
        "categoryList": [{"id": c, "name": CAT[c]} for c in cats.get(sku, ["7145"])]})

print(f"{len(products)} products, "
      f"{sum(len(p['imagesEncoded'][0]) for p in products)//1024} KB of base64")
for p in products:
    print(p["sku"], p["price"], [c["name"] for c in p["categoryList"]], p["name"][:60])

if "--apply" not in sys.argv:
    sys.exit("\ndry run — add --apply to file the review case")

M = """mutation($v: VendorIdentifier!, $r: ProductsRequest!){
  createProductsRequest(vendorIdentifier:$v, productsRequest:$r){
    __typename
    ... on CreateProductsRequestSuccessful { status }
    ... on CreateProductsRequestErrorDuplicatesFound { products { __typename } } } }"""
print(gp.gql(M, {"v": gp.vendor(), "r": {"products": products}}))
```

Then check the case: `productsRequests` → `jiraIssueKey`, and
`productsRequestDetails(vendorIdentifier, jiraIssueKey)` for per-product status
(`reference/glovo/portal.md` → "Adding NEW products through the API").

## Option B — the portal's Add Products / bulk upload

Sign in at `portal.glovoapp.com` in the built-in browser (the user does the
two-step login; never type the password). Store Management → **Add Products**,
upload `yoko-glovo-2026-11-09.xlsx` (column D now holds the Direct links). That is
the Pelican path and it also goes through Glovo's review. Capture the request in
`tools.browser.network.list` while submitting — that is the payload `createSimple
ProductBatchCsv` expects, worth writing down.

## After Glovo approves them

1. **Check the SKUs survived**: `python scripts/glovo-portal.py find YOKO-1625`.
   Onboarding through Excel ate leading zeros once; `YOKO-16xx` has no leading
   zeros, but confirm all 12 are exactly `YOKO-1625 … YOKO-1636`.
   If a SKU changed: `glovo-portal.py --help` → `fix-skus` only handles the
   zero-stripped form; otherwise `productUpdateSKU`.
2. **Switch them on** (ArmSoft stock: 1625 ×7, 1628 ×10, 2 of the rest — all 12
   can be on):
   ```
   python scripts/glovo-portal.py set-active YOKO-1625 YOKO-1626 YOKO-1627 YOKO-1628 \
     YOKO-1629 YOKO-1630 YOKO-1631 YOKO-1632 YOKO-1633 YOKO-1634 YOKO-1635 YOKO-1636 \
     --on --note "new YOKO treats, stock in ArmSoft"        # dry run
   ```
   then the same with `--apply`.
3. **Prices must already match** the sheet of record (rows 1641–1652):
   ```
   python scripts/glovo-portal.py prices --sku YOKO-1625 YOKO-1626 YOKO-1627 YOKO-1628 \
     YOKO-1629 YOKO-1630 YOKO-1631 YOKO-1632 YOKO-1633 YOKO-1634 YOKO-1635 YOKO-1636
   ```
   It should report **0 changes**. A change means the submission took a different
   price (or a wrong SKU match) — investigate before applying.

## ArmSoft — Glovo price type 02

`final/armsoft-2026-11-09/glovo-prices-02-yoko-1625-1636.xml` (12 rows, `<Unit>001`,
`<PriceType>02</PriceType>`, `<Date>2026-11-09T00:00:00`). Built from the
`ArmSoft price 02` sheet of `yoko-glovo-2026-11-09.xlsx`; same shape as the full
`glovo-prices-02.xml` in that folder. Import with the `armsoft-app` skill
(Import → Exchange XML, "Glovo price type 02", branch/database **Siruk**). The
goods 1625–1636 already exist in ArmSoft (`new-goods-1626-1636.xml` was imported
earlier today), so this import only adds the 12 prices. Do it **after** Glovo goes
live, so the till and Glovo never disagree.

## Notes / gotchas

- `.glovo-token` lives 4 h; re-capture from the built-in browser (skill → Token).
  Never refresh it from a script.
- Photos cache: `.siruk-cache/glovo/postimages-yoko-2026-11-09.json` (sku → direct
  link), so a re-run never re-uploads.
- `final/armsoft-2026-11-09/new-goods-1626-1636.xml` has Armenian names written as
  `?` (an earlier encoding slip). Not ours to fix here, but if ArmSoft shows
  question marks for these 12 goods, re-export it as UTF-8.
- Sheet of record: 12 new rows at 1641–1652 of
  `final/glovo/siruk-glovo-products.xlsx`; `prices` will list them under "our SKUs
  not on Glovo" until Glovo approves them. That is expected.
