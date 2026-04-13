from __future__ import annotations

from pathlib import Path

PROMPT_DIR = Path(__file__).resolve().parent


def _read_prompt_file(file_name: str) -> str:
    return (PROMPT_DIR / file_name).read_text(encoding="utf-8").strip()


def get_resume_structure_correction_prompt() -> str:
    return _read_prompt_file("structure_correction.txt")


def get_resume_import_extraction_prompt() -> str:
    return _read_prompt_file("import_extraction.txt")


def get_resume_pdf_to_md_prompt() -> str:
    return _read_prompt_file("resume_pdf_to_md.txt")


def get_resume_pdf_to_md_user_prompt() -> str:
    return _read_prompt_file("pdf_to_md_user.txt")


def get_resume_schema_example() -> str:
    return _read_prompt_file("resume_schema_example.json")


def get_improve_schema_example() -> str:
    return _read_prompt_file("improve_schema_example.json")


def get_parse_resume_prompt() -> str:
    return _read_prompt_file("parse_resume.txt")


def get_extract_keywords_prompt() -> str:
    return _read_prompt_file("extract_keywords.txt")


def get_critical_truthfulness_rules_template() -> str:
    return _read_prompt_file("critical_truthfulness_rules.txt")


def get_improve_resume_nudge_prompt() -> str:
    return _read_prompt_file("improve_resume_nudge.txt")


def get_improve_resume_keywords_prompt() -> str:
    return _read_prompt_file("improve_resume_keywords.txt")


def get_improve_resume_full_prompt() -> str:
    return _read_prompt_file("improve_resume_full.txt")


def get_cover_letter_prompt() -> str:
    return _read_prompt_file("cover_letter.txt")


def get_outreach_message_prompt() -> str:
    return _read_prompt_file("outreach_message.txt")


def get_generate_title_prompt() -> str:
    return _read_prompt_file("generate_title.txt")


def get_analyze_resume_prompt() -> str:
    return _read_prompt_file("analyze_resume.txt")


def get_enhance_description_prompt() -> str:
    return _read_prompt_file("enhance_description.txt")


def get_regenerate_item_prompt() -> str:
    return _read_prompt_file("regenerate_item.txt")


def get_regenerate_skills_prompt() -> str:
    return _read_prompt_file("regenerate_skills.txt")


def get_keyword_injection_prompt() -> str:
    return _read_prompt_file("keyword_injection.txt")


def get_validation_polish_prompt() -> str:
    return _read_prompt_file("validation_polish.txt")
