"""Read and update the routine-orchestrator tracker spreadsheet.

Used by /handoff to replace the failed WebFetch read and to log commit details.
Auth uses the ecosystem-core service account (GOOGLE_SHEETS_CREDS_PATH env var).

Usage:
    python tools/tracker_sync.py read
    python tools/tracker_sync.py log-commit --summary "..." [--next-steps "..."] [--in-progress "..."]
"""
import truststore
truststore.inject_into_ssl()

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

TRACKER_ID = "1jWYuZMoj-3VnyywgbnIzmzrvjAgyne8spazrEOl4TM8"
TRACKER_URL = f"https://docs.google.com/spreadsheets/d/{TRACKER_ID}/edit"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


def _client():
    creds_path = os.environ.get("GOOGLE_SHEETS_CREDS_PATH", "")
    if not creds_path or not Path(creds_path).exists():
        sys.exit(
            f"ERROR: GOOGLE_SHEETS_CREDS_PATH not set or file missing.\n"
            f"  Current value: {creds_path!r}"
        )
    try:
        import gspread
        from google.oauth2.service_account import Credentials
    except ImportError:
        sys.exit("ERROR: pip install gspread google-auth")

    with open(creds_path, encoding="utf-8") as f:
        creds_json = json.load(f)
    creds = Credentials.from_service_account_info(creds_json, scopes=SCOPES)
    email = creds_json.get("client_email", "<unknown>")
    try:
        return gspread.authorize(creds).open_by_key(TRACKER_ID), email
    except (PermissionError, gspread.exceptions.APIError) as exc:
        sys.exit(
            f"ERROR: Could not open tracker sheet (likely missing share).\n"
            f"  Share the sheet with {email} as Editor:\n"
            f"  {TRACKER_URL}\n"
            f"  Underlying error: {exc!r}"
        )


def cmd_read(_args):
    sheet, _ = _client()
    for ws in sheet.worksheets():
        print(f"\n=== Tab: {ws.title} ===")
        for row in ws.get_all_values():
            print(" | ".join(row))


def cmd_log_commit(args):
    import gspread
    sheet, _ = _client()
    try:
        ws = sheet.worksheet("Session Log")
    except gspread.exceptions.WorksheetNotFound:
        sys.exit("ERROR: tracker has no 'Session Log' tab — refusing to guess which tab to append to.")
    row = [
        args.date or datetime.now().strftime("%Y-%m-%d"),
        args.summary,
        args.in_progress or "",
        args.next_steps or "",
    ]
    ws.append_row(row, value_input_option="USER_ENTERED")
    print(f"Logged row to '{ws.title}': {row}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("read").set_defaults(func=cmd_read)

    log = sub.add_parser("log-commit")
    log.add_argument("--summary", required=True, help="What was accomplished this session")
    log.add_argument("--in-progress", default="", help="What is still in progress")
    log.add_argument("--next-steps", default="", help="Next steps")
    log.add_argument("--date", default="", help="Override date (YYYY-MM-DD); default = today")
    log.set_defaults(func=cmd_log_commit)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
