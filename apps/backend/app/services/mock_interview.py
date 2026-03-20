from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal, ROUND_HALF_UP
from uuid import UUID

from sqlalchemy import delete, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.errors import ApiException, ErrorCode
from app.models import (
    JobDescription,
    JobReadinessEvent,
    MatchReport,
    MockInterviewSession,
    MockInterviewTurn,
    Resume,
    ResumeOptimizationSession,
    User,
)
from app.schemas.job import JobStructuredData
from app.schemas.mock_interview import (
    MockInterviewAnswerSubmitRequest,
    MockInterviewAnswerSubmitResponse,
    MockInterviewDeleteResponse,
    MockInterviewReviewResponse,
    MockInterviewSessionCreateRequest,
    MockInterviewSessionResponse,
    MockInterviewTurnResponse,
)
from app.schemas.resume import ResumeStructuredData
from app.services.mock_interview_ai import (
    AIInterviewPlanRequest,
    AIInterviewReviewRequest,
    AIInterviewTurnRequest,
    InterviewPlanPayload,
    InterviewReviewPayload,
    InterviewTurnPayload,
    build_mock_interview_ai_provider,
)

ALLOWED_INTERVIEW_MODES = {
    "general",
    "behavioral",
    "project_deep_dive",
    "technical",
    "hr_fit",
}
ALLOWED_JOB_READINESS_STATES = {
    "draft",
    "analyzed",
    "matched",
    "tailoring_needed",
    "interview_ready",
    "training_in_progress",
    "ready_to_apply",
}


def _utc_now_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _to_decimal_score(value: float) -> Decimal:
    return Decimal(str(round(value, 2))).quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP,
    )


def _normalize_mode(value: str) -> str:
    normalized = value.strip().lower()
    if normalized not in ALLOWED_INTERVIEW_MODES:
        raise ApiException(
            status_code=400,
            code=ErrorCode.BAD_REQUEST,
            message="Unsupported mock interview mode",
        )
    return normalized


def _compact_resume_snapshot(resume: ResumeStructuredData) -> dict[str, object]:
    return {
        "basic_info": resume.basic_info.model_dump(),
        "education": resume.education[:3],
        "work_experience": resume.work_experience[:4],
        "projects": resume.projects[:4],
        "skills": resume.skills.model_dump(),
        "certifications": resume.certifications[:4],
    }


def _compact_job_snapshot(job: JobStructuredData) -> dict[str, object]:
    return {
        "basic": job.basic.model_dump(),
        "must_have": job.must_have[:6],
        "nice_to_have": job.nice_to_have[:6],
        "responsibilities": job.responsibilities[:6],
        "requirements": job.requirements.model_dump(),
        "domain_context": job.domain_context.model_dump(),
        "raw_summary": job.raw_summary,
    }


def _compact_match_report(report: MatchReport) -> dict[str, object]:
    return {
        "fit_band": report.fit_band,
        "overall_score": float(report.overall_score),
        "gap_json": report.gap_json or {},
        "tailoring_plan_json": report.tailoring_plan_json or {},
        "interview_blueprint_json": report.interview_blueprint_json or {},
    }


def _compact_optimization_snapshot(
    optimization_session: ResumeOptimizationSession | None,
) -> dict[str, object]:
    if optimization_session is None:
        return {}
    return {
        "status": optimization_session.status,
        "structured_fact_source": (
            "resume.structured_json"
            if optimization_session.status == "applied"
            else "resume_optimization_session.optimized_resume_json"
        ),
        "optimized_resume_json": optimization_session.optimized_resume_json or {},
        "fact_check_report_json": optimization_session.fact_check_report_json or {},
        "markdown_is_fact_source": False,
    }


