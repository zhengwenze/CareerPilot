from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
import logging
from typing import Any
from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.errors import ApiException, ErrorCode
from app.models import (
    JobDescription,
    MatchReport,
    MockInterviewSession,
    MockInterviewTurn,
    Resume,
    ResumeOptimizationSession,
    User,
)
from app.prompts.mock_interview import (
    get_mock_interview_dynamic_question_prompt,
    get_mock_interview_feedback_prompt,
    get_mock_interview_question_generation_prompt,
    get_mock_interview_recap_prompt,
    get_mock_interview_resume_summary_prompt,
    get_mock_interview_role_summary_prompt,
    get_mock_interview_system_prompt,
)
from app.schemas.ai_runtime import TaskState
from app.schemas.interview_review import (
    DeepReviewResult,
    MockInterviewReviewType,
    coerce_mock_interview_review_type,
)
from app.schemas.mock_interview import (
    MockInterviewAnswerSubmitResponse,
    MockInterviewReviewSummary,
    MockInterviewSessionCreateRequest,
    MockInterviewSessionRecord,
    MockInterviewTurnDecision,
    MockInterviewTurnRecord,
)
from app.services.ai_client import AIProviderConfig, request_text_completion
from app.services.interview_review import review_interview_answer
from app.services.resume_ai import is_ai_configured

logger = logging.getLogger(__name__)

FALLBACK_QUESTIONS = [
    (
        "先请你做一个简短的自我介绍，并重点讲和这个岗位最相关的经历。",
        MockInterviewReviewType.PROJECT_EXPERIENCE,
    ),
    (
        "你简历里最能体现你能力的一个项目是什么？请详细说说。",
        MockInterviewReviewType.PROJECT_EXPERIENCE,
    ),
    (
        "在那个项目中，你承担的核心职责是什么？",
        MockInterviewReviewType.PROJECT_EXPERIENCE,
    ),
    (
        "你在过往经历里遇到过最棘手的问题是什么？你是怎么解决的？",
        MockInterviewReviewType.TECHNICAL_ANALYSIS,
    ),
    (
        "如果让你来胜任这个岗位，你觉得自己最突出的优势是什么？",
        MockInterviewReviewType.PROJECT_EXPERIENCE,
    ),
    (
        "你觉得自己和这个岗位之间还有哪些能力差距？",
        MockInterviewReviewType.PROJECT_EXPERIENCE,
    ),
    (
        "你在团队协作中通常承担什么角色？",
        MockInterviewReviewType.PROJECT_EXPERIENCE,
    ),
    (
        "如果项目进度紧张但需求还在变化，你会怎么处理？",
        MockInterviewReviewType.TECHNICAL_ANALYSIS,
    ),
]

DEFAULT_ENDING_TEXT = "本次模拟面试到这里结束，感谢你的参与。整体交流比较顺畅，建议你继续加强细节表达和案例量化。"


@dataclass(slots=True)
class MainQuestionPlan:
    question_id: str
    category: str
    review_type: MockInterviewReviewType
    text: str
    intent: str
    followup_hints: list[str] = field(default_factory=list)


def utc_now_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _deserialize_task_state(payload: dict[str, Any] | None) -> TaskState:
    return TaskState.model_validate(payload or {})


def _serialize_task_state(state: TaskState) -> dict[str, Any]:
    return state.model_dump(mode="json")


def _mark_prep_state(
    session_record: MockInterviewSession,
    *,
    status: str,
    phase: str,
    message: str,
) -> TaskState:
    plan_json = dict(session_record.plan_json or {})
    state = _deserialize_task_state(plan_json.get("prep_state"))
    now = utc_now_naive()
    if state.started_at is None and status in {"processing", "success", "failed"}:
        state.started_at = now
    state.status = status  # type: ignore[assignment]
    state.phase = phase
    state.message = message
    state.last_updated_at = now
    if status == "success":
        state.completed_at = now
    if status == "failed":
        state.completed_at = now
    plan_json["prep_state"] = _serialize_task_state(state)
    session_record.plan_json = plan_json
    return state


def _append_session_event(
    session_record: MockInterviewSession,
    *,
    event_type: str,
    payload: dict[str, Any] | None = None,
) -> None:
    plan_json = dict(session_record.plan_json or {})
    events = list(plan_json.get("events") or [])
    events.append(
        {
            "event_type": event_type,
            "occurred_at": utc_now_naive().isoformat(),
            "payload": payload or {},
        }
    )
    plan_json["events"] = events[-50:]
    session_record.plan_json = plan_json


def _normalize_text(value: str | None) -> str:
    return " ".join((value or "").split()).strip()


def _dedupe_strings(items: list[str]) -> list[str]:
    values: list[str] = []
    seen: set[str] = set()
    for item in items:
        normalized = _normalize_text(item)
        lowered = normalized.lower()
        if not normalized or lowered in seen:
            continue
        seen.add(lowered)
        values.append(normalized)
    return values


def _truncate_text(value: str, limit: int) -> str:
    normalized = value.strip()
    if len(normalized) <= limit:
        return normalized
    return normalized[:limit].rstrip()


def _extract_json_snippet(content: str) -> str:
    candidate = content.strip()
    if candidate.startswith("```"):
        lines = candidate.splitlines()
        if len(lines) >= 3 and lines[-1].strip().startswith("```"):
            candidate = "\n".join(lines[1:-1]).strip()
    decoder = json.JSONDecoder()
    starts = [index for index, ch in enumerate(candidate) if ch in {"[", "{"}]
    for start in starts:
        try:
            _, end = decoder.raw_decode(candidate[start:])
            return candidate[start : start + end]
        except json.JSONDecodeError:
            continue
    raise ValueError("AI response did not contain valid JSON")


