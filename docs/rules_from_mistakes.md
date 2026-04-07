# Rules From Mistakes

> Add new rules here with the date learned. Never add session-specific rules
> directly to CLAUDE.md — they belong here.
>
> Format: `[YYYY-MM-DD] never do X because Y`

- [2026-03-31] Never use Unicode characters (→, etc.) in print statements — Windows console encoding crashes on them, silently aborting entire functions
- [2026-03-22] MCP servers must be registered in `~/.claude.json` via `claude mcp add` — `settings.json` files are NOT where MCP is registered
