from __future__ import annotations

from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import Settings
from app.core.errors import ApiException
from app.models import (
    JobDescription,
    MatchReport,
    MockInterviewSession,
    Resume,
    ResumeOptimizationSession,
    User,
)
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
                "source": "gap",
                "question_text": "请说明一次你主导实验分析并推动结果落地的经历。",
                "intent": "验证真实项目证据与结果表达。",
                "follow_up_rule": "If result is vague, ask for measurable impact.",
                "rubric": [
                    {
                        "dimension": "evidence",
                        "weight": 30,
                        "criteria": "Candidate gives concrete scenario and actions.",
                    }
                ],
            },
            {
                "group_index": 2,
                "topic": "实验分析优势",
                "source": "strength",
                "question_text": "你认为自己最能打动这个岗位的一段分析经历是什么？",
                "intent": "展开候选人最强项目证据。",
                "follow_up_rule": "If evidence is broad, ask for the strongest proof point.",
                "rubric": [
                    {
                        "dimension": "relevance",
                        "weight": 30,
                        "criteria": "Candidate selects the most job-relevant example.",
                    }
                ],
            },
            {
                "group_index": 3,
                "topic": "跨团队协作",
                "source": "behavioral_general",
                "question_text": "请描述一次你与业务团队协作推进分析结论落地的经历。",
                "intent": "验证协作推进能力。",
                "follow_up_rule": "If ownership is vague, ask for personal contribution.",
                "rubric": [
                    {
                        "dimension": "communication",
                        "weight": 25,
                        "criteria": "Candidate explains personal ownership clearly.",
                    }
                ],
            },
        ],
        "ending_rule": {"max_questions": 6, "max_follow_ups_per_question": 1},
    }


def _mock_interview_evaluation_payload() -> dict[str, object]:
    return {
        "dimension_scores": {
            "relevance": 4,
            "specificity": 2,
            "evidence": 2,
            "structure": 4,
            "communication": 4,
        },
        "summary": "回答方向正确，但结果指标仍然偏少。",
        "strengths": ["经历相关", "表达清楚"],
        "gaps": ["缺少量化结果"],
        "evidence_used": ["实验分析经历", "推动结果落地"],
    }


def _mock_interview_follow_up_decision_payload() -> dict[str, object]:
    return {
        "type": "follow_up",
        "reason": "答案相关但仍然空泛，需要追问具体结果指标。",
        "next_question": {
            "topic": "量化结果表达",
            "question_text": "你提到推动了结果落地，具体有哪些指标变化？",
            "intent": "验证量化结果和业务影响。",
        },
    }


def _mock_interview_next_question_decision_payload() -> dict[str, object]:
    return {
        "type": "next_question",
        "reason": "当前问题已经获得足够信息，进入下一个主问题。",
    }


def _mock_interview_review_payload() -> dict[str, object]:
    return {
        "overall_score": 78,
        "overall_summary": "岗位相关性较强，但指标结果表达仍需继续打磨。",
        "dimension_scores": {
            "relevance": 4,
            "specificity": 3,
            "evidence": 3,
            "structure": 4,
            "communication": 4,
        },
        "strengths": [
            {"label": "经历相关", "reason": "回答紧贴岗位重点。", "severity": "high"},
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
                "question_group_index": 1,
                "source": "gap",
                "question_text": "请说明一次你主导实验分析并推动结果落地的经历。",
                "summary": "能说明背景和动作，但量化结果不够完整。",
                "strengths": ["背景和动作交代较清楚"],
                "gaps": ["结果指标与业务影响不够具体"],
                "suggested_better_answer": "用 STAR 方式补充指标变化与业务收益。",
            }
        ],
        "follow_up_tasks": [
            {
                "title": "补写实验分析结果",
                "task_type": "resume",
                "instruction": "在项目经历中补充实验目标、指标变化与业务收益。",
                "target_section": "work_experience_or_projects",
                "reason": "把面试里缺失的量化结果反补到简历事实层。",
                "source": "mock_interview_review",
            },
            {
                "title": "强化指标表达训练",
                "task_type": "interview",
                "instruction": "围绕同一项目准备 90 秒版本，按背景-动作-指标-影响复述两遍。",
                "target_section": None,
                "reason": "为下一轮模拟面试补强结果表达。",
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


async def _create_optimization_session(
    session: AsyncSession,
    *,
    user: User,
    resume_id: UUID,
    jd_id: UUID,
    match_report_id: UUID,
) -> ResumeOptimizationSession:
    optimization_session = ResumeOptimizationSession(
        user_id=user.id,
        resume_id=resume_id,
        jd_id=jd_id,
        match_report_id=match_report_id,
        source_resume_version=1,
        source_job_version=1,
        status="draft",
        optimized_resume_json={
            **_resume_structured_data().model_dump(),
            "basic_info": {
                **_resume_structured_data().basic_info.model_dump(),
                "summary": "来自 optimized_resume_json 的结构化事实源",
            },
        },
        optimized_resume_md="# 不允许作为事实源\n这段 Markdown 不应被第四模块读取。",
        created_by=user.id,
        updated_by=user.id,
    )
    session.add(optimization_session)
    await session.commit()
    await session.refresh(optimization_session)
    return optimization_session


def _interview_settings() -> Settings:
    return Settings(
        interview_ai_provider="minimax",
        interview_ai_base_url="https://api.minimaxi.com/anthropic",
        interview_ai_api_key="test-key",
        interview_ai_model="MiniMax-M2.5",
    )


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
            settings=_interview_settings(),
        )

    assert result.status == "active"
    assert result.mode == "general"
    assert result.plan_json is not None
    assert result.plan_json.target_role == "增长数据分析师"
    assert [item.source for item in result.plan_json.question_plan] == [
        "gap",
        "strength",
        "behavioral_general",
    ]
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
        if hasattr(payload, "evaluation_json"):
            return _mock_interview_follow_up_decision_payload()
        if hasattr(payload, "candidate_answer"):
            return _mock_interview_evaluation_payload()
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
            settings=_interview_settings(),
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
            settings=_interview_settings(),
        )

    assert answer_result.next_action["type"] == "follow_up"
    assert "turn" in answer_result.next_action
    assert answer_result.next_action["turn"]["question_source"] == "follow_up"
    assert answer_result.submitted_turn_evaluation.gaps == ["缺少量化结果"]
    assert answer_result.submitted_turn_evaluation.dimension_scores.evidence == 2


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
            settings=_interview_settings(),
        )
        review = await finish_mock_interview_session(
            session,
            current_user=test_user,
            session_id=created.id,
            settings=_interview_settings(),
        )

    assert review.status == "completed"
    assert review.review_json is not None
    assert review.review_json.overall_summary == "岗位相关性较强，但指标结果表达仍需继续打磨。"
    assert review.follow_up_tasks_json[0].title == "补写实验分析结果"

    async with session_factory() as session:
        persisted_session = await session.get(MockInterviewSession, created.id)
        persisted_job = await session.get(JobDescription, job_id)
        assert persisted_session is not None
        assert persisted_job is not None
        assert persisted_session.status == "completed"
        assert float(persisted_session.overall_score) == 78.0
        assert persisted_job.status_stage == "training_in_progress"


