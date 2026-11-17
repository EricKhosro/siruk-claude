---
name: ops-receiving
description: Book delivered goods into Siruk Ops stock with the siruk CLI — a supplier e-invoice, a paper invoice (manual receipt) or a purchase order. Every write is a dry run first and goes in only on the user's yes. Use when asked to receive an invoice or a delivery in Ops, raise or receive a purchase order, or "put the delivery into stock". The ArmSoft shop-computer flow is receive-invoices, not this.
---

# Receive deliveries in Siruk Ops (office)

Who runs it: the office, with the owner's Claude workspace. What it does:
supplier invoice or purchase order → a posted Ops receipt, so the goods are in
stock and the supplier is owed. It never creates a product or sets a price.

Read first: `reference/ops.md` (who owns what, units, the write protocol, the
never-list) and `reference/workflows.md` recipes 3, 4 and 5 — the commands are
there, not repeated here. Speak to the user short and plain; no codes or rule
numbers unless asked.

## 0. Before anything

- `uv run --no-sync siruk ops doctor` → `health ok`, a `key`, a role that may
  do the job. If not: tell the user "ask the owner for an Ops key and pipe it
  into `siruk ops token set`" and stop. Never ask for, type, print or look up
  a key or a password.
- Read the target line of every dry run: production or not.

## 1. Pick the recipe

- A supplier e-invoice → recipe 3. The invoice is what arrived; never receive
  from a hafo order, never receive an invoice twice.
- A paper invoice → recipe 4 (`docs new receipt`, then `docs post`).
- A purchase order → recipe 5 (`po receive`).

## 2. Match every line, or stop

Each line must land on **one good** with the quantity in base units. A line
with no good, two candidates, or a unit you cannot place is **unknown**: do not
guess, do not post part of an invoice. Tell the user which lines, and that the
product has to be added first (`/ops-goods`, `/add-products`).

## 3. Write: dry run, show, apply

Every write is the bare command first. Show the user what it will do in plain
words (supplier, invoice, each line, quantity, cost, total, stock now and
after) and which server. Only on their yes to *that* run, repeat it with
`--apply <code>`. A post (`einvoices post`, `docs post`, `po receive`) cannot be
undone; the draft before it can.

- Exit 1 with a new dry run: the plan changed; show it again.
- Exit 3: the outcome is unknown. Run the check the message names; repeat
  nothing until it shows the write did not happen.

## 4. Check and report

`einvoices show`, `docs show`, `po show` and `goods show` say what landed. Two
lines to the user: what is now in stock, what is waiting and why.

## Never, from this command

- Type, print, ask for or store a key, token or password; log in anywhere.
- Run `einvoices pull`, `outbox resend` or any `real-world` command without the
  owner's yes to that run.
- Place a hafo order, acknowledge a replacement invoice, touch the HDM, a till
  sale, a refund or the Z report (`reference/ops.md` "The never-list").
- Use `--override`, `not-stock`, `goods-links link` or `einvoices settle` on
  your own judgement.
- Apply with a code from an earlier run, repeat a write after exit 3 before
  checking, or loop a write.
- Set a price or edit a product: that is siruk's (`/ops-goods`).