def _parse_json(content: str) -> Any:
    return json.loads(_extract_json_snippet(content))


def _build_candidate_profile(*, role_summary: str, resume_summary: str) -> str:
    next_role_summary = role_summary.strip()
    next_resume_summary = resume_summary.strip()
    if next_role_summary and next_resume_summary:
        return f"岗位侧重点：{next_role_summary}\n候选人画像：{next_resume_summary}"
    return next_role_summary or next_resume_summary


def _build_first_question(job: JobDescription, workflow: ResumeOptimizationSession) -> MainQuestionPlan:
    job_title = job.title.strip() or "目标岗位"
    candidate_title = job.company.strip() if job.company else "你当前最相关的经历"
    if workflow.tailored_resume_md.strip():
        text = f"先请你做一个简短自我介绍，并重点讲一段最能证明你适合“{job_title}”的经历。"
    else:
        text = f"先请你做一个简短自我介绍，并说明你为什么想申请“{job_title}”。"
    return MainQuestionPlan(
        question_id="opening-1",
        category="开场",
        review_type=MockInterviewReviewType.PROJECT_EXPERIENCE,
        text=text,
        intent=f"快速判断候选人与岗位 {candidate_title} 的直接相关性",
        followup_hints=["与岗位最相关的经历", "岗位动机"],
    )


def _build_question_rubric(review_type: MockInterviewReviewType) -> list[str]:
    rubric_map = {
        MockInterviewReviewType.TECHNICAL_ANALYSIS: [
            "是否先定义问题现象与指标",
            "是否有分层排查框架",
            "是否避免过快归因",
            "是否体现验证与回归意识",
        ],
        MockInterviewReviewType.PROJECT_EXPERIENCE: [
            "是否讲清背景、职责和动作",
            "是否体现难点与取舍",
            "是否量化结果",
            "是否有 owner 感",
        ],
        MockInterviewReviewType.KNOWLEDGE_FUNDAMENTAL: [
            "概念是否准确",
            "是否解释清楚原理与因果",
            "是否能联系实践场景",
            "是否不是停留在术语层面",
        ],
    }
    return rubric_map[review_type]


def _deserialize_deep_review(payload: dict[str, Any] | None) -> DeepReviewResult | dict[str, Any]:
    if not payload:
        return {}
    try:
        return DeepReviewResult.model_validate(payload)
    except Exception:
        return payload


def _build_review_summary(turns: list[MockInterviewTurn]) -> MockInterviewReviewSummary:
    answered_turns = [turn for turn in turns if _normalize_text(turn.answer_text)]
    strengths: list[str] = []
    risks: list[str] = []
    next_steps: list[str] = []
    if answered_turns:
        strengths.append("已完成至少一轮真实问答，具备继续训练的基础素材。")
    if any(len(_normalize_text(turn.answer_text)) < 60 for turn in answered_turns):
        risks.append("部分回答偏短，建议补足背景、动作和结果。")
    if any(not _normalize_text(turn.answer_text) for turn in turns[-1:]):
        risks.append("最新题目尚未完成作答。")
    if answered_turns:
        next_steps.append("下一轮优先补充指标、规模和个人决策依据。")
    return MockInterviewReviewSummary(
        strengths=_dedupe_strings(strengths),
        risks=_dedupe_strings(risks),
        next_steps=_dedupe_strings(next_steps),
    )


def _serialize_turns(turns: list[MockInterviewTurn]) -> list[MockInterviewTurnRecord]:
    serialized: list[MockInterviewTurnRecord] = []
    for turn in turns:
        decision_json = turn.decision_json or {}
        serialized.append(
            MockInterviewTurnRecord(
                id=turn.id,
                session_id=turn.session_id,
                turn_index=turn.turn_index,
                question_text=turn.question_text,
                question_type="followup" if turn.question_source == "follow_up" else "main",
                main_question_id=turn.question_topic,
                review_type=coerce_mock_interview_review_type(turn.review_type),
                answer_text=turn.answer_text,
                comment_text=str(decision_json.get("comment_text") or "").strip() or None,
                evaluation_json=_deserialize_deep_review(turn.evaluation_json or {}),
                decision_json=decision_json,
                created_at=turn.created_at,
                updated_at=turn.updated_at,
            )
        )
    return serialized


def _serialize_session(
    session_record: MockInterviewSession,
    turns: list[MockInterviewTurn],
) -> MockInterviewSessionRecord:
    serialized_turns = _serialize_turns(turns)
    current_turn = next((turn for turn in reversed(serialized_turns) if turn.answer_text is None), None)
    plan_json = session_record.plan_json or {}
    return MockInterviewSessionRecord(
        id=session_record.id,
        user_id=session_record.user_id,
        job_id=session_record.jd_id,
        resume_optimization_session_id=session_record.optimization_session_id,
        source_job_version=session_record.source_job_version,
        source_resume_version=session_record.source_resume_version,
        status=session_record.status,
        question_count=session_record.current_question_index,
        main_question_index=max(0, int(plan_json.get("main_question_index", 0) or 0)),
        followup_count_for_current_main=int(
            plan_json.get("followup_count_for_current_main", session_record.current_follow_up_count) or 0
        ),
        max_questions=session_record.max_questions,
        max_followups_per_main=session_record.max_follow_ups_per_question,
        prep_state=_deserialize_task_state(plan_json.get("prep_state")),
        current_turn=current_turn,
        turns=serialized_turns,
        review=MockInterviewReviewSummary.model_validate(session_record.review_json or {}),
        ending_text=str(plan_json.get("ending_text") or "").strip() or None,
        error_message=session_record.error_message,
        created_at=session_record.created_at,
        updated_at=session_record.updated_at,
    )


