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

**Old:** `Isabella 5 20260318`
**New:** `20260318-IsabellaM-5` (YYYYMMDD-NameInitial-N)

- Date-first for chronological sorting
- Name + first letter of family name to disambiguate similar names (Isabel vs Isabella)
- Lesson number last, still tracks tutor familiarity

**Migration — rename existing folders:**

```bash
cd ~/Documents/DD\ English\ lessons/

# Annabel
mv "Annabel trial 20260126" "20260126-AnnabelX-trial"
mv "Annabel 1 20260206"     "20260206-AnnabelX-1"
mv "Annabel 2 20260211"     "20260211-AnnabelX-2"
mv "Annabel 3 20260213"     "20260213-AnnabelX-3"
mv "Annabel 4 20260228"     "20260228-AnnabelX-4"
mv "Annabel 5 20260306"     "20260306-AnnabelX-5"
mv "Annabel 6 20260313"     "20260313-AnnabelX-6"

# Emma
mv "Emma trial 20260125"    "20260125-EmmaX-trial"
mv "Emma 1 20260202"        "20260202-EmmaX-1"
mv "Emma 2 20260204"        "20260204-EmmaX-2"
mv "Emma 3 20260207"        "20260207-EmmaX-3"
mv "Emma 4 20260214"        "20260214-EmmaX-4"
mv "Emma 5 20260216"        "20260216-EmmaX-5"
mv "Emma 6 20260218"        "20260218-EmmaX-6"

# Isabella
mv "Isabella trial 20260208" "20260208-IsabellaM-trial"
mv "Isabella 1 20260212"     "20260212-IsabellaM-1"
mv "Isabella 2 20260215"     "20260215-IsabellaM-2"
mv "Isabella 3 20260225"     "20260225-IsabellaM-3"
mv "Isabella 4 20260308"     "20260308-IsabellaM-4"
mv "Isabella 5 20260315"     "20260315-IsabellaM-5"

# G Isabel
mv "G Isabel trail 20260224" "20260224-IsabelG-trial"
mv "G Isabel 1 20260307"     "20260307-IsabelG-1"

# Others (review naming manually)
mv "Gaberiella trial 20260216" "20260216-GaberiellaX-trial"
mv "Lente trail 20260222"      "20260222-LenteX-trial"
mv "Testtutor 1 20260303"      "20260303-TesttutorX-1"
```

Note: `X` is a placeholder for initial — update if you know the family name initial.

---

## Change 2: `calendar_trigger.py`

**Done.** Located at `/Users/yaohua/Documents/testclaude/calendar_trigger.py`

Config file: `~/.english-pipeline/config.json` — **edit before use:**
- Set `calendar_id` (run `--find-calendars` to find it)
- Verify tutor names match exactly what appears in Google Calendar event titles
- Set `next_lesson` numbers correctly for each tutor

---

## Change 3: `--stages` flag in `pipeline.py`

**Done.**

```bash
python3 pipeline.py "20260318-IsabellaM-5" --stages=download,transcribe
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
4. `python3 pipeline.py "20260318-IsabellaM-5" --stages=download` — stages flag works
5. Existing scripts still work with renamed folders
6. `launchctl list | grep english-pipeline` — plist loaded and scheduled
