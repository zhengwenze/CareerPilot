from __future__ import annotations

from uuid import UUID

import pytest
from sqlalchemy import select

from app.core.config import Settings
from app.models import JobDescription, MatchReport, MockInterviewSession, Resume, ResumeOptimizationSession
from app.schemas.ai_runtime import TaskState
from app.schemas.interview_review import (
    DeepReviewResult,
    InterviewLevelJudgment,
    MockInterviewReviewType,
    coerce_mock_interview_review_type,
)
from app.schemas.resume import ResumeBasicInfo, ResumeStructuredData
from app.services import mock_interview as mock_interview_service

from conftest import create_test_user


async def _seed_interview_dependencies(db_session, *, user, suffix: str, tailored_resume_md: str | None = None):
    structured_resume = ResumeStructuredData(
        basic_info=ResumeBasicInfo(
            name="测试候选人",
            summary="主导过前端架构升级与跨团队协作。",
        )
    )
    resume = Resume(
        user_id=user.id,
        file_name=f"resume-{suffix}.pdf",
        file_url=f"https://example.test/resume-{suffix}.pdf",
        storage_bucket="test",
        storage_object_key=f"resume-{suffix}.pdf",
        content_type="application/pdf",
        file_size=123,
        parse_status="success",
        raw_text="# Resume",
        structured_json=structured_resume.model_dump(mode="json"),
        parse_artifacts_json={"canonical_resume_md": "# Resume"},
        created_by=user.id,
        updated_by=user.id,
    )
    job = JobDescription(
        user_id=user.id,
        title=f"Frontend Lead {suffix}",
        jd_text=f"Need React leadership and product thinking for {suffix}",
        latest_version=1,
        priority=3,
        status_stage="interview_ready",
        parse_status="success",
        structured_json={},
        competency_graph_json={},
        created_by=user.id,
        updated_by=user.id,
    )
    db_session.add_all([resume, job])
    await db_session.flush()
    report = MatchReport(
        user_id=user.id,
        resume_id=resume.id,
        jd_id=job.id,
        resume_version=1,
        job_version=1,
        status="success",
        fit_band="strong",
        stale_status="fresh",
        overall_score="88.00",
        rule_score="88.00",
        model_score="88.00",
        created_by=user.id,
        updated_by=user.id,
    )
    db_session.add(report)
    await db_session.flush()
    workflow = ResumeOptimizationSession(
        user_id=user.id,
        resume_id=resume.id,
        jd_id=job.id,
        match_report_id=report.id,
        source_resume_version=1,
        source_job_version=1,
        status="success",
        tailored_resume_json={"document": {}},
        tailored_resume_md=tailored_resume_md
        if tailored_resume_md is not None
        else "# Tailored Resume\n\n## Experience\n- built product",
        created_by=user.id,
        updated_by=user.id,
    )
    db_session.add(workflow)
    await db_session.commit()
    return job, workflow


@pytest.mark.asyncio
async def test_mock_interview_request_text_allows_ollama_without_api_key(monkeypatch: pytest.MonkeyPatch):
    settings = Settings(
        _env_file=None,
        interview_ai_provider="ollama",
        interview_ai_base_url="http://127.0.0.1:11434",
        interview_ai_api_key=None,
        interview_ai_model="qwen2.5:7b",
        interview_ai_model_planning="qwen2.5:7b",
    )

    calls: list[object] = []

    async def fake_request_text_completion(**kwargs) -> str:
        calls.append(kwargs["config"])
        return "OK"

    monkeypatch.setattr(mock_interview_service, "request_text_completion", fake_request_text_completion)

    result = await mock_interview_service._request_text(
        settings,
        prompt="ping",
        max_tokens=32,
    )

    assert result == "OK"
    assert len(calls) == 1
    assert calls[0].provider == "ollama"
    assert calls[0].api_key is None


