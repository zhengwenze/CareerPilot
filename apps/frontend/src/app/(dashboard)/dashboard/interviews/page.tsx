"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import {
  ArrowUpRight,
  CheckCircle2,
  Send,
  Sparkles,
  Trash2,
} from "lucide-react";

import { useAuth } from "@/components/auth-provider";
import { PaperTextarea } from "@/components/brutalist/form-controls";
import {
  PageHeader,
  PageShell,
  PaperSection,
} from "@/components/brutalist/page-shell";
import {
  PageEmptyState,
  PageErrorState,
  PageLoadingState,
} from "@/components/page-state";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { ApiError } from "@/lib/api/client";
import {
  createMockInterviewSession,
  deleteMockInterviewSession,
  fetchMockInterviewReview,
  fetchMockInterviewSession,
  finishMockInterviewSession,
  listMockInterviewSessions,
  submitMockInterviewAnswer,
  type MockInterviewReviewResponse,
  type MockInterviewSessionRecord,
} from "@/lib/api/modules/mock-interviews";

function getErrorMessage(error: unknown) {
  if (error instanceof ApiError) {
    return error.message;
  }
  if (error instanceof Error) {
    return error.message;
  }
  return "操作失败，请稍后重试。";
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat("zh-CN", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

function getSessionStatusLabel(value: string) {
  const labels: Record<string, string> = {
    active: "进行中",
    reviewing: "生成复盘中",
    completed: "已完成",
  };
  return labels[value] ?? value;
}

function getQuestionSourceLabel(value: string) {
  const labels: Record<string, string> = {
    gap: "短板问题",
    strength: "优势问题",
    behavioral_general: "行为问题",
    follow_up: "追问",
  };
  return labels[value] ?? value;
}

function getReadinessLabel(value: string) {
  const labels: Record<string, string> = {
    draft: "草稿",
    analyzed: "已分析",
    matched: "已匹配",
    tailoring_needed: "待优化",
    interview_ready: "可练面试",
    training_in_progress: "训练中",
    ready_to_apply: "可投递",
  };
  return labels[value] ?? value;
}

function getSeverityLabel(value: string) {
  const labels: Record<string, string> = {
    high: "高优先级",
    medium: "中优先级",
    low: "低优先级",
  };
  return labels[value] ?? value;
}

function getModeLabel(value: string) {
  const labels: Record<string, string> = {
    general: "通用模拟",
    behavioral: "行为面试",
    project_deep_dive: "项目深挖",
    technical: "技术追问",
    hr_fit: "HR 匹配",
  };
  return labels[value] ?? value;
}

function getNextActionMessage(value: string | undefined) {
  switch (value) {
    case "follow_up":
      return "已生成追问，继续回答当前主题。";
    case "next_question":
      return "这一题已完成，系统已切到下一题。";
    case "finish_and_review":
      return "本场模拟已结束，复盘结果已生成。";
    default:
      return "回答已提交。";
  }
}

function upsertSession(
  items: MockInterviewSessionRecord[],
  session: MockInterviewSessionRecord,
) {
  const index = items.findIndex((item) => item.id === session.id);
  if (index === -1) {
    return [session, ...items];
  }
  return items.map((item) => (item.id === session.id ? session : item));
}

export default function DashboardInterviewsPage() {
  const { token } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();
  const sessionIdFromQuery = searchParams.get("sessionId");
  const reportId = searchParams.get("reportId");
  const optimizationSessionId = searchParams.get("optimizationSessionId");
  const jobId = searchParams.get("jobId");

  const [sessions, setSessions] = useState<MockInterviewSessionRecord[]>([]);
  const [selectedSession, setSelectedSession] =
    useState<MockInterviewSessionRecord | null>(null);
  const [review, setReview] = useState<MockInterviewReviewResponse | null>(
    null,
  );
  const [answerText, setAnswerText] = useState("");
  const [isPageLoading, setIsPageLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isFinishing, setIsFinishing] = useState(false);
  const [isDeletingSessionId, setIsDeletingSessionId] = useState<string | null>(
    null,
  );
  const [pageError, setPageError] = useState("");
  const [statusMessage, setStatusMessage] = useState("");

  useEffect(() => {
    if (!token) {
      return;
    }

    const accessToken = token;
    let cancelled = false;

    async function loadCompletedReview(sessionId: string) {
      try {
        return await fetchMockInterviewReview(accessToken, sessionId);
      } catch {
        return null;
      }
    }

    async function loadSessionDetail(sessionId: string) {
      const session = await fetchMockInterviewSession(accessToken, sessionId);
      const nextReview =
        session.status === "completed"
          ? await loadCompletedReview(session.id)
          : null;
      return { session, nextReview };
    }

    async function bootstrap() {
      setIsPageLoading(true);
      setPageError("");

      try {
        const list = await listMockInterviewSessions(accessToken, {
          jobId: jobId ?? undefined,
        });
        if (cancelled) {
          return;
        }

        if (reportId && !sessionIdFromQuery) {
          const created = await createMockInterviewSession(accessToken, {
            matchReportId: reportId,
            optimizationSessionId: optimizationSessionId ?? undefined,
          });
          if (cancelled) {
            return;
          }
          const detail = await loadSessionDetail(created.id);
          if (cancelled) {
            return;
          }
          setSessions(upsertSession(list, detail.session));
          setSelectedSession(detail.session);
          setReview(detail.nextReview);
          setAnswerText("");
          setStatusMessage("已创建新的模拟面试会话。");
          router.replace(`/dashboard/interviews?sessionId=${created.id}`);
          return;
        }

        const preferredSessionId = sessionIdFromQuery ?? list[0]?.id ?? null;
        if (!preferredSessionId) {
          setSessions(list);
          setSelectedSession(null);
          setReview(null);
          return;
        }

        const detail = await loadSessionDetail(preferredSessionId);
        if (cancelled) {
          return;
        }
        setSessions(upsertSession(list, detail.session));
        setSelectedSession(detail.session);
        setReview(detail.nextReview);
        setAnswerText("");
      } catch (error) {
        if (!cancelled) {
          setPageError(getErrorMessage(error));
        }
      } finally {
        if (!cancelled) {
          setIsPageLoading(false);
        }
      }
    }

    void bootstrap();

    return () => {
      cancelled = true;
    };
  }, [
    jobId,
    optimizationSessionId,
    reportId,
    router,
    sessionIdFromQuery,
    token,
  ]);

  if (!token) {
    return null;
  }

  if (isPageLoading) {
    return (
      <PageLoadingState
        title="正在加载模拟面试"
        description="我们正在同步最近的训练会话、当前题目和复盘结果。"
      />
    );
  }

  if (pageError && sessions.length === 0 && !selectedSession) {
    return (
      <PageErrorState
        actionLabel="返回专属简历"
        description={pageError}
        onAction={() => router.push("/dashboard/resume")}
        title="模拟面试加载失败"
      />
    );
  }

  async function loadSelectedSession(sessionId: string) {
    if (!token) {
      return;
    }

    setPageError("");
    const nextSession = await fetchMockInterviewSession(token, sessionId);
    const nextReview =
      nextSession.status === "completed"
        ? await fetchMockInterviewReview(token, sessionId).catch(() => null)
        : null;

    setSessions((current) => upsertSession(current, nextSession));
    setSelectedSession(nextSession);
    setReview(nextReview);
    setAnswerText("");
    router.replace(`/dashboard/interviews?sessionId=${sessionId}`);
  }

  async function handleSubmitAnswer() {
    if (!token || !selectedSession?.current_turn) {
      return;
    }

    const nextAnswer = answerText.trim();
    if (!nextAnswer) {
      setPageError("请先写下这一题的回答，再提交。");
      return;
    }

    setIsSubmitting(true);
    setPageError("");
    setStatusMessage("");

    try {
      const result = await submitMockInterviewAnswer(
        token,
        selectedSession.id,
        selectedSession.current_turn.id,
        nextAnswer,
      );
      await loadSelectedSession(selectedSession.id);
      setStatusMessage(getNextActionMessage(result.next_action.type));
    } catch (error) {
      setPageError(getErrorMessage(error));
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleFinishSession() {
    if (!token || !selectedSession) {
      return;
    }

    setIsFinishing(true);
    setPageError("");
    setStatusMessage("");

    try {
      const nextReview = await finishMockInterviewSession(
        token,
        selectedSession.id,
      );
      await loadSelectedSession(selectedSession.id);
      setReview(nextReview);
      setStatusMessage("本场模拟已结束，复盘结果已生成。");
    } catch (error) {
      setPageError(getErrorMessage(error));
    } finally {
      setIsFinishing(false);
    }
  }

  async function handleDeleteSession(sessionId: string) {
    if (!token) {
      return;
    }

    const confirmed = window.confirm("确认删除这场模拟面试吗？");
    if (!confirmed) {
      return;
    }

    setIsDeletingSessionId(sessionId);
    setPageError("");

    try {
      await deleteMockInterviewSession(token, sessionId);
      const nextSessions = sessions.filter((item) => item.id !== sessionId);
      setSessions(nextSessions);
      setStatusMessage("模拟面试已删除。");

      if (selectedSession?.id === sessionId) {
        const nextSelectedId = nextSessions[0]?.id ?? null;
        if (nextSelectedId) {
          await loadSelectedSession(nextSelectedId);
        } else {
          setSelectedSession(null);
          setReview(null);
          setAnswerText("");
          router.replace("/dashboard/interviews");
        }
      }
    } catch (error) {
      setPageError(getErrorMessage(error));
    } finally {
      setIsDeletingSessionId(null);
    }
  }

  return (
    <PageShell className="gap-6">
      <PageHeader
        description="基于岗位快照与匹配报告进入真实问答训练，提交回答后即时生成追问或复盘。"
        eyebrow="Mock Interviews"
        meta={
          <Button asChild type="button" variant="secondary">
            <Link href="/dashboard/resume">
              返回专属简历
              <ArrowUpRight className="ml-2 size-4" />
            </Link>
          </Button>
        }
        title="模拟面试"
      />

      {pageError ? (
        <Alert className="border border-[#1C1C1C]/10 bg-[#F9F8F6] text-[#1C1C1C]">
          <AlertTitle className="text-base font-semibold tracking-tight text-[#1C1C1C]">
            操作失败
          </AlertTitle>
          <AlertDescription className="text-sm leading-relaxed text-[#1C1C1C]/60">
            {pageError}
          </AlertDescription>
        </Alert>
      ) : null}

      {statusMessage ? (
        <Alert className="border border-[#1C1C1C]/10 bg-[#F9F8F6] text-[#1C1C1C]">
          <AlertTitle className="text-base font-semibold tracking-tight text-[#1C1C1C]">
            当前状态
          </AlertTitle>
          <AlertDescription className="text-sm leading-relaxed text-[#1C1C1C]/60">
            {statusMessage}
          </AlertDescription>
        </Alert>
      ) : null}

      <section className="grid gap-6 xl:grid-cols-[320px_minmax(0,1fr)]">
        <PaperSection title="训练会话" eyebrow="Session History">
          {sessions.length === 0 ? (
            <PageEmptyState
              description="先从专属简历进入，这里会保留你的训练记录。"
              title="还没有模拟面试"
            />
          ) : (
            <div className="space-y-3">
              {sessions.map((session) => {
                const isActive = session.id === selectedSession?.id;
                return (
                  <button
                    className={`block w-full border p-4 text-left transition-colors ${
                      isActive
                        ? "border-[#1C1C1C] bg-white"
                        : "border-[#1C1C1C]/10 bg-white hover:border-[#1C1C1C]/20"
                    }`}
                    key={session.id}
                    onClick={() => void loadSelectedSession(session.id)}
                    type="button"
                  >
                    <p className="text-sm font-semibold text-[#1C1C1C]">
                      {getModeLabel(session.mode)} ·{" "}
                      {getSessionStatusLabel(session.status)}
                    </p>
                    <p className="mt-2 text-sm leading-relaxed text-[#1C1C1C]/60">
                      简历 v{session.source_resume_version} / 岗位 v
                      {session.source_job_version}
                    </p>
                    <p className="mt-1 text-xs text-[#1C1C1C]/45">
                      {formatDate(session.created_at)}
                    </p>
                  </button>
                );
              })}
            </div>
          )}
        </PaperSection>

        {!selectedSession ? (
          <PageEmptyState
            description="先从岗位匹配页创建一场训练，或选择左侧已有会话继续。"
            title="还没有选中训练会话"
          />
        ) : (
          <div className="space-y-6">
            <PaperSection
              title={`${getModeLabel(selectedSession.mode)} · ${getSessionStatusLabel(
                selectedSession.status,
              )}`}
              eyebrow="Current Session"
              rightSlot={
                <div className="flex flex-wrap gap-3">
                  <div className="border border-[#1C1C1C]/10 bg-white px-4 py-2 text-sm text-[#1C1C1C]/60">
                    {selectedSession.plan_json?.target_role || "岗位角色未命名"}
                  </div>
                  <Button
                    className="border-b border-[#1C1C1C]/20 bg-white px-4 py-2 text-sm font-medium text-[#1C1C1C] transition-colors hover:bg-[#1C1C1C]/5"
                    disabled={isDeletingSessionId === selectedSession.id}
                    onClick={() => void handleDeleteSession(selectedSession.id)}
                    type="button"
                    variant="secondary"
                  >
                    {isDeletingSessionId === selectedSession.id
                      ? "删除中..."
                      : "删除会话"}
                    <Trash2 className="ml-2 size-4" />
                  </Button>
                </div>
              }
            >
              <div className="grid gap-4 md:grid-cols-3">
                <div className="border border-[#1C1C1C]/10 bg-white px-4 py-4">
                  <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[#1C1C1C]/60">
                    题目进度
                  </p>
                  <p className="mt-2 text-sm leading-relaxed text-[#1C1C1C]/60">
                    第 {selectedSession.current_question_index} 题 / 最多{" "}
                    {selectedSession.max_questions} 题
                  </p>
                </div>
                <div className="border border-[#1C1C1C]/10 bg-white px-4 py-4">
                  <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[#1C1C1C]/60">
                    追问上限
                  </p>
                  <p className="mt-2 text-sm leading-relaxed text-[#1C1C1C]/60">
                    当前 {selectedSession.current_follow_up_count} /{" "}
                    {selectedSession.max_follow_ups_per_question}
                  </p>
                </div>
                <div className="border border-[#1C1C1C]/10 bg-white px-4 py-4">
                  <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[#1C1C1C]/60">
                    当前总评
                  </p>
                  <p className="mt-2 text-sm leading-relaxed text-[#1C1C1C]/60">
                    {selectedSession.overall_score
                      ? `${selectedSession.overall_score} 分`
                      : "完成后生成"}
                  </p>
                </div>
              </div>
              {selectedSession.plan_json?.focus_areas?.length ? (
                <div className="mt-5 space-y-3">
                  <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[#1C1C1C]/60">
                    本场训练重点
                  </p>
                  {selectedSession.plan_json.focus_areas.map((item) => (
                    <div
                      className="border border-[#1C1C1C]/10 bg-white px-4 py-4"
                      key={`${item.topic}-${item.reason}`}
                    >
                      <p className="text-sm font-semibold text-[#1C1C1C]">
                        {item.topic}
                      </p>
                      <p className="mt-2 text-sm leading-relaxed text-[#1C1C1C]/60">
                        {item.reason}
                      </p>
                    </div>
                  ))}
                </div>
              ) : null}
            </PaperSection>

            {selectedSession.status === "active" &&
            selectedSession.current_turn ? (
              <PaperSection
                title="当前题目"
                eyebrow={getQuestionSourceLabel(
                  selectedSession.current_turn.question_source,
                )}
                rightSlot={
                  <Button
                    className="border-b border-[#1C1C1C]/20 bg-white px-4 py-2 text-sm font-medium text-[#1C1C1C] transition-colors hover:bg-[#1C1C1C]/5"
                    disabled={isFinishing}
                    onClick={() => void handleFinishSession()}
                    type="button"
                    variant="secondary"
                  >
                    {isFinishing ? "结束中..." : "结束并生成复盘"}
                    <CheckCircle2 className="ml-2 size-4" />
                  </Button>
                }
              >
                <div className="space-y-4">
                  <div className="border border-[#1C1C1C]/10 bg-white px-4 py-4">
                    <p className="text-sm leading-7 text-[#1C1C1C]">
                      {selectedSession.current_turn.question_text}
                    </p>
                    {selectedSession.current_turn.question_intent ? (
                      <p className="mt-3 text-sm leading-relaxed text-[#1C1C1C]/60">
                        追问目标：{selectedSession.current_turn.question_intent}
                      </p>
                    ) : null}
                  </div>

                  <PaperTextarea
                    onChange={(event) => setAnswerText(event.target.value)}
                    placeholder="用事实、动作、指标和结果来回答。"
                    value={answerText}
                  />

                  <Button
                    className="border-b border-[#1C1C1C]/20 bg-[#1C1C1C] px-5 py-3 text-sm font-medium text-white transition-colors hover:bg-[#1C1C1C]/90 disabled:cursor-not-allowed disabled:opacity-60"
                    disabled={isSubmitting}
                    onClick={() => void handleSubmitAnswer()}
                    type="button"
                  >
                    {isSubmitting ? "提交中..." : "提交回答"}
                    <Send className="ml-2 size-4" />
                  </Button>
                </div>
              </PaperSection>
            ) : null}

            <PaperSection title="问答记录" eyebrow="Transcript">
              <div className="space-y-4">
                {selectedSession.turns.map((turn) => (
                  <div
                    className="border border-[#1C1C1C]/10 bg-white p-4"
                    key={turn.id}
                  >
                    <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[#1C1C1C]/60">
                      第 {turn.turn_index} 轮 ·{" "}
                      {getQuestionSourceLabel(turn.question_source)}
                    </p>
                    <p className="mt-2 text-sm font-semibold text-[#1C1C1C]">
                      {turn.question_text}
                    </p>
                    <p className="mt-3 text-sm leading-relaxed text-[#1C1C1C]/60">
                      {turn.answer_text || "尚未作答"}
                    </p>
                    {turn.evaluation_json?.summary ? (
                      <p className="mt-3 text-sm leading-relaxed text-[#1C1C1C]/60">
                        反馈：{turn.evaluation_json.summary}
                      </p>
                    ) : null}
                  </div>
                ))}
              </div>
            </PaperSection>

            {review?.review_json ? (
              <div className="space-y-6">
                <PaperSection
                  title={`复盘总分 ${review.overall_score ?? "待计算"}`}
                  eyebrow="Review"
                >
                  <p className="text-sm leading-7 text-[#1C1C1C]/68">
                    {review.review_json.overall_summary}
                  </p>
                  <div className="mt-5 grid gap-4 md:grid-cols-2">
                    <div className="border border-[#1C1C1C]/10 bg-white px-4 py-4">
                      <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[#1C1C1C]/60">
                        优势
                      </p>
                      <div className="mt-3 space-y-3">
                        {review.review_json.strengths.map((item) => (
                          <div key={`${item.label}-${item.reason}`}>
                            <p className="text-sm font-semibold text-[#1C1C1C]">
                              {item.label}
                            </p>
                            <p className="mt-1 text-sm leading-relaxed text-[#1C1C1C]/60">
                              {item.reason}
                            </p>
                          </div>
                        ))}
                      </div>
                    </div>
                    <div className="border border-[#1C1C1C]/10 bg-white px-4 py-4">
                      <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[#1C1C1C]/60">
                        待补项
                      </p>
                      <div className="mt-3 space-y-3">
                        {review.review_json.weaknesses.map((item) => (
                          <div key={`${item.label}-${item.reason}`}>
                            <p className="text-sm font-semibold text-[#1C1C1C]">
                              {item.label} · {getSeverityLabel(item.severity)}
                            </p>
                            <p className="mt-1 text-sm leading-relaxed text-[#1C1C1C]/60">
                              {item.reason}
                            </p>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                </PaperSection>

                <PaperSection title="逐题复盘" eyebrow="Question Reviews">
                  <div className="space-y-4">
                    {review.review_json.question_reviews.map((item) => (
                      <div
                        className="border border-[#1C1C1C]/10 bg-white p-4"
                        key={`${item.question_group_index}-${item.question_text}`}
                      >
                        <p className="text-sm font-semibold text-[#1C1C1C]">
                          第 {item.question_group_index} 题
                        </p>
                        <p className="mt-2 text-sm leading-relaxed text-[#1C1C1C]">
                          {item.question_text}
                        </p>
                        <p className="mt-3 text-sm leading-relaxed text-[#1C1C1C]/60">
                          {item.summary}
                        </p>
                        <p className="mt-3 text-sm leading-relaxed text-[#1C1C1C]/60">
                          更优回答方向：{item.suggested_better_answer}
                        </p>
                      </div>
                    ))}
                  </div>
                </PaperSection>

                <PaperSection title="后续动作" eyebrow="Follow-up Tasks">
                  <div className="space-y-4">
                    {review.follow_up_tasks_json.map((item) => (
                      <div
                        className="border border-[#1C1C1C]/10 bg-white p-4"
                        key={`${item.title}-${item.reason}`}
                      >
                        <p className="text-sm font-semibold text-[#1C1C1C]">
                          {item.title} ·{" "}
                          {item.task_type === "resume"
                            ? "简历任务"
                            : "面试任务"}
                        </p>
                        <p className="mt-2 text-sm leading-relaxed text-[#1C1C1C]/60">
                          {item.instruction}
                        </p>
                        <p className="mt-2 text-sm leading-relaxed text-[#1C1C1C]/45">
                          {item.reason}
                        </p>
                      </div>
                    ))}
                    <div className="border border-[#1C1C1C]/10 bg-white p-4">
                      <p className="text-sm font-semibold text-[#1C1C1C]">
                        就绪信号：
                        {getReadinessLabel(
                          review.review_json.job_readiness_signal.status,
                        )}
                      </p>
                      <p className="mt-2 text-sm leading-relaxed text-[#1C1C1C]/60">
                        {review.review_json.job_readiness_signal.reason}
                      </p>
                    </div>
                  </div>
                </PaperSection>
              </div>
            ) : null}

            {!review?.review_json && selectedSession.status !== "active" ? (
              <PageEmptyState
                description="当前会话还在生成复盘，稍后重新进入即可查看完整结论。"
                title="复盘尚未就绪"
              />
            ) : null}

            {selectedSession.optimization_session_id ? (
              <Button
                asChild
                className="border-b border-[#1C1C1C]/20 bg-white px-5 py-3 text-sm font-medium text-[#1C1C1C] transition-colors hover:bg-[#1C1C1C]/5"
                type="button"
              >
                <Link
                  href={`/dashboard/resume?workflowId=${selectedSession.optimization_session_id}`}
                >
                  返回对应专属简历
                  <Sparkles className="ml-2 size-4" />
                </Link>
              </Button>
            ) : null}
          </div>
        )}
      </section>
    </PageShell>
  );
}