def _build_recent_turns_payload(turns: list[MockInterviewTurn], limit: int = 3) -> str:
    payload: list[dict[str, Any]] = []
    answered_turns = [turn for turn in turns if _normalize_text(turn.answer_text)]
    for turn in answered_turns[-limit:]:
        payload.append(
            {
                "question": turn.question_text,
                "answer": _normalize_text(turn.answer_text),
                "question_type": "followup" if turn.question_source == "follow_up" else "main",
                "main_question_id": turn.question_topic,
            }
        )
    return json.dumps(payload, ensure_ascii=False)


def _build_asked_questions(turns: list[MockInterviewTurn]) -> list[str]:
    return [turn.question_text for turn in turns if _normalize_text(turn.question_text)]


def _get_ai_config(settings: Settings, *, model: str | None = None) -> AIProviderConfig:
    return AIProviderConfig(
        provider=settings.interview_ai_provider,
        base_url=settings.interview_ai_base_url,
        api_key=settings.interview_ai_api_key,
        model=model or settings.interview_ai_model_planning or settings.interview_ai_model,
        timeout_seconds=settings.interview_ai_timeout_seconds,
    )


async def _request_text(
    settings: Settings,
    *,
    prompt: str,
    max_tokens: int,
    model: str | None = None,
) -> str:
    if not is_ai_configured(
        provider=settings.interview_ai_provider,
        base_url=settings.interview_ai_base_url,
        model=model or settings.interview_ai_model_planning or settings.interview_ai_model,
        api_key=settings.interview_ai_api_key,
    ):
        raise RuntimeError("Interview AI is not configured")
    return await request_text_completion(
        config=_get_ai_config(settings, model=model),
        instructions=get_mock_interview_system_prompt(),
        payload={"prompt": prompt},
        max_tokens=max_tokens,
    )


def _coerce_main_question(item: Any, index: int) -> MainQuestionPlan:
    if not isinstance(item, dict):
        raise ValueError("Main question item must be an object")
    followup_hints = item.get("followup_hints", [])
    if not isinstance(followup_hints, list):
        followup_hints = []
    category = str(item.get("category", "未分类")).strip() or "未分类"
    text = str(item.get("text", "")).strip()
    intent = str(item.get("intent", "")).strip()
    return MainQuestionPlan(
        question_id=str(item.get("question_id", f"q{index}")).strip() or f"q{index}",
        category=category,
        review_type=coerce_mock_interview_review_type(
            str(item.get("review_type", "")).strip(),
            category=category,
            intent=intent,
            text=text,
        ),
        text=text,
        intent=intent,
        followup_hints=[str(hint).strip() for hint in followup_hints if str(hint).strip()],
    )


async def summarize_role_desc(settings: Settings, target_role_desc: str) -> str:
    try:
        return await _request_text(
            settings,
            prompt=get_mock_interview_role_summary_prompt().format(target_role_desc=target_role_desc),
            max_tokens=350,
            model=settings.interview_ai_model_planning or settings.interview_ai_model,
        )
    except Exception:
        return _truncate_text(target_role_desc, 150)


async def summarize_resume(settings: Settings, resume_md: str) -> str:
    try:
        return await _request_text(
            settings,
            prompt=get_mock_interview_resume_summary_prompt().format(resume_md=resume_md),
            max_tokens=500,
            model=settings.interview_ai_model_planning or settings.interview_ai_model,
        )
    except Exception:
        return _truncate_text(resume_md, 220)


async def generate_main_questions(
    settings: Settings,
    *,
    role_summary: str,
    candidate_profile: str,
) -> list[MainQuestionPlan]:
    try:
        content = await _request_text(
            settings,
            prompt=get_mock_interview_question_generation_prompt().format(
                role_summary=role_summary,
                candidate_profile=candidate_profile,
            ),
            max_tokens=4000,
            model=settings.interview_ai_model_planning or settings.interview_ai_model,
        )
        parsed = _parse_json(content)
        if not isinstance(parsed, list):
            raise ValueError("Main question pool must be a JSON array")
        questions = [_coerce_main_question(item, index + 1) for index, item in enumerate(parsed)]
        questions = [question for question in questions if question.text]
        if questions:
            return questions[:12]
    except Exception:
        logger.exception("Mock interview main question generation fell back to default questions")
    return [
        MainQuestionPlan(
            question_id=f"fallback-q{index + 1}",
            category="通用",
            review_type=review_type,
            text=text,
            intent="fallback",
            followup_hints=[],
        )
        for index, (text, review_type) in enumerate(FALLBACK_QUESTIONS)
    ]


