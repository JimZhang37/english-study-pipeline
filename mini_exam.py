"""Generate a printable mini math exam from mistake notes.

Usage:
    python3 mini_exam.py                            # list math notes, pick interactively
    python3 mini_exam.py --subject math             # same
    python3 mini_exam.py --subject math --category algebra
    python3 mini_exam.py 2026-03-22-001 2026-03-22-004   # direct selection
"""

import argparse
import asyncio
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

import markdown as _md
import yaml
from jinja2 import Environment, FileSystemLoader

from config import DEFAULT_SUBJECT, MISTAKES_DIR


# ---------------------------------------------------------------------------
# Note parsing
# ---------------------------------------------------------------------------

def _parse_frontmatter(text: str) -> dict:
    """Extract YAML frontmatter from a markdown file."""
    m = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    if not m:
        return {}
    return yaml.safe_load(m.group(1)) or {}


def _extract_section(text: str, heading: str) -> str:
    """Return the body of a ## heading section (stops at next ##)."""
    pattern = rf"## {re.escape(heading)}\n(.*?)(?=\n## |\Z)"
    m = re.search(pattern, text, re.DOTALL)
    return m.group(1).strip() if m else ""


def _clean_problem_text(raw: str) -> str:
    """Strip image embeds and parenthetical photo references."""
    # Remove ![[...]] image embeds
    text = re.sub(r"!\[\[.*?\]\]", "", raw)
    # Remove parenthetical notes like （第3题）or （请对照原图...）
    text = re.sub(r"（[^）]*）", "", text)
    return text.strip()


def _problem_to_html(raw: str) -> str:
    """Convert problem markdown to HTML for exam rendering.

    - Strips Obsidian image embeds ![[...]]
    - Strips workflow instruction lines (右键图片...)
    - Preserves LaTeX math ($...$ and $$...$$) so KaTeX handles it
    - Converts markdown formatting to HTML
    """
    text = re.sub(r"!\[\[.*?\]\]", "", raw)
    text = re.sub(r"右键图片[^\n]*\n?", "", text)

    math_store: list[str] = []

    def _save(m: re.Match) -> str:
        math_store.append(m.group(0))
        return f"MATHPLACEHOLDER{len(math_store) - 1}END"

    text = re.sub(r"\$\$[\s\S]+?\$\$", _save, text)
    text = re.sub(r"\$[^$\n]+\$", _save, text)

    html = _md.markdown(text, extensions=["extra"])

    for i, block in enumerate(math_store):
        html = html.replace(f"MATHPLACEHOLDER{i}END", block)

    return html.strip()


def _wiki_to_filename(wiki_link: str) -> str:
    """Extract filename from [[filename.jpg]] or "[[filename.jpg]]"."""
    m = re.search(r"\[\[(.+?)\]\]", wiki_link)
    return m.group(1) if m else wiki_link


