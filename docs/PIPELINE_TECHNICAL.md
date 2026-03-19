# English Study Pipeline — Technical Reference

## Architecture

Each stage is a standalone Python script. They can be run individually or orchestrated by `pipeline.py`.

```
pipeline.py
  ├── preply_download.py  "20260318-TutorName-5"   → part_*.webm files in lesson folder
  ├── transcribe.py       "20260318-TutorName-5"   → merged_lessons.webm + transcript files
  └── analyze.py          "20260318-TutorName-5"   → YYYY-MM-DD-lesson.md in Obsidian vault
```

---

## Stage 1: Download (`preply_download.py`)

**Input:** lesson folder name (e.g. `"20260318-TutorName-5"`)
**Output:** `part_01.webm … part_N.webm` extracted into `~/Documents/Your English lessons/20260318-TutorName-5/`

### How it works
1. Creates the lesson folder in `~/Documents/Your English lessons/`
2. Kills any running Chrome, copies Default profile to `/tmp/chrome-session`
3. Launches Chrome with `--remote-debugging-port=9222` and connects via CDP
4. Navigates to Preply dashboard, clicks first lesson in "Lesson Insights AI beta"
5. Downloads the zip, extracts `part_*.webm` files into the lesson folder, deletes the zip
6. Terminates Chrome and cleans up the temp profile

### Why CDP instead of Playwright launch
Using `launch_persistent_context` with the real Chrome profile causes Playwright to inject `--use-mock-keychain` and `--password-store=basic`, corrupting macOS Keychain cookies. CDP connects to an already-running Chrome instead.

---

## Stage 2: Transcribe (`transcribe.py`)

**Input:** `part_*.webm` files in the lesson folder
**Output:** `merged_lessons.webm`, `merged_lessons.json`, `merged_lessons.txt`, `merged_lessons.srt`, `merged_lessons.vtt`, `merged_lessons.tsv`

### How it works
1. Generates `mylist.txt` listing all parts in order
2. Runs `ffmpeg -f concat` to merge parts into `merged_lessons.webm` (skipped if already exists)
3. Sets `TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD=1` env var for PyTorch compatibility
4. Runs WhisperX on the merged file (skipped if `merged_lessons.json` already exists)

### WhisperX command
```bash
whisperx merged_lessons.webm \
  --model small \
  --diarize \
  --hf_token $HF_TOKEN \
  --compute_type int8 \
  --device cpu \
  --language English \
  --highlight_words False \
  --output_dir <lesson_folder>
```

### Requirements
- `ffmpeg` installed and on PATH
- `whisperx` installed (`pip install whisperx`)
- `HF_TOKEN` environment variable set (HuggingFace token for diarization model)

---

## Stage 3: Analyze (`analyze.py`)

**Input:** `merged_lessons.txt` — plain text with speaker labels (`[SPEAKER_00]: ...`)
**Output:** `~/Documents/obsidian vault/Your class folder/YYYY-MM-DD-lesson.md`

### How it works
1. Reads `merged_lessons.txt` from the lesson folder
2. Derives the date from the folder name (e.g. `20260212` → `2026-02-12`)
3. Calls `claude -p` with the `lesson-vocab-cards` skill, passing the transcript
4. The skill identifies the tutor, extracts Keywords and Vocabulary, and calls `obsidian-anki-writer` to save cards

### Skills used
- **`lesson-vocab-cards`** — extracts two tiers of vocabulary from the transcript
- **`obsidian-anki-writer`** — writes cards to the Obsidian vault in Obsidian-to-Anki format

### Card format
```markdown
TARGET DECK: Preply::2026-02-12

## Keywords

START
Cloze
Text: I keep all my clothes in my {{c1::wardrobe}} in the corner of my room.
Back Extra: I keep all my clothes in my wardrobe in the corner of my room.
END

## Vocabulary

START
Cloze
Text: I {{c1::struggle::st...}} with math, so I need to study harder.
Back Extra: I struggle with math, so I need to study harder.
END
```

- `Text` — cloze sentence with `{{c1::word}}` or `{{c1::word::hint}}`
- `Back Extra` — same sentence with all cloze markers stripped (plain text, for AnkiMorphs)
- `am-*` fields — auto-filled by AnkiMorphs after sync; never set manually

---

## Orchestrator (`pipeline.py`)

```bash
python3 pipeline.py "20260318-TutorName-5"               # full pipeline
python3 pipeline.py "20260318-TutorName-5" --skip-download  # skip download if parts exist
```

Runs the three stages in sequence. Stops immediately if any stage fails.

---

## Dependencies

```bash
pip install playwright
playwright install chrome

pip install whisperx
# ffmpeg must be installed (e.g. brew install ffmpeg)

export HF_TOKEN=your_huggingface_token
```

Claude Code must be running for `analyze.py` (uses `claude -p` subprocess with skills).

---

## Obsidian audio playback (separate workflow)

For reviewing lesson recordings with tune buttons:

```bash
# Use the obsidian-audio-playback skill in Claude Code
# Timestamp lookup utility:
python3 ~/.claude/skills/obsidian-audio-playback/scripts/srt_timestamps.py \
  "~/Documents/Your English lessons/<folder>/merged_lessons.srt" \
  "phrase to find" "another phrase"
```

Output: `~/Documents/obsidian vault/Your class folder/YYYY-MM-DD-playback-test.md`
