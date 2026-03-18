from __future__ import annotations

from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import Settings
from app.core.errors import ApiException
from app.models import JobDescription, MatchReport, MockInterviewSession, Resume, User
from app.schemas.job import JobCreateRequest
from app.schemas.match_report import MatchReportCreateRequest
from app.schemas.mock_interview import (
    MockInterviewAnswerSubmitRequest,
    MockInterviewSessionCreateRequest,
)
from app.schemas.resume import ResumeStructuredData
from app.services.job import create_job, process_job_parse_job
from app.services.match_report import create_match_report, process_match_report
from app.services.mock_interview import (
    create_mock_interview_session,
    finish_mock_interview_session,
    submit_mock_interview_answer,
)


def _resume_structured_data() -> ResumeStructuredData:
    return ResumeStructuredData(
        basic_info={
            "name": "郑文泽",
            "email": "zheng@example.com",
            "phone": "13800138000",
            "location": "上海",
            "summary": "负责数据分析与增长实验复盘。",
        },
        education=["新疆大学 软件工程 本科 2023.09-2027.06"],
        work_experience=["CareerPilot 数据分析实习生 负责指标体系和实验分析"],
        projects=["增长分析平台 从0到1搭建实验复盘看板"],
        skills={
            "technical": ["Python", "SQL"],
            "tools": ["Tableau"],
            "languages": ["English"],
        },
        certifications=["百度之星金奖"],
    )


def _mock_match_ai_payload() -> dict[str, object]:
    return {
        "overall_score": 81,
        "fit_band": "strong",
        "summary": "简历与岗位方向匹配较强，但量化结果表达仍需补强。",
        "reasoning": "技能和职责较为匹配，但部分结果证据还不够具体。",
        "confidence": 0.86,
        "strengths": [
            {"label": "实验分析", "reason": "有相关项目经历支撑。", "severity": "high"}
        ],
        "must_fix": [
            {
                "label": "量化结果表达",
                "reason": "岗位要求结果导向表达。",
                "severity": "high",
            }
        ],
        "should_fix": [
            {
                "label": "跨团队协作",
                "reason": "可以进一步补充协作推动细节。",
                "severity": "medium",
            }
        ],
        "evidence_map_json": {
            "matched_resume_fields": {"skills": ["Python", "SQL", "Tableau"]},
            "matched_jd_fields": {"required_skills": ["Python", "SQL", "Tableau"]},
            "missing_items": ["量化结果表达"],
            "notes": ["AI 已整理面试与改写重点。"],
            "candidate_profile": {"skills": ["Python", "SQL", "Tableau"]},
        },
        "action_pack_json": {
            "resume_tailoring_tasks": [
                {
                    "priority": 1,
                    "title": "补充指标结果",
                    "instruction": "在项目经历中补充指标变化与业务影响。",
                    "target_section": "work_experience_or_projects",
                }
            ],
            "interview_focus_areas": [
                {
                    "topic": "量化结果表达",
                    "reason": "岗位需要结果导向叙述。",
                    "priority": "high",
                }
            ],
            "missing_user_inputs": [
                {
                    "field": "metrics",
                    "question": "是否有实验分析带来的指标提升可以补充？",
                }
            ],
        },
        "tailoring_plan_json": {
            "target_summary": "增长数据分析师",
            "rewrite_tasks": [
                {
                    "priority": 1,
                    "title": "补充指标结果",
                    "instruction": "在项目经历中补充指标变化与业务影响。",
                    "target_section": "work_experience_or_projects",
                }
            ],
            "must_add_evidence": ["量化结果表达"],
            "missing_info_questions": [
                {
                    "field": "metrics",
                    "question": "是否有实验分析带来的指标提升可以补充？",
                }
            ],
        },
        "interview_blueprint_json": {
            "target_role": "增长数据分析师",
            "focus_areas": [
                {
                    "topic": "量化结果表达",
                    "reason": "需要能说清业务结果。",
                    "priority": "high",
                }
            ],
            "question_pack": [
                {
                    "topic": "量化结果表达",
                    "question": "请说明一次你主导实验分析并推动结果落地的经历。",
                    "intent": "验证真实项目证据与结果表达。",
                }
            ],
            "follow_up_rules": ["若只讲过程不讲结果，则追问量化指标。"],
            "rubric": [
                {
                    "dimension": "量化结果表达",
                    "weight": 30,
                    "criteria": "是否说清背景、动作、指标和影响。",
                }
            ],
        },
    }


