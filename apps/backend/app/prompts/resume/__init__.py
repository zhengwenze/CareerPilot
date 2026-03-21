from __future__ import annotations

from pathlib import Path

PROMPT_DIR = Path(__file__).resolve().parent


def get_resume_structure_correction_prompt() -> str:
    return (PROMPT_DIR / "structure_correction.txt").read_text(encoding="utf-8").strip()
