# English Study Pipeline

Automates the work between a Preply tutoring session and active vocabulary study in Anki, reducing manual effort to a single review step in Obsidian.

## Pipeline stages

```
Download → Transcribe → Analyze → Review → Anki
```

| Stage | Script | Status | What happens |
|---|---|---|---|
| **Download** | `preply_download.py` | ✅ Done | Fetch audio zip from Preply, extract parts into lesson folder |
| **Transcribe** | `transcribe.py` | ✅ Done | Merge parts, run WhisperX diarization, produce transcript files |
| **Analyze** | `analyze.py` | ✅ Done | Extract vocabulary cards via Claude skills, save to Obsidian |
| **Review** | — | Manual | Human reviews and edits cards in Obsidian |
| **Anki** | — | Manual | Trigger Obsidian-to-Anki sync |

## Prerequisites and assumptions

This pipeline is not fully self-contained — it relies on external applications and assumes certain conditions are already in place.

### Desktop applications

| Application | Required for | Assumption |
|---|---|---|
| **[Obsidian](https://obsidian.md)** | Review + sync | Vault exists and path is set in `config.py` |
| **[Obsidian-to-Anki plugin](https://github.com/Pseudonium/Obsidian_to_Anki)** | Anki sync | Plugin installed and configured in Obsidian |
| **[Anki](https://apps.ankiweb.net)** | Flashcard study | Must be running when the Obsidian-to-Anki sync is triggered |
| **[Claude Code](https://claude.ai/code)** | Analyze stage | `analyze.py` calls `claude -p` as a subprocess; Claude Code must be installed and authenticated |
| **Google Chrome** | Download stage | You are already logged into your Preply account in Chrome |

The **Review** and **Anki** stages in the pipeline table above are manual steps performed inside Obsidian and Anki — there are no scripts for them.

### Command-line tools

| Tool | Required for | Install |
|---|---|---|
| **Python 3** | All stages | `brew install python` |
| **[ffmpeg](https://ffmpeg.org)** | Transcribe stage | `brew install ffmpeg` |
| **[WhisperX](https://github.com/m-bain/whisperX)** | Transcribe stage | `pip install whisperx` |
| **[Playwright](https://playwright.dev/python/)** | Download stage | `pip install playwright && playwright install chrome` |

**Note on WhisperX:** transcription runs entirely on your local machine — no audio is sent to any cloud service. WhisperX downloads the Whisper model weights on first run and performs all inference locally. This requires enough RAM/CPU (or a GPU) to run the model, and a HuggingFace token for the speaker diarization model.

## Setup

```bash
# Copy config template and fill in your personal paths
cp config.example.py config.py
# Edit config.py with your actual lesson folder and Obsidian vault paths

pip install playwright
playwright install chrome
pip install whisperx
# ffmpeg must also be installed (e.g. brew install ffmpeg on macOS)

export HF_TOKEN=your_huggingface_token  # HuggingFace token for WhisperX diarization
```

## Running

```bash
# Full pipeline (single command)
python3 pipeline.py "20260318-TutorName-5"

# Skip download if audio parts already exist
python3 pipeline.py "20260318-TutorName-5" --skip-download

# Select specific stages
python3 pipeline.py "20260318-TutorName-5" --stages=download,transcribe
```

## Flashcard design

Cards are generated in two tiers:
- **Keywords** — 3–6 words the student visibly struggled with or got wrong
- **Vocabulary** — 6–10 broader useful words and collocations from the lesson

All cards use **cloze format**. The `Text` field contains the cloze sentence; `Back Extra` is the same sentence with cloze markers stripped (used by AnkiMorphs for frequency ranking).

## Review step (intentional)

The human review step is kept deliberately. AI-generated flashcards are not always reliable — the review step in Obsidian allows the learner to:
- Remove low-quality or irrelevant cards
- Fix incorrect sentences
- Add personal notes or context

Obsidian is the **source of truth** for all cards. Edits always happen in the markdown file; Anki is treated as read-only. The Obsidian-to-Anki plugin handles syncing.

## Separate: audio playback files

In addition to vocab cards, the `lesson-analyzer playback` skill can create interactive playback files that let you listen to specific lesson moments with fine-tune buttons. These are created on demand, not part of the automated pipeline.

## Technical details

See [docs/PIPELINE_TECHNICAL.md](docs/PIPELINE_TECHNICAL.md) for architecture, stage internals, and dependency details.