def _mock_interview_planner_payload() -> dict[str, object]:
    return {
        "session_summary": "围绕岗位短板与项目证据展开本场训练。",
        "mode": "general",
        "target_role": "增长数据分析师",
        "focus_areas": [
            {
                "topic": "量化结果表达",
                "reason": "当前岗位最需要补强这一项。",
                "priority": "high",
            }
        ],
        "question_plan": [
            {
                "group_index": 1,
                "topic": "量化结果表达",
                "source": "blueprint",
                "question_text": "请说明一次你主导实验分析并推动结果落地的经历。",
                "intent": "验证真实项目证据与结果表达。",
                "follow_up_rule": "If result is vague, ask for measurable impact.",
                "rubric": [
                    {
                        "dimension": "specificity_of_evidence",
                        "weight": 30,
                        "criteria": "Candidate gives concrete scenario and actions.",
                    }
                ],
            },
            {
                "group_index": 2,
                "topic": "跨团队协作",
                "source": "blueprint",
                "question_text": "请描述一次你与业务团队协作推进分析结论落地的经历。",
                "intent": "验证协作推进能力。",
                "follow_up_rule": "If ownership is vague, ask for personal contribution.",
                "rubric": [
                    {
                        "dimension": "ownership_and_depth",
                        "weight": 25,
                        "criteria": "Candidate explains personal ownership clearly.",
                    }
                ],
            },
        ],
        "ending_rule": {"max_questions": 6, "max_follow_ups_per_question": 1},
    }


def _mock_interview_follow_up_payload() -> dict[str, object]:
    return {
        "evaluation": {
            "dimension_scores": {
                "relevance_to_job": 82,
                "specificity_of_evidence": 68,
                "ownership_and_depth": 75,
                "structure_and_clarity": 74,
                "results_and_metrics": 60,
                "risk_flags": 10,
            },
            "summary": "回答方向正确，但结果指标仍然偏少。",
            "strengths": ["经历相关", "表达清楚"],
            "gaps": ["缺少量化结果"],
            "evidence_used": ["项目经历", "实验分析能力"],
        },
        "decision": {
            "type": "follow_up",
            "reason": "需要继续追问具体结果指标。",
            "next_question": {
                "topic": "量化结果表达",
                "question_text": "你提到推动了结果落地，具体有哪些指标变化？",
                "intent": "验证量化结果和业务影响。",
            },
        },
    }


def _mock_interview_review_payload() -> dict[str, object]:
    return {
        "overall_score": 78,
        "overall_summary": "岗位相关性较强，但指标结果表达仍需继续打磨。",
        "dimension_scores": {
            "relevance_to_job": 82,
            "specificity_of_evidence": 71,
            "ownership_and_depth": 76,
            "structure_and_clarity": 75,
            "results_and_metrics": 66,
        },
        "strengths": [
            {"label": "经历相关", "reason": "回答紧贴岗位重点。"},
        ],
        "weaknesses": [
            {
                "label": "量化结果表达",
                "reason": "缺少清晰指标变化和业务影响。",
                "severity": "high",
            }
        ],
        "question_reviews": [
            {
                "question_text": "请说明一次你主导实验分析并推动结果落地的经历。",
                "what_went_well": "能说明背景和动作。",
                "what_was_missing": "结果指标与影响不够具体。",
                "better_answer_direction": "用 STAR 方式补充指标变化与业务收益。",
            }
        ],
        "follow_up_tasks": [
            {
                "title": "补写实验分析结果",
                "instruction": "在项目经历中补充实验目标、指标变化与业务收益。",
                "target_section": "work_experience_or_projects",
                "source": "mock_interview_review",
            }
        ],
        "job_readiness_signal": {
            "status": "training_in_progress",
            "reason": "还需要继续强化结果表达后再进入投递。",
        },
    }


async def _create_parsed_resume(session: AsyncSession, *, user: User) -> Resume:
    resume = Resume(
        id=uuid4(),
        user_id=user.id,
        file_name="resume.pdf",
        file_url="minio://career-pilot/resume.pdf",
        storage_bucket="career-pilot",
        storage_object_key=f"resumes/{user.id}/resume.pdf",
        content_type="application/pdf",
        file_size=1024,
        parse_status="success",
        parse_error=None,
        raw_text="郑文泽 数据分析 SQL Python 指标体系 实验分析 增长分析",
        structured_json=_resume_structured_data().model_dump(),
        latest_version=1,
        created_by=user.id,
        updated_by=user.id,
    )
    session.add(resume)
    await session.commit()
    await session.refresh(resume)
    return resume


