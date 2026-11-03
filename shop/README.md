# Shop computer setup

The shop computer runs three commands:

- **`/receive-invoices`** (skill: `.claude/skills/receive-invoices/SKILL.md`)
  pulls new supplier e-invoices in ArmSoft and posts the warehouse receipt
  when every line is a good Siruk already sells. An invoice with a new
  product is left for the office (`state/open-items.csv`).
- **`/refund`** (skill: `.claude/skills/refund/SKILL.md`) refunds a till
  sale — one Վերադարձ (Կտրոն) against the original HDM receipt, printed on
  the register attached to this computer (it doesn't print from the office).
- **`/send-to-scale`** (skill: `.claude/skills/send-to-scale/SKILL.md`)
  sends every ArmSoft good to the Axiom label scale on the shop network
  (192.168.0.99), e.g. after the office changes a per-kg price.

## Before setup (office, once)

- The shop signs in to GitHub with **its own account or a fine-grained token
  limited to this repo** — not the office owner's account (the repo holds the
  admin login and API setup).
- On GitHub, **protect `main`**: pull request required, no direct pushes,
  no force pushes. That is what really keeps the shop off `main`; the rules
  below only ask Claude to.

## One-time setup

1. Install Git, the GitHub CLI (`gh`), Python, `uv` and Claude Code. Sign in:
   `gh auth login` (the shop's account), then Claude. Clone this repo and run
   `uv sync` in it. ArmSoft signed in to database **Siruk** (not
   TestAPI_SIRUK); computer use granted for ArmSoft (ՀԾ-Առևտուր). Check the
   scale: `Test-NetConnection 192.168.0.99 -Port 33581` → True.
2. Copy the two lock-down files into place (both are gitignored there):

   ```
   copy shop\settings.local.json .claude\settings.local.json
   copy shop\CLAUDE.local.md CLAUDE.local.md
   ```

   `settings.local.json` blocks every Siruk write tool, the import / brand /
   attribute / ArmSoft-sync skills, the `siruk` CLI and the write scripts.
   `CLAUDE.local.md` tells Claude it is talking to the seller.
3. Remove the admin password line from `CLAUDE.md` on this machine, then
   `git update-index --skip-worktree CLAUDE.md` so the edit is never
   committed or pushed.
4. Someone from the office logs in to the admin once so `.siruk-token` exists.
   The token expires; the seller can't renew it.
5. First runs with someone from the office there: `/receive-invoices`,
   `/send-to-scale` (show Claude the steps its skill still marks *unseen*),
   `/refund` when a real case comes.

## Every run — a branch and a pull request

The seller just types the command (`/receive-invoices`, `/refund`,
`/send-to-scale`); Claude does the git part itself, per `CLAUDE.local.md` →
"Git on this computer":

1. Start: `git switch main`, `git pull`, then a new branch
   `shop/<date>-<job>` (e.g. `shop/2026-11-04-receive`; `-2` if it exists).
   One branch per run, never a long-lived one — the office edits the same
   notes files, and an old branch would clash.
2. End: commit **only the files the run wrote** (`knowledge/`, `state/`,
   `final/`), push the branch, `gh pr create --base main` with what was done.
3. The office reviews and merges the pull request, the same day if it can.
   The shop never merges and never pushes `main`.

Never `git add -A` here — it would push the edited `CLAUDE.md`.

An earlier shop pull request that isn't merged yet is fine: the new run still
starts from `main` (ArmSoft itself, not the notes, decides whether an invoice
was already received), and the office settles any clash in the notes when it
merges.

When the office changes `shop/CLAUDE.local.md` or `shop/settings.local.json`,
someone from the office copies them into place again (setup step 2); Claude
notices the copies are stale after a pull and says so, but doesn't copy them
itself.

If `git pull` refuses because the office changed `CLAUDE.md`: put the
password line back (or `git update-index --no-skip-worktree CLAUDE.md` and
`git checkout CLAUDE.md`), pull, then repeat setup step 3.

## Limits

The deny list is a guardrail against mistakes, not a wall: Claude could still
reach the API another way, and the token on this machine has full admin
rights. If the developers can make a read-only admin user, use its token here.
