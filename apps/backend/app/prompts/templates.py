"""LLM prompt templates for resume processing."""

from app.prompts.resume import (
    get_cover_letter_prompt,
    get_critical_truthfulness_rules_template,
    get_extract_keywords_prompt,
    get_generate_title_prompt,
    get_improve_resume_full_prompt,
    get_improve_resume_keywords_prompt,
    get_improve_resume_nudge_prompt,
    get_improve_schema_example,
    get_outreach_message_prompt,
    get_parse_resume_prompt,
    get_resume_schema_example,
)

# Language code to full name mapping
LANGUAGE_NAMES = {
    "en": "English",
    "es": "Spanish",
    "zh": "Chinese (Simplified)",
    "ja": "Japanese",
    "pt": "Brazilian Portuguese",
}


def get_language_name(code: str) -> str:
    """Get full language name from code."""
    return LANGUAGE_NAMES.get(code, "English")


RESUME_SCHEMA_EXAMPLE = get_resume_schema_example()
IMPROVE_SCHEMA_EXAMPLE = get_improve_schema_example()
PARSE_RESUME_PROMPT = get_parse_resume_prompt()
EXTRACT_KEYWORDS_PROMPT = get_extract_keywords_prompt()
CRITICAL_TRUTHFULNESS_RULES_TEMPLATE = get_critical_truthfulness_rules_template()


def _build_truthfulness_rules(rule_7: str) -> str:
    return CRITICAL_TRUTHFULNESS_RULES_TEMPLATE.format(rule_7=rule_7)


CRITICAL_TRUTHFULNESS_RULES = {
    "nudge": _build_truthfulness_rules(
        "DO NOT add new bullet points or content - only rephrase existing content"
    ),
    "keywords": _build_truthfulness_rules(
        "You may rephrase existing bullet points to include keywords, "
        "but do NOT add new bullet points"
    ),
    "full": _build_truthfulness_rules(
        "You may expand existing bullet points or add new ones that "
        "elaborate on existing work, but DO NOT invent entirely new "
        "responsibilities"
    ),
}

IMPROVE_RESUME_PROMPT_NUDGE = get_improve_resume_nudge_prompt()
IMPROVE_RESUME_PROMPT_KEYWORDS = get_improve_resume_keywords_prompt()
IMPROVE_RESUME_PROMPT_FULL = get_improve_resume_full_prompt()

IMPROVE_PROMPT_OPTIONS = [
    {
        "id": "nudge",
        "label": "Light nudge",
        "description": "Minimal edits to better align existing experience.",
    },
    {
        "id": "keywords",
        "label": "Keyword enhance",
        "description": "Blend in relevant keywords without changing role or scope.",
    },
    {
        "id": "full",
        "label": "Full tailor",
        "description": "Comprehensive tailoring using the job description.",
    },
]

IMPROVE_RESUME_PROMPTS = {
    "nudge": IMPROVE_RESUME_PROMPT_NUDGE,
    "keywords": IMPROVE_RESUME_PROMPT_KEYWORDS,
    "full": IMPROVE_RESUME_PROMPT_FULL,
}

DEFAULT_IMPROVE_PROMPT_ID = "keywords"

# Backward-compatible alias
IMPROVE_RESUME_PROMPT = IMPROVE_RESUME_PROMPT_FULL

COVER_LETTER_PROMPT = get_cover_letter_prompt()
OUTREACH_MESSAGE_PROMPT = get_outreach_message_prompt()
GENERATE_TITLE_PROMPT = get_generate_title_prompt()

# Alias for backward compatibility
RESUME_SCHEMA = RESUME_SCHEMA_EXAMPLE
