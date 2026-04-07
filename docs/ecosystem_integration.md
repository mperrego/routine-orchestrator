# Ecosystem Integration — Routine Orchestrator

This project is part of the mperrego ecosystem. Mothership: github.com/mperrego/ecosystem-core
Global architecture context: see ecosystem-core/CLAUDE.md and ecosystem-core/docs/.

## Mothership Dispatch
On every push to master, `.github/workflows/notify_mothership.yml` reads `version.txt` and dispatches a `project-update` event to ecosystem-core. ecosystem-core then updates the global manifest and Master Sheet Tab 1 automatically.

## sync_core
- Pinned version: `sync_core-v1.1.0`
- Commit hash: `47d82a054fc87469ea9b3287a656c544b6a5e307`
- New in v1.1.0: `module_checker` — `get_active_modules()`, `is_module_active()`, `check_module_upgrades()`
- Import path: set `ECOSYSTEM_CORE_PATH` env var to the ecosystem-core folder
- **Only `manifest_reader` is imported** in this project — there is no DB, so DB-related sync_core modules are not used
- Do NOT update the pin without testing — always pin to a specific commit hash, never to "main" or "latest"

## Component Registry
Before writing any new utility function, check:
`ecosystem-core/component_registry/registry.json`

Relevant for this project:
- `db_connector` (status=promoted) — available if a DB is ever added (currently not used)
- `save_json` / `load_json` (status=stable) — could replace hand-rolled JSON persistence in `settings.json` and `Routines/*.json`

## Environment Variables
| Variable | Purpose |
|---|---|
| `ECOSYSTEM_CORE_PATH` | Path to ecosystem-core repo on local machine (required for sync_core import) |
| `ECOSYSTEM_PAT` | GitHub token for dispatch events (set as Windows env var) |

All secrets MUST be set as Windows env vars via `setx`. Never store real keys in `.env`.

## Connected Tools (MCP)
- GitHub: connected
- Google Drive: connected
- Tracker (Google Sheet): https://docs.google.com/spreadsheets/d/1jWYuZMoj-3VnyywgbnIzmzrvjAgyne8spazrEOl4TM8/edit

### MCP Registration Note
- MCP servers must be registered in `~/.claude.json` via `claude mcp add`
- `settings.json` files are NOT where MCP is registered (learned 2026-03-22)

## Master Sheet
Global ecosystem registry: https://docs.google.com/spreadsheets/d/1uT7J5Hp1kx3xGKQDft4Okptk4MQPXDQq89O9VPVVDs0/edit

## Version Tracking
- `version.txt` in the project root is the canonical version source.
- The `/handoff` command syncs the version from CLAUDE.md → `version.txt` before committing.
- On push, `notify_mothership.yml` reads `version.txt` → dispatches to ecosystem-core → updates manifest.json → updates Master Sheet Tab 1 automatically.
- Never edit `version.txt` manually — let `/handoff` manage it.