@pytest.mark.asyncio
async def test_mock_interview_flow_follow_up_is_limited_to_one_per_main_question(
    session_factory: async_sessionmaker[AsyncSession],
    test_user: User,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_interview_request_json_completion(**kwargs: object) -> dict[str, object]:
        payload = kwargs["payload"]
        if hasattr(payload, "session_mode"):
            return _mock_interview_planner_payload()
        if hasattr(payload, "evaluation_json"):
            return _mock_interview_follow_up_decision_payload()
        if hasattr(payload, "candidate_answer"):
            return _mock_interview_evaluation_payload()
        raise AssertionError("Unexpected AI stage during follow-up limit test")

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
            settings=_interview_settings(),
        )
        assert created.current_turn is not None

        first_answer = await submit_mock_interview_answer(
            session,
            current_user=test_user,
            session_id=created.id,
            turn_id=created.current_turn.id,
            payload=MockInterviewAnswerSubmitRequest(
                answer_text="我做了实验分析，也推动方案落地。"
            ),
            settings=_interview_settings(),
        )
        follow_up_turn = first_answer.next_action["turn"]

        second_answer = await submit_mock_interview_answer(
            session,
            current_user=test_user,
            session_id=created.id,
            turn_id=follow_up_turn["id"],
            payload=MockInterviewAnswerSubmitRequest(
                answer_text="指标提升我暂时没有整理出来，但策略后续上线了。"
            ),
            settings=_interview_settings(),
        )

    assert first_answer.next_action["type"] == "follow_up"
    assert second_answer.next_action["type"] == "next_question"
    assert second_answer.next_action["turn"]["question_source"] == "strength"


@pytest.mark.asyncio
async def test_mock_interview_flow_uses_optimized_resume_json_not_markdown_as_fact_source(
    session_factory: async_sessionmaker[AsyncSession],
    test_user: User,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_interview_request_json_completion(**kwargs: object) -> dict[str, object]:
        payload = kwargs["payload"]
        if hasattr(payload, "session_mode"):
            assert payload.resume_snapshot["basic_info"]["summary"] == (
                "来自 optimized_resume_json 的结构化事实源"
            )
            assert "Markdown" not in str(payload.resume_snapshot)
            assert payload.optimization_snapshot["structured_fact_source"] == (
                "resume_optimization_session.optimized_resume_json"
            )
            return _mock_interview_planner_payload()
        raise AssertionError("Unexpected AI stage during optimization fact source test")

    monkeypatch.setattr(
        "app.services.mock_interview_ai.request_json_completion",
        fake_interview_request_json_completion,
    )

    resume_id, job_id, report_id = await _create_ready_match_report(
        session_factory=session_factory,
        user=test_user,
        monkeypatch=monkeypatch,
    )

    async with session_factory() as session:
        optimization_session = await _create_optimization_session(
            session,
            user=test_user,
            resume_id=resume_id,
            jd_id=job_id,
            match_report_id=report_id,
        )

        result = await create_mock_interview_session(
            session,
            current_user=test_user,
            payload=MockInterviewSessionCreateRequest(
                match_report_id=report_id,
                optimization_session_id=optimization_session.id,
            ),
            settings=_interview_settings(),
        )

    assert result.plan_json is not None
    assert result.status == "active"


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
        if hasattr(payload, "evaluation_json"):
            return _mock_interview_follow_up_decision_payload()
        if hasattr(payload, "candidate_answer"):
            return _mock_interview_evaluation_payload()
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
            settings=_interview_settings(),
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
                settings=_interview_settings(),
            )

    assert exc_info.value.status_code == 409
    assert "stale" in exc_info.value.message.lower() or "changed" in exc_info.value.message.lower()