@pytest.mark.asyncio
async def test_mock_interview_request_text_allows_codex2gpt_without_api_key(
    monkeypatch: pytest.MonkeyPatch,
):
    settings = Settings(
        _env_file=None,
        interview_ai_provider="codex2gpt",
        interview_ai_base_url="http://127.0.0.1:18100/v1",
        interview_ai_api_key=None,
        interview_ai_model="gpt-5.4",
        interview_ai_model_planning="gpt-5.4",
    )

    calls: list[object] = []

    async def fake_request_text_completion(**kwargs) -> str:
        calls.append(kwargs["config"])
        return "OK"

    monkeypatch.setattr(mock_interview_service, "request_text_completion", fake_request_text_completion)

    result = await mock_interview_service._request_text(
        settings,
        prompt="ping",
        max_tokens=32,
    )

    assert result == "OK"
    assert len(calls) == 1
    assert calls[0].provider == "codex2gpt"
    assert calls[0].api_key is None


async def test_mock_interview_returns_first_question_then_prepares_followups_async(
    app, client, db_session, monkeypatch
):
    monkeypatch.setattr("app.routers.mock_interviews.schedule_mock_interview_prep", lambda *args, **kwargs: None)
    monkeypatch.setattr("app.routers.mock_interviews.schedule_mock_interview_turn", lambda *args, **kwargs: None)

    user, token = await create_test_user(db_session, email="interview-demo@example.com")
    job, workflow = await _seed_interview_dependencies(
        db_session,
        user=user,
        suffix="demo",
        tailored_resume_md="# Tailored Resume\n\n## Experience\n- optimized frontend architecture",
    )

    calls: list[tuple[str, str]] = []
    decisions = iter(
        [
            mock_interview_service.MockInterviewTurnDecision(
                need_comment=False,
                comment_text="",
                next_action="next_main",
                next_question="",
                reason="move from opening to main question",
            ),
            mock_interview_service.MockInterviewTurnDecision(
                need_comment=False,
                comment_text="",
                next_action="followup",
                next_question="你刚才提到架构升级，具体是怎么推进落地的？",
                reason="probe execution details",
            ),
            mock_interview_service.MockInterviewTurnDecision(
                need_comment=True,
                comment_text="这个例子比较完整。",
                next_action="end",
                next_question="",
                reason="enough evidence gathered",
            ),
        ]
    )

    async def fake_summarize_role_desc(settings, target_role_desc: str) -> str:
        del settings
        calls.append(("summarize_role_desc", target_role_desc))
        return "岗位需要 React 架构和团队带领能力"

    async def fake_summarize_resume(settings, resume_md: str) -> str:
        del settings
        calls.append(("summarize_resume", resume_md))
        return "候选人做过前端架构升级和跨团队协作"

    async def fake_generate_main_questions(settings, *, role_summary: str, candidate_profile: str):
        del settings
        calls.append(("generate_main_questions", f"{role_summary} || {candidate_profile}"))
        return [
            mock_interview_service.MainQuestionPlan(
                question_id="main-1",
                category="项目经历",
                review_type=MockInterviewReviewType.PROJECT_EXPERIENCE,
                text="请讲一个你主导前端架构升级的项目。",
                intent="评估候选人是否有真实主导经验",
                followup_hints=["推进方式", "影响结果"],
            )
        ]

    async def fake_decide_next_turn(
        settings,
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
    ):
        del settings, role_summary, candidate_profile, current_main_question, question_count, max_total_questions
        calls.append(
            (
                "decide_next_turn",
                f"{current_question_type} || {followup_count_for_current_main} || {current_question} || {recent_turns} || {candidate_answer}",
            )
        )
        return next(decisions)

    async def fake_generate_ending_text(settings, *, candidate_profile: str, recent_turns: str) -> str:
        del settings
        calls.append(("generate_ending_text", f"{candidate_profile} || {recent_turns}"))
        return "今天先到这里，感谢你的回答。整体思路清楚，后续继续强化案例细节。"

    async def fake_review_interview_answer(
        settings,
        *,
        review_type: MockInterviewReviewType,
        role_summary: str,
        candidate_profile: str,
        question: str,
        answer: str,
        company_or_style: str = "",
    ) -> DeepReviewResult:
        del settings, role_summary, candidate_profile, company_or_style
        calls.append(("review_interview_answer", f"{review_type.value} || {question} || {answer}"))
        return DeepReviewResult(
            status="ready",
            score=6.5,
            level_judgment=InterviewLevelJudgment.DIRECTIONALLY_CORRECT_BUT_NOT_SYSTEMATIC,
            overall_comment="方向是对的，但回答还不够成体系。",
            strengths=["方向正确", "有结构意识"],
            weaknesses=["排查维度不完整", "过快归因"],
            missing_framework=["数据输入", "通信与 overlap"] if review_type == MockInterviewReviewType.TECHNICAL_ANALYSIS else [],
            stronger_answer_outline=["先定义问题现象", "再做对照实验", "最后验证优化收益"],
            interviewer_concern="像能参与排查，但还不足以独立主导。",
            display_comment="这一题我会给你 6.5/10。方向是对的，但还不够成体系。",
        )

    monkeypatch.setattr(mock_interview_service, "summarize_role_desc", fake_summarize_role_desc)
    monkeypatch.setattr(mock_interview_service, "summarize_resume", fake_summarize_resume)
    monkeypatch.setattr(mock_interview_service, "generate_main_questions", fake_generate_main_questions)
    monkeypatch.setattr(mock_interview_service, "decide_next_turn", fake_decide_next_turn)
    monkeypatch.setattr(mock_interview_service, "generate_ending_text", fake_generate_ending_text)
    monkeypatch.setattr(mock_interview_service, "review_interview_answer", fake_review_interview_answer)

    response = await client.post(
        "/mock-interviews",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "job_id": str(job.id),
            "resume_id": str(workflow.resume_id),
            "resume_optimization_session_id": str(workflow.id),
        },
    )
    assert response.status_code == 201
    created_session = response.json()["data"]
    assert "自我介绍" in created_session["current_turn"]["question_text"]
    assert created_session["prep_state"]["status"] == "processing"

    await mock_interview_service.process_mock_interview_prep(
        session_id=UUID(created_session["id"]),
        session_factory=app.state.session_factory,
        settings=app.state.settings,
    )

    response = await client.get(
        f"/mock-interviews/{created_session['id']}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    prepared_session = response.json()["data"]
    assert prepared_session["prep_state"]["status"] == "success"
    assert prepared_session["current_turn"]["question_text"] == created_session["current_turn"]["question_text"]
    assert calls[:3] == [
        ("summarize_role_desc", job.jd_text),
        ("summarize_resume", workflow.tailored_resume_md),
        (
            "generate_main_questions",
            "岗位需要 React 架构和团队带领能力 || 岗位侧重点：岗位需要 React 架构和团队带领能力\n候选人画像：候选人做过前端架构升级和跨团队协作",
        ),
    ]

    response = await client.post(
        f"/mock-interviews/{created_session['id']}/turns/{created_session['current_turn']['id']}/answer",
        headers={"Authorization": f"Bearer {token}"},
        json={"answer_text": "我负责拆分历史单体前端，落地微前端和统一组件规范。"},
    )
    assert response.status_code == 200
    assert response.json()["data"]["next_action"]["type"] == "processing"

    await mock_interview_service.process_mock_interview_turn(
        session_id=UUID(created_session["id"]),
        turn_id=UUID(created_session["current_turn"]["id"]),
        session_factory=app.state.session_factory,
        settings=app.state.settings,
    )

    response = await client.get(
        f"/mock-interviews/{created_session['id']}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    main_session = response.json()["data"]
    assert main_session["current_turn"]["question_type"] == "main"
    assert main_session["current_turn"]["question_text"] == "请讲一个你主导前端架构升级的项目。"
    answered_opening = next(turn for turn in main_session["turns"] if turn["turn_index"] == 1)
    assert answered_opening["review_type"] == "project_experience"
    assert answered_opening["evaluation_json"]["status"] == "ready"
    assert answered_opening["evaluation_json"]["display_comment"].startswith("这一题我会给你 6.5/10")

    response = await client.post(
        f"/mock-interviews/{created_session['id']}/turns/{main_session['current_turn']['id']}/answer",
        headers={"Authorization": f"Bearer {token}"},
        json={"answer_text": "我先统一技术方案，再按域拆分并配合业务团队灰度上线。"},
    )
    assert response.status_code == 200
    assert response.json()["data"]["next_action"]["type"] == "processing"

    await mock_interview_service.process_mock_interview_turn(
        session_id=UUID(created_session["id"]),
        turn_id=UUID(main_session["current_turn"]["id"]),
        session_factory=app.state.session_factory,
        settings=app.state.settings,
    )

    response = await client.get(
        f"/mock-interviews/{created_session['id']}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    followup_session = response.json()["data"]
    assert followup_session["current_turn"]["question_type"] == "followup"
    assert followup_session["current_turn"]["question_text"] == "你刚才提到架构升级，具体是怎么推进落地的？"

    response = await client.post(
        f"/mock-interviews/{created_session['id']}/turns/{followup_session['current_turn']['id']}/answer",
        headers={"Authorization": f"Bearer {token}"},
        json={"answer_text": "我会先盘点现有前端架构风险，再安排业务灰度和统一组件规范。"},
    )
    assert response.status_code == 200

    await mock_interview_service.process_mock_interview_turn(
        session_id=UUID(created_session["id"]),
        turn_id=UUID(followup_session["current_turn"]["id"]),
        session_factory=app.state.session_factory,
        settings=app.state.settings,
    )

    response = await client.get(
        f"/mock-interviews/{created_session['id']}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    completed_session = response.json()["data"]
    assert completed_session["status"] == "completed"
    assert completed_session["ending_text"].startswith("今天先到这里")
    assert any(call[0] == "generate_ending_text" for call in calls)
    assert any(call[0] == "review_interview_answer" for call in calls)


@pytest.mark.asyncio
async def test_mock_interview_can_start_with_job_and_original_resume_only(
    app, client, db_session, monkeypatch
):
    monkeypatch.setattr("app.routers.mock_interviews.schedule_mock_interview_prep", lambda *args, **kwargs: None)

    user, token = await create_test_user(db_session, email="interview-original-only@example.com")
    job, workflow = await _seed_interview_dependencies(db_session, user=user, suffix="original-only")
    resume = await db_session.get(Resume, workflow.resume_id)
    assert resume is not None
    resume.parse_artifacts_json = {"canonical_resume_md": "# Master Resume\n\n- built resilient frontend systems"}
    db_session.add(resume)
    await db_session.commit()

    calls: list[tuple[str, str]] = []

    async def fake_summarize_role_desc(settings, target_role_desc: str) -> str:
        del settings
        calls.append(("summarize_role_desc", target_role_desc))
        return "岗位需要候选人证明复杂前端项目经验"

    async def fake_summarize_resume(settings, resume_md: str) -> str:
        del settings
        calls.append(("summarize_resume", resume_md))
        return "候选人原始简历包含复杂前端系统建设经历"

    async def fake_generate_main_questions(settings, *, role_summary: str, candidate_profile: str):
        del settings
        calls.append(("generate_main_questions", f"{role_summary} || {candidate_profile}"))
        return []

    monkeypatch.setattr(mock_interview_service, "summarize_role_desc", fake_summarize_role_desc)
    monkeypatch.setattr(mock_interview_service, "summarize_resume", fake_summarize_resume)
    monkeypatch.setattr(mock_interview_service, "generate_main_questions", fake_generate_main_questions)

    response = await client.post(
        "/mock-interviews",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "job_id": str(job.id),
            "resume_id": str(resume.id),
        },
    )
    assert response.status_code == 201
    created_session = response.json()["data"]
    assert created_session["resume_id"] == str(resume.id)
    assert created_session["resume_optimization_session_id"] is None
    assert "原始简历" in created_session["current_turn"]["question_text"]

    await mock_interview_service.process_mock_interview_prep(
        session_id=UUID(created_session["id"]),
        session_factory=app.state.session_factory,
        settings=app.state.settings,
    )

    assert calls[:2] == [
        ("summarize_role_desc", job.jd_text),
        ("summarize_resume", "# Master Resume\n\n- built resilient frontend systems"),
    ]


@pytest.mark.asyncio
async def test_mock_interview_falls_back_to_original_resume_when_tailored_markdown_missing(
    app, client, db_session, monkeypatch
):
    monkeypatch.setattr("app.routers.mock_interviews.schedule_mock_interview_prep", lambda *args, **kwargs: None)

    user, token = await create_test_user(db_session, email="interview-fallback-original@example.com")
    job, workflow = await _seed_interview_dependencies(
        db_session,
        user=user,
        suffix="fallback-original",
        tailored_resume_md="   ",
    )
    resume = await db_session.get(Resume, workflow.resume_id)
    assert resume is not None
    resume.parse_artifacts_json = {"canonical_resume_md": "# Source Resume\n\n- shipped product architecture changes"}
    db_session.add(resume)
    await db_session.commit()

    calls: list[tuple[str, str]] = []

    async def fake_summarize_role_desc(settings, target_role_desc: str) -> str:
        del settings
        calls.append(("summarize_role_desc", target_role_desc))
        return "岗位需要候选人体现系统设计与落地经验"

    async def fake_summarize_resume(settings, resume_md: str) -> str:
        del settings
        calls.append(("summarize_resume", resume_md))
        return "候选人原始简历里有可复用的系统设计经历"

    async def fake_generate_main_questions(settings, *, role_summary: str, candidate_profile: str):
        del settings
        calls.append(("generate_main_questions", f"{role_summary} || {candidate_profile}"))
        return []

    monkeypatch.setattr(mock_interview_service, "summarize_role_desc", fake_summarize_role_desc)
    monkeypatch.setattr(mock_interview_service, "summarize_resume", fake_summarize_resume)
    monkeypatch.setattr(mock_interview_service, "generate_main_questions", fake_generate_main_questions)

    response = await client.post(
        "/mock-interviews",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "job_id": str(job.id),
            "resume_id": str(resume.id),
            "resume_optimization_session_id": str(workflow.id),
        },
    )
    assert response.status_code == 201
    created_session = response.json()["data"]
    assert created_session["resume_optimization_session_id"] is None
    assert "原始简历" in created_session["current_turn"]["question_text"]

    await mock_interview_service.process_mock_interview_prep(
        session_id=UUID(created_session["id"]),
        session_factory=app.state.session_factory,
        settings=app.state.settings,
    )

    assert calls[:2] == [
        ("summarize_role_desc", job.jd_text),
        ("summarize_resume", "# Source Resume\n\n- shipped product architecture changes"),
    ]


async def test_mock_interview_list_and_finish_return_structured_runtime_state(
    app, client, db_session, monkeypatch
):
    monkeypatch.setattr("app.routers.mock_interviews.schedule_mock_interview_prep", lambda *args, **kwargs: None)

    user, token = await create_test_user(db_session, email="interview-list@example.com")
    job, workflow = await _seed_interview_dependencies(db_session, user=user, suffix="list")

    response = await client.post(
        "/mock-interviews",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "job_id": str(job.id),
            "resume_id": str(workflow.resume_id),
            "resume_optimization_session_id": str(workflow.id),
        },
    )
    assert response.status_code == 201
    session = response.json()["data"]

    response = await client.get(
        f"/mock-interviews?job_id={job.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    sessions = response.json()["data"]
    listed = next(item for item in sessions if item["id"] == session["id"])
    assert listed["prep_state"]["status"] == "processing"
    assert listed["review"] == {"strengths": [], "risks": [], "next_steps": []}

    response = await client.post(
        f"/mock-interviews/{session['id']}/finish",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    finished = response.json()["data"]
    assert finished["status"] == "completed"
    assert finished["prep_state"]["status"] == "success"
    assert isinstance(finished["review"]["strengths"], list)
    assert isinstance(finished["review"]["risks"], list)
    assert isinstance(finished["review"]["next_steps"], list)


async def test_mock_interview_rejects_cross_user_supports_retry_and_events(
    app, client, db_session, monkeypatch
):
    monkeypatch.setattr("app.routers.mock_interviews.schedule_mock_interview_prep", lambda *args, **kwargs: None)
    monkeypatch.setattr("app.routers.mock_interviews.schedule_mock_interview_turn", lambda *args, **kwargs: None)

    user_a, token_a = await create_test_user(db_session, email="interview-a@example.com")
    user_b, token_b = await create_test_user(db_session, email="interview-b@example.com")
    job_a, workflow_a = await _seed_interview_dependencies(db_session, user=user_a, suffix="a")
    _, workflow_empty = await _seed_interview_dependencies(
        db_session,
        user=user_a,
        suffix="empty",
        tailored_resume_md="   ",
    )
    _, workflow_b = await _seed_interview_dependencies(db_session, user=user_b, suffix="b")

    response = await client.post(
        "/mock-interviews",
        headers={"Authorization": f"Bearer {token_a}"},
        json={
            "job_id": str(job_a.id),
            "resume_id": str(workflow_b.resume_id),
            "resume_optimization_session_id": str(workflow_b.id),
        },
    )
    assert response.status_code == 404

    response = await client.post(
        "/mock-interviews",
        headers={"Authorization": f"Bearer {token_a}"},
        json={
            "job_id": str(job_a.id),
            "resume_id": str(workflow_empty.resume_id),
            "resume_optimization_session_id": str(workflow_empty.id),
        },
    )
    assert response.status_code == 409

    response = await client.post(
        "/mock-interviews",
        headers={"Authorization": f"Bearer {token_a}"},
        json={
            "job_id": str(job_a.id),
            "resume_id": str(workflow_a.resume_id),
            "resume_optimization_session_id": str(workflow_a.id),
        },
    )
    assert response.status_code == 201
    session = response.json()["data"]

    session_query = await db_session.execute(
        select(MockInterviewSession).where(MockInterviewSession.id == UUID(session["id"]))
    )
    session_record = session_query.scalar_one()
    next_plan_json = dict(session_record.plan_json or {})
    next_plan_json["prep_state"] = TaskState(
        status="failed",
        phase="failed",
        message="准备失败，可重试。",
    ).model_dump(mode="json")
    session_record.plan_json = next_plan_json
    db_session.add(session_record)
    await db_session.commit()
    db_session.expire_all()

    response = await client.post(
        f"/mock-interviews/{session['id']}/retry-prep",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert response.status_code == 200

    session_query = await db_session.execute(
        select(MockInterviewSession).where(MockInterviewSession.id == UUID(session["id"]))
    )
    session_record = session_query.scalar_one()
    assert session_record.plan_json["prep_state"]["status"] == "processing"

    response = await client.post(
        f"/mock-interviews/{session['id']}/events",
        headers={"Authorization": f"Bearer {token_a}"},
        json={"event_type": "interview_page_exit", "payload": {"source": "test"}},
    )
    assert response.status_code == 200
    db_session.expire_all()

    session_query = await db_session.execute(
        select(MockInterviewSession).where(MockInterviewSession.id == UUID(session["id"]))
    )
    session_record = session_query.scalar_one()
    assert session_record.plan_json["events"][-1]["event_type"] == "interview_page_exit"

    response = await client.get(
        f"/mock-interviews/{session['id']}",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert response.status_code == 404

    response = await client.delete(
        f"/mock-interviews/{session['id']}",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert response.status_code == 404


def test_mock_interview_review_type_coercion_uses_explicit_or_safe_fallbacks():
    assert (
        coerce_mock_interview_review_type("technical_analysis")
        == MockInterviewReviewType.TECHNICAL_ANALYSIS
    )
    assert (
        coerce_mock_interview_review_type("", category="系统设计", text="你会怎么排查线上性能瓶颈？")
        == MockInterviewReviewType.TECHNICAL_ANALYSIS
    )
    assert (
        coerce_mock_interview_review_type("", category="基础原理", text="讲一下虚拟内存的原理")
        == MockInterviewReviewType.KNOWLEDGE_FUNDAMENTAL
    )
    assert (
        coerce_mock_interview_review_type("", category="项目经历", text="讲一个你主导的项目")
        == MockInterviewReviewType.PROJECT_EXPERIENCE
    )


@pytest.mark.asyncio
async def test_mock_interview_turn_deep_review_failure_does_not_block_next_turn(
    app, client, db_session, monkeypatch
):
    monkeypatch.setattr("app.routers.mock_interviews.schedule_mock_interview_prep", lambda *args, **kwargs: None)
    monkeypatch.setattr("app.routers.mock_interviews.schedule_mock_interview_turn", lambda *args, **kwargs: None)

    user, token = await create_test_user(db_session, email="interview-deep-review-fail@example.com")
    job, workflow = await _seed_interview_dependencies(db_session, user=user, suffix="deep-review-fail")

    async def fake_summarize_role_desc(settings, target_role_desc: str) -> str:
        del settings, target_role_desc
        return "岗位需要候选人具备排查复杂问题的能力"

    async def fake_summarize_resume(settings, resume_md: str) -> str:
        del settings, resume_md
        return "候选人做过复杂系统排查与性能优化"

    async def fake_generate_main_questions(settings, *, role_summary: str, candidate_profile: str):
        del settings, role_summary, candidate_profile
        return [
            mock_interview_service.MainQuestionPlan(
                question_id="ta-1",
                category="技术分析",
                review_type=MockInterviewReviewType.TECHNICAL_ANALYSIS,
                text="如果线上吞吐突然下降，你会怎么排查？",
                intent="评估系统化排查能力",
                followup_hints=["指标", "验证"],
            )
        ]

    async def fake_decide_next_turn(settings, **kwargs):
        del settings, kwargs
        return mock_interview_service.MockInterviewTurnDecision(
            need_comment=True,
            comment_text="先继续往下回答。",
            next_action="next_main",
            next_question="",
            reason="move on",
        )

    async def fake_review_interview_answer(settings, **kwargs):
        del settings, kwargs
        return DeepReviewResult.failed()

    monkeypatch.setattr(mock_interview_service, "summarize_role_desc", fake_summarize_role_desc)
    monkeypatch.setattr(mock_interview_service, "summarize_resume", fake_summarize_resume)
    monkeypatch.setattr(mock_interview_service, "generate_main_questions", fake_generate_main_questions)
    monkeypatch.setattr(mock_interview_service, "decide_next_turn", fake_decide_next_turn)
    monkeypatch.setattr(mock_interview_service, "review_interview_answer", fake_review_interview_answer)

    response = await client.post(
        "/mock-interviews",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "job_id": str(job.id),
            "resume_id": str(workflow.resume_id),
            "resume_optimization_session_id": str(workflow.id),
        },
    )
    assert response.status_code == 201
    created_session = response.json()["data"]

    await mock_interview_service.process_mock_interview_prep(
        session_id=UUID(created_session["id"]),
        session_factory=app.state.session_factory,
        settings=app.state.settings,
    )

    response = await client.post(
        f"/mock-interviews/{created_session['id']}/turns/{created_session['current_turn']['id']}/answer",
        headers={"Authorization": f"Bearer {token}"},
        json={"answer_text": "我会先看监控和 profiling，再拆分数据、计算、通信路径。"},
    )
    assert response.status_code == 200

    await mock_interview_service.process_mock_interview_turn(
        session_id=UUID(created_session["id"]),
        turn_id=UUID(created_session["current_turn"]["id"]),
        session_factory=app.state.session_factory,
        settings=app.state.settings,
    )

    response = await client.get(
        f"/mock-interviews/{created_session['id']}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    session_payload = response.json()["data"]
    answered_turn = next(turn for turn in session_payload["turns"] if turn["turn_index"] == 1)
    assert answered_turn["evaluation_json"]["status"] == "failed"
    assert answered_turn["evaluation_json"]["display_comment"] == "本次深度点评暂时不可用"
    assert session_payload["current_turn"] is not None
