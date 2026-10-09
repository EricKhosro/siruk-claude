# OpenCode setup

This project was built for Claude Code (`.claude/`, `CLAUDE.md`). OpenCode V2
reads most of that directly; this directory adds the few pieces it does not.
Nothing in `.claude/` was removed — Claude Code still works unchanged.

## How each piece is wired

| Thing | Where OpenCode finds it | Notes |
|---|---|---|
| Project instructions | `AGENTS.md` (repo root) | A **symlink** to `CLAUDE.md`. OpenCode V2 loads `AGENTS.md` only and ignores `CLAUDE.md`, so the symlink makes the existing handbook apply to both tools with no copy to keep in sync. |
| Skills | `.claude/skills/*/SKILL.md` | Auto-discovered by OpenCode's project-compatibility search. No copy needed. |
| Slash commands | `.opencode/commands/*.md` | `/add-products`, `/create-brand`, `/manage-attributes`, `/google-lens`. Each loads its skill via the `skill` tool. OpenCode does not turn a skill into a `/` command by itself, so these replace the Claude Code behaviour. |
| `attribute-manager` agent | `.opencode/agents/attribute-manager.md` | A **symlink** to `.claude/agents/attribute-manager.md`. OpenCode does not read `.claude/agents/`, and its file layout is the same (frontmatter + body = system prompt). The shared file carries `mode: subagent` for OpenCode and `name:` for Claude Code; each ignores the other's field. |
| MCP servers | `opencode.jsonc` (repo root), `mcp.servers` | `.mcp.json` is Claude Code's file and is not read. `chrome-devtools` is repeated there. |
| Permissions | `opencode.jsonc`, `permissions` | Demo work runs unattended; commands touching `api.siruk.am` (production) ask first. |

## Using it

The same entry points as before:

```
/add-products csv/armsoft-goods-not-on-siruk-2026-10-05.csv
/create-brand "Some Brand"
/manage-attributes add a value "In Jelly" to Food Texture
/google-lens Trixie Batik collar
```

You can also just describe the task; the skills are advertised to the model and
load themselves. To force one, mention it as `@add-products`.

The product-type spec skills (`toys`, `dry-food`, `wet-food`, `treats`,
`supplements`, `grooming`, `accessories`) are read by `/add-products` and
`/manage-attributes` as before; they need no command of their own.

## Adding a new skill

Drop it in `.claude/skills/<id>/SKILL.md` (or `.opencode/skills/<id>/SKILL.md`)
with a `description` in the frontmatter — it is picked up automatically. Add a
matching `.opencode/commands/<id>.md` only if you want a `/` command for it.

## Adding a new agent

Put it in `.opencode/agents/<id>.md` with `mode: subagent` in the frontmatter
(the body is the system prompt). Keep a single source of truth by symlinking
into `.claude/agents/` if Claude Code also needs it, as `attribute-manager`
does.

## Verifying

```sh
opencode debug agents          # attribute-manager should be listed, mode subagent
opencode mcp list              # chrome-devtools should connect
```
