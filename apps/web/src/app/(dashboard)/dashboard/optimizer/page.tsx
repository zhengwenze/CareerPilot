"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { ArrowUpRight, CheckCircle2, WandSparkles } from "lucide-react";

import { useAuth } from "@/components/auth-provider";
import {
  PageEmptyState,
  PageErrorState,
  PageLoadingState,
} from "@/components/page-state";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { ApiError } from "@/lib/api/client";
import {
  applyResumeOptimizationSession,
  createResumeOptimizationSession,
  fetchResumeOptimizationSession,
  generateResumeOptimizationSuggestions,
  updateResumeOptimizationSession,
  type ResumeOptimizationSectionDraft,
  type ResumeOptimizationSessionRecord,
  type ResumeOptimizationTaskState,
} from "@/lib/api/modules/optimizer";

function getErrorMessage(error: unknown) {
  if (error instanceof ApiError) {
    return error.message;
  }
  if (error instanceof Error) {
    return error.message;
  }
  return "操作失败，请稍后重试。";
}

function getFitBandLabel(value: string) {
  const labels: Record<string, string> = {
    excellent: "强适配",
    strong: "较强适配",
    partial: "部分适配",
    weak: "低适配",
    unknown: "待生成",
  };
  return labels[value] ?? value;
}

