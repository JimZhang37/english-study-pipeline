"""
Transcribe lesson audio to text using WhisperX with speaker diarization.

Usage:
    python3 transcribe.py "20260212-IsabellaM-1"

Requires:
    HF_TOKEN environment variable — your HuggingFace token for diarization
    ffmpeg and whisperx installed

Steps:
    1. Concatenate part_*.webm → merged_lessons.webm  (skipped if already exists)
    2. Run WhisperX transcription + diarization      (skipped if already exists)
"""

import os
import subprocess
import sys
from pathlib import Path

from config import LESSONS_DIR


def run(cmd: list[str], env: dict = None) -> None:
    """Run a command, printing it first. Exit on failure."""
    print(f"  $ {' '.join(cmd)}")
    result = subprocess.run(cmd, env=env)
    if result.returncode != 0:
        print(f"  ERROR: command failed (exit {result.returncode})", file=sys.stderr)
        sys.exit(1)


def main():
    if len(sys.argv) != 2:
        print("Usage: python3 transcribe.py \"<lesson folder>\"")
        sys.exit(1)

    lesson = sys.argv[1]
    folder = LESSONS_DIR / lesson

    if not folder.exists():
        print(f"Error: folder not found: {folder}", file=sys.stderr)
        sys.exit(1)

    hf_token = os.environ.get("HF_TOKEN")
    if not hf_token:
        print("Error: HF_TOKEN environment variable is not set.", file=sys.stderr)
        print("  export HF_TOKEN=your_token_here", file=sys.stderr)
        sys.exit(1)

    print(f"Lesson: {lesson}")
    print()

    # Step 1: Concatenate parts into merged_lessons.webm
    merged = folder / "merged_lessons.webm"
    if merged.exists():
        print(f"[concat] Skipping — {merged.name} already exists.")
    else:
        parts = sorted(folder.glob("part_*.webm"))
        if not parts:
            print("Error: no part_*.webm files found.", file=sys.stderr)
            sys.exit(1)

        mylist = folder / "mylist.txt"
        mylist.write_text("\n".join(f"file '{p.name}'" for p in parts) + "\n")
        print(f"[concat] Merging {len(parts)} parts → merged_lessons.webm")
        run([
            "ffmpeg", "-f", "concat", "-safe", "0",
            "-i", str(mylist), "-c", "copy", str(merged),
        ])

    print()

    # Step 2: Transcribe with WhisperX
    transcript = folder / "merged_lessons.json"
    if transcript.exists():
        print("[whisperx] Skipping — merged_lessons.json already exists.")
    else:
        print("[whisperx] Transcribing + diarizing...")
        env = {**os.environ, "TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD": "1"}
        run([
            "whisperx", str(merged),
            "--model", "small",
            "--diarize",
            "--hf_token", hf_token,
            "--compute_type", "int8",
            "--device", "cpu",
            "--language", "English",
            "--highlight_words", "False",
            "--output_dir", str(folder),
        ], env=env)

    print()
    print("Done! Output files are in:")
    print(f"  {folder}")


if __name__ == "__main__":
    main()
