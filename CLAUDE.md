# CLAUDE.md — Routine Orchestrator

## What this project does
A GUI application for building and running automation routines — sequences of audio playback, TTS announcements, timed waits, and external Python scripts. Designed to be triggered via voice commands (e.g. "Alexa play X") by passing a routine name as a CLI argument, which auto-loads and runs it then closes.

## Environment
- OS: Windows 11, PowerShell terminal inside VS Code
- Python: 3.12.10
- Path: `C:\Users\mperr\My Drive\Python Programs\Setting Up Python Routines`
- GitHub: https://github.com/mperrego/routine-orchestrator
- Activate venv: `venv\Scripts\activate` (PowerShell) or `source venv/Scripts/activate` (bash)

## How to run
- Run GUI: `python Orchestrator_main_gui.py`
- Run routine from CLI (auto-run + auto-close): `python Orchestrator_main_gui.py RoutineName`
  - RoutineName matches a JSON file in `Routines/` (e.g. `PlaySilvaMeditation`)
- Install dependencies: `pip install -r requirements.txt`

## Stack
Python 3.12 · customtkinter · tkinter · pygame · pydub · gTTS · pyttsx3 · pychromecast · threading · subprocess

## Current status
- Version: see `version.txt` (canonical) — currently v9.4
- Currently working on: (updated by `/handoff`)
- All core features working: GUI build/edit/save/load/run, audio (MP3/WAV/M4A), Cast playback, TTS announcements, Wait actions, external scripts, CLI auto-run, folder bookmarking, timed playback, status bar, title bar with unsaved-changes indicator, Save/Save As split, speaker fallback

## HARD RULES — non-negotiable
- Never read, print, or log secrets (or `.env` contents) under any circumstance
- All secrets are Windows env vars (`setx`) — never hardcoded
- **JSON-only persistence — do NOT add SQLite or any database**
- Audio playback / TTS / subprocess / sleeps run on a background daemon thread — NEVER block the Tk main loop
- Never delete or overwrite user routine files without confirmation
- Never use Unicode characters (→, ✓, etc.) in `print` statements — Windows console crashes on them
- Never add dependencies without asking
- Never use libraries with paid API keys without flagging it first

## Action types
Audio | Announcement | Wait | Script — see `docs/architecture.md` for details

## sync_core
Pinned to commit `47d82a054fc87469ea9b3287a656c544b6a5e307` (v1.1.0).
Only `manifest_reader` is imported (no DB in this project).
Set `ECOSYSTEM_CORE_PATH` env var to the ecosystem-core folder.
Full integration details → `docs/ecosystem_integration.md`.

## How I want you to work
- Read existing code before changing it
- Explain approach in 1–2 sentences before implementing
- Small focused changes, not rewrites
- Discuss vision in chat BEFORE entering Plan Mode (do not auto-enter)
- Confirm the plan before switching to implementation
- Build one phase at a time, test before moving to the next
- Be direct and concise

## Standing instructions
- AUTO-HANDOFF: run `/handoff` at session start
- After any task: commit + push + update tracker
- `/handoff` appends a date-stamped session note to `docs/sessions/{YYYY-MM}.md` (NOT to CLAUDE.md)
- The only field in CLAUDE.md that `/handoff` may mutate is "Currently working on" under Current status
- Rules learned from mistakes → `docs/rules_from_mistakes.md`
- Before writing any utility function: check `ecosystem-core/component_registry/registry.json`

## Pointers (read these when relevant)

| Doc | When to read |
|---|---|
| `docs/architecture.md` | Project structure, action types, threading model, CLI auto-run |
| `docs/coding_standards.md` | Code style, GUI/Tkinter conventions, full "Do not" list |
| `docs/rules_from_mistakes.md` | Before fixing recurring bugs |
| `docs/ecosystem_integration.md` | sync_core, mothership dispatch, env vars, MCP, master sheet |
| `docs/sessions/YYYY-MM.md` | "What did we do on X?" |

## Ecosystem
Part of the mperrego ecosystem. Mothership: github.com/mperrego/ecosystem-core
Master Sheet: https://docs.google.com/spreadsheets/d/1uT7J5Hp1kx3xGKQDft4Okptk4MQPXDQq89O9VPVVDs0/edit
Project tracker: https://docs.google.com/spreadsheets/d/1jWYuZMoj-3VnyywgbnIzmzrvjAgyne8spazrEOl4TM8/edit