export default function DashboardOptimizerPage() {
  const { token } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();
  const reportId = searchParams.get("reportId");
  const initialSessionId = searchParams.get("sessionId");

  const [session, setSession] = useState<ResumeOptimizationSessionRecord | null>(
    null
  );
  const [draftSections, setDraftSections] = useState<
    Record<string, ResumeOptimizationSectionDraft>
  >({});
  const [selectedTasks, setSelectedTasks] = useState<
    ResumeOptimizationTaskState[]
  >([]);
  const [isPageLoading, setIsPageLoading] = useState(true);
  const [isGenerating, setIsGenerating] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [isApplying, setIsApplying] = useState(false);
  const [pageError, setPageError] = useState("");
  const [statusMessage, setStatusMessage] = useState("");

  useEffect(() => {
    if (!token) {
      return;
    }
    if (!reportId && !initialSessionId) {
      setIsPageLoading(false);
      return;
    }

    const accessToken = token;
    let cancelled = false;

    async function bootstrap() {
      setIsPageLoading(true);
      setPageError("");

      try {
        const nextSession = initialSessionId
          ? await fetchResumeOptimizationSession(accessToken, initialSessionId)
          : await createResumeOptimizationSession(accessToken, reportId!);

        if (cancelled) {
          return;
        }

        setSession(nextSession);
        setDraftSections(nextSession.draft_sections);
        setSelectedTasks(nextSession.selected_tasks);
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
  }, [initialSessionId, reportId, token]);

  if (!token) {
    return null;
  }

  if (isPageLoading) {
    return (
      <PageLoadingState
        title="正在加载简历优化"
        description="我们正在读取岗位快照、定制任务和当前简历草案。"
      />
    );
  }

  if (!reportId && !initialSessionId) {
    return (
      <PageEmptyState
        title="缺少岗位上下文"
        description="请先从岗位工作台进入简历优化，这里不会脱离岗位快照单独开工。"
      />
    );
  }

  if (!session) {
    return (
      <PageErrorState
        title="简历优化加载失败"
        description={pageError || "未能加载优化会话。"}
        actionLabel="返回岗位工作台"
        onAction={() => router.push("/dashboard/jobs")}
      />
    );
  }

  async function handleGenerateSuggestions() {
    if (!token) {
      return;
    }
    setIsGenerating(true);
    setPageError("");
    setStatusMessage("");
    try {
      const saved = await updateResumeOptimizationSession(token, session.id, {
        draft_sections: draftSections,
        selected_tasks: selectedTasks,
      });
      setSession(saved);
      const nextSession = await generateResumeOptimizationSuggestions(token, session.id);
      setSession(nextSession);
      setDraftSections(nextSession.draft_sections);
      setSelectedTasks(nextSession.selected_tasks);
      setStatusMessage("已生成新的改写草案。");
    } catch (error) {
      setPageError(getErrorMessage(error));
    } finally {
      setIsGenerating(false);
    }
  }

  async function handleSaveDraft() {
    if (!token) {
      return;
    }
    setIsSaving(true);
    setPageError("");
    setStatusMessage("");
    try {
      const nextSession = await updateResumeOptimizationSession(token, session.id, {
        draft_sections: draftSections,
        selected_tasks: selectedTasks,
      });
      setSession(nextSession);
      setStatusMessage("草案已保存。");
    } catch (error) {
      setPageError(getErrorMessage(error));
    } finally {
      setIsSaving(false);
    }
  }

  async function handleApply() {
    if (!token) {
      return;
    }
    setIsApplying(true);
    setPageError("");
    setStatusMessage("");
    try {
      const result = await applyResumeOptimizationSession(token, session.id);
      const nextSession = await fetchResumeOptimizationSession(token, session.id);
      setSession(nextSession);
      setDraftSections(nextSession.draft_sections);
      setSelectedTasks(nextSession.selected_tasks);
      setStatusMessage(
        `已应用到当前简历，简历版本升级到 v${result.applied_resume_version}。`
      );
    } catch (error) {
      setPageError(getErrorMessage(error));
    } finally {
      setIsApplying(false);
    }
  }

  return (
    <div className="space-y-8">
      {pageError ? (
        <Alert className="rounded-[1.5rem] border-[#ff3b30]/20 bg-[#fff5f5]">
          <AlertTitle className="text-black">操作失败</AlertTitle>
          <AlertDescription className="text-black/72">{pageError}</AlertDescription>
        </Alert>
      ) : null}

      {session.is_stale ? (
        <Alert className="rounded-[1.5rem] border-[#ff9500]/20 bg-[#FFF7E6]">
          <AlertTitle className="text-black">当前岗位快照已过期</AlertTitle>
          <AlertDescription className="text-black/72">
            这份优化会话基于旧的匹配结果。建议回到岗位工作台重新匹配后，再继续编辑。
          </AlertDescription>
        </Alert>
      ) : null}

      <section className="grid gap-5 xl:grid-cols-[320px_minmax(0,1fr)_320px]">
        <Card className="rounded-[2rem] border border-black/10 bg-[#f5f5f7] py-0 shadow-none">
          <CardHeader className="px-6 py-6">
            <CardTitle className="text-xl font-semibold text-black">任务清单</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4 px-6 pb-6">
            <div>
              <p className="text-xs font-medium tracking-[0.12em] text-black/45 uppercase">
                必须补证据
              </p>
              <p className="mt-2 text-sm leading-7 text-black/68">
                {session.optimizer_context.must_add_evidence.join("、") || "暂无"}
              </p>
            </div>
            <div className="space-y-3">
              {selectedTasks.map((task) => (
                <label
                  className="block rounded-[1.5rem] border border-black/10 bg-white px-4 py-4"
                  key={task.key}
                >
                  <div className="flex items-start gap-3">
                    <input
                      checked={task.selected}
                      className="mt-1"
                      onChange={(event) =>
                        setSelectedTasks((current) =>
                          current.map((item) =>
                            item.key === task.key
                              ? { ...item, selected: event.target.checked }
                              : item
                          )
                        )
                      }
                      type="checkbox"
                    />
                    <div>
                      <p className="text-sm font-medium text-black">
                        P{task.priority} · {task.title}
                      </p>
                      <p className="mt-2 text-sm leading-7 text-black/68">
                        {task.instruction}
                      </p>
                    </div>
                  </div>
                </label>
              ))}
              {selectedTasks.length === 0 ? (
                <p className="text-sm text-black/58">当前岗位快照还没有改写任务。</p>
              ) : null}
            </div>
          </CardContent>
        </Card>

        <div className="space-y-5">
          {Object.values(draftSections).map((section) => (
            <Card
              className="rounded-[2rem] border border-black/10 bg-white py-0 shadow-[0_18px_48px_rgba(0,0,0,0.05)]"
              key={section.key}
            >
              <CardHeader className="space-y-4 px-6 py-6">
                <div className="flex items-center justify-between gap-3">
                  <CardTitle className="text-2xl font-semibold tracking-[-0.04em] text-black">
                    {section.label}
                  </CardTitle>
                  <label className="text-sm text-black/68">
                    <input
                      checked={section.selected}
                      className="mr-2"
                      onChange={(event) =>
                        setDraftSections((current) => ({
                          ...current,
                          [section.key]: {
                            ...current[section.key],
                            selected: event.target.checked,
                          },
                        }))
                      }
                      type="checkbox"
                    />
                    应用此区块
                  </label>
                </div>
              </CardHeader>
              <CardContent className="space-y-4 px-6 pb-6">
                <div>
                  <p className="text-xs font-medium tracking-[0.12em] text-black/45 uppercase">
                    当前内容
                  </p>
                  <Textarea
                    className="mt-2 min-h-[96px] rounded-[1.75rem] border-black/10 bg-[#f5f5f7] text-black"
                    onChange={(event) =>
                      setDraftSections((current) => ({
                        ...current,
                        [section.key]: {
                          ...current[section.key],
                          original_text: event.target.value,
                        },
                      }))
                    }
                    value={section.original_text}
                  />
                </div>
                <div>
                  <p className="text-xs font-medium tracking-[0.12em] text-black/45 uppercase">
                    建议草案
                  </p>
                  <Textarea
                    className="mt-2 min-h-[144px] rounded-[1.75rem] border-black/10 bg-[#F5F9FF] text-black"
                    onChange={(event) =>
                      setDraftSections((current) => ({
                        ...current,
                        [section.key]: {
                          ...current[section.key],
                          suggested_text: event.target.value,
                        },
                      }))
                    }
                    value={section.suggested_text}
                  />
                </div>
              </CardContent>
            </Card>
          ))}
        </div>

        <Card className="rounded-[2rem] border border-black/10 bg-[#f5f5f7] py-0 shadow-none">
          <CardHeader className="space-y-3 px-6 py-6">
            <CardTitle className="text-2xl font-semibold tracking-[-0.04em] text-black">
              应用与回流
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4 px-6 pb-6">
            <div className="rounded-[1.5rem] border border-black/10 bg-white px-4 py-4">
              <p className="text-sm font-medium text-black">
                {session.optimizer_context.job_title}
              </p>
              <p className="mt-2 text-sm leading-7 text-black/68">
                {session.optimizer_context.company || "未填写公司"} ·{" "}
                {getFitBandLabel(session.optimizer_context.fit_band)}
              </p>
              <p className="text-sm leading-7 text-black/68">
                简历 v{session.source_resume_version} / 岗位 v{session.source_job_version}
              </p>
            </div>
            <div className="rounded-[1.5rem] border border-black/10 bg-white px-4 py-4">
              <p className="text-sm font-medium text-black">岗位摘要</p>
              <p className="mt-2 text-sm leading-7 text-black/68">
                {session.optimizer_context.target_summary || "暂无"}
              </p>
            </div>
            <div className="rounded-[1.5rem] border border-black/10 bg-white px-4 py-4">
              <p className="text-sm font-medium text-black">原始短板</p>
              <p className="mt-2 text-sm leading-7 text-black/68">
                {session.optimizer_context.gap_summary.join("、") || "暂无"}
              </p>
            </div>
            <div className="space-y-3">
              <Button
                className="w-full rounded-full bg-[#0071E3] text-white hover:bg-[#0077ED]"
                disabled={isGenerating}
                onClick={handleGenerateSuggestions}
                type="button"
              >
                {isGenerating ? "生成中..." : "生成/刷新草案"}
                <WandSparkles className="size-4" />
              </Button>
              <Button
                className="w-full rounded-full border-black/10 bg-white text-black hover:bg-[#f5f5f7]"
                disabled={isSaving}
                onClick={handleSaveDraft}
                type="button"
                variant="outline"
              >
                {isSaving ? "保存中..." : "保存草案"}
              </Button>
              <Button
                className="w-full rounded-full"
                disabled={isApplying || session.is_stale}
                onClick={handleApply}
                type="button"
              >
                {isApplying ? "应用中..." : "应用到当前简历"}
                <CheckCircle2 className="size-4" />
              </Button>
              {statusMessage ? (
                <p className="text-sm leading-7 text-black/62">{statusMessage}</p>
              ) : null}
            </div>
            <Button
              asChild
              className="w-full rounded-full border-black/10 bg-white text-black hover:bg-[#f5f5f7]"
              type="button"
              variant="outline"
            >
              <Link href={`/dashboard/jobs?jobId=${session.jd_id}&staleHint=1`}>
                返回岗位工作台
                <ArrowUpRight className="size-4" />
              </Link>
            </Button>
            {session.applied_resume_version ? (
              <p className="text-sm text-black/68">
                最近已应用到简历 v{session.applied_resume_version}
              </p>
            ) : null}
          </CardContent>
        </Card>
      </section>
    </div>
  );
}
