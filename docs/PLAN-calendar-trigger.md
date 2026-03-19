# Plan: Google Calendar Auto-Trigger for English Pipeline

## Status

- [x] Change 1: New folder naming convention — scripts updated
- [x] Change 2: `calendar_trigger.py` — created
- [x] Change 3: `--stages` flag in `pipeline.py` — done
- [x] Change 4: launchd plist — created at `~/Library/LaunchAgents/com.english-pipeline.calendar-trigger.plist`
- [ ] Rename existing lesson folders to new format (manual, see below)
- [ ] Google Cloud setup (manual, see below)
- [ ] Set HF_TOKEN in plist
- [ ] Load plist with launchctl

---

## Context

After each Preply lesson, the user manually runs `python3 pipeline.py "TutorName N YYYYMMDD"`. This feature automates that: a daily cron job checks Google Calendar for completed lessons and triggers the download pipeline automatically. This is a single-user demo — simplicity over robustness.

---

## Change 1: New folder naming convention

**Old:** `TutorName N YYYYMMDD`
**New:** `20260318-TutorName-N` (YYYYMMDD-NameInitial-N)

- Date-first for chronological sorting
- Name + first letter of family name to disambiguate similar names
- Lesson number last, still tracks tutor familiarity

**Migration — rename existing folders:**

```bash
cd ~/Documents/Your\ English\ lessons/

mv "TutorName trial YYYYMMDD" "YYYYMMDD-TutorName-trial"
mv "TutorName 1 YYYYMMDD"     "YYYYMMDD-TutorName-1"
# ... repeat for each lesson folder
```

Note: Use your actual tutor names and dates.

---

## Change 2: `calendar_trigger.py`

**Done.** Located at `calendar_trigger.py` in the project root.

Config file: `~/.english-pipeline/config.json` — **edit before use:**
- Set `calendar_id` (run `--find-calendars` to find it)
- Verify tutor names match exactly what appears in Google Calendar event titles
- Set `next_lesson` numbers correctly for each tutor

---

## Change 3: `--stages` flag in `pipeline.py`

**Done.**

```bash
python3 pipeline.py "20260318-TutorName-5" --stages=download,transcribe
```

---

## Change 4: launchd plist

**Done.** Located at `~/Library/LaunchAgents/com.english-pipeline.calendar-trigger.plist`

Before loading:
1. Edit the plist and replace `YOUR_HF_TOKEN_HERE` with your actual HF token
2. Verify `python3` path is correct: `which python3`

Then load:
```bash
launchctl load ~/Library/LaunchAgents/com.english-pipeline.calendar-trigger.plist
# Verify it loaded:
launchctl list | grep english-pipeline
```

---

## Google Cloud setup (manual, one-time)

1. Go to https://console.cloud.google.com
2. Create a new project (e.g. "english-pipeline")
3. Enable **Google Calendar API**
4. Go to APIs & Services → Credentials → Create Credentials → OAuth 2.0 Client ID
5. Application type: **Desktop app**
6. Download the JSON and save as `~/.english-pipeline/credentials.json`
7. Install dependencies:
   ```bash
   pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib
   ```
8. Run auth:
   ```bash
   python3 calendar_trigger.py --auth
   ```
9. Find your Preply calendar ID:
   ```bash
   python3 calendar_trigger.py --find-calendars
   ```
10. Edit `~/.english-pipeline/config.json` — set `calendar_id`

---

## Verification checklist

1. `python3 calendar_trigger.py --auth` — completes OAuth flow
2. `python3 calendar_trigger.py --find-calendars` — lists calendars
3. `python3 calendar_trigger.py --dry-run` — detects a recent lesson correctly
4. `python3 pipeline.py "20260318-TutorName-5" --stages=download` — stages flag works
5. Existing scripts still work with renamed folders
6. `launchctl list | grep english-pipeline` — plist loaded and scheduled