async def decide_next_turn(
    settings: Settings,
    *,
    role_summary: str,
    candidate_profile: str,
    current_main_question: str,
    current_question: str,
    current_question_type: str,
    followup_count_for_current_main: int,
    question_count: int,
    max_total_questions: int,
    recent_turns: str,
    candidate_answer: str,
) -> MockInterviewTurnDecision:
    if question_count >= max_total_questions:
        return MockInterviewTurnDecision(
            need_comment=False,
            comment_text="",
            next_action="end",
            next_question="",
            reason="question budget exhausted",
        )
    try:
        content = await _request_text(
            settings,
            prompt=get_mock_interview_feedback_prompt().format(
                role_summary=role_summary,
                candidate_profile=candidate_profile,
                current_main_question=current_main_question,
                current_question=current_question,
                current_question_type=current_question_type,
                followup_count_for_current_main=followup_count_for_current_main,
                question_count=question_count,
                max_total_questions=max_total_questions,
                recent_turns=recent_turns,
                candidate_answer=candidate_answer,
            ),
            max_tokens=700,
            model=settings.interview_ai_model_realtime or settings.interview_ai_model,
        )
        parsed = _parse_json(content)
        if not isinstance(parsed, dict):
            raise ValueError("Turn decision must be a JSON object")
        next_action = str(parsed.get("next_action", "next_main")).strip()
        if next_action not in {"followup", "next_main", "end"}:
            next_action = "next_main"
        return MockInterviewTurnDecision(
            need_comment=bool(parsed.get("need_comment", False)),
            comment_text=str(parsed.get("comment_text", "")).strip(),
            next_action=next_action,  # type: ignore[arg-type]
            next_question=str(parsed.get("next_question", "")).strip(),
            reason=str(parsed.get("reason", "")).strip(),
        )
    except Exception:
        answer_length = len(candidate_answer.strip())
        should_follow_up = (
            answer_length < 80
            and followup_count_for_current_main < 2
            and question_count < max_total_questions
        )
        if should_follow_up:
            return MockInterviewTurnDecision(
                need_comment=False,
                comment_text="",
                next_action="followup",
                next_question=f"你刚才提到“{_truncate_text(candidate_answer, 24)}”，能再具体展开一下吗？",
                reason="fallback short-answer followup",
            )
        return MockInterviewTurnDecision(
            need_comment=answer_length >= 80,
            comment_text="你的回答方向是对的，可以继续保持这种结构化表达。" if answer_length >= 80 else "",
            next_action="end" if question_count >= max_total_questions else "next_main",
            next_question="" if question_count >= max_total_questions else current_question,
            reason="fallback next main",
        )


async def generate_dynamic_main_question(
    settings: Settings,
    *,
    role_summary: str,
    candidate_profile: str,
    asked_questions: list[str],
) -> MainQuestionPlan:
    try:
        content = await _request_text(
            settings,
            prompt=get_mock_interview_dynamic_question_prompt().format(
                role_summary=role_summary,
                candidate_profile=candidate_profile,
                asked_questions=asked_questions,
            ),
            max_tokens=500,
            model=settings.interview_ai_model_planning or settings.interview_ai_model,
        )
        parsed = _parse_json(content)
        if not isinstance(parsed, dict):
            raise ValueError("Dynamic main question must be a JSON object")
        return _coerce_main_question(parsed, len(asked_questions) + 1)
    except Exception:
        fallback_text, fallback_review_type = FALLBACK_QUESTIONS[len(asked_questions) % len(FALLBACK_QUESTIONS)]
        return MainQuestionPlan(
            question_id=f"fallback-extra-{len(asked_questions) + 1}",
            category="通用",
            review_type=fallback_review_type,
            text=fallback_text,
            intent="fallback",
            followup_hints=[],
        )


async def generate_ending_text(
    settings: Settings,
    *,
    candidate_profile: str,
    recent_turns: str,
) -> str:
    try:
        return await _request_text(
            settings,
            prompt=get_mock_interview_recap_prompt().format(
                candidate_profile=candidate_profile,
                recent_turns=recent_turns,
            ),
            max_tokens=180,
            model=settings.interview_ai_model_realtime or settings.interview_ai_model,
        )
    except Exception:
        return DEFAULT_ENDING_TEXT


def _find_main_question(plan_json: dict[str, Any], *, question_id: str | None) -> dict[str, Any] | None:
    for item in plan_json.get("main_questions", []):
        if isinstance(item, dict) and str(item.get("question_id")) == str(question_id):
            return item
    return None


def _resolve_turn_review_type(
    plan_json: dict[str, Any],
    *,
    question_type: str,
    main_question_id: str | None,
    fallback_review_type: MockInterviewReviewType = MockInterviewReviewType.PROJECT_EXPERIENCE,
) -> MockInterviewReviewType:
    question = _find_main_question(plan_json, question_id=main_question_id) or {}
    if question_type == "followup" and not question and plan_json.get("current_main_question_id"):
        question = _find_main_question(plan_json, question_id=str(plan_json.get("current_main_question_id"))) or {}
    if question:
        return coerce_mock_interview_review_type(
            str(question.get("review_type", "")).strip(),
            category=str(question.get("category", "")).strip(),
            intent=str(question.get("intent", "")).strip(),
            text=str(question.get("text", "")).strip(),
        )
    current_review_type = str(plan_json.get("current_review_type", "")).strip()
    if current_review_type:
        return coerce_mock_interview_review_type(current_review_type)
    return fallback_review_type


def _get_or_build_next_question(plan_json: dict[str, Any]) -> tuple[str, str, str | None]:
    queued_followup = _normalize_text(str(plan_json.get("queued_followup_question") or ""))
    if queued_followup:
        plan_json["queued_followup_question"] = None
        return queued_followup, "followup", plan_json.get("current_main_question_id")

    main_question_index = int(plan_json.get("main_question_index", 0) or 0)
    main_questions = plan_json.get("main_questions", [])
    if 0 <= main_question_index < len(main_questions):
        question = main_questions[main_question_index]
        if isinstance(question, dict):
            return (
                str(question.get("text") or ""),
                "main",
                str(question.get("question_id") or "") or None,
            )

    return "", "main", None


