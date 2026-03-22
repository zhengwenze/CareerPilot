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
    case "followup":
      return "已生成追问，继续回答当前主题。";
    case "next_main":
      return "这一题已完成，系统已切到下一题。";
    case "end":
      return "本场模拟已结束。";
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
            "我们正在根据当前用户自己的岗位 JD 和优化简历生成主问题池。这一步通常需要 1 到 2 分钟，请不要刷新页面。"
          );
          const created = await createMockInterviewSession(token!, {
            jobId,
            optimizationSessionId,
          });
          if (cancelled) {
            return;
          }
          const detail = await loadSessionDetail(created.id);
          if (cancelled) {
            return;
          }
          setSessions(upsertSession(list, detail));
          setSelectedSession(detail);
          setAnswerText("");
          setStatusMessage("已创建新的模拟面试会话。");
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

  return (
    <PageShell className="gap-6">
      <PageHeader
        description="基于当前用户自己的岗位 JD 和优化简历进入真实问答训练。"
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
              description="先从专属简历进入，这里会保留当前用户自己的训练记录。"
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
                      模拟面试 · {getSessionStatusLabel(session.status)}
                    </p>
                    <p className="mt-2 text-sm leading-relaxed text-[#1C1C1C]/60">
                      简历 v{session.source_resume_version} / 岗位 v
                      {session.source_job_version}
                    </p>
                    <p className="mt-1 text-xs text-[#1C1C1C]/45">
                      {formatDate(session.created_at)}
                    </p>
                    {session.current_turn ? (
                      <p className="mt-3 line-clamp-2 text-sm leading-relaxed text-[#1C1C1C]/60">
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
            description="先从专属简历生成优化简历，再创建一场训练。"
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
                    className="border-b border-[#1C1C1C]/20 bg-white px-4 py-2 text-sm font-medium text-[#1C1C1C] transition-colors hover:bg-[#1C1C1C]/5"
                    disabled={isFinishing}
                    onClick={() => void handleFinishSession()}
                    type="button"
                    variant="secondary"
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
