# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project purpose

An English study automation pipeline. The goal is to reduce the manual work between a Preply tutoring session and active vocabulary study. The pipeline stages:

1. **Download** — fetch lesson audio zip from Preply's "Lesson Insights AI beta", extract parts into lesson folder (`preply_download.py`, implemented)
2. **Transcribe** — merge audio parts and generate transcript with speaker diarization via WhisperX (`transcribe.py`, implemented)
3. **Analyze** — extract vocabulary cards from transcript using Claude skills, save to Obsidian (`analyze.py`, implemented)
4. **Study** — human reviews cards in Obsidian, then syncs to Anki via Obsidian-to-Anki plugin

All stages are orchestrated by `pipeline.py`.

## Scripts

| Script | Usage | What it does |
|---|---|---|
| `pipeline.py` | `python3 pipeline.py "20260318-TutorName-5"` | Runs all three stages in sequence |
| `preply_download.py` | `python3 preply_download.py "20260318-TutorName-5"` | Downloads + extracts audio parts into lesson folder |
| `transcribe.py` | `python3 transcribe.py "20260318-TutorName-5"` | Merges parts, runs WhisperX, outputs transcript files |
| `analyze.py` | `python3 analyze.py "20260318-TutorName-5"` | Extracts vocab cards and saves to Obsidian vault |
| `calendar_trigger.py` | `python3 calendar_trigger.py` | Checks Google Calendar for completed lessons, triggers pipeline |

`pipeline.py` accepts `--skip-download` or `--stages=download,transcribe,analyze` to control which stages run.

## Data locations

Actual paths are set in `config.py` (gitignored). See `config.example.py` for the template.

- Lesson folders: `<LESSONS_DIR>/<YYYYMMDD-TutorName-N>/`
  - e.g. `20260212-TutorName-1/`
  - Contains: `part_01.webm` … `part_N.webm` (from download), then `merged_lessons.webm`, `merged_lessons.json`, `.txt`, `.srt`, `.vtt`, `.tsv` (from transcribe)
- Anki cards: `<VAULT_DIR>/YYYY-MM-DD-lesson.md`
- Audio playback files: `<VAULT_DIR>/YYYY-MM-DD-playback-test.md`

## Environment variables

- `HF_TOKEN` — HuggingFace token, required by WhisperX for speaker diarization. Set in shell profile:
  ```bash
  export HF_TOKEN=your_token_here
  ```

## Analyze stage details

- Uses **Claude skills** (`lesson-vocab-cards` → `obsidian-anki-writer`), not raw API calls
- Input: `merged_lessons.txt` — plain text transcript with speaker labels (e.g. `[SPEAKER_00]: ...`)
- Output: Obsidian markdown with `TARGET DECK: Preply::YYYY-MM-DD`
- Two tiers: **Keywords** (3-6 words student struggled with) and **Vocabulary** (6-10 broader useful words)
- Card format: Cloze note type — `Text` has cloze syntax, `Back Extra` is the same sentence with cloze markers stripped (plain text, for AnkiMorphs)
- `am-*` fields (AnkiMorphs plugin) are auto-filled after sync — do not set manually
- Manual review in Obsidian before syncing to Anki is intentional (AI output quality varies)

## Setup

```bash
cp config.example.py config.py   # then edit config.py with your actual paths
pip install playwright
playwright install chrome
# WhisperX and ffmpeg must also be installed
export HF_TOKEN=your_huggingface_token

# For calendar trigger (optional)
pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib
```

## Running

```bash
# Full pipeline
python3 pipeline.py "20260318-TutorName-5"

# Select specific stages
python3 pipeline.py "20260318-TutorName-5" --stages=download,transcribe

# Individual stages
python3 preply_download.py "20260318-TutorName-5"
python3 transcribe.py "20260318-TutorName-5"
python3 analyze.py "20260318-TutorName-5"

# Calendar trigger
python3 calendar_trigger.py --auth          # one-time OAuth setup
python3 calendar_trigger.py --find-calendars # find Preply calendar ID
python3 calendar_trigger.py --dry-run       # test without running pipeline
python3 calendar_trigger.py                 # normal run
```

## Calendar trigger

Config: `~/.english-pipeline/config.json` — set `calendar_id` and tutor mappings.
Schedule: `~/Library/LaunchAgents/com.english-pipeline.calendar-trigger.plist` — runs daily at 10 PM.
Logs: `~/.english-pipeline/logs/`

## Development approach

Test new approaches in isolation before applying them to the project. Solve one problem at a time — verify a technique works on its own before wiring it into a larger script. This saves time and avoids debugging multiple unknowns at once.

## Planning workflow

At the end of plan mode, before handing off to a new session:
1. Ask the user if they want to switch models (e.g. Sonnet for implementation)
2. Save the plan file path to MEMORY.md (not here — the filename is ephemeral and changes per plan)

To hand off: start a new session, optionally run `/model claude-sonnet-4-6`, then reference the plan file from MEMORY.md.

## Obsidian audio playback

- Playback files: `<VAULT_DIR>/YYYY-MM-DD-playback-test.md`
- Use the `obsidian-audio-playback` skill to create these — it handles button definitions, URL encoding, and timestamp extraction
- Timestamp extraction uses `~/.claude/skills/obsidian-audio-playback/scripts/srt_timestamps.py` — pass the SRT file and phrases to search, get back seconds
- Tune buttons use Templater templates: `tune-earlier.md`, `tune-later.md`, `tune-end-earlier.md`, `tune-end-later.md`
- Startup click tracker (`startup-click-tracker.md`) must be registered in Templater → Startup Templates
- Button definitions must appear at the TOP of the playback file — Buttons plugin registers them top-to-bottom
- Files must be opened in **Live Preview mode** — tune buttons don't work in Reading mode

## Chrome automation constraints

The download step uses **Chrome remote debugging (CDP)** rather than Playwright's built-in browser launch, to preserve real macOS Keychain cookies and login sessions.

- **Never use `launch_persistent_context`** with the real Chrome profile — Playwright injects `--use-mock-keychain` and `--password-store=basic`, which corrupts macOS cookie encryption and logs the user out of all accounts.
- **Always copy the profile** to `/tmp/chrome-session` first; never point Chrome at the original `~/Library/Application Support/Google/Chrome/Default`.
- Chrome blocks `--remote-debugging-port` when `--user-data-dir` is the default Chrome path — the non-default temp path is required.
- Connect via `playwright.chromium.connect_over_cdp("http://localhost:9222")` after launching Chrome as a subprocess.
