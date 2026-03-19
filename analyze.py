"""
Lesson Transcript Analyzer
--------------------------
Analyzes English lesson transcripts and saves output to Obsidian vault.

Usage:
    python3 analyze.py "20260206-AnnabelX-1"                   # vocab cards only (default)
    python3 analyze.py "20260206-AnnabelX-1" --all             # all tasks
    python3 analyze.py "20260206-AnnabelX-1" --tasks vocab weaknesses strengths

Available tasks:
    vocab       (default) Generate Anki vocabulary cards via obsidian-anki-writer skill
    weaknesses  Identify student weak points
    strengths   Identify student strengths
    tutor       Note good tutor practices
    summary     Write a lesson summary
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path

# --- Config ---
LESSONS_DIR = Path.home() / "Documents" / "DD English lessons"
VAULT_DIR = Path.home() / "Documents" / "obsidian vault" / "DD's English speaking class"

ALL_TASKS = ["vocab"]

# Future tasks (not yet implemented):
# TASK_TITLES = {
#     "weaknesses": "Student Weak Points",
#     "strengths": "Student Strengths",
#     "tutor": "Tutor Good Practices",
#     "summary": "Lesson Summary",
# }

# --- Prompts ---

VOCAB_PROMPT = """\
Use the lesson-vocab-cards skill to extract vocabulary flashcards from this \
lesson transcript and save them to Obsidian.

Deck: Preply::{date}
File: {out_file}

Transcript:
{transcript}"""

# Future prompts (commented out until implemented):
# WEAKNESSES_PROMPT = "..."
# STRENGTHS_PROMPT = "..."
# TUTOR_PROMPT = "..."
# SUMMARY_PROMPT = "..."


def parse_date(folder_name: str) -> str:
    """Extract YYYY-MM-DD from folder name like '20260206-AnnabelX-1'."""
    match = re.search(r"(\d{8})", folder_name.strip())
    if not match:
        raise ValueError(f"Cannot parse date from folder name: {folder_name!r}")
    raw = match.group(1)
    return f"{raw[:4]}-{raw[4:6]}-{raw[6:]}"


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


def run_vocab(transcript: str, date: str, out_file: Path):
    """Run vocab task — claude uses obsidian-anki-writer skill to write cards directly."""
    prompt = VOCAB_PROMPT.format(transcript=transcript, date=date, out_file=out_file)
    print(f"  [vocab] Running...", end=" ", flush=True)
    output = run_claude(prompt, allow_writes=True)
    print("done.")
    print(f"  {output}")


# Future functions (commented out until implemented):
# def run_analysis_task(task, transcript): ...
# def save_analysis(outputs, date, lesson): ...


def main():
    parser = argparse.ArgumentParser(
        description="Analyze English lesson transcripts and save to Obsidian."
    )
    parser.add_argument("lesson", help="Lesson folder name, e.g. '20260206-AnnabelX-1'")
    args = parser.parse_args()

    txt_file = LESSONS_DIR / args.lesson / "merged_lessons.txt"
    if not txt_file.exists():
        print(f"Error: {txt_file} not found", file=sys.stderr)
        sys.exit(1)

    transcript = txt_file.read_text()
    date = parse_date(args.lesson)
    VAULT_DIR.mkdir(parents=True, exist_ok=True)
    vocab_out_file = VAULT_DIR / f"{date}-lesson.md"

    print(f"Lesson: {args.lesson}")
    print(f"Date:   {date}")
    print()

    run_vocab(transcript, date, vocab_out_file)

    print("\nDone! Review in Obsidian before syncing to Anki.")


if __name__ == "__main__":
    main()
