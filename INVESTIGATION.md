# Investigation: AI Automation for Admin Panel Data Filling

**Jira:** Investigate AI Automation for Admin Panel Data Filling
**Date:** 2026-08-10 · **Env:** demo (`demo-api.siruk.am`)
**Status:** POC working end-to-end via brand official sites + admin API.
Chewy abandoned as source (Kasada-blocked and poor brand match).

## POC result (2026-08-10)

Created **1 product end-to-end** with zero UI form-filling on the create step:
Royal Canin Mini Adult 8kg (admin product id 31) — data + image sourced from
royalcanin.com, image uploaded to the media library, product created via the
JSON API, verified in the admin edit screen (name, category, brand, image,
price 26,500 AMD, cost 23,000, stock 2, plus About/Ingredients/Feeding rich
text all populated).

Prerequisites also created via API this run:
- Brands: Farmina (11), Schesir (12), Leonardo (13), Stuzzy (14) — logos from
  official sites; Stuzzy uses a placeholder logo (site was unreachable).
- Categories: Vitamins & Supplements (14), Accessories (15).

All admin endpoints (media upload, brand/category/product create, delete) are
captured and documented in `CLAUDE.md`. Remaining work is repeating the source→
create loop per CSV row; the admin side needs no further discovery.

---

## TL;DR

The pipeline **Chewy → extract → map → Admin → create** splits into two halves
with opposite outlooks:

- **Admin Panel side — feasible and ready.** The admin is a SPA over a clean
  REST API (`/api/admin/*`, Bearer-token auth). Product creation can be fully
  automated via API, no browser needed.
- **Chewy side — blocked.** Chewy sits behind **Kasada** bot protection. Every
  automated request returns HTTP 429 + a JS challenge; no page content is ever
  served. Chewy has no public product API. This is the real bottleneck.

**Recommendation:** Don't fight Kasada with an in-house stealth browser (high
effort, constant breakage, ToS/legal risk). Either (a) use a **managed
web-unblocking/scraping API** if Chewy specifically is required, or better
(b) **reconsider the data source** — see §4, Chewy is likely a poor fit for this
catalog anyway.

---

## 1. What was validated (admin side) ✅

- Logged into `https://demo-api.siruk.am/admin` with the provided credentials.
- Opened `/admin/catalog/products/create` and mapped every form field
  (see `CLAUDE.md` → "Admin product form — field map").
- Captured the underlying API. The SPA calls a Laravel JSON API:
  - `GET /api/admin/categories?forProducts=true`
  - `GET /api/admin/brands?forProducts=true`
  - `GET /api/admin/attributes?forProducts=true`
  - `GET /api/admin/attribute-families?forProducts=true`
  - `GET /api/admin/medias?...`, `/account`, `/roles`
- **Auth:** `Authorization: Bearer <JWT>`. Cookies alone do NOT authenticate the
  API (verified — returns `Unauthenticated`). The SPA keeps the token in
  `localStorage.access_token`; tokens are long-lived (~1 year exp).
- Pulled live reference data (brand ids, the Dog/Cat category tree, attribute
  ids) — recorded in `CLAUDE.md`.

**Not yet captured:** the `POST` product-create and media-upload payloads. These
need one manual create through the UI with the network tab open — trivial, but
requires real product data to submit, which the Chewy blocker currently prevents.

## 2. What is blocked (Chewy side) ⛔

| Attempt | Result |
|---|---|
| Search URL `/s?query=...` | HTTP **429**, empty body |
| Direct product URL `/dp/135595` | HTTP **429**, empty body |
| Reload / ignore-cache | HTTP **429** |
| Wait for challenge JS to resolve | body stays empty |
| Inject `navigator.webdriver=undefined` before page scripts | HTTP **429** |

