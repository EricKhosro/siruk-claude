---
name: ops-stock
description: Look at and correct stock in Siruk Ops with the siruk CLI — where the stock is and why, a write-off, a count, a transfer between locations, opening a sealed bag, reorder levels and the reorder list. Every write is a dry run first. Use when asked "where is my stock", to write off, count or move goods, open bags, or set what to reorder.
---

# Stock in Siruk Ops (office)

Who runs it: the office, with the owner's Claude workspace. Reads are free;
every write posts a stock document or changes a good, so it is a dry run first.

Read first: `reference/ops.md` and `reference/workflows.md` recipes 6, 7 and
8 — the commands are there. Short and plain with the user.

## 0. Before anything

`uv run --no-sync siruk ops doctor` → `health ok`, a `key`, a role that may do
the job (`ops stock` and `ops history` are for a manager's key). If it fails:
tell the user to ask the owner for a key and pipe it into `siruk ops token
set`; stop. Never ask for, type or print a key or password.

## 1. Where is my stock (recipe 8)

Answer from `goods list` / `goods show`, then `ops stock` and `ops history`
when asked why a number is what it is. Say which location and date. When siruk's
figure and Ops differ, Ops is right.

## 2. Change stock (recipe 6)

- Write-off: a reason (`damaged`, `expired`, `lost`, `other`) and a note.
- Count: what is on the shelf now, each good once; ask for the real count.
- Transfer: from one location to a different one.
- Open a bag: how many sealed bags, at which location.

Each is the bare command, shown to the user (goods, quantities, locations,
stock now and after), then `--apply <code>` on their yes to that run. A document
is saved as a draft first and posted second; show both dry runs. Posted
documents never change: a mistake gets a new document.

## 3. Reorder (recipe 7)

`goods set` takes `--reorder-mode`, `--reorder-point`, `--reorder-target` (pieces)
and `--low-stock-at`. `reorder show --due`, `build`, `lines` and `list` read and
shape the pending list; `reorder accept` (manager) makes a **draft** purchase
order and the CLI refuses it while `reorder.autoPlace` is on. The order itself
is placed with hafo by the owner, never here.

## 4. Check and report

`docs show <id>`, `goods show`, `goods list` after each write. One or two lines
to the user: what changed, the new stock.

## Never, from this command

- Type, print or ask for a key, token or password.
- Count, write off or move on a guess; use `--tag` or `--key` to repeat a write
  that already went through. A second `open-bag` after a successful one opens
  another bag, so check the count first.
- Repeat a write after exit 3 before running the check the message names.
- Place a hafo order, switch a setting, touch the HDM, a till sale, a refund,
  the Z report or the scale (`reference/ops.md` "The never-list").
- Run a `real-world` command without the owner's yes to that run.
