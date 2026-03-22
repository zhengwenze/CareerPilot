from __future__ import annotations

from uuid import UUID

from sqlalchemy import select

from app.models import (
    JobDescription,
    MatchReport,
    MockInterviewSession,
    Resume,
    ResumeOptimizationSession,
)
from app.services import mock_interview as mock_interview_service

from conftest import create_test_user


async def _seed_interview_dependencies(db_session, *, user, suffix: str, tailored_resume_md: str | None = None):
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
        structured_json={},
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
        status="ready",
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


async def test_mock_interview_uses_demo_prepare_chain_and_runtime_flow(client, db_session, monkeypatch):
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
                next_action="followup",
                next_question="你刚才提到架构升级，具体是怎么推进落地的？",
                reason="probe execution details",
            ),
            mock_interview_service.MockInterviewTurnDecision(
                need_comment=True,
                comment_text="这个例子比较完整。",
                next_action="next_main",
                next_question="",
                reason="switch to next main",
            ),
            mock_interview_service.MockInterviewTurnDecision(
                need_comment=False,
                comment_text="",
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

    async def fake_generate_dynamic_main_question(
        settings,
        *,
        role_summary: str,
        candidate_profile: str,
        asked_questions: list[str],
    ):
        del settings
        calls.append(
            (
                "generate_dynamic_main_question",
                f"{role_summary} || {candidate_profile} || {' | '.join(asked_questions)}",
            )
        )
        return mock_interview_service.MainQuestionPlan(
            question_id="main-2",
            category="岗位匹配",
            text="如果你加入这个岗位，前 90 天会优先解决什么问题？",
            intent="验证岗位理解",
            followup_hints=["优先级", "协作策略"],
        )

    async def fake_generate_ending_text(settings, *, candidate_profile: str, recent_turns: str) -> str:
        del settings
        calls.append(("generate_ending_text", f"{candidate_profile} || {recent_turns}"))
        return "今天先到这里，感谢你的回答。整体思路清楚，后续继续强化案例细节。"

    monkeypatch.setattr(mock_interview_service, "summarize_role_desc", fake_summarize_role_desc)
    monkeypatch.setattr(mock_interview_service, "summarize_resume", fake_summarize_resume)
    monkeypatch.setattr(mock_interview_service, "generate_main_questions", fake_generate_main_questions)
    monkeypatch.setattr(mock_interview_service, "decide_next_turn", fake_decide_next_turn)
    monkeypatch.setattr(
        mock_interview_service,
        "generate_dynamic_main_question",
        fake_generate_dynamic_main_question,
    )
    monkeypatch.setattr(mock_interview_service, "generate_ending_text", fake_generate_ending_text)

    response = await client.post(
        "/mock-interviews",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "job_id": str(job.id),
            "resume_optimization_session_id": str(workflow.id),
        },
    )
    assert response.status_code == 201
    created_session = response.json()["data"]
    assert created_session["current_turn"]["question_text"] == "请讲一个你主导前端架构升级的项目。"
    assert calls[:3] == [
        ("summarize_role_desc", job.jd_text),
        ("summarize_resume", workflow.tailored_resume_md),
        (
            "generate_main_questions",
            "岗位需要 React 架构和团队带领能力 || 岗位侧重点：岗位需要 React 架构和团队带领能力\n候选人画像：候选人做过前端架构升级和跨团队协作",
        ),
    ]

    session_query = await db_session.execute(
        select(MockInterviewSession).where(MockInterviewSession.id == UUID(created_session["id"]))
    )
    session_record = session_query.scalar_one()
    assert session_record.plan_json["resume_summary"] == "候选人做过前端架构升级和跨团队协作"
    assert session_record.plan_json["candidate_profile"].startswith("岗位侧重点：")

    response = await client.post(
        f"/mock-interviews/{created_session['id']}/turns/{created_session['current_turn']['id']}/answer",
        headers={"Authorization": f"Bearer {token}"},
        json={"answer_text": "我负责拆分历史单体前端，落地微前端和统一组件规范。"},
    )
    assert response.status_code == 200
    assert response.json()["data"]["next_action"]["type"] == "followup"

    response = await client.get(
        f"/mock-interviews/{created_session['id']}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    followup_session = response.json()["data"]
    assert followup_session["followup_count_for_current_main"] == 1
    assert followup_session["current_turn"]["question_type"] == "followup"
    assert followup_session["current_turn"]["question_text"] == "你刚才提到架构升级，具体是怎么推进落地的？"

    response = await client.post(
        f"/mock-interviews/{created_session['id']}/turns/{followup_session['current_turn']['id']}/answer",
        headers={"Authorization": f"Bearer {token}"},
        json={"answer_text": "我先统一技术方案，再按域拆分并配合业务团队灰度上线。"},
    )
    assert response.status_code == 200
    assert response.json()["data"]["next_action"]["type"] == "next_main"

    response = await client.get(
        f"/mock-interviews/{created_session['id']}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    dynamic_main_session = response.json()["data"]
    assert dynamic_main_session["current_turn"]["question_type"] == "main"
    assert dynamic_main_session["current_turn"]["question_text"] == "如果你加入这个岗位，前 90 天会优先解决什么问题？"
    assert any(call[0] == "generate_dynamic_main_question" for call in calls)

    response = await client.post(
        f"/mock-interviews/{created_session['id']}/turns/{dynamic_main_session['current_turn']['id']}/answer",
        headers={"Authorization": f"Bearer {token}"},
        json={"answer_text": "我会先盘点现有前端架构风险，建立交付基线，再针对最痛的流程问题下手。"},
    )
    assert response.status_code == 200
    assert response.json()["data"]["next_action"]["type"] == "end"
    assert response.json()["data"]["next_action"]["ending_text"].startswith("今天先到这里")

    response = await client.get(
        f"/mock-interviews/{created_session['id']}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    completed_session = response.json()["data"]
    assert completed_session["status"] == "completed"
    assert completed_session["current_turn"] is None
    assert completed_session["ending_text"].startswith("今天先到这里")


async def test_mock_interview_rejects_cross_user_and_missing_tailored_resume(client, db_session, monkeypatch):
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

    async def fake_summarize_role_desc(settings, target_role_desc: str) -> str:
        del settings
        return target_role_desc

    async def fake_summarize_resume(settings, resume_md: str) -> str:
        del settings
        return resume_md

    async def fake_generate_main_questions(settings, *, role_summary: str, candidate_profile: str):
        del settings, role_summary, candidate_profile
        return [
            mock_interview_service.MainQuestionPlan(
                question_id="main-1",
                category="通用",
                text="请介绍一下你自己。",
                intent="fallback test",
                followup_hints=[],
            )
        ]

    monkeypatch.setattr(mock_interview_service, "summarize_role_desc", fake_summarize_role_desc)
    monkeypatch.setattr(mock_interview_service, "summarize_resume", fake_summarize_resume)
    monkeypatch.setattr(mock_interview_service, "generate_main_questions", fake_generate_main_questions)

    response = await client.post(
        "/mock-interviews",
        headers={"Authorization": f"Bearer {token_a}"},
        json={
            "job_id": str(job_a.id),
            "resume_optimization_session_id": str(workflow_b.id),
        },
    )
    assert response.status_code == 404

    response = await client.post(
        "/mock-interviews",
        headers={"Authorization": f"Bearer {token_a}"},
        json={
            "job_id": str(job_a.id),
            "resume_optimization_session_id": str(workflow_empty.id),
        },
    )
    assert response.status_code == 409

    response = await client.post(
        "/mock-interviews",
        headers={"Authorization": f"Bearer {token_a}"},
        json={
            "job_id": str(job_a.id),
            "resume_optimization_session_id": str(workflow_a.id),
        },
    )
    assert response.status_code == 201
    session = response.json()["data"]

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