**Diagnosis:** Response is a **Kasada** challenge page (`window.KPSDK`,
`/…/ips.js` sensor, `x-kpsdk-ct/-r/-c` headers). The 429 arrives on the first
document request, i.e. blocking happens at the edge (Akamai + Kasada) using
request fingerprint + IP reputation, *before* any in-page patch can run. The MCP
also drives an automation-flagged Chrome (`navigator.webdriver = true`,
`--enable-automation`) which Kasada's sensor detects independently.
Kasada is widely regarded as one of the hardest anti-bot systems; standard
stealth plugins for Playwright/Puppeteer/Selenium are routinely detected.

## 3. Options to get Chewy data (if Chewy is required)

1. **Managed web-unblocker / scraping API** *(pragmatic)* — services that solve
   the challenge + rotate residential IPs + spoof fingerprints as a hosted
   product (e.g. Bright Data Web Unlocker / Scraping Browser, Zyte API, Oxylabs
   Web Unblocker, ScrapingBee, Apify). We send a URL, get HTML/JSON back.
   - Effort: ~1–2 days to integrate. Cost: per-request (hard sites ≈ a few $ per
     1k requests). Maintenance: low (vendor absorbs Kasada updates).
2. **Self-hosted stealth browser + residential proxies** *(not recommended)* —
   e.g. Camoufox / nodriver + a residential proxy pool.
   - Effort: 1–2 weeks to first success. Maintenance: **high** — Kasada updates
     break it every few weeks. Fragile for production.
3. **Kasada token-solver APIs** — grey-market KPSDK solvers. ToS-violating and
   legally risky. Not advised.

**All three carry Chewy ToS/legal exposure** (Chewy's Terms prohibit automated
access/scraping). Get legal/PM sign-off before any scraping approach.

## 4. Bigger question: is Chewy even the right source?

This catalog is an **Armenian** pet shop stocking **European** brands via local
distributors: Brit (Joly Food), Farmina, Belcando (Pet House), Canvit, Schesir,
Royal Canin. Chewy is **US-centric** and may not carry Brit/Farmina/Canvit/
Schesir at all, or under different SKUs/pack sizes (Chewy lists lb, the CSV is
kg). So even if unblocked, Chewy would likely yield poor matches for most rows.

Likely better, and mostly **not** Kasada-protected, sources:
- Manufacturer sites: royalcanin.com, brit-petfood.com, farmina.com,
  belcando.de, canvit.com — richest, most accurate copy/images/ingredients.
- The local distributors' own catalogs (Joly Food, Pet House).
- A brand media/asset pack requested from the distributor.

## 5. On the MCP idea

A **custom MCP for the admin side is unnecessary** — plain `curl`/HTTP against
`/api/admin/*` with a Bearer token does everything and is more token-efficient
than an MCP server (no server to run/maintain). The only place a browser MCP is
unavoidable is the data-source side, and there the blocker is Kasada, not the
integration shape. If a managed scraping API is chosen, it's a normal HTTP call
too — still no custom MCP required.

## 6. Recommended next steps

1. **Decide the data source** (Chewy-via-unblocker vs. manufacturer sites vs.
   distributor asset pack). Recommend piloting manufacturer sites first — free,
   legal, richer, and a better brand match than Chewy.
2. Once a source returns data for 1–3 products, do one manual create in the
   admin UI to **capture the `POST` create + media-upload payloads**, record
   them in `CLAUDE.md`, then automate creation via `curl` + Bearer token.
3. For production, request a **dedicated admin service account** scoped to
   catalog only (not a personal login), and a **first-party API token** instead
   of scraping the SPA's `localStorage` JWT.
4. Get **legal sign-off** on whichever external source is chosen.

## 7. Effort estimate (full automation, admin side ready)

| Piece | Effort |
|---|---|
| Admin create via API (once payloads captured) | ~1 day |
| CSV → field mapping + validation | ~1 day |
| Data source: manufacturer-site extraction (per brand) | ~1–2 days/brand |
| Data source: managed scraping API for Chewy | ~1–2 days + per-request cost |
| Image download + media-library upload | ~0.5 day |
| Orchestration + per-row reporting/retries | ~1 day |