def _assign_current_question(
    plan_json: dict[str, Any],
    *,
    question_text: str,
    question_type: str,
    main_question_id: str | None,
    review_type: MockInterviewReviewType,
) -> None:
    plan_json["current_question"] = question_text
    plan_json["current_question_type"] = question_type
    plan_json["current_main_question_id"] = main_question_id
    plan_json["current_review_type"] = review_type.value
    if question_type == "main":
        plan_json["followup_count_for_current_main"] = 0


def _apply_turn_decision(plan_json: dict[str, Any], decision: MockInterviewTurnDecision) -> bool:
    if decision.next_action == "followup":
        plan_json["followup_count_for_current_main"] = int(
            plan_json.get("followup_count_for_current_main", 0) or 0
        ) + 1
        plan_json["queued_followup_question"] = decision.next_question
        return False

    plan_json["queued_followup_question"] = None
    if decision.next_action == "next_main":
        plan_json["main_question_index"] = int(plan_json.get("main_question_index", 0) or 0) + 1
        plan_json["followup_count_for_current_main"] = 0
        return False

    return True


async def get_mock_interview_session_or_404(
    session: AsyncSession,
    *,
    current_user: User,
    session_id: UUID,
) -> MockInterviewSession:
    result = await session.execute(
        select(MockInterviewSession).where(
            MockInterviewSession.id == session_id,
            MockInterviewSession.user_id == current_user.id,
        )
    )
    session_record = result.scalar_one_or_none()
    if session_record is None:
        raise ApiException(
            status_code=404,
            code=ErrorCode.NOT_FOUND,
            message="Mock interview session not found",
        )
    return session_record


async def get_mock_interview_turn_or_404(
    session: AsyncSession,
    *,
    current_user: User,
    session_id: UUID,
    turn_id: UUID,
) -> MockInterviewTurn:
    session_record = await get_mock_interview_session_or_404(
        session,
        current_user=current_user,
        session_id=session_id,
    )
    result = await session.execute(
        select(MockInterviewTurn).where(
            MockInterviewTurn.id == turn_id,
            MockInterviewTurn.session_id == session_record.id,
        )
    )
    turn = result.scalar_one_or_none()
    if turn is None:
        raise ApiException(
            status_code=404,
            code=ErrorCode.NOT_FOUND,
            message="Mock interview turn not found",
        )
    return turn


async def _list_session_turns(
    session: AsyncSession,
    *,
    session_id: UUID,
) -> list[MockInterviewTurn]:
    result = await session.execute(
        select(MockInterviewTurn)
        .where(MockInterviewTurn.session_id == session_id)
        .order_by(MockInterviewTurn.turn_index.asc(), MockInterviewTurn.created_at.asc())
    )
    return list(result.scalars().all())


async def list_mock_interview_sessions(
    session: AsyncSession,
    *,
    current_user: User,
    job_id: UUID | None = None,
) -> list[MockInterviewSessionRecord]:
    statement = select(MockInterviewSession).where(MockInterviewSession.user_id == current_user.id)
    if job_id is not None:
        statement = statement.where(MockInterviewSession.jd_id == job_id)
    result = await session.execute(statement.order_by(desc(MockInterviewSession.created_at)))
    items: list[MockInterviewSessionRecord] = []
    for session_record in result.scalars().all():
        turns = await _list_session_turns(session, session_id=session_record.id)
        items.append(_serialize_session(session_record, turns))
    return items


async def get_mock_interview_session_detail(
    session: AsyncSession,
    *,
    current_user: User,
    session_id: UUID,
) -> MockInterviewSessionRecord:
    session_record = await get_mock_interview_session_or_404(
        session,
        current_user=current_user,
        session_id=session_id,
    )
    turns = await _list_session_turns(session, session_id=session_record.id)
    return _serialize_session(session_record, turns)


async def retry_mock_interview_prep(
    session: AsyncSession,
    *,
    current_user: User,
    session_id: UUID,
) -> MockInterviewSession:
    session_record = await get_mock_interview_session_or_404(
        session,
        current_user=current_user,
        session_id=session_id,
    )
    state = _mark_prep_state(
        session_record,
        status="processing",
        phase="retrying",
        message="正在重新准备后续题目。",
    )
    state.completed_at = None
    state.first_completed_at = None
    session_record.plan_json = {**(session_record.plan_json or {}), "prep_state": _serialize_task_state(state)}
    session_record.error_message = None
    _append_session_event(session_record, event_type="mock_interview_retry_requested")
    session.add(session_record)
    await session.commit()
    await session.refresh(session_record)
    return session_record


async def record_mock_interview_event(
    session: AsyncSession,
    *,
    current_user: User,
    session_id: UUID,
    event_type: str,
    payload: dict[str, Any] | None = None,
) -> None:
    session_record = await get_mock_interview_session_or_404(
        session,
        current_user=current_user,
        session_id=session_id,
    )
    _append_session_event(session_record, event_type=event_type, payload=payload)
    session.add(session_record)
    await session.commit()


