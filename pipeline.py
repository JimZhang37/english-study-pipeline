"""
English Study Pipeline
----------------------
Orchestrates the full pipeline for a single lesson:
  1. Download  — fetch audio parts from Preply and extract into lesson folder
  2. Transcribe — merge parts and run WhisperX diarization
  3. Analyze   — extract vocabulary cards and save to Obsidian

Usage:
    python3 pipeline.py "20260318-IsabellaM-5"
    python3 pipeline.py "20260318-IsabellaM-5" --skip-download
    python3 pipeline.py "20260318-IsabellaM-5" --stages=download,transcribe

Requires:
    HF_TOKEN environment variable set (for WhisperX diarization)
"""

import argparse
import subprocess
import sys
from pathlib import Path

LESSONS_DIR = Path.home() / "Documents" / "DD English lessons"
SCRIPTS_DIR = Path(__file__).parent

ALL_STAGES = ["download", "transcribe", "analyze"]


def run_step(name: str, cmd: list[str]) -> None:
    print(f"\n{'='*50}")
    print(f"  STEP: {name}")
    print(f"{'='*50}")
    result = subprocess.run(cmd)
    if result.returncode != 0:
        print(f"\nPipeline failed at step: {name}", file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="English study pipeline")
    parser.add_argument("lesson", help="Lesson folder name, e.g. '20260318-IsabellaM-5'")
    parser.add_argument("--skip-download", action="store_true", help="Skip download step (backward compat)")
    parser.add_argument("--stages", help="Comma-separated stages to run (default: all)")
    args = parser.parse_args()

    if args.stages:
        stages = [s.strip() for s in args.stages.split(",")]
        invalid = [s for s in stages if s not in ALL_STAGES]
        if invalid:
            print(f"Error: unknown stages: {', '.join(invalid)}", file=sys.stderr)
            print(f"Valid stages: {', '.join(ALL_STAGES)}", file=sys.stderr)
            sys.exit(1)
    else:
        stages = list(ALL_STAGES)
        if args.skip_download:
            stages.remove("download")

    lesson = args.lesson
    folder = LESSONS_DIR / lesson

    print(f"Lesson: {lesson}")
    print(f"Folder: {folder}")
    print(f"Stages: {', '.join(stages)}")

    if "download" in stages:
        run_step("Download", ["python3", str(SCRIPTS_DIR / "preply_download.py"), lesson])
    else:
        if not folder.exists():
            print(f"Error: folder not found: {folder}", file=sys.stderr)
            sys.exit(1)
        print("\n[download] Skipped.")

    if "transcribe" in stages:
        run_step("Transcribe", ["python3", str(SCRIPTS_DIR / "transcribe.py"), lesson])

    if "analyze" in stages:
        run_step("Analyze", ["python3", str(SCRIPTS_DIR / "analyze.py"), lesson])

    print(f"\n{'='*50}")
    print("  PIPELINE COMPLETE")
    print(f"{'='*50}")
    print(f"Lesson folder : {folder}")
    print(f"Review cards in Obsidian before syncing to Anki.")


if __name__ == "__main__":
    main()
