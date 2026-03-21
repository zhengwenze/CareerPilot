from __future__ import annotations

from pathlib import Path
from string import Template

PROMPT_DIR = Path(__file__).resolve().parent / "mock_interview"


def render_mock_interview_prompt(template_name: str, **variables: str) -> str:
    template_path = PROMPT_DIR / f"{template_name}.txt"
    template = Template(template_path.read_text(encoding="utf-8"))
    return template.substitute(**variables)


def render_mock_interview_repair_prompt(*, base_instructions: str) -> str:
    template_path = PROMPT_DIR / "json_repair.txt"
    template = Template(template_path.read_text(encoding="utf-8"))
    return template.substitute(base_instructions=base_instructions)