async def process_mock_interview_prep(
    *,
    session_id: UUID,
    session_factory,
    settings: Settings,
) -> None:
    async with session_factory() as session:
        session_record = await session.get(MockInterviewSession, session_id)
        if session_record is None:
            return
        job = await session.get(JobDescription, session_record.jd_id)
        workflow = await session.get(ResumeOptimizationSession, session_record.optimization_session_id)
        if job is None or workflow is None:
            state = _mark_prep_state(
                session_record,
                status="failed",
                phase="failed",
                message="准备失败，缺少岗位或优化简历信息。",
            )
            state.metrics["failure_reason"] = "missing_dependencies"
            session_record.plan_json = {**(session_record.plan_json or {}), "prep_state": _serialize_task_state(state)}
            session_record.error_message = "准备失败，缺少岗位或优化简历信息。"
            session.add(session_record)
            await session.commit()
            return

        try:
            state = _mark_prep_state(
                session_record,
                status="processing",
                phase="summarizing_context",
                message="正在准备后续题。",
            )
            session_record.plan_json = {**(session_record.plan_json or {}), "prep_state": _serialize_task_state(state)}
            session.add(session_record)
            await session.commit()

            tailored_resume_md = workflow.tailored_resume_md or ""
            role_summary = await summarize_role_desc(settings, job.jd_text)
            resume_summary = await summarize_resume(settings, tailored_resume_md)
            candidate_profile = _build_candidate_profile(
                role_summary=role_summary,
                resume_summary=resume_summary,
            )
            main_questions = await generate_main_questions(
                settings,
                role_summary=role_summary,
                candidate_profile=candidate_profile,
            )

            plan_json = dict(session_record.plan_json or {})
            existing_question = plan_json.get("current_question") or ""
            existing_question_id = plan_json.get("current_main_question_id") or ""
            if main_questions:
                if not existing_question:
                    existing_question = main_questions[0].text
                    existing_question_id = main_questions[0].question_id
                    plan_json["current_review_type"] = main_questions[0].review_type.value
                remaining_questions = [asdict(item) for item in main_questions if item.question_id != existing_question_id]
            else:
                remaining_questions = []
            plan_json.update(
                {
                    "role_summary": role_summary,
                    "resume_summary": resume_summary,
                    "candidate_profile": candidate_profile,
                    "main_questions": remaining_questions,
                    "prep_state": _serialize_task_state(
                        TaskState(
                            status="success",
                            phase="ready",
                            message="后续题目已准备完成。",
                            started_at=state.started_at,
                            first_completed_at=state.first_completed_at or utc_now_naive(),
                            completed_at=utc_now_naive(),
                            last_updated_at=utc_now_naive(),
                            metrics={
                                "first_question_latency_ms": int(
                                    max(
                                        0,
                                        (
                                            (state.first_completed_at or utc_now_naive())
                                            - (state.started_at or utc_now_naive())
                                        ).total_seconds()
                                        * 1000,
                                    )
                                )
                            },
                        )
                    ),
                }
            )
            session_record.plan_json = plan_json
            _append_session_event(session_record, event_type="mock_interview_prep_completed")
            session.add(session_record)
            await session.commit()
        except Exception as exc:
            state = _mark_prep_state(
                session_record,
                status="failed",
                phase="failed",
                message="准备后续题目失败，可重试。",
            )
            state.metrics["failure_reason"] = str(exc)
            session_record.plan_json = {**(session_record.plan_json or {}), "prep_state": _serialize_task_state(state)}
            session_record.error_message = str(exc)
            _append_session_event(
                session_record,
                event_type="mock_interview_prep_failed",
                payload={"message": str(exc)},
            )
            session.add(session_record)
            await session.commit()


