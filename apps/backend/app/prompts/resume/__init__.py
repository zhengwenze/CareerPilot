from __future__ import annotations

from pathlib import Path

PROMPT_DIR = Path(__file__).resolve().parent


def get_resume_structure_correction_prompt() -> str:
    return (PROMPT_DIR / "structure_correction.txt").read_text(encoding="utf-8").strip()


def get_resume_import_extraction_prompt() -> str:
    return (PROMPT_DIR / "import_extraction.txt").read_text(encoding="utf-8").strip()