def load_notes(subject: str, category_prefix: str | None = None) -> list[dict]:
    """Scan MISTAKES_DIR/<subject>/*.md and return sorted list of note dicts."""
    note_dir = MISTAKES_DIR / subject
    if not note_dir.exists():
        print(f"Error: {note_dir} does not exist.", file=sys.stderr)
        sys.exit(1)

    notes = []
    for path in sorted(note_dir.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        fm = _parse_frontmatter(text)
        if not fm:
            continue

        note_category = fm.get("category", "")
        if category_prefix and not note_category.startswith(category_prefix):
            continue

        raw_problem = _extract_section(text, "原题")
        problem_html = _problem_to_html(raw_problem)

        # Extract diagram image from 原题 (if any)
        diagram_match = re.search(r"!\[\[(.+?)\]\]", raw_problem)
        diagram_filename = diagram_match.group(1) if diagram_match else None

        # Extract clean redo photo from 重做 section (used when photo_mode is true)
        raw_redo = _extract_section(text, "重做")
        redo_match = re.search(r"!\[\[(.+?)\]\]", raw_redo)
        redo_filename = redo_match.group(1) if redo_match else None

        zhi_shi_dian_raw = _extract_section(text, "知识点")
        # First line only
        zhi_shi_dian = zhi_shi_dian_raw.splitlines()[0].strip() if zhi_shi_dian_raw else ""

        note_id = path.stem

        notes.append(
            {
                "id": note_id,
                "date": str(fm.get("date", "")),
                "category": note_category,
                "problem_html": problem_html,
                "diagram_filename": diagram_filename,
                "redo_filename": redo_filename,
                "exam_mode": "photo" if fm.get("photo_mode", False) else "text",
                "zhi_shi_dian": zhi_shi_dian,
                "path": path,
            }
        )

    return notes


# ---------------------------------------------------------------------------
# CLI selection
# ---------------------------------------------------------------------------

ANSWER_HEIGHTS = {"small": 40, "medium": 80, "large": 120}


def display_notes(notes: list[dict], subject: str) -> None:
    print(f"\nAvailable mistakes ({subject}):\n")
    print(f"  {'#':<4} {'Date':<12} {'Category':<32} 知识点")
    print(f"  {'-'*4} {'-'*12} {'-'*32} {'-'*30}")
    for i, note in enumerate(notes, 1):
        zsd = note["zhi_shi_dian"]
        # Strip markdown formatting for display
        zsd_clean = re.sub(r"\$[^$]+\$", "[math]", zsd)
        if len(zsd_clean) > 30:
            zsd_clean = zsd_clean[:27] + "..."
        print(f"  {i:<4} {note['date']:<12} {note['category']:<32} {zsd_clean}")
    print()


def prompt_selection(notes: list[dict]) -> list[dict]:
    """Return list of selected note dicts."""
    raw = input("Select problems (comma-separated numbers): ").strip()
    if not raw:
        print("No selection made.")
        sys.exit(0)

    selected = []
    for token in raw.split(","):
        token = token.strip()
        try:
            idx = int(token) - 1
        except ValueError:
            print(f"Invalid selection: {token!r}", file=sys.stderr)
            sys.exit(1)
        if idx < 0 or idx >= len(notes):
            print(f"Number out of range: {token!r}", file=sys.stderr)
            sys.exit(1)
        selected.append(notes[idx])

    return selected


def prompt_answer_size() -> int:
    raw = input("Answer space — small/medium/large [medium]: ").strip().lower()
    if not raw:
        raw = "medium"
    if raw not in ANSWER_HEIGHTS:
        print(f"Invalid size {raw!r}, using medium.", file=sys.stderr)
        raw = "medium"
    return ANSWER_HEIGHTS[raw]


# ---------------------------------------------------------------------------
# Direct-selection mode (positional args are note IDs)
# ---------------------------------------------------------------------------

def select_by_ids(notes: list[dict], note_ids: list[str]) -> list[dict]:
    """Select notes by ID."""
    id_map = {n["id"]: n for n in notes}
    selected = []
    for note_id in note_ids:
        if note_id not in id_map:
            print(f"Note not found: {note_id!r}", file=sys.stderr)
            sys.exit(1)
        selected.append(id_map[note_id])
    return selected


# ---------------------------------------------------------------------------
# PDF output path
# ---------------------------------------------------------------------------

def get_output_path() -> Path:
    exams_dir = MISTAKES_DIR / "exams"
    exams_dir.mkdir(parents=True, exist_ok=True)
    today = date.today().isoformat()
    base = exams_dir / f"{today}-exam.pdf"
    if not base.exists():
        return base
    n = 2
    while True:
        candidate = exams_dir / f"{today}-exam-{n}.pdf"
        if not candidate.exists():
            return candidate
        n += 1


# ---------------------------------------------------------------------------
# HTML rendering and PDF generation
# ---------------------------------------------------------------------------

def build_problems(selected: list[dict]) -> list[dict]:
    """Build problem dicts for the Jinja2 template."""
    problems = []
    attachments_dir = MISTAKES_DIR / "attachments"
    for note in selected:
        exam_mode = note["exam_mode"]
        if exam_mode == "photo" and note["redo_filename"]:
            problems.append({
                "mode": "photo",
                "image_url": (attachments_dir / note["redo_filename"]).as_uri(),
                "zhi_shi_dian": note["zhi_shi_dian"],
            })
        else:
            # text mode (default), optionally with diagram
            diagram_url = None
            if note["diagram_filename"]:
                diagram_url = (attachments_dir / note["diagram_filename"]).as_uri()
            problems.append({
                "mode": "text",
                "problem_html": note["problem_html"],
                "diagram_url": diagram_url,
                "zhi_shi_dian": note["zhi_shi_dian"],
            })
    return problems


def render_html(problems: list[dict], answer_height: int) -> str:
    template_dir = Path(__file__).parent / "templates"
    env = Environment(loader=FileSystemLoader(str(template_dir)))
    template = env.get_template("exam_template.html")
    return template.render(
        problems=problems,
        answer_height=answer_height,
        today=date.today().isoformat(),
        problem_count=len(problems),
    )


async def generate_pdf(html: str, output_path: Path) -> None:
    import tempfile
    from playwright.async_api import async_playwright

    with tempfile.NamedTemporaryFile(suffix=".html", delete=False, mode="w", encoding="utf-8") as f:
        f.write(html)
        tmp_path = Path(f.name)

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()
            await page.goto(tmp_path.as_uri(), wait_until="networkidle")
            await page.pdf(path=str(output_path), format="A4", print_background=True)
            await browser.close()
    finally:
        tmp_path.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def parse_args():
    parser = argparse.ArgumentParser(description="Generate a mini math exam from mistake notes.")
    parser.add_argument("note_ids", nargs="*", help="Direct note IDs (e.g. 2026-03-22-001)")
    parser.add_argument("--subject", default=DEFAULT_SUBJECT, help="Subject folder name")
    parser.add_argument("--category", default=None, help="Filter by category prefix")
    return parser.parse_args()


def main():
    args = parse_args()
    notes = load_notes(args.subject, args.category)

    if not notes:
        print("No notes found.", file=sys.stderr)
        sys.exit(1)

    if args.note_ids:
        selected = select_by_ids(notes, args.note_ids)
        answer_height = ANSWER_HEIGHTS["medium"]
    else:
        display_notes(notes, args.subject)
        selected = prompt_selection(notes)
        answer_height = prompt_answer_size()

    problems = build_problems(selected)
    html = render_html(problems, answer_height)
    output_path = get_output_path()

    print(f"\nGenerating PDF → {output_path}")
    asyncio.run(generate_pdf(html, output_path))
    print("Done.")
    subprocess.run(["open", str(output_path)])


if __name__ == "__main__":
    main()
