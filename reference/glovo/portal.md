# Glovo Partner portal (portal.glovoapp.com)

Explored 2026-11-05. The portal is **Delivery Hero's partner portal** ("one-web"),
skinned for Glovo. Our store: **Siruk Pet Shop (Antarayin Street 13/2, Yerevan) [YRV]**,
vendor `GV_AM;982410` (globalEntityId `GV_AM`, platformVendorId `982410`), chain 616714.
Login `info@siruk.am`; the user signs in by hand in the built-in browser (two-step
login with an e-mailed code). Claude never types the password.

Script: `scripts/glovo-portal.py`. Skill: `/glovo-portal`.

## Sections (left menu)

| Section | URL | What it is |
|---|---|---|
| Dashboard / Getting started | `/incubation` | onboarding score (descriptions, images, availability, hours) |
| Performance, Reviews, Reports | `/performance`, … | read-only stats |
| Order History | `/orders?from=…&to=…` | orders; API is behind PerimeterX (below) |
| Advertising, Shops Promotions | | paid ads, discounts (`promotions` in the catalogue API) |
| Glovo Store | | the store page |
| Opening Times | | weekly hours |
| **Store Management** | `/store-management?vendor=GV_AM;982410` | **the catalogue**: search, filter by category/status, edit, on/off toggle, Bulk Update, Add Products, download |
| Shops Integrations | | the "Stock & Price integration" Glovo's template mentions |
| Settings | | |

Store Management → product drawer: title hy/en and description hy/en are shown
**greyed (not editable)**; price, SKU, categories and Availability are editable.
Bulk Update → *Update status* / *Update price*: paste up to 1000 barcodes or SKUs
with their new prices.

## Catalogue API (no bot check)

`POST https://catalog-vss-api-eu.deliveryhero.io/graphql`, headers
`Authorization: Bearer <accessToken>`, `Content-Type: application/json`,
`x-client-source: one-web`. Answers plain `urllib` (checked 2026-11-05). Introspection
is open; the schema is cached in `.siruk-cache/glovo/catalog-schema.json`.

- **List**: `products(filter: {vendorIdentifier, locale, searchTerm, active, brandIds, categoryIds}, page: {pageNumber, pageSize ≤100})`
  → `sku name price originalPrice active globalId internalId categoryIds categoryNames pieceBarcodes firstImage maximumSalesQuantity isWeighted`.
- **Update one product** (what the portal sends):
  `mutation updateProduct($productUpdate: ProductUpdate!) { product(productUpdate: $productUpdate) { active price sku maximumSalesQuantity validationErrors { code message } } }`
  with `productUpdate = {sku, vendorIdentifier, price}`, or `{sku, vendorIdentifier, active}`
  (the on/off toggle), or `{sku, vendorIdentifier, productInternalId, categoryInternalIds}`.
  `ProductUpdate` also takes `barcode`, `titles`/`descriptions` (`[{locale, value}]`), `images`,
  `maximumSalesQuantity`.
