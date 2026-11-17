---
name: ops-goods
description: Set up a product's goods in Siruk Ops with the siruk CLI — sync the new product from siruk, set its fiscal name and ADG code, extra barcodes, a loose good's PLU, and its store or Glovo price and code per price type. Every write is a dry run first. Use after /add-products for a new product, or when asked to change a fiscal name, barcode, PLU or per-type price.
---

# Goods in Siruk Ops (office)

Who runs it: the office, with the owner's Claude workspace. Siruk owns the
product and **every price**; Ops owns stock, cost, barcodes, PLU, the fiscal
name and the ADG code (`reference/ops.md` "Who owns what").

Read first: `reference/ops.md` and `reference/workflows.md` recipes 1 and 2 —
the commands are there. Short and plain with the user.

## 0. Before anything

`uv run --no-sync siruk ops doctor` → `health ok`, a `key`, a manager or
warehouse person (`ops catalog sync` needs a manager). If not: tell the user to ask the owner for a key and pipe it
into `siruk ops token set`; stop. Never ask for, type or print a key or password.
Prices go to siruk: `siruk doctor` must pass too.

## 1. A new product (recipe 1)

The product is made with `/add-products` (`siruk create`, dry run first). Then
`siruk ops catalog sync` (dry run, show, `--apply`), `goods show` to find it,
`goods set` for the **fiscal name** (50 characters at most) and the **ADG
code**. Stock is not automatic: it comes by a receipt (`/ops-receiving`). Say
so to the user.

## 2. Codes and prices (recipe 2)

- Extra barcode: `goods barcode add` / `rm`. A loose good's PLU: `goods plu`.
- A store or Glovo price, compare-at or code: `siruk prices set … --type <code>`.
  The website price is the website's; take a price only from the pricing rules
  (`reference/pricing.md`) or the user, never at or below cost.
- `goods set-many` for many goods: one dry run, one code, shown in full.

Every write is the bare command, shown to the user, then `--apply <code>` on
their yes to that run. Check with `goods show` and `prices show`.

## Never, from this command

- Type, print or ask for a key, token or password.
- Invent a fiscal name, ADG code, barcode, PLU or price; the user or the
  product's source gives it.
- Set cost or stock here (cost comes from paid invoices, stock from documents).
- Merge goods (`goods-links link`) without the evidence and the owner's yes.
- Send to the scale, or touch the HDM, a till sale, a refund or the Z report
  (`reference/ops.md` "The never-list").
- Repeat a write after exit 3 before running the check the message names.
