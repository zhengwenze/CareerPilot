"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import {
  ArrowUpRight,
  CheckCircle2,
  Send,
  Trash2,
} from "lucide-react";

import { useAuth } from "@/components/auth-provider";
import { PaperTextarea } from "@/components/brutalist/form-controls";
import {
  MetaChip,
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
  fetchMockInterviewSession,
  finishMockInterviewSession,
  listMockInterviewSessions,
  recordMockInterviewEvent,
  retryMockInterviewPrep,
  submitMockInterviewAnswer,
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
    completed: "已完成",
    failed: "失败",
  };
  return labels[value] ?? value;
}

function getQuestionTypeLabel(value: string) {
  return value === "followup" ? "追问" : "主问题";
}

function getNextActionMessage(value: unknown) {
  switch (value) {
    case "processing":
      return "回答已提交，系统正在准备下一题。";
    default:
      return "回答已提交。";
  }
}

function upsertSession(
  items: MockInterviewSessionRecord[],
  session: MockInterviewSessionRecord
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
  const optimizationSessionId = searchParams.get("optimizationSessionId");
  const jobId = searchParams.get("jobId");

  const [sessions, setSessions] = useState<MockInterviewSessionRecord[]>([]);
  const [selectedSession, setSelectedSession] =
    useState<MockInterviewSessionRecord | null>(null);
  const [answerText, setAnswerText] = useState("");
  const [isPageLoading, setIsPageLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isFinishing, setIsFinishing] = useState(false);
  const [isDeletingSessionId, setIsDeletingSessionId] = useState<string | null>(
    null
  );
  const [isRetryingPrep, setIsRetryingPrep] = useState(false);
  const [pageError, setPageError] = useState("");
  const [statusMessage, setStatusMessage] = useState("");
  const [loadingTitle, setLoadingTitle] = useState("正在加载模拟面试");
  const [loadingDescription, setLoadingDescription] = useState(
    "我们正在同步当前用户的训练会话和当前题目。"
  );

  useEffect(() => {
    if (!token) {
      return;
    }

    let cancelled = false;

    async function loadSessionDetail(sessionId: string) {
      return await fetchMockInterviewSession(token!, sessionId);
    }

    async function bootstrap() {
      setIsPageLoading(true);
      setPageError("");
      setLoadingTitle("正在加载模拟面试");
      setLoadingDescription("我们正在同步当前用户的训练会话和当前题目。");

      try {
        const list = await listMockInterviewSessions(token!, {
          jobId: jobId ?? undefined,
        });
        if (cancelled) {
          return;
        }

        if (jobId && optimizationSessionId && !sessionIdFromQuery) {
          setLoadingTitle("正在准备 AI 面试官");
          setLoadingDescription(
            "我们会先快速给出第一题，再在后台准备后续题。"
          );
          const created = await createMockInterviewSession(token!, {
            jobId,
            optimizationSessionId,
          });
          if (cancelled) {
            return;
          }
          setSessions(upsertSession(list, created));
          setSelectedSession(created);
          setAnswerText("");
          setStatusMessage(created.prep_state.message || "已创建新的模拟面试会话。");
          router.replace(`/dashboard/interviews?sessionId=${created.id}`);
          return;
        }

        const preferredSessionId = sessionIdFromQuery ?? list[0]?.id ?? null;
        if (!preferredSessionId) {
          setSessions(list);
          setSelectedSession(null);
          return;
        }

        const detail = await loadSessionDetail(preferredSessionId);
        if (cancelled) {
          return;
        }
        setSessions(upsertSession(list, detail));
        setSelectedSession(detail);
        setAnswerText("");
      } catch (error) {
        if (!cancelled) {
          setPageError(getErrorMessage(error));
          setSelectedSession(null);
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
  }, [jobId, optimizationSessionId, router, sessionIdFromQuery, token]);

  useEffect(() => {
    if (
      !token ||
      !selectedSession?.id ||
      selectedSession.prep_state.status !== "processing"
    ) {
      return;
    }

    const timer = window.setInterval(async () => {
      try {
        const nextSession = await fetchMockInterviewSession(token, selectedSession.id);
        setSessions((current) => upsertSession(current, nextSession));
        setSelectedSession(nextSession);
      } catch {
        // keep the current visible state until the next retry
      }
    }, 2000);

    return () => window.clearInterval(timer);
  }, [selectedSession?.id, selectedSession?.prep_state.status, token]);

  useEffect(() => {
    if (
      !token ||
      !selectedSession?.id ||
      selectedSession.prep_state.status !== "processing"
    ) {
      return;
    }

    const sendExitEvent = () => {
      void recordMockInterviewEvent(token, selectedSession.id, {
        event_type: "interview_page_exit",
        payload: {
          phase: selectedSession.prep_state.phase,
          status: selectedSession.prep_state.status,
        },
      }).catch(() => undefined);
    };

    const handleVisibilityChange = () => {
      if (document.visibilityState === "hidden") {
        sendExitEvent();
      }
    };

    window.addEventListener("beforeunload", sendExitEvent);
    document.addEventListener("visibilitychange", handleVisibilityChange);
    return () => {
      window.removeEventListener("beforeunload", sendExitEvent);
      document.removeEventListener("visibilitychange", handleVisibilityChange);
    };
  }, [selectedSession?.id, selectedSession?.prep_state.phase, selectedSession?.prep_state.status, token]);

  if (!token) {
    return null;
  }

  if (isPageLoading) {
    return (
      <PageLoadingState
        title={loadingTitle}
        description={loadingDescription}
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
    setSessions((current) => upsertSession(current, nextSession));
    setSelectedSession(nextSession);
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
        nextAnswer
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
      const nextSession = await finishMockInterviewSession(
        token,
        selectedSession.id
      );
      setSessions((current) => upsertSession(current, nextSession));
      setSelectedSession(nextSession);
      setStatusMessage("本场模拟已结束。");
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

  async function handleRetryPrep() {
    if (!token || !selectedSession) {
      return;
    }

    setIsRetryingPrep(true);
    setPageError("");

    try {
      await retryMockInterviewPrep(token, selectedSession.id);
      const nextSession = await fetchMockInterviewSession(token, selectedSession.id);
      setSessions((current) => upsertSession(current, nextSession));
      setSelectedSession(nextSession);
      setStatusMessage("正在重新准备后续题。");
    } catch (error) {
      setPageError(getErrorMessage(error));
    } finally {
      setIsRetryingPrep(false);
    }
  }

  return (
    <PageShell className="gap-8 py-4 md:py-6">
      <PageHeader
        description="继续当前岗位上下文，直接训练。"
        eyebrow="Mock Interviews"
        meta={
          <>
            <MetaChip>{sessions.length} 场训练</MetaChip>
            <MetaChip>{selectedSession ? "会话已选中" : "等待会话"}</MetaChip>
          </>
        }
        title="模拟面试"
      >
        <div className="bw-workbench-hero">
          <div className="bw-flow-strip">
            <div className="bw-flow-step">
              <strong>Step 1</strong>
              <span>选择会话</span>
            </div>
            <div className="bw-flow-step">
              <strong>Step 2</strong>
              <span>回答问题</span>
            </div>
            <div className="bw-flow-step">
              <strong>Step 3</strong>
              <span>查看复盘</span>
            </div>
            <div className="bw-flow-step">
              <strong>Step 4</strong>
              <span>继续下一轮</span>
            </div>
          </div>

          <div className="flex flex-wrap gap-2">
            <Button asChild type="button" variant="outline">
              <Link href="/dashboard/resume">
                返回专属简历
                <ArrowUpRight className="size-4" />
              </Link>
            </Button>
          </div>
        </div>
      </PageHeader>

      {pageError ? (
        <Alert className="border border-[#e5e5e5] bg-[#fafafa] text-[#111111]">
          <AlertTitle>错误</AlertTitle>
          <AlertDescription>{pageError}</AlertDescription>
        </Alert>
      ) : null}

      {statusMessage ? (
        <Alert className="border border-[#e5e5e5] bg-[#fafafa] text-[#111111]">
          <AlertTitle>状态</AlertTitle>
          <AlertDescription>{statusMessage}</AlertDescription>
        </Alert>
      ) : null}

      <section className="grid gap-6 xl:grid-cols-[300px_minmax(0,1fr)]">
        <PaperSection title="训练会话" eyebrow="Session History">
          {sessions.length === 0 ? (
            <PageEmptyState
              description="先从专属简历开始。"
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
                        ? "border-[#111111] bg-[#111111] text-[#fafafa]"
                        : "border-[#1C1C1C]/10 bg-white hover:border-[#1C1C1C]/20"
                    }`}
                    key={session.id}
                    onClick={() => void loadSelectedSession(session.id)}
                    type="button"
                  >
                    <p className={`text-sm font-semibold ${isActive ? "text-[#fafafa]" : "text-[#1C1C1C]"}`}>
                      模拟面试 · {getSessionStatusLabel(session.status)}
                    </p>
                    <p className={`mt-2 text-sm leading-relaxed ${isActive ? "text-[#fafafa]/80" : "text-[#1C1C1C]/60"}`}>
                      简历 v{session.source_resume_version} / 岗位 v
                      {session.source_job_version}
                    </p>
                    <p className={`mt-1 text-xs ${isActive ? "text-[#fafafa]/65" : "text-[#1C1C1C]/45"}`}>
                      {formatDate(session.created_at)}
                    </p>
                    {session.current_turn ? (
                      <p className={`mt-3 line-clamp-2 text-sm leading-relaxed ${isActive ? "text-[#fafafa]/80" : "text-[#1C1C1C]/60"}`}>
                        当前题目：{session.current_turn.question_text}
                      </p>
                    ) : null}
                  </button>
                );
              })}
            </div>
          )}
        </PaperSection>

        {!selectedSession ? (
          <PageEmptyState
            description="先创建或选择一场训练。"
            title="还没有选中训练会话"
          />
        ) : (
          <div className="space-y-6">
            <PaperSection
              title={`模拟面试 · ${getSessionStatusLabel(selectedSession.status)}`}
              eyebrow="Current Session"
              rightSlot={
                <div className="flex flex-wrap gap-3">
                  <div className="border border-[#1C1C1C]/10 bg-white px-4 py-2 text-sm text-[#1C1C1C]/60">
                    已提问 {selectedSession.question_count} / {selectedSession.max_questions}
                  </div>
                  {selectedSession.prep_state.status === "failed" ? (
                    <Button
                      disabled={isRetryingPrep}
                      onClick={() => void handleRetryPrep()}
                      type="button"
                      variant="outline"
                    >
                      {isRetryingPrep ? "重试中..." : "重试准备"}
                    </Button>
                  ) : null}
                  <Button
                    disabled={isDeletingSessionId === selectedSession.id}
                    onClick={() => void handleDeleteSession(selectedSession.id)}
                    type="button"
                    variant="outline"
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
                    主问题进度
                  </p>
                  <p className="mt-2 text-sm leading-relaxed text-[#1C1C1C]/60">
                    第 {selectedSession.main_question_index + 1} 组
                  </p>
                </div>
                <div className="border border-[#1C1C1C]/10 bg-white px-4 py-4">
                  <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[#1C1C1C]/60">
                    追问上限
                  </p>
                  <p className="mt-2 text-sm leading-relaxed text-[#1C1C1C]/60">
                    当前 {selectedSession.followup_count_for_current_main} /{" "}
                    {selectedSession.max_followups_per_main}
                  </p>
                </div>
                <div className="border border-[#1C1C1C]/10 bg-white px-4 py-4">
                  <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[#1C1C1C]/60">
                    会话状态
                  </p>
                  <p className="mt-2 text-sm leading-relaxed text-[#1C1C1C]/60">
                    {getSessionStatusLabel(selectedSession.status)}
                  </p>
                </div>
              </div>
              <div className="mt-4 border border-[#e5e5e5] bg-[#fafafa] p-4">
                <p className="text-sm font-medium text-[#1C1C1C]">
                  {selectedSession.prep_state.message || "等待准备状态。"}
                </p>
                <p className="mt-2 text-sm text-[#1C1C1C]/60">
                  阶段：{selectedSession.prep_state.phase || "idle"} · 状态：
                  {selectedSession.prep_state.status}
                </p>
              </div>
            </PaperSection>

            {selectedSession.status === "active" &&
            selectedSession.current_turn ? (
              <PaperSection
                title="当前题目"
                eyebrow={getQuestionTypeLabel(
                  selectedSession.current_turn.question_type
                )}
                rightSlot={
                  <Button
                    disabled={isFinishing}
                    onClick={() => void handleFinishSession()}
                    type="button"
                    variant="outline"
                  >
                    {isFinishing ? "结束中..." : "结束面试"}
                    <CheckCircle2 className="ml-2 size-4" />
                  </Button>
                }
              >
                <div className="space-y-4">
                  <div className="border border-[#1C1C1C]/10 bg-white px-4 py-4">
                    <p className="text-sm leading-7 text-[#1C1C1C]">
                      {selectedSession.current_turn.question_text}
                    </p>
                  </div>

                  <PaperTextarea
                    onChange={(event) => setAnswerText(event.target.value)}
                    placeholder="用事实、动作、指标和结果来回答。"
                    value={answerText}
                  />

                  <Button
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
                      第 {turn.turn_index} 轮 · {getQuestionTypeLabel(turn.question_type)}
                    </p>
                    <p className="mt-2 text-sm font-semibold text-[#1C1C1C]">
                      {turn.question_text}
                    </p>
                    <p className="mt-3 text-sm leading-relaxed text-[#1C1C1C]/60">
                      {turn.answer_text || "尚未作答"}
                    </p>
                    {turn.comment_text ? (
                      <p className="mt-3 text-sm leading-relaxed text-[#1C1C1C]/60">
                        点评：{turn.comment_text}
                      </p>
                    ) : null}
                  </div>
                ))}
              </div>
            </PaperSection>

            {(selectedSession.review.strengths.length > 0 ||
              selectedSession.review.risks.length > 0 ||
              selectedSession.review.next_steps.length > 0) ? (
              <PaperSection title="结构化复盘" eyebrow="Review">
                <div className="grid gap-4 md:grid-cols-3">
                  <div className="border border-[#1C1C1C]/10 bg-white p-4">
                    <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#1C1C1C]/55">
                      亮点
                    </p>
                    <div className="mt-3 space-y-2 text-sm leading-6 text-[#1C1C1C]/70">
                      {selectedSession.review.strengths.length ? (
                        selectedSession.review.strengths.map((item) => (
                          <p key={item}>{item}</p>
                        ))
                      ) : (
                        <p>暂未生成。</p>
                      )}
                    </div>
                  </div>
                  <div className="border border-[#1C1C1C]/10 bg-white p-4">
                    <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#1C1C1C]/55">
                      风险
                    </p>
                    <div className="mt-3 space-y-2 text-sm leading-6 text-[#1C1C1C]/70">
                      {selectedSession.review.risks.length ? (
                        selectedSession.review.risks.map((item) => (
                          <p key={item}>{item}</p>
                        ))
                      ) : (
                        <p>暂未生成。</p>
                      )}
                    </div>
                  </div>
                  <div className="border border-[#1C1C1C]/10 bg-white p-4">
                    <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#1C1C1C]/55">
                      下一步
                    </p>
                    <div className="mt-3 space-y-2 text-sm leading-6 text-[#1C1C1C]/70">
                      {selectedSession.review.next_steps.length ? (
                        selectedSession.review.next_steps.map((item) => (
                          <p key={item}>{item}</p>
                        ))
                      ) : (
                        <p>暂未生成。</p>
                      )}
                    </div>
                  </div>
                </div>
              </PaperSection>
            ) : null}

            {selectedSession.ending_text ? (
              <PaperSection title="结束语" eyebrow="Closing">
                <p className="text-sm leading-7 text-[#1C1C1C]/68">
                  {selectedSession.ending_text}
                </p>
              </PaperSection>
            ) : null}
          </div>
        )}
      </section>
    </PageShell>
  );
}
