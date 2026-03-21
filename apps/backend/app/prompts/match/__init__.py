from __future__ import annotations

from pathlib import Path

PROMPT_DIR = Path(__file__).resolve().parent


def get_match_report_generation_prompt() -> str:
    return (PROMPT_DIR / "report_generation.txt").read_text(encoding="utf-8").strip()


def get_match_report_repair_prompt() -> str:
    return (PROMPT_DIR / "report_repair.txt").read_text(encoding="utf-8").strip()
