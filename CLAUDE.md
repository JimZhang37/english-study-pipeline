# CLAUDE.md

This file provides guidance to Claude Code when working with code in this repository.

## Project overview

A personal study support system for one kid. The core pattern across all subjects: **capture input → LLM analysis → Obsidian vault → active study**.

Two active workflows:
- **English**: Preply tutoring audio → transcription → vocabulary cards and tutor feedback
- **Math / school subjects**: graded test photos → cropped mistake images → structured mistake notes

Obsidian is the shared storage and review layer. AI generates content; a parent validates in Obsidian before syncing to Anki or sending feedback to tutors.

This is a **personal, localized system** — it depends on specific accounts (Preply, iCloud), local apps (Obsidian, Anki, Chrome), and a local Claude Code installation. Suggestions should favor simplicity and local execution over scalable or generic architectures.

## English study workflow

**Input:** Preply lesson audio, fetched from "Lesson Insights AI beta" via Chrome automation
**Stages:**
1. `preply_download.py` — downloads audio zip, extracts `part_N.webm` files into lesson folder
2. `transcribe.py` — merges audio parts, runs WhisperX with speaker diarization, outputs `.txt/.srt/.vtt/.tsv`
3. `analyze.py` — calls `claude -p` with `english-study:lesson-analyzer` skill; writes to Obsidian vault

**Outputs:**
- Vocab cards: `<VAULT_DIR>/YYYY-MM-DD-lesson.md` — Anki cloze format, synced via Obsidian-to-Anki plugin
- Tutor report: `<VAULT_DIR>/YYYY-MM-DD-TutorName-tutor-report.md` — parent copy-pastes to Preply
- Audio playback: `<VAULT_DIR>/YYYY-MM-DD-playback-test.md` — Obsidian file with tune buttons for reviewing audio

**Orchestrator:** `pipeline.py "YYYYMMDD-TutorName-N"` runs all three stages. Use `--skip-download` or `--stages=download,transcribe` to run partial pipelines.

**Vocab card format:** Cloze note type. `Text` has `{{c1::word}}` syntax; `Back Extra` is the same sentence plain (for AnkiMorphs). `am-*` fields are auto-filled after Anki sync — do not set manually. Two tiers: Keywords (3-6 words student struggled with) and Vocabulary (6-10 broader useful words).

**Tutor report:** Reads previous reports from the same tutor for cross-lesson trend analysis. Sections: Highlights, Suggested Focus, Student Progress, Engagement Signals, Recommended Topics.

## Math mistake notes workflow (crop-first)

**Input:** iPhone test photos deposited into iCloud inbox (`MISTAKES_INBOX`)
**Stages:**
1. `capture_mistakes.py` — compresses photos, copies to `<MISTAKES_DIR>/attachments/`, generates prep file with image embeds and duplicate buttons. Deduplicates via `~/.english-pipeline/processed-photos.json`.
2. Parent opens prep file in Obsidian Live Preview, right-clicks images → crop to isolate one mistake per image. Uses "复制" button when a photo has multiple mistakes.
3. `/mistake-notes:finalize-mistakes` skill — reads each cropped image via AI vision, extracts structured fields, writes individual note files, deletes inbox source photos.

**Outputs:** `<MISTAKES_DIR>/<subject>/YYYY-MM-DD-NNN.md` per mistake

**File locations:**
- Prep files: `<MISTAKES_DIR>/reviews/YYYY-MM-DD-prep.md`
- Attachments: `<MISTAKES_DIR>/attachments/YYYY-MM-DD-pNN.jpg`

## LLM integration

`analyze.py` and `finalize-mistakes` call `claude -p` with Claude Code skills — not raw API calls. Skills carry specialized context: card formats, report structure, mistake taxonomy. Claude Code must be installed and authenticated where these scripts run.

Skills used:
- `english-study:lesson-analyzer` — vocab extraction and tutor report generation
- `english-study:obsidian-anki-writer` — writes cards to Obsidian in Anki format
- `mistake-notes:finalize-mistakes` — extracts structured data from cropped mistake images

