# Mini Math Exam Generator — Design Spec

## Context

The mistake notes system accumulates individual mistake notes in `<MISTAKES_DIR>/<subject>/`. Each note contains the original problem (原题), error analysis, correct answer, and a cropped photo. The parent wants to create printable mini exams from these notes so the child can re-practice past mistakes on paper.

This iteration focuses on **manual selection** of problems via a CLI script, with PDF output suitable for A4 printing.

## Overview

A new script `mini_exam.py` that:
1. Scans mistake notes from Obsidian vault
2. Displays them in the terminal for manual selection
3. Generates an HTML exam and converts it to A4 PDF via Playwright

## Detailed Design

### 1. CLI Interface

```bash
# List all math mistakes, user picks interactively
python3 mini_exam.py --subject math

# Filter by category
python3 mini_exam.py --subject math --category algebra

# Direct selection by note ID
python3 mini_exam.py 2026-03-23-001 2026-03-23-002 2026-03-23-003
```

**Terminal display** — numbered list with metadata:
```
Available mistakes (math):

  #  Date        Category                     知识点 (truncated)
  1  2026-03-23  algebra/substitution-method   换元后用 (a-b)² 求 ab...
  2  2026-03-23  algebra/square-of-binomial    完全平方公式展开...
  3  2026-03-23  geometry/line-relationships   同一平面内两直线位置关系...
  4  2026-03-23  algebra/equation-solving      一元二次方程求解...

Select problems (comma-separated numbers, e.g. 1,3,4):
```

After selection, the user is asked for answer space size:
```
Answer space per problem — small/medium/large [medium]:
```

### 2. Problem Rendering: Text vs Image

**Default: always use text** from the 原题 field (stripping `![[...]]` image embeds). The 原题 field contains the full problem text for all current notes, including geometry.

**Image override:** During selection, user can suffix a number with `i` to force image rendering for that problem:
```
Select problems: 1,2,3i,4
```
Problem 3 will embed the cropped photo instead of text. This handles cases where a problem genuinely needs a diagram (e.g., a triangle with marked angles).

**Text extraction logic:**
- Read the `## 原题` section from the note
- Strip lines matching `![[...]]` (image embeds)
- Strip parenthetical notes like `（第N题...）`
- Keep LaTeX math (`$...$` and `$$...$$`) — rendered in HTML via KaTeX

### 3. HTML Template

A single Jinja2 template (`exam_template.html`) producing an A4-ready page:

**Structure:**
```
┌─────────────────────────────┐
│     数学错题小测验            │  ← Title
│  2026-03-24 · 共 8 题       │  ← Date + count
│  姓名：________              │  ← Name blank
├─────────────────────────────┤
│ 1. [Problem text or image]  │
│    ┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄  │  ← Answer space (dashed)
│                             │
│ 2. [Problem text or image]  │
│    ┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄  │
│           ...               │
└─────────────────────────────┘
```

**CSS details:**
- A4 page: `@page { size: A4; margin: 20mm 15mm; }`
- Font: system Chinese font (PingFang SC / Noto Sans CJK)
- LaTeX math: KaTeX CSS (bundled or CDN)
- Page break: `page-break-inside: avoid` on each problem block
- Answer space height: configurable (small=40px, medium=80px, large=120px)
- Problem images: `max-width: 100%; max-height: 200px; object-fit: contain`

### 4. PDF Generation

Use Playwright (already installed) to convert HTML → PDF:

```python
async with async_playwright() as p:
    browser = await p.chromium.launch()
    page = await browser.new_page()
    await page.set_content(html_content)
    await page.pdf(path=output_path, format='A4', print_background=True)
    await browser.close()
```

No need for CDP or real Chrome profile — this uses Playwright's bundled Chromium, which is fine for PDF generation.

### 5. File Locations

- Script: `mini_exam.py` (project root)
- Template: `templates/exam_template.html`
- Output: `<MISTAKES_DIR>/exams/YYYY-MM-DD-exam.pdf` (auto-created dir)
- If multiple exams on same day: `YYYY-MM-DD-exam-2.pdf`, etc.

### 6. Dependencies

- `jinja2` — HTML templating
- `pyyaml` — already used for frontmatter parsing
- `playwright` — already installed
- KaTeX — loaded via CDN in the HTML template for LaTeX rendering

### 7. Config Integration

Reads `MISTAKES_DIR` from `config.local.md` (same as `capture_mistakes.py`).

## Out of Scope (Future Iterations)

- Auto-selection (spaced repetition, LLM-curated, random)
- Browser UI for selection
- Separate answer key PDF
- 练习题 (practice problems) as bonus questions
- Tracking which problems have been tested and when

## Verification

1. Run `python3 mini_exam.py --subject math` — should list all 4 current notes
2. Select 2-3 problems, generate PDF
3. Open PDF — verify A4 layout, Chinese text renders correctly, LaTeX math renders
4. Test image mode: select a problem with `i` suffix, verify image appears in PDF
5. Print on paper to verify margins and readability

## Critical Files

- `config.py` — centralized config loader; use `from config import MISTAKES_DIR`
- `config.local.md` — user's actual paths (gitignored)
- `<MISTAKES_DIR>/math/*.md` — mistake note files to scan
- `<MISTAKES_DIR>/attachments/*.jpg` — images for image-mode problems