async def process_mock_interview_turn(
    *,
    session_id: UUID,
    turn_id: UUID,
    session_factory,
    settings: Settings,
) -> None:
    async with session_factory() as session:
        session_record = await session.get(MockInterviewSession, session_id)
        turn = await session.get(MockInterviewTurn, turn_id)
        if session_record is None or turn is None:
            return
        try:
            state = _mark_prep_state(
                session_record,
                status="processing",
                phase="preparing_next_turn",
                message="正在准备下一题。",
            )
            session_record.plan_json = {**(session_record.plan_json or {}), "prep_state": _serialize_task_state(state)}
            session.add(session_record)
            await session.commit()

            turns = await _list_session_turns(session, session_id=session_record.id)
            plan_json = dict(session_record.plan_json or {})
            current_main_question_id = str(plan_json.get("current_main_question_id") or turn.question_topic or "")
            current_main_question = _find_main_question(plan_json, question_id=current_main_question_id) or {}
            decision = await decide_next_turn(
                settings,
                role_summary=str(plan_json.get("role_summary") or ""),
                candidate_profile=str(plan_json.get("candidate_profile") or ""),
                current_main_question=str(current_main_question.get("text") or turn.question_text),
                current_question=turn.question_text,
                current_question_type=str(plan_json.get("current_question_type") or "main"),
                followup_count_for_current_main=int(
                    plan_json.get("followup_count_for_current_main", session_record.current_follow_up_count) or 0
                ),
                question_count=session_record.current_question_index,
                max_total_questions=session_record.max_questions,
                recent_turns=_build_recent_turns_payload(turns),
                candidate_answer=str(turn.answer_text or ""),
            )

            deep_review = await review_interview_answer(
                settings,
                review_type=coerce_mock_interview_review_type(turn.review_type),
                role_summary=str(plan_json.get("role_summary") or ""),
                candidate_profile=str(plan_json.get("candidate_profile") or ""),
                question=turn.question_text,
                answer=str(turn.answer_text or ""),
                company_or_style="",
            )

            turn.decision_json = decision.model_dump()
            turn.evaluation_json = deep_review.model_dump(mode="json")
            turn.updated_at = utc_now_naive()
            session.add(turn)

            interview_ended = _apply_turn_decision(plan_json, decision)
            session_record.current_follow_up_count = int(
                plan_json.get("followup_count_for_current_main", session_record.current_follow_up_count) or 0
            )

            if not interview_ended and session_record.current_question_index >= session_record.max_questions:
                interview_ended = True

            if interview_ended:
                plan_json["queued_followup_question"] = None
                ending_text = await generate_ending_text(
                    settings,
                    candidate_profile=str(plan_json.get("candidate_profile") or ""),
                    recent_turns=_build_recent_turns_payload(turns),
                )
                plan_json["ending_text"] = ending_text
                session_record.status = "completed"
            else:
                question_text, question_type, main_question_id = _get_or_build_next_question(plan_json)
                if not question_text:
                    dynamic_main_question = await generate_dynamic_main_question(
                        settings,
                        role_summary=str(plan_json.get("role_summary") or ""),
                        candidate_profile=str(plan_json.get("candidate_profile") or ""),
                        asked_questions=_build_asked_questions(turns),
                    )
                    main_questions = list(plan_json.get("main_questions") or [])
                    main_questions.append(asdict(dynamic_main_question))
                    plan_json["main_questions"] = main_questions
                    question_text, question_type, main_question_id = _get_or_build_next_question(plan_json)

                next_review_type = _resolve_turn_review_type(
                    plan_json,
                    question_type=question_type,
                    main_question_id=main_question_id,
                )

                _assign_current_question(
                    plan_json,
                    question_text=question_text,
                    question_type=question_type,
                    main_question_id=main_question_id,
                    review_type=next_review_type,
                )
                session_record.current_follow_up_count = int(
                    plan_json.get("followup_count_for_current_main", session_record.current_follow_up_count) or 0
                )
                session_record.current_question_index += 1
                next_turn = MockInterviewTurn(
                    session_id=session_record.id,
                    turn_index=session_record.current_question_index,
                    question_group_index=int(plan_json.get("main_question_index", 0) or 0) + 1,
                    question_source="follow_up" if question_type == "followup" else "main",
                    review_type=next_review_type.value,
                    question_topic=str(main_question_id or ""),
                    question_text=question_text,
                    question_intent=decision.reason if question_type == "followup" else "",
                    question_rubric_json=_build_question_rubric(next_review_type),
                    status="asked",
                    evaluation_json={},
                    decision_json={},
                    asked_at=utc_now_naive(),
                    created_by=session_record.updated_by,
                    updated_by=session_record.updated_by,
                )
                session.add(next_turn)

            ready_state = TaskState(
                status="success",
                phase="ready",
                message="下一轮已准备完成。",
                started_at=state.started_at,
                first_completed_at=state.first_completed_at or utc_now_naive(),
                completed_at=utc_now_naive(),
                last_updated_at=utc_now_naive(),
            )
            session_record.plan_json = {
                **plan_json,
                "prep_state": _serialize_task_state(ready_state),
            }
            updated_turns = await _list_session_turns(session, session_id=session_record.id)
            session_record.review_json = _build_review_summary(updated_turns).model_dump(mode="json")
            session.add(session_record)
            await session.commit()
        except Exception as exc:
            state = _mark_prep_state(
                session_record,
                status="failed",
                phase="failed",
                message="准备下一题失败，可重试。",
            )
            state.metrics["failure_reason"] = str(exc)
            session_record.plan_json = {**(session_record.plan_json or {}), "prep_state": _serialize_task_state(state)}
            session_record.error_message = str(exc)
            session.add(session_record)
            await session.commit()