Install plugins:
```
/plugin marketplace add yaohua/yaohua-claude-plugins
/plugin install english-study@yaohua-claude-plugins
/plugin install mistake-notes@yaohua-claude-plugins
```

## Scripts

| Script | Usage | What it does |
|---|---|---|
| `pipeline.py` | `python3 pipeline.py "20260318-TutorName-5"` | Runs English study pipeline (download → transcribe → analyze) |
| `preply_download.py` | `python3 preply_download.py "20260318-TutorName-5"` | Downloads + extracts Preply audio parts |
| `transcribe.py` | `python3 transcribe.py "20260318-TutorName-5"` | Merges audio, runs WhisperX, outputs transcript files |
| `analyze.py` | `python3 analyze.py "20260318-TutorName-5"` | Extracts vocab cards (default); add `--tasks tutor-report` or `--all` |
| `capture_mistakes.py` | `python3 capture_mistakes.py` | Imports test photos from iCloud inbox, generates prep file |
| `calendar_trigger.py` | `python3 calendar_trigger.py` | Checks Google Calendar for completed lessons, triggers pipeline |

## Data locations

Actual paths are set in `config.local.md` (gitignored). See `config.example.md` for the template.

- Lessons: `<LESSONS_DIR>/YYYYMMDD-TutorName-N/` — contains audio parts, merged audio, transcript files
- Vault: `<VAULT_DIR>/` — all Obsidian output (vocab cards, tutor reports, playback files)
- Mistakes: `<MISTAKES_DIR>/` — subdirs by subject, plus `attachments/` and `reviews/`

## Environment variables

- `HF_TOKEN` — HuggingFace token, required by WhisperX for speaker diarization

## Setup

```bash
cp config.example.md config.local.md   # fill in your actual paths
pip install playwright && playwright install chrome
# WhisperX and ffmpeg must also be installed
export HF_TOKEN=your_huggingface_token
```

## Obsidian audio playback

- Use the `lesson-analyzer playback` skill to create playback files
- Timestamp extraction uses `scripts/srt_timestamps.py` bundled in the plugin
- Tune buttons use Templater templates: `tune-earlier.md`, `tune-later.md`, `tune-end-earlier.md`, `tune-end-later.md`
- Startup click tracker (`startup-click-tracker.md`) must be registered in Templater → Startup Templates
- **Button definitions must appear at the TOP of the file** — Buttons plugin registers top-to-bottom
- **Open in Live Preview mode** — tune buttons don't work in Reading mode

## Chrome automation constraints

The download step uses Chrome remote debugging (CDP) to preserve real macOS Keychain cookies.

- **Never use `launch_persistent_context`** with the real Chrome profile — Playwright adds `--use-mock-keychain` and `--password-store=basic`, corrupting macOS cookie encryption
- **Always copy the profile** to `/tmp/chrome-session`; never use the original
- Chrome blocks `--remote-debugging-port` on the default user-data-dir path — requires a non-default temp path
- Connect via `playwright.chromium.connect_over_cdp("http://localhost:9222")` after launching Chrome as subprocess

## Skill design principles

- **Use parallel subagents for batch work** — if a skill loops over N items (images, files, records) and each generates significant output, dispatch one subagent per item using the Agent tool. This avoids the 32k output token limit and runs faster. The main agent coordinates: pre-assign IDs, spawn all agents in one message, collect results, do final cleanup. See `mistake-notes:finalize-mistakes` as the reference implementation.

## Planning workflow

At the end of plan mode, before handing off to a new session:
1. Ask the user if they want to switch models (e.g. Sonnet for implementation)
2. Save the plan file path to MEMORY.md (not here — the filename is ephemeral)

**Always save the plan link to auto memory immediately after a plan is written.** The user will clear context and start a new session for implementation — if the plan path isn't in memory, the next session won't know where to find it.

To hand off: start a new session, optionally run `/model claude-sonnet-4-6`, then reference the plan file from MEMORY.md.

@config.local.md
