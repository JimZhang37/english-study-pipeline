# Mistake Notes: Crop-First Workflow

**Date:** 2026-03-23
**Status:** Final

## Context

The current mistake notes workflow has AI extract all questions from raw test photos, then the human reviews checkboxes to mark real mistakes. This fails in practice because input photos are messy — multiple questions per photo, poor image quality, handwriting — causing unreliable AI extraction.

The new approach flips the order: **human isolates individual mistakes first** (by cropping), then AI processes clean single-question images. This trades AI-first convenience for human-first reliability.

## Workflow Overview

```
[Inbox photos] → capture_mistakes.py → [Prep file in Obsidian]
                                              ↓
                                    Human crops in Obsidian
                                    (Image Converter plugin)
                                              ↓
                              /mistake-notes:finalize-mistakes
                                              ↓
                                    [Individual mistake notes]
```

Three steps: **import** (script) → **crop** (human) → **extract + output** (skill).

## Step 1: Import Script (`capture_mistakes.py`)

Python script. Deterministic file operations, no AI.

**Input:** Photos in `MISTAKES_INBOX` (iCloud folder).

**Operations:**
1. Scan inbox for images (JPG, PNG, HEIC, HEIF, WebP)
2. Compress each to JPEG (max 1600px, quality 80) — requires `pillow-heif` for HEIC support
3. Save compressed copies to `<MISTAKES_DIR>/attachments/` as `YYYY-MM-DD-p01.jpg`, `p02.jpg`, etc.
4. Generate prep file at `<MISTAKES_DIR>/reviews/YYYY-MM-DD-prep.md`
5. Update dedup registry (`~/.english-pipeline/processed-photos.json`)
6. Source photos remain in inbox until finalization (safety net)

**Same-day collision handling:** If `YYYY-MM-DD-prep.md` already exists with `status: prep`, append new photos to it (next available `pNN` number). If `status: done`, create `YYYY-MM-DD-prep-2.md`.

**Prep file format:**

```markdown
---
date: 2026-03-23
subject: math
learner: DD
status: prep
photo_folder: /path/to/inbox
---

# 错题裁剪 — 2026-03-23

每张照片裁剪出一道错题。如有多道错题，点击「复制」按钮复制照片后分别裁剪。
完成后运行 `/mistake-notes:finalize-mistakes`。

---

## 📷 p01

![[2026-03-23-p01.jpg]]

`button-duplicate`

---

## 📷 p02

![[2026-03-23-p02.jpg]]

`button-duplicate`

---
```

Button definitions at the top of the file (required by Buttons plugin):

```markdown
```button
name 复制
id duplicate
type template cursor
action duplicate-photo
```
```

**Duplicate button mechanism:** Uses `type template cursor` with a single shared button definition (`id: duplicate`). Inline references via `` `button-duplicate` `` in each section. The Templater template uses `window.__lastClickPos` (from the existing startup-click-tracker) to detect which section was clicked, then finds the nearest `![[...]]` embed above that position to determine which photo to duplicate. This is the same pattern used by the audio playback tune buttons.

**Template logic (`duplicate-photo.md`):**
1. Read `window.__lastClickPos` to find the clicked line
2. Scan upward from that line to find the nearest `![[YYYY-MM-DD-pNN.jpg]]` embed
3. Extract the date prefix and photo ID (e.g., `2026-03-23-p01`)
4. Find next available suffix: check for `-b`, `-c`, etc. in attachments folder
5. Copy the image file: `YYYY-MM-DD-p01.jpg` → `YYYY-MM-DD-p01-b.jpg`
6. Insert embed text at cursor: `![[YYYY-MM-DD-p01-b.jpg]]`

## Step 2: Human Crop (Manual in Obsidian)

Not automated. The human:

1. Opens the prep file in Obsidian **Live Preview mode**
2. For each photo:
   - Right-click → Image Converter → crop to isolate one mistake
   - If multiple mistakes: click "复制" button → new image copy appears → crop that too
3. Result: every embedded image shows exactly one mistake
4. Return to Claude Code and run `/mistake-notes:finalize-mistakes`

**Image Converter crop behavior:** The crop function modifies the image file in-place (same filename, same path). The `selectedFilenamePreset: NoteName-Timestamp` setting only applies to new image imports, not to crop operations. Verify during implementation.

## Step 3: Finalize Skill (`finalize-mistakes`)

Claude skill. Uses AI vision to extract structured data from each cropped image.

**Input:** Prep file with `status: prep`.

**Operations:**
1. Auto-detect latest prep file (or accept path argument)
2. Parse all `![[...]]` image embeds from the file
3. For each image:
   - Read the cropped image (Claude's native vision via Read tool)
   - Extract structured fields using extraction guide:
     - 题目 (question)
     - 学生答案 (student answer)
     - 错误分析 (error analysis)
     - 正确答案 (correct answer)
     - 知识点 (concept)
     - 分类 (category)
     - 练习题 (practice problem)
     - 练习答案 (practice solution)
   - Write individual mistake note to `<MISTAKES_DIR>/<subject>/YYYY-MM-DD-NNN.md`
   - Mark image as processed in prep file frontmatter (for idempotency)
4. After all images succeed: delete source photos from inbox (path from `photo_folder` frontmatter)
5. Update prep file status: `prep` → `done`

**Idempotency:** The prep file frontmatter tracks which images have been processed (e.g., `processed: [p01, p01-b, p02]`). If the skill is re-run after a partial failure, it skips already-processed images.

**No human review gate** — images are already curated, AI extraction is reliable on clean single-question images. Human reviews notes in Obsidian afterward.

## Files to Create/Modify

| File | Action | Location | Purpose |
|------|--------|----------|---------|
| `capture_mistakes.py` | Rewrite | Project repo | Import script — compress, copy, generate prep file |
| `finalize-mistakes/SKILL.md` | Rewrite | Plugin repo | AI extraction from cropped images |
| `capture-mistakes/SKILL.md` | Remove | Plugin repo | No longer needed — import is done by Python script directly |
| `duplicate-photo.md` | Create | Vault `Templates/` | Templater template for duplicating photos |
| Extraction guide references | Keep | Plugin repo | Same structured fields, reuse existing extraction-guide.md |

## What's Removed

- **capture-mistakes skill** — replaced by `capture_mistakes.py` script (no AI needed for import)
- **Review file with checkboxes** — replaced by prep file with crop workflow
- **AI extraction from raw multi-question photos** — replaced by extraction from clean cropped images
- **Interactive terminal review** (save/edit/skip) — no longer needed
