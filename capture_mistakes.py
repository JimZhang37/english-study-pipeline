#!/usr/bin/env python3
"""Import test photos into Obsidian for crop-first mistake workflow.

Scans MISTAKES_INBOX for images, compresses to JPEG, copies to vault
attachments folder, and generates a prep file for manual cropping in Obsidian.
No AI, no interactive review — just deterministic file operations.
"""

import argparse
import json
import re
import sys
from datetime import date
from io import BytesIO
from pathlib import Path

from PIL import Image

try:
    import pillow_heif
    pillow_heif.register_heif_opener()
except ImportError:
    pass  # HEIC support unavailable

from config import DEFAULT_LEARNER, DEFAULT_SUBJECT, MISTAKES_DIR, MISTAKES_INBOX

REGISTRY_PATH = Path.home() / ".english-pipeline" / "processed-photos.json"
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".heic", ".heif", ".webp"}


def load_registry() -> dict:
    if REGISTRY_PATH.exists():
        return json.loads(REGISTRY_PATH.read_text())
    return {}


def save_registry(registry: dict) -> None:
    REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    REGISTRY_PATH.write_text(json.dumps(registry, indent=2, ensure_ascii=False))


def scan_photos(folder: Path) -> list[Path]:
    return sorted(
        f for f in folder.iterdir()
        if f.suffix.lower() in IMAGE_EXTENSIONS and not f.name.startswith(".")
    )


def compress_photo(path: Path, max_dim: int = 1600, quality: int = 80) -> bytes:
    img = Image.open(path)
    img.thumbnail((max_dim, max_dim))
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")
    buf = BytesIO()
    img.save(buf, format="JPEG", quality=quality)
    return buf.getvalue()


def find_next_photo_num(attachments_dir: Path, date_str: str) -> int:
    """Find next available pNN number for this date in attachments."""
    existing = list(attachments_dir.glob(f"{date_str}-p*.jpg"))
    if not existing:
        return 1
    nums = []
    for f in existing:
        m = re.search(rf"{re.escape(date_str)}-p(\d+)", f.stem)
        if m:
            nums.append(int(m.group(1)))
    return max(nums, default=0) + 1


def resolve_prep_path(reviews_dir: Path, date_str: str) -> tuple[Path, bool]:
    """Find the right prep file path, handling same-day collisions.

    Returns (path, append) — if append=True, add to existing file.
    """
    base = reviews_dir / f"{date_str}-prep.md"
    if not base.exists():
        return base, False

    # Existing file — check status
    content = base.read_text()
    if "status: prep" in content:
        return base, True  # append to existing prep file

    # status: done — find next available suffix
    n = 2
    while True:
        path = reviews_dir / f"{date_str}-prep-{n}.md"
        if not path.exists():
            return path, False
        if "status: prep" in path.read_text():
            return path, True
        n += 1


def generate_prep_header(date_str: str, subject: str, learner: str,
                         photo_folder: str) -> str:
    return f"""---
date: {date_str}
subject: {subject}
learner: {learner}
status: prep
photo_folder: "{photo_folder}"
---

```button
name 复制
id duplicate
type template cursor
action duplicate-photo
```
^button-duplicate

# 错题裁剪 — {date_str}

每张照片裁剪出一道错题。如有多道错题，点击「复制」按钮复制照片后分别裁剪。
完成后运行 `/mistake-notes:finalize-mistakes`。
"""


def generate_photo_section(photo_id: str, date_str: str) -> str:
    return f"""
---

## 📷 {photo_id}

![[{date_str}-{photo_id}.jpg]]

`button-duplicate`
"""


def main():
    parser = argparse.ArgumentParser(
        description="Import test photos into Obsidian for crop-first mistake workflow"
    )
    parser.add_argument(
        "photo_folder", nargs="?", type=Path, default=MISTAKES_INBOX,
        help=f"Folder containing test photos (default: MISTAKES_INBOX)"
    )
    parser.add_argument("--subject", default=DEFAULT_SUBJECT)
    parser.add_argument("--learner", default=DEFAULT_LEARNER)
    parser.add_argument("--date", default=None, help="Date override (YYYY-MM-DD)")
    args = parser.parse_args()

    if not args.photo_folder.is_dir():
        print(f"Error: {args.photo_folder} is not a directory")
        sys.exit(1)

    date_str = args.date or date.today().isoformat()
    photos = scan_photos(args.photo_folder)
    if not photos:
        print(f"No image files found in {args.photo_folder}")
        sys.exit(0)

    # Dedup: skip already-processed photos
    registry = load_registry()
    new_photos = []
    for p in photos:
        if p.name in registry:
            print(f"⚠ Skipping {p.name} — already processed on {registry[p.name]['processed_at']}")
        else:
            new_photos.append(p)
    photos = new_photos
    if not photos:
        print("All photos have already been processed.")
        sys.exit(0)

    print(f"Found {len(photos)} new photo(s) in {args.photo_folder}")

    # Set up directories
    attachments_dir = MISTAKES_DIR / "attachments"
    reviews_dir = MISTAKES_DIR / "reviews"
    attachments_dir.mkdir(parents=True, exist_ok=True)
    reviews_dir.mkdir(parents=True, exist_ok=True)

    # Resolve prep file
    prep_path, append = resolve_prep_path(reviews_dir, date_str)
    next_num = find_next_photo_num(attachments_dir, date_str)

    # Process photos
    photo_sections = []
    processed = []

    for photo_path in photos:
        photo_id = f"p{next_num:02d}"
        dest_name = f"{date_str}-{photo_id}.jpg"
        dest_path = attachments_dir / dest_name

        try:
            compressed = compress_photo(photo_path)
            dest_path.write_bytes(compressed)
            print(f"  {photo_path.name} → {dest_name} ({len(compressed) / 1024:.0f} KB)")
        except Exception as e:
            print(f"  Error processing {photo_path.name}: {e}")
            continue

        photo_sections.append(generate_photo_section(photo_id, date_str))
        processed.append(photo_path.name)
        next_num += 1

    if not processed:
        print("No photos were processed successfully.")
        sys.exit(1)

    # Write or append prep file
    if append:
        existing = prep_path.read_text()
        prep_path.write_text(existing + "".join(photo_sections))
        print(f"\nAppended {len(processed)} photo(s) to {prep_path.name}")
    else:
        header = generate_prep_header(
            date_str, args.subject, args.learner, str(args.photo_folder)
        )
        prep_path.write_text(header + "".join(photo_sections))
        print(f"\nCreated {prep_path.name} with {len(processed)} photo(s)")

    # Update registry
    for name in processed:
        registry[name] = {
            "processed_at": date_str,
            "prep_file": str(prep_path.relative_to(MISTAKES_DIR)),
        }
    save_registry(registry)

    print(f"Prep file: {prep_path}")
    print("Next: open in Obsidian, crop each photo, then run /mistake-notes:finalize-mistakes")


if __name__ == "__main__":
    main()
