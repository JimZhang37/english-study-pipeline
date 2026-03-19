# English Study Pipeline — Overview

## Goal

Automate the work between a Preply tutoring session and active vocabulary study in Anki, reducing manual effort to a single review step in Obsidian.

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

## Running

```bash
# Full pipeline (single command)
python3 pipeline.py "Isabella 5 20260318"

# Skip download if audio parts already exist
python3 pipeline.py "Isabella 5 20260318" --skip-download
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

In addition to vocab cards, the `obsidian-audio-playback` Claude skill can create interactive playback files that let you listen to specific lesson moments with fine-tune buttons. These are created on demand, not part of the automated pipeline.