def serialize_mock_interview_turn(turn: MockInterviewTurn) -> MockInterviewTurnResponse:
    return MockInterviewTurnResponse(
        id=turn.id,
        session_id=turn.session_id,
        turn_index=turn.turn_index,
        question_group_index=turn.question_group_index,
        question_source=turn.question_source,
        question_topic=turn.question_topic,
        question_text=turn.question_text,
        question_intent=turn.question_intent,
        question_rubric_json=list(turn.question_rubric_json or []),
        answer_text=turn.answer_text,
        answer_latency_seconds=turn.answer_latency_seconds,
        status=turn.status,
        evaluation_json=turn.evaluation_json or {},
        decision_json=turn.decision_json or {},
        asked_at=turn.asked_at,
        answered_at=turn.answered_at,
        evaluated_at=turn.evaluated_at,
        created_at=turn.created_at,
        updated_at=turn.updated_at,
    )


def _serialize_mock_interview_session(
    session_record: MockInterviewSession,
    turns: list[MockInterviewTurn],
) -> MockInterviewSessionResponse:
    current_turn = next((turn for turn in reversed(turns) if turn.status == "asked"), None)
    return MockInterviewSessionResponse(
        id=session_record.id,
        user_id=session_record.user_id,
        resume_id=session_record.resume_id,
        jd_id=session_record.jd_id,
        match_report_id=session_record.match_report_id,
        optimization_session_id=session_record.optimization_session_id,
        source_resume_version=session_record.source_resume_version,
        source_job_version=session_record.source_job_version,
        mode=session_record.mode,
        status=session_record.status,
        current_question_index=session_record.current_question_index,
        current_follow_up_count=session_record.current_follow_up_count,
        max_questions=session_record.max_questions,
        max_follow_ups_per_question=session_record.max_follow_ups_per_question,
        plan_json=session_record.plan_json or {},
        review_json=session_record.review_json or {},
        follow_up_tasks_json=list(session_record.follow_up_tasks_json or []),
        overall_score=session_record.overall_score,
        error_message=session_record.error_message,
        current_turn=serialize_mock_interview_turn(current_turn) if current_turn is not None else None,
        turns=[serialize_mock_interview_turn(turn) for turn in turns],
        created_at=session_record.created_at,
        updated_at=session_record.updated_at,
    )


async def _list_turns(
    session: AsyncSession,
    *,
    session_id: UUID,
) -> list[MockInterviewTurn]:
    result = await session.execute(
        select(MockInterviewTurn)
        .where(MockInterviewTurn.session_id == session_id)
        .order_by(MockInterviewTurn.turn_index.asc())
    )
    return list(result.scalars().all())


