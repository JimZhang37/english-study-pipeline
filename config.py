"""Unified config — parses config.local.md for all paths and defaults."""

import re
from pathlib import Path

_config_path = Path(__file__).parent / "config.local.md"
if not _config_path.exists():
    raise FileNotFoundError(
        f"Missing {_config_path}. Copy config.example.md to config.local.md and fill in your paths."
    )

_text = _config_path.read_text()
_vals = dict(re.findall(r"^- (\w+): (.+)$", _text, re.MULTILINE))


def _path(key: str) -> Path:
    val = _vals[key]
    if val.startswith("~/"):
        val = str(Path.home()) + val[1:]
    return Path(val)


VAULT_DIR = _path("VAULT_DIR")
LESSONS_DIR = _path("LESSONS_DIR")
MISTAKES_INBOX = _path("MISTAKES_INBOX")
MISTAKES_DIR = _path("MISTAKES_DIR")
DEFAULT_SUBJECT = _vals.get("DEFAULT_SUBJECT", "math")
DEFAULT_LEARNER = _vals.get("DEFAULT_LEARNER", "DD")
