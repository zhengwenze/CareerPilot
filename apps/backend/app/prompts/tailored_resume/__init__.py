from __future__ import annotations

from pathlib import Path

PROMPT_DIR = Path(__file__).resolve().parent


def get_tailored_resume_rewrite_prompt() -> str:
    return (PROMPT_DIR / "rewrite_only.txt").read_text(encoding="utf-8").strip()


def get_tailored_resume_grammar_prompt() -> str:
    return (PROMPT_DIR / "grammar_check.txt").read_text(encoding="utf-8").strip()


def get_tailored_resume_polish_prompt() -> str:
    return (PROMPT_DIR / "polish_markdown.txt").read_text(encoding="utf-8").strip()
