from __future__ import annotations

from pathlib import Path

from app.schemas.interview_review import MockInterviewReviewType

PROMPT_DIR = Path(__file__).resolve().parent


def get_mock_interview_system_prompt() -> str:
    return (PROMPT_DIR / "system.txt").read_text(encoding="utf-8").strip()


def get_mock_interview_role_summary_prompt() -> str:
    return (PROMPT_DIR / "role_summary.txt").read_text(encoding="utf-8").strip()


def get_mock_interview_resume_summary_prompt() -> str:
    return (PROMPT_DIR / "resume_summary.txt").read_text(encoding="utf-8").strip()


def get_mock_interview_question_generation_prompt() -> str:
    return (PROMPT_DIR / "question_generation.txt").read_text(encoding="utf-8").strip()


def get_mock_interview_feedback_prompt() -> str:
    return (PROMPT_DIR / "feedback.txt").read_text(encoding="utf-8").strip()


def get_mock_interview_dynamic_question_prompt() -> str:
    return (PROMPT_DIR / "dynamic_question.txt").read_text(encoding="utf-8").strip()


def get_mock_interview_recap_prompt() -> str:
    return (PROMPT_DIR / "recap.txt").read_text(encoding="utf-8").strip()


def get_mock_interview_deep_review_system_prompt() -> str:
    return (PROMPT_DIR / "deep_review_system.txt").read_text(encoding="utf-8").strip()


def get_mock_interview_deep_review_user_prompt() -> str:
    return (PROMPT_DIR / "deep_review_user.txt").read_text(encoding="utf-8").strip()


def get_mock_interview_deep_review_rubric(review_type: MockInterviewReviewType) -> str:
    file_map = {
        MockInterviewReviewType.TECHNICAL_ANALYSIS: "deep_review_rubric_technical_analysis.txt",
        MockInterviewReviewType.PROJECT_EXPERIENCE: "deep_review_rubric_project_experience.txt",
        MockInterviewReviewType.KNOWLEDGE_FUNDAMENTAL: "deep_review_rubric_knowledge_fundamental.txt",
    }
    return (PROMPT_DIR / file_map[review_type]).read_text(encoding="utf-8").strip()
