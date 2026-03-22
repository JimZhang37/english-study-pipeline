"""
Lesson Transcript Analyzer
--------------------------
Analyzes English lesson transcripts and saves output to Obsidian vault.

Usage:
    python3 analyze.py "20260206-Annabel-1"                          # vocab cards only (default)
    python3 analyze.py "20260206-Annabel-1" --tasks tutor-report     # tutor report only
    python3 analyze.py "20260206-Annabel-1" --tasks vocab tutor-report
    python3 analyze.py "20260206-Annabel-1" --all                    # all tasks

Available tasks:
    vocab         (default) Generate Anki vocabulary cards via obsidian-anki-writer skill
    tutor-report  Generate a feedback report for the tutor (plain markdown)
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path

from config import LESSONS_DIR, VAULT_DIR

ALL_TASKS = ["vocab", "tutor-report"]

# --- Prompts ---

# Single-task prompts (one claude -p call for one task)

VOCAB_PROMPT = """\
Use the english-study:lesson-analyzer skill to extract vocabulary flashcards from this \
lesson transcript and save them to Obsidian.

Tutor name: {tutor_name}
Deck: Preply::{date}
File: {vocab_file}
Transcript file: {transcript_file}

Transcript:
{transcript}"""

TUTOR_REPORT_PROMPT = """\
Use the english-study:lesson-analyzer skill with argument "tutor-report" to generate \
a tutor feedback report for this lesson and save it to: {report_file}

Tutor name: {tutor_name}
Lesson date: {date}
Transcript file: {transcript_file}

{previous_reports_section}

Transcript:
{transcript}"""

# Combined prompt (one claude -p call for all tasks — shared analysis context)

ALL_TASKS_PROMPT = """\
Use the english-study:lesson-analyzer skill with argument "all" to analyze this \
lesson transcript. This will run vocab extraction and tutor report in sequence, \
sharing the same analysis context.

Tutor name: {tutor_name}
Lesson date: {date}
Transcript file: {transcript_file}

Vocab output:
  Deck: Preply::{date}
  File: {vocab_file}

Tutor report output:
  File: {report_file}

{previous_reports_section}

