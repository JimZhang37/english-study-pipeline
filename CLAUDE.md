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
| `analyze.py` | `python3 analyze.py "20260318-TutorName-5"` | Extracts vocab cards and saves to Obsidian vault (default: vocab only; use `--tasks tutor-report` or `--all`) |
| `calendar_trigger.py` | `python3 calendar_trigger.py` | Checks Google Calendar for completed lessons, triggers pipeline |
| `capture_mistakes.py` | `python3 capture_mistakes.py` | Imports test photos from iCloud inbox into Obsidian for crop-first mistake workflow |

`pipeline.py` accepts `--skip-download` or `--stages=download,transcribe,analyze` to control which stages run.

## Data locations

Actual paths are set in `config.local.md` (gitignored). See `config.example.md` for the template.

- Lessons dir: `~/Documents/DD English lessons/`
- Vault dir: `~/Documents/obsidian vault/DD's English speaking class/`
- Lesson folders: `<LESSONS_DIR>/<YYYYMMDD-TutorName-N>/`
  - e.g. `20260212-TutorName-1/`
  - Contains: `part_01.webm` … `part_N.webm` (from download), then `merged_lessons.webm`, `merged_lessons.json`, `.txt`, `.srt`, `.vtt`, `.tsv` (from transcribe)
- Anki cards: `<VAULT_DIR>/YYYY-MM-DD-lesson.md`
- Tutor reports: `<VAULT_DIR>/YYYY-MM-DD-TutorName-tutor-report.md`
- Audio playback files: `<VAULT_DIR>/YYYY-MM-DD-playback-test.md`

## Environment variables

- `HF_TOKEN` — HuggingFace token, required by WhisperX for speaker diarization. Set in shell profile:
  ```bash
  export HF_TOKEN=your_token_here
  ```

## Plugin dependency

This project uses the **english-study** and **mistake-notes** Claude Code plugins. Install with:

```
/plugin marketplace add yaohua/yaohua-claude-plugins
/plugin install english-study@yaohua-claude-plugins
/plugin install mistake-notes@yaohua-claude-plugins
```

The `@config.local.md` reference below loads your paths into every session.

@config.local.md

## Mistake notes workflow (crop-first)

A separate workflow for capturing mistakes from graded test photos (math, science, etc.) into Obsidian.

Three steps: **import** (script) → **crop** (human in Obsidian) → **extract** (AI skill).

1. **Import:** `python3 capture_mistakes.py` — scans `MISTAKES_INBOX` (iCloud), compresses photos to JPEG, copies to `<MISTAKES_DIR>/attachments/`, generates a prep file at `<MISTAKES_DIR>/reviews/YYYY-MM-DD-prep.md` with image embeds and duplicate buttons
2. **Crop:** Human opens prep file in Obsidian Live Preview, right-clicks each image → Image Converter → crop to isolate one mistake per image. Uses "复制" button to duplicate images when a photo has multiple mistakes
3. **Extract:** Run `/mistake-notes:finalize-mistakes` — reads each cropped image via AI vision, extracts structured fields, writes individual mistake note files to `<MISTAKES_DIR>/<subject>/YYYY-MM-DD-NNN.md`, deletes inbox source photos

- Prep files: `<MISTAKES_DIR>/reviews/YYYY-MM-DD-prep.md`
- Mistake notes: `<MISTAKES_DIR>/<subject>/YYYY-MM-DD-NNN.md`
- Attachments: `<MISTAKES_DIR>/attachments/YYYY-MM-DD-pNN.jpg`
- Dedup registry: `~/.english-pipeline/processed-photos.json`
- Duplicate-photo template: `<VAULT_DIR>/../Templates/duplicate-photo.md`

## Analyze stage details

- Uses **Claude skills** (`english-study:lesson-analyzer` → task-specific reference files), not raw API calls
- Input: `merged_lessons.txt` — plain text transcript with speaker labels (e.g. `[SPEAKER_00]: ...`)
- **vocab task** (default):
  - Output: Obsidian markdown with `TARGET DECK: Preply::YYYY-MM-DD`
  - Two tiers: **Keywords** (3-6 words student struggled with) and **Vocabulary** (6-10 broader useful words)
  - Card format: Cloze note type — `Text` has cloze syntax, `Back Extra` is the same sentence with cloze markers stripped (plain text, for AnkiMorphs)
  - `am-*` fields (AnkiMorphs plugin) are auto-filled after sync — do not set manually
  - Chains to `english-study:obsidian-anki-writer` skill
- **tutor-report task**:
  - Output: plain markdown report (no Anki syntax) — `YYYY-MM-DD-TutorName-tutor-report.md`
  - Sections: Highlights, Suggested Focus, Student Progress, Engagement Signals, Recommended Topics
  - Reads previous reports from the same tutor for cross-lesson trend analysis
  - User copy-pastes into Preply messaging
- Manual review in Obsidian before syncing/sending is intentional (AI output quality varies)

## Gitignored config

`config.local.md` is the single gitignored config file containing all personal paths. It replaces the old `config.py` + `plugin-config.local.md` setup.

- `config.example.md` — committed template; copy and fill in your paths
- `config.py` — committed parser; reads `config.local.md` at import time
- When creating a new worktree: `ln -s ../../../config.local.md config.local.md`
- The `@config.local.md` reference in this file auto-loads paths into every Claude session; fails silently if missing

## Setup

```bash
cp config.example.md config.local.md   # then edit config.local.md with your actual paths
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
python3 analyze.py "20260318-TutorName-5"                          # vocab only (default)
python3 analyze.py "20260318-TutorName-5" --tasks tutor-report     # tutor report only
python3 analyze.py "20260318-TutorName-5" --all                    # vocab + tutor report

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
- Use the `lesson-analyzer playback` skill to create these — it handles button definitions, URL encoding, and timestamp extraction
- Timestamp extraction uses the script bundled in the plugin (`scripts/srt_timestamps.py` via `${CLAUDE_SKILL_DIR}`) — pass the SRT file and phrases to search, get back seconds
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
