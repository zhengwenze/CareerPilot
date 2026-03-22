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
from app.schemas.mock_interview import (
    MockInterviewAnswerSubmitResponse,
    MockInterviewSessionCreateRequest,
    MockInterviewSessionRecord,
    MockInterviewTurnDecision,
    MockInterviewTurnRecord,
)
from app.services.ai_client import AIProviderConfig, request_text_completion

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """你是一名专业、自然、正式的中文面试官。

任务是基于候选人的目标岗位描述和优化后的简历内容，发起一场模拟面试。

行为规则：
1. 总提问预算固定，系统会告诉你还剩多少次提问。
2. 每次只能输出一个问题。
3. 允许在提问前给出一句非常短的点评，但点评不是必须的。
4. 点评必须简短、自然、不过度教学。
5. 对同一个主问题，最多追问 2 次。
6. 若候选人的回答已经足够完整，就切换到下一个主问题。
7. 问题必须贴近岗位描述和简历内容。
8. 不要输出多个并列问题。
9. 不要输出长段分析。
10. 不要输出总结报告。
11. 语气保持真实面试风格，默认正式但不过度施压。
12. 如果信息不足，也不要抱怨输入格式，而是基于已有内容尽量生成合理问题。
""".strip()

ROLE_SUMMARY_PROMPT = """请将下面的目标岗位描述压缩为一段简洁摘要，用于后续模拟面试。

要求：
1. 提取岗位名称、级别线索、核心技能、业务方向、优先关注点。
2. 不要编造不存在的信息。
3. 输出中文。
4. 控制在 150 字以内。

目标岗位描述：
{target_role_desc}
""".strip()

RESUME_SUMMARY_PROMPT = """请根据下面的简历 Markdown，提炼一份候选人画像摘要，用于模拟面试。

要求：
1. 提取核心经历、项目、技能、教育背景、岗位匹配亮点。
2. 若简历结构混乱，也要尽量提炼有效信息。
3. 不要编造不存在的经历。
4. 输出中文。
5. 控制在 220 字以内。

简历 Markdown：
{resume_md}
""".strip()

MAIN_QUESTION_POOL_PROMPT = """你要生成一场模拟面试的主问题池。

输入信息：
- 岗位摘要：{role_summary}
- 候选人画像：{candidate_profile}

要求：
1. 生成 12 个主问题。
2. 问题要尽量覆盖：
   - 自我介绍/求职动机
   - 项目经历
   - 岗位核心能力
   - 技术/业务理解
   - 协作沟通/行为面
3. 问题必须贴合岗位摘要和候选人画像。
4. 每个问题都要尽量具体，避免空泛。
5. 每个问题只问一个点。
6. 每题附带：
   - question_id
   - category
   - text
   - intent
   - followup_hints（给出1~3个可能追问方向）
7. 输出 JSON 数组，不要输出额外说明。
""".strip()

TURN_DECISION_PROMPT = """你正在进行一场模拟面试。

输入信息：
- 岗位摘要：{role_summary}
- 候选人画像：{candidate_profile}
- 当前主问题：{current_main_question}
- 当前问题：{current_question}
- 当前问题类型：{current_question_type}
- 当前主问题下已追问次数：{followup_count_for_current_main}
- 当前总提问次数：{question_count}
- 最大提问次数：{max_total_questions}
- 最近对话：{recent_turns}
- 候选人本轮回答：{candidate_answer}

请你判断：
1. 是否需要一句短点评
2. 下一步是追问、切换到下一个主问题，还是结束
3. 如果追问或切到下一个主问题，请给出下一个问题

强约束：
1. 点评不是必须的；若给点评，必须非常短。
2. 同一主问题最多追问 2 次。
3. 问题必须具体，只问一个点。
4. 如果总提问次数已经达到上限，则 next_action 必须为 "end"。
5. 不要输出总结报告。
6. 输出必须是 JSON 对象。
""".strip()

DYNAMIC_MAIN_QUESTION_PROMPT = """你要为一场模拟面试补充 1 个新的主问题。

输入：
- 岗位摘要：{role_summary}
- 候选人画像：{candidate_profile}
- 已问过的问题列表：{asked_questions}

要求：
1. 新问题不能与已问过的问题重复。
2. 问题要贴合岗位和候选人经历。
3. 只输出 1 个主问题。
4. 输出 JSON 对象。
""".strip()

ENDING_PROMPT = """请为一场已经结束的模拟面试生成极简结束语。

要求：
1. 只写 2~3 句。
2. 语气自然、礼貌、正式。
3. 可以有一句非常轻量的总体反馈，但不要写成总结报告。
4. 不要分点。
5. 不要超过 80 个中文字符。

候选人画像：
{candidate_profile}

最近几轮对话：
{recent_turns}
""".strip()

FALLBACK_QUESTIONS = [
    "先请你做一个简短的自我介绍，并重点讲和这个岗位最相关的经历。",
    "你简历里最能体现你能力的一个项目是什么？请详细说说。",
    "在那个项目中，你承担的核心职责是什么？",
    "你在过往经历里遇到过最棘手的问题是什么？你是怎么解决的？",
    "如果让你来胜任这个岗位，你觉得自己最突出的优势是什么？",
    "你觉得自己和这个岗位之间还有哪些能力差距？",
    "你在团队协作中通常承担什么角色？",
    "如果项目进度紧张但需求还在变化，你会怎么处理？",
]

DEFAULT_ENDING_TEXT = "本次模拟面试到这里结束，感谢你的参与。整体交流比较顺畅，建议你继续加强细节表达和案例量化。"


