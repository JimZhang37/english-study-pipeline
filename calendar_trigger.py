"""
Google Calendar Trigger for English Pipeline
---------------------------------------------
Checks Google Calendar for completed Preply lessons and auto-triggers the pipeline.

Setup (one-time):
    1. Create a Google Cloud project and enable Google Calendar API
    2. Create OAuth 2.0 Client ID (Desktop app)
    3. Download credentials.json to ~/.english-pipeline/
    4. pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib
    5. python3 calendar_trigger.py --auth

Usage:
    python3 calendar_trigger.py              # normal run: poll, detect, trigger
    python3 calendar_trigger.py --auth       # one-time OAuth flow
    python3 calendar_trigger.py --find-calendars  # list all calendars
    python3 calendar_trigger.py --dry-run    # show what would happen
"""

import argparse
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

CONFIG_DIR = Path.home() / ".english-pipeline"
CONFIG_FILE = CONFIG_DIR / "config.json"
CREDENTIALS_FILE = CONFIG_DIR / "credentials.json"
TOKEN_FILE = CONFIG_DIR / "token.json"
LOG_DIR = CONFIG_DIR / "logs"
SCRIPTS_DIR = Path(__file__).parent

SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]


def load_config() -> dict:
    if not CONFIG_FILE.exists():
        print(f"Error: config file not found: {CONFIG_FILE}", file=sys.stderr)
        print("Create it from the template first.", file=sys.stderr)
        sys.exit(1)
    return json.loads(CONFIG_FILE.read_text())


def save_config(config: dict) -> None:
    CONFIG_FILE.write_text(json.dumps(config, indent=2) + "\n")


def get_credentials() -> Credentials:
    """Load or refresh OAuth credentials."""
    creds = None
    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        TOKEN_FILE.write_text(creds.to_json())
    if not creds or not creds.valid:
        if not CREDENTIALS_FILE.exists():
            print(f"Error: {CREDENTIALS_FILE} not found.", file=sys.stderr)
            print("Download it from Google Cloud Console.", file=sys.stderr)
            sys.exit(1)
        flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_FILE), SCOPES)
        creds = flow.run_local_server(port=0)
        TOKEN_FILE.write_text(creds.to_json())
        print(f"Token saved to {TOKEN_FILE}")
    return creds


def do_auth():
    """Run the OAuth flow and save token."""
    print("Starting OAuth flow...")
    get_credentials()
    print("Authentication complete!")


def do_find_calendars():
    """List all calendars to help find the Preply calendar ID."""
    creds = get_credentials()
    service = build("calendar", "v3", credentials=creds)
    calendars = service.calendarList().list().execute()
    print(f"\nFound {len(calendars['items'])} calendars:\n")
    for cal in calendars["items"]:
        primary = " (primary)" if cal.get("primary") else ""
        print(f"  {cal['summary']}{primary}")
        print(f"    ID: {cal['id']}")
        print()


def get_todays_events(service, calendar_id: str) -> list:
    """Fetch all events from today."""
    now = datetime.now(timezone.utc)
    start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_day = start_of_day + timedelta(days=1)

    events_result = (
        service.events()
        .list(
            calendarId=calendar_id,
            timeMin=start_of_day.isoformat(),
            timeMax=end_of_day.isoformat(),
            singleEvents=True,
            orderBy="startTime",
        )
        .execute()
    )
    return events_result.get("items", [])


def match_tutor(event_title: str, tutors: dict) -> str | None:
    """Match an event title to a tutor key. Returns tutor key or None."""
    for tutor_key, info in tutors.items():
        if info["full_event_name"].lower() in event_title.lower():
            return tutor_key
    return None


def build_folder_name(date_str: str, tutor_key: str, lesson_num: int) -> str:
    """Build folder name in new format: YYYYMMDD-TutorKey-N."""
    return f"{date_str}-{tutor_key}-{lesson_num}"


def run_pipeline(folder_name: str, stages: list[str]) -> bool:
    """Run the pipeline and return True on success."""
    cmd = ["python3", str(SCRIPTS_DIR / "pipeline.py"), folder_name]
    if stages:
        cmd.append(f"--stages={','.join(stages)}")
    print(f"  Running: {' '.join(cmd)}")
    result = subprocess.run(cmd)
    return result.returncode == 0


def do_run(dry_run: bool = False):
    """Main run: poll calendar, detect finished lessons, trigger pipeline."""
    config = load_config()
    calendar_id = config["calendar_id"]
    delay_minutes = config.get("delay_minutes", 15)
    stages = config.get("stages", [])
    tutors = config.get("tutors", {})
    processed = set(config.get("processed_events", []))

    creds = get_credentials()
    service = build("calendar", "v3", credentials=creds)

    now = datetime.now(timezone.utc)
    print(f"Checking calendar for completed lessons (delay: {delay_minutes}min)...")
    print(f"Current time (UTC): {now.isoformat()}")

    events = get_todays_events(service, calendar_id)
    if not events:
        print("No events found today.")
        return

    triggered = 0
    for event in events:
        event_id = event["id"]
        title = event.get("summary", "")

        # Skip already processed
        if event_id in processed:
            print(f"  [{title}] Already processed, skipping.")
            continue

        # Check if event has ended
        end_str = event.get("end", {}).get("dateTime")
        if not end_str:
            continue  # all-day event or no end time
        end_time = datetime.fromisoformat(end_str)
        if end_time.tzinfo is None:
            end_time = end_time.replace(tzinfo=timezone.utc)

        minutes_since_end = (now - end_time).total_seconds() / 60
        if minutes_since_end < delay_minutes:
            print(f"  [{title}] Ended {minutes_since_end:.0f}min ago (< {delay_minutes}min), waiting.")
            continue

        # Match tutor
        tutor_key = match_tutor(title, tutors)
        if not tutor_key:
            print(f"  [{title}] Unknown tutor, skipping.")
            continue

        tutor_info = tutors[tutor_key]
        lesson_num = tutor_info["next_lesson"]
        date_str = end_time.strftime("%Y%m%d")
        folder_name = build_folder_name(date_str, tutor_key, lesson_num)

        print(f"\n  [{title}] → {folder_name}")

        if dry_run:
            print(f"  [DRY RUN] Would run pipeline for {folder_name} (stages: {stages or 'all'})")
            triggered += 1
            continue

        success = run_pipeline(folder_name, stages)
        if success:
            # Mark processed and increment lesson number
            processed.add(event_id)
            tutor_info["next_lesson"] = lesson_num + 1
            triggered += 1
            print(f"  [{title}] Pipeline complete. Next lesson: {lesson_num + 1}")
        else:
            print(f"  [{title}] Pipeline FAILED — will retry on next run.")

    # Save updated config (prune processed_events to last 50)
    if not dry_run:
        config["processed_events"] = list(processed)[-50:]
        save_config(config)

    action = "would trigger" if dry_run else "triggered"
    print(f"\nDone. {triggered} lesson(s) {action}.")


def main():
    parser = argparse.ArgumentParser(description="Google Calendar trigger for English pipeline")
    parser.add_argument("--auth", action="store_true", help="Run OAuth flow")
    parser.add_argument("--find-calendars", action="store_true", help="List all calendars")
    parser.add_argument("--dry-run", action="store_true", help="Show what would happen")
    args = parser.parse_args()

    if args.auth:
        do_auth()
    elif args.find_calendars:
        do_find_calendars()
    else:
        do_run(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