async def get_mock_interview_session_record_or_404(
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


async def _get_turn_or_404(
    session: AsyncSession,
    *,
    session_record: MockInterviewSession,
    turn_id: UUID,
) -> MockInterviewTurn:
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


async def _get_match_report_or_404(
    session: AsyncSession,
    *,
    current_user: User,
    report_id: UUID,
) -> MatchReport:
    result = await session.execute(
        select(MatchReport).where(
            MatchReport.id == report_id,
            MatchReport.user_id == current_user.id,
        )
    )
    report = result.scalar_one_or_none()
    if report is None:
        raise ApiException(
            status_code=404,
            code=ErrorCode.NOT_FOUND,
            message="Match report not found",
        )
    return report


async def _get_optimization_session_or_404(
    session: AsyncSession,
    *,
    current_user: User,
    optimization_session_id: UUID,
) -> ResumeOptimizationSession:
    result = await session.execute(
        select(ResumeOptimizationSession).where(
            ResumeOptimizationSession.id == optimization_session_id,
            ResumeOptimizationSession.user_id == current_user.id,
        )
    )
    optimization_session = result.scalar_one_or_none()
    if optimization_session is None:
        raise ApiException(
            status_code=404,
            code=ErrorCode.NOT_FOUND,
            message="Resume optimization session not found",
        )
    return optimization_session


async def _assert_match_context_ready(
    session: AsyncSession,
    *,
    report: MatchReport,
) -> tuple[Resume, JobDescription]:
    if report.status != "success":
        raise ApiException(
            status_code=409,
            code=ErrorCode.CONFLICT,
            message="Match report must be generated successfully before mock interview",
        )
    if report.stale_status != "fresh":
        raise ApiException(
            status_code=409,
            code=ErrorCode.CONFLICT,
            message="Match report is stale and must be refreshed before mock interview",
        )

    resume = await session.get(Resume, report.resume_id)
    job = await session.get(JobDescription, report.jd_id)
    if resume is None or job is None:
        raise ApiException(
            status_code=404,
            code=ErrorCode.NOT_FOUND,
            message="Related resume or job record not found",
        )
    if resume.parse_status != "success" or not resume.structured_json:
        raise ApiException(
            status_code=409,
            code=ErrorCode.CONFLICT,
            message="Resume must be parsed successfully before mock interview",
        )
    if job.parse_status != "success" or not job.structured_json:
        raise ApiException(
            status_code=409,
            code=ErrorCode.CONFLICT,
            message="Job must be parsed successfully before mock interview",
        )
    return resume, job


async def _assert_session_context_fresh(
    session: AsyncSession,
    *,
    session_record: MockInterviewSession,
) -> tuple[Resume, JobDescription, MatchReport]:
    resume = await session.get(Resume, session_record.resume_id)
    job = await session.get(JobDescription, session_record.jd_id)
    report = await session.get(MatchReport, session_record.match_report_id)
    if resume is None or job is None or report is None:
        raise ApiException(
            status_code=404,
            code=ErrorCode.NOT_FOUND,
            message="Mock interview context record not found",
        )
    if report.stale_status != "fresh":
        raise ApiException(
            status_code=409,
            code=ErrorCode.CONFLICT,
            message="Mock interview context is stale because match report changed",
        )
    if resume.latest_version != session_record.source_resume_version:
        raise ApiException(
            status_code=409,
            code=ErrorCode.CONFLICT,
            message="Resume has changed since this mock interview session started",
        )
    if job.latest_version != session_record.source_job_version:
        raise ApiException(
            status_code=409,
            code=ErrorCode.CONFLICT,
            message="Job has changed since this mock interview session started",
        )
    return resume, job, report


def _build_first_turn(
    *,
    session_record: MockInterviewSession,
    plan: InterviewPlanPayload,
    current_user: User,
) -> MockInterviewTurn:
    first_question = plan.question_plan[0]
    now = _utc_now_naive()
    return MockInterviewTurn(
        session_id=session_record.id,
        turn_index=1,
        question_group_index=first_question.group_index,
        question_source=first_question.source,
        question_topic=first_question.topic,
        question_text=first_question.question_text,
        question_intent=first_question.intent,
        question_rubric_json=[item.model_dump() for item in first_question.rubric],
        status="asked",
        asked_at=now,
        created_by=current_user.id,
        updated_by=current_user.id,
    )


def _build_follow_up_turn(
    *,
    session_record: MockInterviewSession,
    previous_turn: MockInterviewTurn,
    turn_index: int,
    question_topic: str,
    question_text: str,
    question_intent: str,
    current_user: User,
) -> MockInterviewTurn:
    now = _utc_now_naive()
    return MockInterviewTurn(
        session_id=session_record.id,
        turn_index=turn_index,
        question_group_index=previous_turn.question_group_index,
        question_source="follow_up",
        question_topic=question_topic,
        question_text=question_text,
        question_intent=question_intent,
        question_rubric_json=list(previous_turn.question_rubric_json or []),
        status="asked",
        asked_at=now,
        created_by=current_user.id,
        updated_by=current_user.id,
    )


def _build_planned_main_turn(
    *,
    session_record: MockInterviewSession,
    turn_index: int,
    plan_question: dict[str, object],
    current_user: User,
) -> MockInterviewTurn:
    now = _utc_now_naive()
    return MockInterviewTurn(
        session_id=session_record.id,
        turn_index=turn_index,
        question_group_index=int(plan_question.get("group_index") or 1),
        question_source=str(plan_question.get("source") or "planner_generated"),
        question_topic=str(plan_question.get("topic") or "unknown"),
        question_text=str(plan_question.get("question_text") or ""),
        question_intent=str(plan_question.get("intent") or "") or None,
        question_rubric_json=list(plan_question.get("rubric") or []),
        status="asked",
        asked_at=now,
        created_by=current_user.id,
        updated_by=current_user.id,
    )


async def _record_readiness_event_from_review(
    session: AsyncSession,
    *,
    current_user: User,
    job: JobDescription,
    report: MatchReport,
    review_payload: InterviewReviewPayload,
) -> None:
    status_to = review_payload.job_readiness_signal.status
    if status_to not in ALLOWED_JOB_READINESS_STATES:
        status_to = "training_in_progress"
    session.add(
        JobReadinessEvent(
            user_id=current_user.id,
            job_id=job.id,
            resume_id=report.resume_id,
            match_report_id=report.id,
            status_from=job.status_stage,
            status_to=status_to,
            reason=review_payload.job_readiness_signal.reason,
            metadata_json={
                "source": "mock_interview_review",
                "overall_score": review_payload.overall_score,
                "mode": report.interview_blueprint_json.get("mode"),
            },
            created_by=current_user.id,
            updated_by=current_user.id,
        )
    )
    job.status_stage = status_to
    job.updated_by = current_user.id
    session.add(job)


async def _generate_and_persist_review(
    session: AsyncSession,
    *,
    current_user: User,
    session_record: MockInterviewSession,
    settings: Settings,
) -> MockInterviewReviewResponse:
    resume, job, report = await _assert_session_context_fresh(session, session_record=session_record)
    turns = await _list_turns(session, session_id=session_record.id)
    provider = build_mock_interview_ai_provider(settings)

    transcript = [
        {
            "question_text": turn.question_text,
            "answer_text": turn.answer_text,
            "evaluation": turn.evaluation_json or {},
        }
        for turn in turns
        if turn.answer_text
    ]

    review_payload = await provider.review(
        AIInterviewReviewRequest(
            session_context={
                "mode": session_record.mode,
                "target_role": (session_record.plan_json or {}).get("target_role"),
                "resume_version": session_record.source_resume_version,
                "job_version": session_record.source_job_version,
            },
            match_report_snapshot=_compact_match_report(report),
            transcript=transcript,
        )
    )

    session_record.review_json = review_payload.model_dump()
    session_record.follow_up_tasks_json = [
        item.model_dump() for item in review_payload.follow_up_tasks
    ]
    session_record.overall_score = _to_decimal_score(review_payload.overall_score)
    session_record.status = "completed"
    session_record.error_message = None
    session_record.updated_by = current_user.id
    session.add(session_record)

    await _record_readiness_event_from_review(
        session,
        current_user=current_user,
        job=job,
        report=report,
        review_payload=review_payload,
    )
    await session.commit()
    await session.refresh(session_record)

    return MockInterviewReviewResponse(
        session_id=session_record.id,
        status=session_record.status,
        overall_score=session_record.overall_score,
        review_json=session_record.review_json or {},
        follow_up_tasks_json=list(session_record.follow_up_tasks_json or []),
    )


async def create_mock_interview_session(
    session: AsyncSession,
    *,
    current_user: User,
    payload: MockInterviewSessionCreateRequest,
    settings: Settings,
) -> MockInterviewSessionResponse:
    mode = _normalize_mode(payload.mode)
    report = await _get_match_report_or_404(
        session,
        current_user=current_user,
        report_id=payload.match_report_id,
    )
    resume, job = await _assert_match_context_ready(session, report=report)
    optimization_session: ResumeOptimizationSession | None = None
    if payload.optimization_session_id is not None:
        optimization_session = await _get_optimization_session_or_404(
            session,
            current_user=current_user,
            optimization_session_id=payload.optimization_session_id,
        )

    provider = build_mock_interview_ai_provider(settings)
    resume_snapshot = ResumeStructuredData.model_validate(resume.structured_json)
    if optimization_session is not None and optimization_session.status != "applied":
        # Module 4 can only consume structured optimization snapshots before apply.
        optimized_snapshot = optimization_session.optimized_resume_json or {}
        if optimized_snapshot:
            resume_snapshot = ResumeStructuredData.model_validate(optimized_snapshot)
    job_snapshot = JobStructuredData.model_validate(job.structured_json)
    plan = await provider.plan(
        AIInterviewPlanRequest(
            resume_snapshot=_compact_resume_snapshot(resume_snapshot),
            job_snapshot=_compact_job_snapshot(job_snapshot),
            match_report_snapshot=_compact_match_report(report),
            optimization_snapshot=_compact_optimization_snapshot(optimization_session),
            session_mode=mode,
            constraints={"max_questions": 6, "max_follow_ups_per_question": 1},
        )
    )
    if not plan.question_plan:
        raise ApiException(
            status_code=502,
            code=ErrorCode.SERVICE_UNAVAILABLE,
            message="Mock interview planner returned an empty question plan",
        )

    session_record = MockInterviewSession(
        user_id=current_user.id,
        resume_id=resume.id,
        jd_id=job.id,
        match_report_id=report.id,
        optimization_session_id=payload.optimization_session_id,
        source_resume_version=resume.latest_version,
        source_job_version=job.latest_version,
        mode=mode,
        status="active",
        current_question_index=1,
        current_follow_up_count=0,
        max_questions=plan.ending_rule.max_questions,
        max_follow_ups_per_question=plan.ending_rule.max_follow_ups_per_question,
        plan_json=plan.model_dump(),
        review_json={},
        follow_up_tasks_json=[],
        overall_score=None,
        error_message=None,
        created_by=current_user.id,
        updated_by=current_user.id,
    )
    session.add(session_record)
    await session.flush()

    first_turn = _build_first_turn(
        session_record=session_record,
        plan=plan,
        current_user=current_user,
    )
    session.add(first_turn)
    await session.commit()
    await session.refresh(session_record)
    turns = await _list_turns(session, session_id=session_record.id)
    return _serialize_mock_interview_session(session_record, turns)


async def get_mock_interview_session(
    session: AsyncSession,
    *,
    current_user: User,
    session_id: UUID,
) -> MockInterviewSessionResponse:
    session_record = await get_mock_interview_session_record_or_404(
        session,
        current_user=current_user,
        session_id=session_id,
    )
    turns = await _list_turns(session, session_id=session_record.id)
    return _serialize_mock_interview_session(session_record, turns)


async def list_mock_interview_sessions(
    session: AsyncSession,
    *,
    current_user: User,
    job_id: UUID | None = None,
    resume_id: UUID | None = None,
    status: str | None = None,
    mode: str | None = None,
) -> list[MockInterviewSessionResponse]:
    query = select(MockInterviewSession).where(MockInterviewSession.user_id == current_user.id)
    if job_id is not None:
        query = query.where(MockInterviewSession.jd_id == job_id)
    if resume_id is not None:
        query = query.where(MockInterviewSession.resume_id == resume_id)
    if status:
        query = query.where(MockInterviewSession.status == status)
    if mode:
        query = query.where(MockInterviewSession.mode == mode)
    query = query.order_by(desc(MockInterviewSession.created_at))
    result = await session.execute(query)
    session_records = list(result.scalars().all())
    payloads: list[MockInterviewSessionResponse] = []
    for session_record in session_records:
        turns = await _list_turns(session, session_id=session_record.id)
        payloads.append(_serialize_mock_interview_session(session_record, turns))
    return payloads


async def submit_mock_interview_answer(
    session: AsyncSession,
    *,
    current_user: User,
    session_id: UUID,
    turn_id: UUID,
    payload: MockInterviewAnswerSubmitRequest,
    settings: Settings,
) -> MockInterviewAnswerSubmitResponse:
    session_record = await get_mock_interview_session_record_or_404(
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
    _resume, _job, report = await _assert_session_context_fresh(session, session_record=session_record)
    turn = await _get_turn_or_404(session, session_record=session_record, turn_id=turn_id)
    if turn.status != "asked":
        raise ApiException(
            status_code=409,
            code=ErrorCode.CONFLICT,
            message="This mock interview turn has already been answered",
        )

    answer_text = payload.answer_text.strip()
    if not answer_text:
        raise ApiException(
            status_code=400,
            code=ErrorCode.BAD_REQUEST,
            message="Answer text cannot be empty",
        )

    now = _utc_now_naive()
    turn.answer_text = answer_text
    turn.status = "answered"
    turn.answered_at = now
    if turn.asked_at is not None:
        turn.answer_latency_seconds = max(
            0,
            int((now - turn.asked_at).total_seconds()),
        )
    turn.updated_by = current_user.id
    session.add(turn)
    await session.flush()

    turns = await _list_turns(session, session_id=session_record.id)
    provider = build_mock_interview_ai_provider(settings)
    evaluation_result = await provider.evaluate_turn(
        AIInterviewTurnRequest(
            session_context={
                "mode": session_record.mode,
                "target_role": (session_record.plan_json or {}).get("target_role"),
            },
            current_question={
                "group_index": turn.question_group_index,
                "topic": turn.question_topic,
                "question_text": turn.question_text,
                "intent": turn.question_intent or "",
                "rubric": list(turn.question_rubric_json or []),
            },
            conversation_history=[
                {
                    "question_text": item.question_text,
                    "answer_text": item.answer_text,
                }
                for item in turns
                if item.turn_index < turn.turn_index and item.answer_text
            ],
            candidate_answer={"answer_text": answer_text},
            remaining_question_topics=[
                str(item.get("topic"))
                for item in (session_record.plan_json or {}).get("question_plan", [])
                if int(item.get("group_index") or 0) > turn.question_group_index
            ],
            constraints={
                "follow_up_used": session_record.current_follow_up_count,
                "max_follow_ups_per_question": session_record.max_follow_ups_per_question,
            },
        )
    )

    turn.evaluation_json = evaluation_result.evaluation.model_dump()
    turn.decision_json = evaluation_result.decision.model_dump()
    turn.status = "evaluated"
    turn.evaluated_at = _utc_now_naive()
    session.add(turn)

    next_action: dict[str, object] = {"type": evaluation_result.decision.type}
    next_turn: MockInterviewTurn | None = None
    plan_questions = list((session_record.plan_json or {}).get("question_plan", []))

    if evaluation_result.decision.type == "follow_up":
        if session_record.current_follow_up_count >= session_record.max_follow_ups_per_question:
            raise ApiException(
                status_code=409,
                code=ErrorCode.CONFLICT,
                message="Follow-up limit reached for current question",
            )
        if evaluation_result.decision.next_question is None:
            raise ApiException(
                status_code=502,
                code=ErrorCode.SERVICE_UNAVAILABLE,
                message="Mock interview AI did not return follow-up question content",
            )
        next_turn = _build_follow_up_turn(
            session_record=session_record,
            previous_turn=turn,
            turn_index=len(turns) + 1,
            question_topic=evaluation_result.decision.next_question.topic,
            question_text=evaluation_result.decision.next_question.question_text,
            question_intent=evaluation_result.decision.next_question.intent,
            current_user=current_user,
        )
        session_record.current_follow_up_count += 1
        session_record.updated_by = current_user.id
        session.add(session_record)
        session.add(next_turn)
        await session.flush()
        next_action["turn"] = serialize_mock_interview_turn(next_turn).model_dump()
    elif evaluation_result.decision.type == "next_question":
        next_plan_index = session_record.current_question_index
        if next_plan_index >= len(plan_questions):
            session_record.status = "reviewing"
            session_record.updated_by = current_user.id
            session.add(session_record)
            await session.commit()
            review_response = await _generate_and_persist_review(
                session,
                current_user=current_user,
                session_record=session_record,
                settings=settings,
            )
            next_action = {
                "type": "finish_and_review",
                "review": review_response.model_dump(),
            }
        else:
            next_turn = _build_planned_main_turn(
                session_record=session_record,
                turn_index=len(turns) + 1,
                plan_question=plan_questions[next_plan_index],
                current_user=current_user,
            )
            session_record.current_question_index += 1
            session_record.current_follow_up_count = 0
            session_record.updated_by = current_user.id
            session.add(session_record)
            session.add(next_turn)
            await session.flush()
            next_action["turn"] = serialize_mock_interview_turn(next_turn).model_dump()
    else:
        session_record.status = "reviewing"
        session_record.updated_by = current_user.id
        session.add(session_record)
        await session.commit()
        review_response = await _generate_and_persist_review(
            session,
            current_user=current_user,
            session_record=session_record,
            settings=settings,
        )
        next_action["review"] = review_response.model_dump()

    if next_turn is not None:
        await session.commit()

    return MockInterviewAnswerSubmitResponse(
        session_id=session_record.id,
        submitted_turn_id=turn.id,
        submitted_turn_evaluation=turn.evaluation_json or {},
        next_action=next_action,
    )


async def finish_mock_interview_session(
    session: AsyncSession,
    *,
    current_user: User,
    session_id: UUID,
    settings: Settings,
) -> MockInterviewReviewResponse:
    session_record = await get_mock_interview_session_record_or_404(
        session,
        current_user=current_user,
        session_id=session_id,
    )
    if session_record.status not in {"active", "reviewing"}:
        if session_record.status == "completed":
            return MockInterviewReviewResponse(
                session_id=session_record.id,
                status=session_record.status,
                overall_score=session_record.overall_score,
                review_json=session_record.review_json or {},
                follow_up_tasks_json=list(session_record.follow_up_tasks_json or []),
            )
        raise ApiException(
            status_code=409,
            code=ErrorCode.CONFLICT,
            message="Mock interview session cannot be finished",
        )

    session_record.status = "reviewing"
    session_record.updated_by = current_user.id
    session.add(session_record)
    await session.commit()
    return await _generate_and_persist_review(
        session,
        current_user=current_user,
        session_record=session_record,
        settings=settings,
    )


async def get_mock_interview_review(
    session: AsyncSession,
    *,
    current_user: User,
    session_id: UUID,
) -> MockInterviewReviewResponse:
    session_record = await get_mock_interview_session_record_or_404(
        session,
        current_user=current_user,
        session_id=session_id,
    )
    if session_record.status != "completed":
        raise ApiException(
            status_code=409,
            code=ErrorCode.CONFLICT,
            message="Mock interview review is not ready yet",
        )
    return MockInterviewReviewResponse(
        session_id=session_record.id,
        status=session_record.status,
        overall_score=session_record.overall_score,
        review_json=session_record.review_json or {},
        follow_up_tasks_json=list(session_record.follow_up_tasks_json or []),
    )


async def delete_mock_interview_session(
    session: AsyncSession,
    *,
    current_user: User,
    session_id: UUID,
) -> MockInterviewDeleteResponse:
    session_record = await get_mock_interview_session_record_or_404(
        session,
        current_user=current_user,
        session_id=session_id,
    )
    await session.execute(
        delete(MockInterviewTurn).where(MockInterviewTurn.session_id == session_record.id)
    )
    await session.delete(session_record)
    await session.commit()
    return MockInterviewDeleteResponse(message="Mock interview session deleted successfully")