Transcript:
{transcript}"""


def parse_date(folder_name: str) -> str:
    """Extract YYYY-MM-DD from folder name like '20260206-Annabel-1'."""
    match = re.search(r"(\d{8})", folder_name.strip())
    if not match:
        raise ValueError(f"Cannot parse date from folder name: {folder_name!r}")
    raw = match.group(1)
    return f"{raw[:4]}-{raw[4:6]}-{raw[6:]}"


def parse_tutor_name(folder_name: str) -> str:
    """Extract tutor name from folder like '20260206-Annabel-1' → 'Annabel'.

    Format: YYYYMMDD-TutorName-N where tutor name may contain spaces (e.g. 'G Isabel').
    First part is date (8 digits), last part is lesson number/label.
    """
    parts = folder_name.strip().split("-")
    if len(parts) < 3:
        raise ValueError(f"Cannot parse tutor name from: {folder_name!r}")
    return "-".join(parts[1:-1])


def next_version_path(base_path: Path) -> Path:
    """Return a non-conflicting file path, appending -v2, -v3, etc. if file exists.

    Example: 2026-03-21-lesson.md exists → returns 2026-03-21-lesson-v2.md
             2026-03-21-lesson-v2.md exists → returns 2026-03-21-lesson-v3.md
    """
    if not base_path.exists():
        return base_path

    stem = base_path.stem
    suffix = base_path.suffix
    parent = base_path.parent

    match = re.search(r"-v(\d+)$", stem)
    if match:
        base_stem = stem[:match.start()]
        current_v = int(match.group(1))
    else:
        base_stem = stem
        current_v = 1

    version = current_v + 1
    while True:
        candidate = parent / f"{base_stem}-v{version}{suffix}"
        if not candidate.exists():
            return candidate
        version += 1


def run_claude(prompt: str, allow_writes: bool = False) -> str:
    """Call claude -p and return the output."""
    cmd = ["claude", "-p", prompt, "--add-dir", str(LESSONS_DIR)]
    if allow_writes:
        cmd += ["--add-dir", str(VAULT_DIR), "--permission-mode", "acceptEdits"]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  ERROR: claude -p failed:\n{result.stderr}", file=sys.stderr)
        sys.exit(1)
    return result.stdout.strip()


def gather_previous_reports(vault_dir: Path, tutor_name: str,
                            current_date: str, max_reports: int = 5) -> str:
    """Find and read recent tutor reports for this tutor only.

    Reports use naming: YYYY-MM-DD-TutorName-tutor-report.md
    Only reads reports from the same tutor — no cross-referencing between tutors.
    """
    pattern = f"*-{tutor_name}-tutor-report.md"
    report_files = sorted(vault_dir.glob(pattern), reverse=True)
    report_files = [f for f in report_files if current_date not in f.name]
    report_files = report_files[:max_reports]

    if not report_files:
        return ""

    sections = [f"Previous tutor reports for {tutor_name} (for trend analysis):"]
    for f in report_files:
        sections.append(f"\n--- {f.name} ---\n{f.read_text()}")
    return "\n".join(sections)


def main():
    parser = argparse.ArgumentParser(
        description="Analyze English lesson transcripts and save to Obsidian."
    )
    parser.add_argument("lesson", help="Lesson folder name, e.g. '20260206-Annabel-1'")
    parser.add_argument("--tasks", nargs="+", choices=ALL_TASKS,
                        help="Tasks to run (default: vocab)")
    parser.add_argument("--all", action="store_true", help="Run all tasks")
    args = parser.parse_args()

    txt_file = LESSONS_DIR / args.lesson / "merged_lessons.txt"
    if not txt_file.exists():
        print(f"Error: {txt_file} not found", file=sys.stderr)
        sys.exit(1)

    transcript = txt_file.read_text()
    date = parse_date(args.lesson)
    tutor_name = parse_tutor_name(args.lesson)
    VAULT_DIR.mkdir(parents=True, exist_ok=True)

    if args.all:
        tasks = list(ALL_TASKS)
    elif args.tasks:
        tasks = args.tasks
    else:
        tasks = ["vocab"]

    # Resolve output paths
    out_files = {}
    if "vocab" in tasks:
        out_files["vocab"] = next_version_path(VAULT_DIR / f"{date}-lesson.md")
    if "tutor-report" in tasks:
        out_files["tutor-report"] = next_version_path(
            VAULT_DIR / f"{date}-{tutor_name}-tutor-report.md"
        )

    # Gather previous reports if tutor-report is requested
    previous_section = "No previous tutor reports found for this tutor."
    if "tutor-report" in tasks:
        previous = gather_previous_reports(VAULT_DIR, tutor_name, date)
        if previous:
            previous_section = previous

    print(f"Lesson: {args.lesson}")
    print(f"Date:   {date}")
    print(f"Tutor:  {tutor_name}")
    print(f"Tasks:  {', '.join(tasks)}")
    print()

    # Single claude -p call when multiple tasks — shared analysis context
    if len(tasks) > 1:
        print("  [all] Running all tasks in one session...", end=" ", flush=True)
        prompt = ALL_TASKS_PROMPT.format(
            tutor_name=tutor_name,
            date=date,
            transcript_file=txt_file,
            vocab_file=out_files["vocab"],
            report_file=out_files["tutor-report"],
            previous_reports_section=previous_section,
            transcript=transcript,
        )
        output = run_claude(prompt, allow_writes=True)
        print("done.")
        print(f"  {output}")
    else:
        # Single task — use the focused prompt
        task = tasks[0]
        if task == "vocab":
            print("  [vocab] Running...", end=" ", flush=True)
            prompt = VOCAB_PROMPT.format(
                tutor_name=tutor_name, date=date,
                vocab_file=out_files["vocab"],
                transcript_file=txt_file, transcript=transcript,
            )
        elif task == "tutor-report":
            print("  [tutor-report] Running...", end=" ", flush=True)
            prompt = TUTOR_REPORT_PROMPT.format(
                tutor_name=tutor_name, date=date,
                report_file=out_files["tutor-report"],
                transcript_file=txt_file,
                previous_reports_section=previous_section,
                transcript=transcript,
            )
        output = run_claude(prompt, allow_writes=True)
        print("done.")
        print(f"  {output}")

    print()
    if "vocab" in out_files:
        print(f"Vocab cards: {out_files['vocab']}")
        print("Review in Obsidian before syncing to Anki.")
    if "tutor-report" in out_files:
        print(f"Tutor report: {out_files['tutor-report']}")


if __name__ == "__main__":
    main()
