# Session Handoff

Perform a full session handoff by completing these steps in order:

## Step 1 — Read CLAUDE.md
Read the project CLAUDE.md file at the project root to load current status, known issues, rules, and standing instructions.

## Step 2 — Read the Google Sheets Tracker
Use WebFetch to read the routine-orchestrator tracker spreadsheet:
URL: https://docs.google.com/spreadsheets/d/1jWYuZMoj-3VnyywgbnIzmzrvjAgyne8spazrEOl4TM8/edit

Read all tabs to get the current task status, progress, and any blockers.

## Step 3 — Sync version.txt
Read the CLAUDE.md "Current status" section and extract the version number (e.g. `v8.5` → `8.5`).
Write that version (without the `v` prefix) to `version.txt` in the project root.
This ensures `notify_mothership.yml` dispatches the correct version to ecosystem-core on push,
which in turn updates `manifest.json` and the Master Tracker spreadsheet automatically.

## Step 4 — Append session note + Backup
1. Compute the current year-month dynamically (e.g. `2026-04`).
2. Open `docs/sessions/{YYYY-MM}.md` (create it with an `# Session Notes — Month YYYY` header if missing).
3. Append a date-stamped entry summarizing what was done this session. NEVER overwrite — always append.
4. If there are uncommitted changes: stage all changes, commit with a descriptive message, and push to GitHub.
5. Update the tracker spreadsheet with the commit details (date, summary of changes).
6. The ONLY field in CLAUDE.md that `/handoff` may mutate is "Currently working on" under Current status. NEVER write session notes into CLAUDE.md — they live exclusively in `docs/sessions/`.

## Step 5 — Check git status
Run `git status` and `git log --oneline -5` to confirm the push succeeded and see recent history.

## Step 6 — Summarize
Give a concise status summary covering:
1. **Last session**: What was accomplished (based on recent commits and CLAUDE.md session notes)
2. **Current state**: What's working, what's in progress, any known issues
3. **Tracker highlights**: Key items from the spreadsheet (open tasks, blockers, upcoming work)
4. **Pending items**: Anything that needs attention this session

Keep the summary scannable — use short bullet points, not paragraphs. End with: "Ready for instructions."