@dataclass(slots=True)
class MainQuestionPlan:
    question_id: str
    category: str
    text: str
    intent: str
    followup_hints: list[str] = field(default_factory=list)


def utc_now_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _normalize_text(value: str | None) -> str:
    return " ".join((value or "").split()).strip()


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
                answer_text=turn.answer_text,
                comment_text=str(decision_json.get("comment_text") or "").strip() or None,
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
        main_question_index=int(plan_json.get("main_question_index", 0) or 0),
        followup_count_for_current_main=int(
            plan_json.get("followup_count_for_current_main", session_record.current_follow_up_count) or 0
        ),
        max_questions=session_record.max_questions,
        max_followups_per_main=session_record.max_follow_ups_per_question,
        current_turn=current_turn,
        turns=serialized_turns,
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
    if not settings.interview_ai_api_key:
        raise RuntimeError("Interview AI is not configured")
    return await request_text_completion(
        config=_get_ai_config(settings, model=model),
        instructions=SYSTEM_PROMPT,
        payload={"prompt": prompt},
        max_tokens=max_tokens,
    )


def _coerce_main_question(item: Any, index: int) -> MainQuestionPlan:
    if not isinstance(item, dict):
        raise ValueError("Main question item must be an object")
    followup_hints = item.get("followup_hints", [])
    if not isinstance(followup_hints, list):
        followup_hints = []
    return MainQuestionPlan(
        question_id=str(item.get("question_id", f"q{index}")).strip() or f"q{index}",
        category=str(item.get("category", "未分类")).strip() or "未分类",
        text=str(item.get("text", "")).strip(),
        intent=str(item.get("intent", "")).strip(),
        followup_hints=[str(hint).strip() for hint in followup_hints if str(hint).strip()],
    )


async def summarize_role_desc(settings: Settings, target_role_desc: str) -> str:
    try:
        return await _request_text(
            settings,
            prompt=ROLE_SUMMARY_PROMPT.format(target_role_desc=target_role_desc),
            max_tokens=350,
            model=settings.interview_ai_model_planning or settings.interview_ai_model,
        )
    except Exception:
        return _truncate_text(target_role_desc, 150)


async def summarize_resume(settings: Settings, resume_md: str) -> str:
    try:
        return await _request_text(
            settings,
            prompt=RESUME_SUMMARY_PROMPT.format(resume_md=resume_md),
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
            prompt=MAIN_QUESTION_POOL_PROMPT.format(
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
            text=text,
            intent="fallback",
            followup_hints=[],
        )
        for index, text in enumerate(FALLBACK_QUESTIONS)
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
            prompt=TURN_DECISION_PROMPT.format(
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
            prompt=DYNAMIC_MAIN_QUESTION_PROMPT.format(
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
        fallback_text = FALLBACK_QUESTIONS[len(asked_questions) % len(FALLBACK_QUESTIONS)]
        return MainQuestionPlan(
            question_id=f"fallback-extra-{len(asked_questions) + 1}",
            category="通用",
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
            prompt=ENDING_PROMPT.format(
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
) -> None:
    plan_json["current_question"] = question_text
    plan_json["current_question_type"] = question_type
    plan_json["current_main_question_id"] = main_question_id
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
    first_question = main_questions[0]

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
            "role_summary": role_summary,
            "resume_summary": resume_summary,
            "candidate_profile": candidate_profile,
            "main_questions": [asdict(item) for item in main_questions],
            "main_question_index": 0,
            "followup_count_for_current_main": 0,
            "current_question": first_question.text,
            "current_question_type": "main",
            "current_main_question_id": first_question.question_id,
            "queued_followup_question": None,
            "ending_text": None,
        },
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
        question_topic=first_question.question_id,
        question_text=first_question.text,
        question_intent=first_question.intent,
        question_rubric_json=[],
        status="asked",
        evaluation_json={},
        decision_json={},
        asked_at=asked_at,
        created_by=current_user.id,
        updated_by=current_user.id,
    )
    session.add(turn)
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
    plan_json = dict(session_record.plan_json or {})
    turns = await _list_session_turns(session, session_id=session_record.id)
    now = utc_now_naive()

    turn.answer_text = normalized_answer
    turn.status = "answered"
    turn.answered_at = now
    turn.evaluated_at = now
    turn.updated_by = current_user.id
    session.add(turn)

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
        candidate_answer=normalized_answer,
    )

    turn.decision_json = decision.model_dump()
    turn.evaluation_json = {"summary": decision.comment_text if decision.need_comment else ""}
    session.add(turn)

    interview_ended = _apply_turn_decision(plan_json, decision)
    session_record.current_follow_up_count = int(
        plan_json.get("followup_count_for_current_main", session_record.current_follow_up_count) or 0
    )

    next_action_payload: dict[str, Any] = {"type": decision.next_action}
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
        next_action_payload["ending_text"] = ending_text
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

        _assign_current_question(
            plan_json,
            question_text=question_text,
            question_type=question_type,
            main_question_id=main_question_id,
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
            question_topic=str(main_question_id or ""),
            question_text=question_text,
            question_intent=decision.reason if question_type == "followup" else "",
            question_rubric_json=[],
            status="asked",
            evaluation_json={},
            decision_json={},
            asked_at=now,
            created_by=current_user.id,
            updated_by=current_user.id,
        )
        session.add(next_turn)

    session_record.plan_json = plan_json
    session_record.updated_by = current_user.id
    session.add(session_record)
    await session.commit()
    return MockInterviewAnswerSubmitResponse(
        session_id=session_record.id,
        submitted_turn_id=turn.id,
        next_action=next_action_payload,
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
        session_record.plan_json = plan_json
        session_record.status = "completed"
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