async def _create_ready_match_report(
    *,
    session_factory: async_sessionmaker[AsyncSession],
    user: User,
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[UUID, UUID, UUID]:
    async def fake_match_request_json_completion(**_: object) -> dict[str, object]:
        return _mock_match_ai_payload()

    monkeypatch.setattr(
        "app.services.match_ai.request_json_completion",
        fake_match_request_json_completion,
    )

    async with session_factory() as session:
        resume = await _create_parsed_resume(session, user=user)
        job, parse_job = await create_job(
            session,
            current_user=user,
            payload=JobCreateRequest(
                title="增长数据分析师",
                company="CareerPilot",
                job_city="上海",
                employment_type="全职",
                source_name="Boss直聘",
                source_url="https://example.com/jobs/mock-interview",
                priority=2,
                jd_text=(
                    "岗位职责\n"
                    "- 负责增长分析、实验分析与指标体系建设\n"
                    "- 联动业务团队推进优化策略落地\n"
                    "任职要求\n"
                    "- 本科及以上\n"
                    "- 熟练使用 Python、SQL、Tableau"
                ),
            ),
        )
        resume_id = resume.id
        job_id = job.id
        parse_job_id = parse_job.id

    await process_job_parse_job(
        job_id=job_id,
        parse_job_id=parse_job_id,
        session_factory=session_factory,
    )

    async with session_factory() as session:
        report = await create_match_report(
            session,
            current_user=user,
            job_id=job_id,
            payload=MatchReportCreateRequest(
                resume_id=resume_id,
                force_refresh=True,
            ),
        )
        report_id = report.id

    await process_match_report(
        report_id=report_id,
        session_factory=session_factory,
        settings=Settings(
            match_ai_provider="minimax",
            match_ai_base_url="https://api.minimaxi.com/anthropic",
            match_ai_api_key="test-key",
            match_ai_model="MiniMax-M2.5",
        ),
    )
    return resume_id, job_id, report_id


@pytest.mark.asyncio
async def test_mock_interview_flow_creates_session_from_match_report(
    session_factory: async_sessionmaker[AsyncSession],
    test_user: User,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_interview_request_json_completion(**kwargs: object) -> dict[str, object]:
        payload = kwargs["payload"]
        if hasattr(payload, "session_mode"):
            return _mock_interview_planner_payload()
        raise AssertionError("Unexpected AI stage during session creation")

    monkeypatch.setattr(
        "app.services.mock_interview_ai.request_json_completion",
        fake_interview_request_json_completion,
    )

    _resume_id, _job_id, report_id = await _create_ready_match_report(
        session_factory=session_factory,
        user=test_user,
        monkeypatch=monkeypatch,
    )

    async with session_factory() as session:
        result = await create_mock_interview_session(
            session,
            current_user=test_user,
            payload=MockInterviewSessionCreateRequest(match_report_id=report_id),
            settings=Settings(
                interview_ai_provider="minimax",
                interview_ai_base_url="https://api.minimaxi.com/anthropic",
                interview_ai_api_key="test-key",
                interview_ai_model="MiniMax-M2.5",
            ),
        )

    assert result.status == "active"
    assert result.mode == "general"
    assert result.plan_json["target_role"] == "增长数据分析师"
    assert len(result.turns) == 1
    assert result.current_turn is not None
    assert result.current_turn.question_text == "请说明一次你主导实验分析并推动结果落地的经历。"


@pytest.mark.asyncio
async def test_mock_interview_flow_submit_answer_creates_follow_up(
    session_factory: async_sessionmaker[AsyncSession],
    test_user: User,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_interview_request_json_completion(**kwargs: object) -> dict[str, object]:
        payload = kwargs["payload"]
        if hasattr(payload, "session_mode"):
            return _mock_interview_planner_payload()
        if hasattr(payload, "candidate_answer"):
            return _mock_interview_follow_up_payload()
        raise AssertionError("Unexpected AI stage during answer submission")

    monkeypatch.setattr(
        "app.services.mock_interview_ai.request_json_completion",
        fake_interview_request_json_completion,
    )

    _resume_id, _job_id, report_id = await _create_ready_match_report(
        session_factory=session_factory,
        user=test_user,
        monkeypatch=monkeypatch,
    )

    async with session_factory() as session:
        created = await create_mock_interview_session(
            session,
            current_user=test_user,
            payload=MockInterviewSessionCreateRequest(match_report_id=report_id),
            settings=Settings(
                interview_ai_provider="minimax",
                interview_ai_base_url="https://api.minimaxi.com/anthropic",
                interview_ai_api_key="test-key",
                interview_ai_model="MiniMax-M2.5",
            ),
        )
        assert created.current_turn is not None

        answer_result = await submit_mock_interview_answer(
            session,
            current_user=test_user,
            session_id=created.id,
            turn_id=created.current_turn.id,
            payload=MockInterviewAnswerSubmitRequest(
                answer_text="我在实习中负责实验分析，也推动了策略落地。"
            ),
            settings=Settings(
                interview_ai_provider="minimax",
                interview_ai_base_url="https://api.minimaxi.com/anthropic",
                interview_ai_api_key="test-key",
                interview_ai_model="MiniMax-M2.5",
            ),
        )

    assert answer_result.next_action["type"] == "follow_up"
    assert "turn" in answer_result.next_action
    assert answer_result.next_action["turn"]["question_source"] == "follow_up"
    assert answer_result.submitted_turn_evaluation["gaps"] == ["缺少量化结果"]


@pytest.mark.asyncio
async def test_mock_interview_flow_finish_generates_review_and_updates_session(
    session_factory: async_sessionmaker[AsyncSession],
    test_user: User,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_interview_request_json_completion(**kwargs: object) -> dict[str, object]:
        payload = kwargs["payload"]
        if hasattr(payload, "session_mode"):
            return _mock_interview_planner_payload()
        if hasattr(payload, "transcript"):
            return _mock_interview_review_payload()
        raise AssertionError("Unexpected AI stage during session finish")

    monkeypatch.setattr(
        "app.services.mock_interview_ai.request_json_completion",
        fake_interview_request_json_completion,
    )

    _resume_id, job_id, report_id = await _create_ready_match_report(
        session_factory=session_factory,
        user=test_user,
        monkeypatch=monkeypatch,
    )

    async with session_factory() as session:
        created = await create_mock_interview_session(
            session,
            current_user=test_user,
            payload=MockInterviewSessionCreateRequest(match_report_id=report_id),
            settings=Settings(
                interview_ai_provider="minimax",
                interview_ai_base_url="https://api.minimaxi.com/anthropic",
                interview_ai_api_key="test-key",
                interview_ai_model="MiniMax-M2.5",
            ),
        )
        review = await finish_mock_interview_session(
            session,
            current_user=test_user,
            session_id=created.id,
            settings=Settings(
                interview_ai_provider="minimax",
                interview_ai_base_url="https://api.minimaxi.com/anthropic",
                interview_ai_api_key="test-key",
                interview_ai_model="MiniMax-M2.5",
            ),
        )

    assert review.status == "completed"
    assert review.review_json["overall_summary"] == "岗位相关性较强，但指标结果表达仍需继续打磨。"
    assert review.follow_up_tasks_json[0]["title"] == "补写实验分析结果"

    async with session_factory() as session:
        persisted_session = await session.get(MockInterviewSession, created.id)
        persisted_job = await session.get(JobDescription, job_id)
        assert persisted_session is not None
        assert persisted_job is not None
        assert persisted_session.status == "completed"
        assert float(persisted_session.overall_score) == 78.0
        assert persisted_job.status_stage == "training_in_progress"


@pytest.mark.asyncio
async def test_mock_interview_flow_blocks_when_context_turns_stale(
    session_factory: async_sessionmaker[AsyncSession],
    test_user: User,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_interview_request_json_completion(**kwargs: object) -> dict[str, object]:
        payload = kwargs["payload"]
        if hasattr(payload, "session_mode"):
            return _mock_interview_planner_payload()
        if hasattr(payload, "candidate_answer"):
            return _mock_interview_follow_up_payload()
        raise AssertionError("Unexpected AI stage during stale-context test")

    monkeypatch.setattr(
        "app.services.mock_interview_ai.request_json_completion",
        fake_interview_request_json_completion,
    )

    resume_id, _job_id, report_id = await _create_ready_match_report(
        session_factory=session_factory,
        user=test_user,
        monkeypatch=monkeypatch,
    )

    async with session_factory() as session:
        created = await create_mock_interview_session(
            session,
            current_user=test_user,
            payload=MockInterviewSessionCreateRequest(match_report_id=report_id),
            settings=Settings(
                interview_ai_provider="minimax",
                interview_ai_base_url="https://api.minimaxi.com/anthropic",
                interview_ai_api_key="test-key",
                interview_ai_model="MiniMax-M2.5",
            ),
        )

    async with session_factory() as session:
        resume = await session.get(Resume, resume_id)
        report = await session.get(MatchReport, report_id)
        assert resume is not None
        assert report is not None
        resume.latest_version = 2
        report.stale_status = "stale"
        session.add(resume)
        session.add(report)
        await session.commit()

    async with session_factory() as session:
        with pytest.raises(ApiException) as exc_info:
            await submit_mock_interview_answer(
                session,
                current_user=test_user,
                session_id=created.id,
                turn_id=created.current_turn.id,  # type: ignore[union-attr]
                payload=MockInterviewAnswerSubmitRequest(answer_text="我做了实验分析。"),
                settings=Settings(
                    interview_ai_provider="minimax",
                    interview_ai_base_url="https://api.minimaxi.com/anthropic",
                    interview_ai_api_key="test-key",
                    interview_ai_model="MiniMax-M2.5",
                ),
            )

    assert exc_info.value.status_code == 409
    assert "stale" in exc_info.value.message.lower() or "changed" in exc_info.value.message.lower()
