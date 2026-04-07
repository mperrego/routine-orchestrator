# Coding Standards — Routine Orchestrator

## Code Style
- Use clear variable names — this is an early-stage project, readability matters
- Add comments explaining what each function does
- Keep functions small and single-purpose
- Print progress updates to terminal so it's clear what step is running
- 4-space indentation, PEP 8

## GUI / Tkinter Conventions
- Audio playback, TTS generation, subprocess calls, and `time.sleep` MUST run on a background daemon thread — never on the Tk main loop. Blocking the main loop freezes the UI.
- Use `customtkinter` for the main window and dialogs; fall back to standard `tkinter` for menus and file dialogs.
- Status bar updates and title bar updates from a worker thread should be marshaled back to the main loop via Tk's standard thread-safe mechanisms.

## Console Output (Windows)
- Never use Unicode characters (→, ✓, etc.) in `print` statements. Windows console encoding crashes on them and silently aborts the function. Use ASCII alternatives (`->`, `[ok]`).

## Do Not (full list)
- Do not delete or overwrite any output files without asking first
- Do not change the folder structure without discussing it
- Do not use libraries that require paid API keys without flagging it first
- Do not run scripts that make external API calls without confirming cost implications
- Never display, print, or log the contents of `.env` under any circumstances
- Never add SQLite or any database — this project is JSON-only by design