async def create_mock_interview_session(
    session: AsyncSession,
    *,
    current_user: User,
    payload: MockInterviewSessionCreateRequest,
    settings: Settings,
) -> MockInterviewSessionRecord:
    job = await session.get(JobDescription, payload.job_id)
    workflow = await session.get(ResumeOptimizationSession, payload.resume_optimization_session_id)
    if job is None or job.user_id != current_user.id:
        raise ApiException(status_code=404, code=ErrorCode.NOT_FOUND, message="Job not found")
    if workflow is None or workflow.user_id != current_user.id:
        raise ApiException(
            status_code=404,
            code=ErrorCode.NOT_FOUND,
            message="Tailored resume workflow not found",
        )
    if workflow.jd_id != job.id:
        raise ApiException(
            status_code=409,
            code=ErrorCode.CONFLICT,
            message="Workflow does not belong to the target job",
        )

    resume = await session.get(Resume, workflow.resume_id)
    report = await session.get(MatchReport, workflow.match_report_id)
    if resume is None or resume.user_id != current_user.id:
        raise ApiException(status_code=404, code=ErrorCode.NOT_FOUND, message="Resume not found")
    if report is None or report.user_id != current_user.id:
        raise ApiException(status_code=404, code=ErrorCode.NOT_FOUND, message="Match report not found")

    tailored_resume_md = workflow.tailored_resume_md or ""
    if not tailored_resume_md.strip():
        raise ApiException(
            status_code=409,
            code=ErrorCode.CONFLICT,
            message="Tailored resume markdown is not ready",
        )

    del settings
    first_question = _build_first_question(job, workflow)
    prep_state = TaskState(
        status="processing",
        phase="preparing_question_pool",
        message="首题已生成，正在准备后续题。",
        started_at=utc_now_naive(),
        last_updated_at=utc_now_naive(),
    )

    session_record = MockInterviewSession(
        user_id=current_user.id,
        resume_id=resume.id,
        jd_id=job.id,
        match_report_id=report.id,
        optimization_session_id=workflow.id,
        source_resume_version=workflow.source_resume_version,
        source_job_version=workflow.source_job_version,
        mode="general",
        status="active",
        current_question_index=1,
        current_follow_up_count=0,
        max_questions=16,
        max_follow_ups_per_question=2,
        plan_json={
            "role_summary": "",
            "resume_summary": "",
            "candidate_profile": "",
            "main_questions": [],
            "main_question_index": -1,
            "followup_count_for_current_main": 0,
            "current_question": first_question.text,
            "current_question_type": "main",
            "current_main_question_id": first_question.question_id,
            "current_review_type": first_question.review_type.value,
            "queued_followup_question": None,
            "ending_text": None,
            "prep_state": prep_state.model_dump(mode="json"),
        },
        review_json=MockInterviewReviewSummary().model_dump(mode="json"),
        created_by=current_user.id,
        updated_by=current_user.id,
    )
    session.add(session_record)
    await session.flush()

    asked_at = utc_now_naive()
    turn = MockInterviewTurn(
        session_id=session_record.id,
        turn_index=1,
        question_group_index=1,
        question_source="main",
        review_type=first_question.review_type.value,
        question_topic=first_question.question_id,
        question_text=first_question.text,
        question_intent=first_question.intent,
        question_rubric_json=_build_question_rubric(first_question.review_type),
        status="asked",
        evaluation_json={},
        decision_json={},
        asked_at=asked_at,
        created_by=current_user.id,
        updated_by=current_user.id,
    )
    session.add(turn)
    _append_session_event(session_record, event_type="mock_interview_created")
    await session.commit()
    return await get_mock_interview_session_detail(
        session,
        current_user=current_user,
        session_id=session_record.id,
    )


async def submit_mock_interview_answer(
    session: AsyncSession,
    *,
    current_user: User,
    session_id: UUID,
    turn_id: UUID,
    answer_text: str,
    settings: Settings,
) -> MockInterviewAnswerSubmitResponse:
    session_record = await get_mock_interview_session_or_404(
        session,
        current_user=current_user,
        session_id=session_id,
    )
    if session_record.status != "active":
        raise ApiException(
            status_code=409,
            code=ErrorCode.CONFLICT,
            message="Mock interview session is not active",
        )
    turn = await get_mock_interview_turn_or_404(
        session,
        current_user=current_user,
        session_id=session_id,
        turn_id=turn_id,
    )
    if turn.answer_text:
        raise ApiException(
            status_code=409,
            code=ErrorCode.CONFLICT,
            message="This interview turn has already been answered",
        )

    normalized_answer = answer_text.strip()
    now = utc_now_naive()

    turn.answer_text = normalized_answer
    turn.status = "answered"
    turn.evaluation_json = DeepReviewResult.pending().model_dump(mode="json")
    turn.answered_at = now
    turn.evaluated_at = now
    turn.updated_by = current_user.id
    session.add(turn)
    plan_json = dict(session_record.plan_json or {})
    plan_json["prep_state"] = TaskState(
        status="processing",
        phase="preparing_next_turn",
        message="回答已保存，正在准备下一题。",
        started_at=utc_now_naive(),
        last_updated_at=utc_now_naive(),
    ).model_dump(mode="json")
    session_record.plan_json = plan_json
    session_record.updated_by = current_user.id
    session_record.review_json = _build_review_summary(
        await _list_session_turns(session, session_id=session_record.id)
    ).model_dump(mode="json")
    session.add(session_record)
    await session.commit()
    return MockInterviewAnswerSubmitResponse(
        session_id=session_record.id,
        submitted_turn_id=turn.id,
        next_action={"type": "processing"},
    )


async def finish_mock_interview_session(
    session: AsyncSession,
    *,
    current_user: User,
    session_id: UUID,
    settings: Settings,
) -> MockInterviewSessionRecord:
    session_record = await get_mock_interview_session_or_404(
        session,
        current_user=current_user,
        session_id=session_id,
    )
    turns = await _list_session_turns(session, session_id=session_record.id)
    plan_json = dict(session_record.plan_json or {})
    if session_record.status != "completed":
        ending_text = await generate_ending_text(
            settings,
            candidate_profile=str(plan_json.get("candidate_profile") or ""),
            recent_turns=_build_recent_turns_payload(turns),
        )
        plan_json["ending_text"] = ending_text
        plan_json["prep_state"] = TaskState(
            status="success",
            phase="completed",
            message="本场模拟面试已结束。",
            started_at=_deserialize_task_state(plan_json.get("prep_state")).started_at,
            completed_at=utc_now_naive(),
            last_updated_at=utc_now_naive(),
        ).model_dump(mode="json")
        session_record.plan_json = plan_json
        session_record.status = "completed"
        session_record.review_json = _build_review_summary(turns).model_dump(mode="json")
        session_record.updated_by = current_user.id
        session.add(session_record)
        await session.commit()
    return await get_mock_interview_session_detail(
        session,
        current_user=current_user,
        session_id=session_id,
    )


async def delete_mock_interview_session(
    session: AsyncSession,
    *,
    current_user: User,
    session_id: UUID,
) -> None:
    session_record = await get_mock_interview_session_or_404(
        session,
        current_user=current_user,
        session_id=session_id,
    )
    await session.delete(session_record)
    await session.commit()