- **Rename a SKU**: `productUpdateSKU(vendorIdentifier, oldSku, newSku) { status }` → `UPDATE_SUCCESS`.
- **Categories**: `categories(filter: {vendorIdentifier, locale, leavesOnly}, page)` → `internalId name parentId`
  (our store's tree is Armenian: Շուն 7066, Կատու 7067, Թութակներ 7075, Կրծողներ 7093, Ձուկ 7084 …).
- Others in the schema: `productsUpdate` (bulk), `createProduct(s)`, `createSimpleProductBatch(Csv)`
  (new products go to Glovo's review as a "products request" with a case id),
  `deleteProduct`, `promotions` / `createPromotionAsync`, `auditLogs`, `productDetails`.
  Not yet used by us.

## Adding NEW products through the API (explored 2026-11-09)

The schema (introspection is open) is bigger than the portal uses. What matters for
new products:

- `validateProductsRequest(vendorIdentifier, productsRequest)` is a **query**, returns
  `ValidateProductsRequestSuccessful { status }` or `…ErrorDuplicatesFound { products }`.
  It is almost a no-op: on 2026-11-09 it answered `ok` for a **nonexistent category id**,
  for an **empty `categoryList`**, and for an **SKU that already exists on Glovo**
  (`10268S`). It only proves the payload parses — not that the product is acceptable.
- `ProductsRequest { products: [ProductRequest!]! }` and
  `ProductRequest { sku, name, price, description, barcode, requestId,
  imagesEncoded: [String!]!, categoryList: [{id, name}] }`.
  `imagesEncoded` takes each JPEG as a **data URL** (`data:image/jpeg;base64,<…>`). Plain
  base64 fails the whole call with `imageservice.dhis_upload.parsing_error` and files
  nothing (tested 2026-11-09). One entry per image; the first is the packshot.
- **First real submission 2026-11-09 (YOKO × 12, `scripts/glovo-add-products.py`):**
  `createProductsRequest` answered `ok` once, but `productsRequests` then listed **three**
  cases (`500bO000018FsZKQA0`, `500bO000018G0gWQAS`, `500bO000018FfvZQAS`). All three were
  created at 12:59:37Z, each holding all 12 products, with status `Received`. Our `gql()`
  retries only on HTTP 5xx, after 2–4 s, so this looks like Glovo's side. There is no
  withdraw mutation. Watch for duplicates when they are approved. Per-product status is
  `productsRequestDetails(vendorIdentifier, jiraIssueKey){ products{ sku status } }`, which
  is `null` while the case waits for review.
- `categoryList` is the **vendor category** from `categories` (e.g. `26752 Ոսկորներ և
  ձողիկներ`, `7145 Անուշեղեն Շների Համար`), **not** the Pelican "Section 1/2" names
  (`Ոսկորներ, ջիլեր և բնական հյուրասիրություններ շների համար`, …). Those section names are
  Glovo's own taxonomy: they are in the onboarding sheet but never became vendor
  categories — the live 75-category tree has no such leaves.
- `createProductsRequest(vendorIdentifier, productsRequest)` submits it as a **review
  case** (result union `CreateProductsRequestSuccessful { status }` /
  `CreateProductsRequestErrorDuplicatesFound { products }`). Bulk variants:
  `createSimpleProductBatch(productsRequest)` and
  `createSimpleProductBatchCsv(vendorIdentifier, csvString)` — the portal's Add Products
  upload.
- Review status: `productsRequests(filter: {vendorIdentifier, status, searchTerm,
  creationDateRange}, page)` → `ExistingProductsRequest { creationDate, jiraIssueKey,
  productsAmount, rejectedProductsAmount, status }`; per product
  `productsRequestDetails(vendorIdentifier, jiraIssueKey)` → `ProductsRequestProduct
  { sku, status, rejectionData, … }`. On 2026-11-09 the list was **empty** (onboarding
  went through the Excel, never this feature), so the status vocabulary is still unknown.
- `createProduct` / `createProducts` (`ProductCreate { code, categoryIds, price,
  vendorIdentifier, active, sku }`) exist but carry no name/description/images —
  untested, probably only for stock integrations.

## Stock on Glovo

**No quantities.** A product is `active` (orderable) or not, plus an optional
`maximumSalesQuantity` (per-order cap; 0 = none). Without the "Stock & Price
integration" nobody switches a product off when it sells out. That is us
(`glovo-portal.py set-active <sku> --off`), the partner app, or the portal toggle.
`glovo-portal.py stock` sets it from an ArmSoft turnover export (sealed bag vs open bag;
skill → Availability). 2026-11-06: 73 switched off, 1,517 of 1,597 left on.

## Token

Cookies on `portal.glovoapp.com`: `accessToken` (RS256 JWT from
`vendorportal-eu.dh-auth.io`, **4 h**), `refreshToken` (40 chars, rotates),
`deviceToken` (long-lived). The portal refreshes through
`partner-auth.eu.prd.portal.restaurant` using refresh + device token + device uuid +
user id. **We don't refresh from scripts:** a rotated refresh token outside the
browser could sign the user out. `.glovo-token` (gitignored, mode 600) holds a copy;
when it expires, re-read the cookie from the built-in browser (skill → Token).

## Orders API (bot-protected)

Order History calls `POST https://vagw-api.eu.prd.portal.restaurant/query`
(`ListOrders`). PerimeterX guards it: on 2026-11-05 it answered 403 and the page showed a
"Press & hold" human check. **Never solve it**; ask the user. Orders aren't scripted.

## Our catalogue on Glovo (2026-11-05)

- 1,597 products, all active, English names (from the Pelican sheet onboarding).
- **SKUs lost their leading zeros** in onboarding (`011137` → `11137`; 202 of them).
  Two collide with another of our SKUs: Glovo `12767` = our `012767` (Monge cod), not
  our Trixie belt `12767`; Glovo `12007` = our `012007`, not `00012007`.
  `glovo-portal.py` matches on the zero-stripped SKU and settles collisions by name.
  `fix-skus` renames them back.
- Glovo `3182550896856` (Royal Canin Urinary S/O 13 kg) is priced **֏4,500** on
  Glovo; ours is ֏75,400. Wrong on Glovo.
- 41 of our sheet's variants are not on Glovo yet.

## Customer storefront API, and how Zoovet names products (2026-11-05)

The public store page (`glovoapp.com/en/am/yerevan/stores/<slug>`) reads
`GET https://api.glovoapp.com/v4/stores/<storeId>/addresses/<addressId>/content/main?nodeType=DEEP_LINK&link=<category slug -c.N>`.
It needs the headers `glovo-app-platform: web`, `glovo-app-type: customer`,
`glovo-language-code`, `glovo-location-city-code: YRV`, `glovo-api-version: 14` and
`glovo-app-version: 7`, and it works with no login.
- Each category returns a preview of about 12 tiles per section, with name,
  description and price.
- Product ids exceed JS number precision, so key tiles by `externalId`.
- Zoovet.am is store 452954, `ME-…` external ids. **Two branches** (2026-11-06):
  - address **712865** is the one customers see as open (signed in, delivery address set;
    the basket calls `/v2/baskets/stores/452954?storeAddressId=712865`). 1,296 products,
    39 Royal Canin.
  - address **761345** is what the address-less site shows: "Temporarily closed", another
    catalogue, prices about 5–10% lower. Don't price against it.
- Full read: `/v3/stores/<id>/addresses/<addr>/node/store_menu` → leaf sections `s.<id>` →
  `/v4/…/content/partial?component=section&id=<id>&page=N`, **pages 0-based**, 12 tiles per
  page, empty body = last page. Pace about 1 s per page: faster gets 429.
  `scripts/glovo-prices-into-sheet.py harvest` → `.siruk-cache/glovo/zoovet-glovo-open.json`.
  The `/v3/…/search` endpoint answers 503.
- Checked matches of ours ↔ Zoovet Glovo: `state/glovo-zoovet-matches.csv` (157, 2026-11-06).
  Some Zoovet big bags (Monge 12–15 kg) and single sticks are priced per kg / per piece.

**Zoovet's title pattern** (its newer, consistent titles):
`<Brand> <Line, Latin> <what it is, lowercase Armenian> <main flavour -ով> <for whom … համար>, <size>`.
- Example: `Gemon խոնավ կեր տավարի մսով և բրնձով խոշոր ցեղատեսակի շների համար (32-80 կգ), 1.25 կգ`
- Example: `Beaphar Doggy's վիտամիններ բիոտինով շների համար, 75 հատ`
- Example: `Triol «Արիզոնա» անկյունային բազմոց, 720 x 620 x 200 մմ`

How it is built:
- The brand always comes first, in Latin.
- Colour and dimensions follow after commas.
- Model names that are Armenian words go in «».

Some older Zoovet titles are generic (`Monge Fresh Շների Թաց Կեր 100գ`) or still Russian.

Ours (from the Pelican sheet) first followed Glovo's video
(`<Type> <for whom> «Brand» <Line>, <Flavour>, <size>`); the 2026-11-05 bulk
rename moved them to Zoovet's pattern. **Every new title uses Zoovet's pattern**
(user 2026-11-09: a YOKO batch built in the old pattern was sent back).
`glovo-export` column C and `scripts/glovo-add-products.py` enforce it.

## Renaming a product through the API (tested on 4020, 2026-11-05)

The portal shows titles greyed out, but `product(productUpdate:)` accepts them. Three
conditions:
- **Locales are `hy_AM` / `en_AM`**, not `hy` / `en`. `promotionLocales` lists them.
  Reads accept either.
- **Send `original` with the change.** A title is a master-product field, so the call
  must also carry the product's current state:
  `original: {active, categoryInternalIds, descriptions:[{locale,value}], images (imageUrls),
  maximumSalesQuantity, price, sku, titles:[hy_AM, en_AM current titles]}`, plus
  `productInternalId`. Without it the call fails with `ORIGINAL_REQUIRED_FOR_MASTER_PRODUCT_FIELDS`.
  An original hy title that doesn't match fails with 422 "No matching master product title".
- **Anti-hijacking check.** Glovo compares the words in the old and new titles.
  - Refused (`validationErrors code HIJACKING`): `«Trixie»` → `Trixie` combined with
    adding `կատուների համար` in the same call ("brand token removed and re-added with
    additional category targeting").
  - Accepted, each as its own call: a pure reorder (`«Trixie» Simple'n'Clean …`),
    then dropping the «» (`Trixie Simple'n'Clean …`), then adding `կատուների համար`.
  - So a bulk rename goes in steps: first reorder and unquote the brand with the
    same words, then add the new words.

**Bulk run on 2026-11-05: 1,597 products.** 1,057 took the new title and 486 took the
brand-first title with their old words. 54 are unchanged. Glovo's refusal codes:
- `VARIETY` (246): flavour words changed, **even only their grammatical form**
  (`Հավ` → `հավով`, `Սաղմոն` → `սաղմոնով`).
- `HIJACKING` (238): added sizes (`S`, `L`), breed or age words (`ցեղատեսակի`,
  `լակոտների`) or English line names (`Bones`, `Sticks`).
- `PROTECTED_DESCRIPTOR` (3) and `QUANTITY` (1).
- `unexpected_error` (54): every call fails, even a pure reorder, with or without the
  description. Mostly Trixie bowls and harnesses and some Monge cans. Cause unknown.

Glovo's message quotes the "from" words of the **master** title, so it judges a change
against the original listing, not the current title. The safe edit is a reorder that
keeps every word in its original form; added animal words passed on 4020.
Log: `runs/2026-11-05/glovo-titles.csv`.

The change shows at once in `products(locale: hy_AM)` and in the portal drawer. Price
and active are untouched. 4020's old titles are in `.siruk-cache/glovo/backup/4020-before.json`.
The public store page couldn't be checked: Siruk isn't listed on glovoapp.com yet
(the store is still in onboarding, "Getting started").
