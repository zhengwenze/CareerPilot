"""LLM prompt templates for AI-powered resume enrichment."""

from app.prompts.resume import (
    get_analyze_resume_prompt,
    get_enhance_description_prompt,
    get_regenerate_item_prompt,
    get_regenerate_skills_prompt,
)

ANALYZE_RESUME_PROMPT = get_analyze_resume_prompt()
ENHANCE_DESCRIPTION_PROMPT = get_enhance_description_prompt()
REGENERATE_ITEM_PROMPT = get_regenerate_item_prompt()
REGENERATE_SKILLS_PROMPT = get_regenerate_skills_prompt()
