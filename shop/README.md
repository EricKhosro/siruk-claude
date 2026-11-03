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

## One-time setup

1. Clone this repo; install Claude Code, `uv`, Python; ArmSoft signed in to
   database "Siruk"; computer use granted for ArmSoft.
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

## Every run

```
git pull
```

Then in Claude: `/receive-invoices` (or `/refund`, `/send-to-scale`). Afterwards commit only what the run
writes:

```
git add knowledge state final
git commit -m "Shop: received invoices"
git push
```

Never `git add -A` here — it would push the edited `CLAUDE.md`.

If `git pull` refuses because the office changed `CLAUDE.md`: put the
password line back (or `git update-index --no-skip-worktree CLAUDE.md` and
`git checkout CLAUDE.md`), pull, then repeat setup step 3.

## Limits

The deny list is a guardrail against mistakes, not a wall: Claude could still
reach the API another way, and the token on this machine has full admin
rights. If the developers can make a read-only admin user, use its token here.
