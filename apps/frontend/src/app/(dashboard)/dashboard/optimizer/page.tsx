"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { ArrowUpRight, CheckCircle2, Download, Sparkles, WandSparkles } from "lucide-react";

import { useAuth } from "@/components/auth-provider";
import {
  PageEmptyState,
  PageErrorState,
  PageLoadingState,
} from "@/components/page-state";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { ApiError } from "@/lib/api/client";
import {
  applyResumeOptimizationSession,
  createResumeOptimizationSession,
  downloadResumeOptimizationMarkdown,
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

function getMissingInfoQuestions(
  tailoringPlanSnapshot: Record<string, unknown>
): Array<{ field: string; question: string }> {
  const items = tailoringPlanSnapshot.missing_info_questions;
  if (!Array.isArray(items)) {
    return [];
  }

  return items.flatMap((item) => {
    if (!item || typeof item !== "object") {
      return [];
    }
    const field = "field" in item && typeof item.field === "string" ? item.field : "";
    const question =
      "question" in item && typeof item.question === "string" ? item.question : "";
    if (!question) {
      return [];
    }
    return [{ field, question }];
  });
}

function PaperSection({
  title,
  eyebrow,
  accentClassName = "bg-[#2f55d4]",
  children,
}: {
  title: string;
  eyebrow?: string;
  accentClassName?: string;
  children: React.ReactNode;
}) {
  return (
    <section className="border-b border-[#1C1C1C]/10 bg-[#F9F8F6]">
      <div className="border-b border-[#1C1C1C]/10 px-5 py-4 sm:px-6">
        {eyebrow ? (
          <div className="mb-3 flex items-center gap-3">
            <span className={`size-2.5 ${accentClassName}`} />
            <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[#1C1C1C]/60">
              {eyebrow}
            </p>
          </div>
        ) : null}
        <h2 className="text-xl font-semibold tracking-tight text-[#1C1C1C]">
          {title}
        </h2>
      </div>
      <div className="px-5 py-5 sm:px-6">{children}</div>
    </section>
  );
}

function PaperTextarea(
  props: React.TextareaHTMLAttributes<HTMLTextAreaElement>,
) {
  return (
    <textarea
      {...props}
      className={`min-h-[96px] w-full border-b border-[#1C1C1C]/20 bg-transparent px-4 py-3 text-sm leading-relaxed text-[#1C1C1C] outline-none placeholder:text-[#1C1C1C]/40 ${props.className ?? ""}`}
    />
  );
}

function PaperCheckbox({
  checked,
  onChange,
  label,
}: {
  checked: boolean;
  onChange: (checked: boolean) => void;
  label: string;
}) {
  return (
    <label className="flex cursor-pointer items-center gap-3">
      <input
        checked={checked}
        className="size-5 cursor-pointer accent-[#2f55d4]"
        onChange={(e) => onChange(e.target.checked)}
        type="checkbox"
      />
      <span className="text-sm text-black/70">{label}</span>
    </label>
  );
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
  const [isDownloading, setIsDownloading] = useState(false);
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
      <div className="space-y-6">
        <PageEmptyState
          title="缺少岗位上下文"
          description="请先从岗位工作台进入简历优化，这里不会脱离岗位快照单独开工。"
        />
        <Button
          asChild
          className="border-b border-[#1C1C1C]/20 bg-white px-5 py-3 text-sm font-medium text-[#1C1C1C] transition-colors hover:bg-[#1C1C1C]/5"
          type="button"
        >
          <Link href="/dashboard/jobs">
            返回岗位工作台
            <ArrowUpRight className="ml-2 size-4" />
          </Link>
        </Button>
      </div>
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

  const missingInfoQuestions = getMissingInfoQuestions(
    session.tailoring_plan_snapshot
  );

  async function handleGenerateSuggestions() {
    if (!token || !session) {
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
    if (!token || !session) {
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
    if (!token || !session) {
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

  async function handleDownloadMarkdown() {
    if (!token || !session) {
      return;
    }

    setIsDownloading(true);
    setPageError("");
    setStatusMessage("");

    try {
      const result = await downloadResumeOptimizationMarkdown(token, session.id);
      const objectUrl = window.URL.createObjectURL(result.blob);
      const link = document.createElement("a");
      link.href = objectUrl;
      link.download =
        result.fileName || session.downloadable_file_name || "optimized_resume.md";
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(objectUrl);
      setStatusMessage("Markdown 已下载，可直接用于投递或复盘。");
    } catch (error) {
      setPageError(getErrorMessage(error));
    } finally {
      setIsDownloading(false);
    }
  }

  return (
    <div className="space-y-6">
      <header className="border-b border-[#1C1C1C]/10 bg-[#F9F8F6]">
        <div className="flex flex-col gap-6 px-6 py-6 sm:px-8 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <div className="inline-flex items-center border border-[#1C1C1C]/10 bg-white px-5 py-3">
              <span className="mr-4 text-2xl leading-none text-[#1C1C1C]">
                *
              </span>
              <span className="text-[1.55rem] font-semibold uppercase tracking-tight text-[#1C1C1C] sm:text-[1.8rem]">
                Resume Optimizer
              </span>
            </div>

            <div className="mt-6">
              <h1 className="text-3xl font-semibold tracking-tight text-[#1C1C1C] sm:text-4xl">
                简历优化
              </h1>
            </div>

            <p className="mt-5 max-w-3xl text-base leading-relaxed text-[#1C1C1C]/60 sm:text-[1.05rem]">
              基于匹配报告生成改写草案，确认后应用到结构化简历。
            </p>
          </div>

          <Button
            asChild
            className="border-b border-[#1C1C1C]/20 bg-white px-5 py-3 text-sm font-medium text-[#1C1C1C] transition-colors hover:bg-[#1C1C1C]/5"
            type="button"
          >
            <Link href={`/dashboard/jobs?jobId=${session.jd_id}&staleHint=1`}>
              返回岗位工作台
              <ArrowUpRight className="ml-2 size-4" />
            </Link>
          </Button>
        </div>
      </header>

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

      {session.is_stale ? (
        <Alert className="border border-[#1C1C1C]/10 bg-[#F9F8F6] text-[#1C1C1C]">
          <AlertTitle className="text-base font-semibold tracking-tight text-[#1C1C1C]">
            当前岗位快照已过期
          </AlertTitle>
          <AlertDescription className="text-sm leading-7 text-black/72">
            这份优化会话基于旧的匹配结果。建议回到岗位工作台重新匹配后，再继续编辑。
          </AlertDescription>
        </Alert>
      ) : null}

      <section className="grid gap-6 lg:grid-cols-[300px_minmax(0,1fr)_280px]">
        <PaperSection title="任务清单" eyebrow="Task List">
          <div className="space-y-4">
            <div>
              <p className="text-[11px] font-bold uppercase tracking-[0.18em] text-black/45">
                必须补证据
              </p>
              <p className="mt-2 text-sm leading-7 text-black/70">
                {session.optimizer_context.must_add_evidence.join("、") || "暂无"}
              </p>
            </div>
            <div className="space-y-3">
              {selectedTasks.map((task) => (
                <div
                  className="border border-[#1C1C1C]/10 bg-white p-4"
                  key={task.key}
                >
                  <PaperCheckbox
                    checked={task.selected}
                    label=""
                    onChange={(checked) =>
                      setSelectedTasks((current) =>
                        current.map((item) =>
                          item.key === task.key
                            ? { ...item, selected: checked }
                            : item
                        )
                      )
                    }
                  />
                  <div className="mt-2">
                    <p className="text-sm font-semibold text-black">
                      P{task.priority} · {task.title}
                    </p>
                    <p className="mt-1 text-sm leading-6 text-black/70">
                      {task.instruction}
                    </p>
                  </div>
                </div>
              ))}
              {selectedTasks.length === 0 ? (
                <p className="text-sm text-black/50">当前岗位快照还没有改写任务。</p>
              ) : null}
            </div>
          </div>
        </PaperSection>

        <div className="space-y-5">
          {missingInfoQuestions.length > 0 ? (
            <PaperSection title="先补这些事实" eyebrow="Missing Info" accentClassName="bg-[#1C1C1C]">
              <div className="space-y-3">
                {missingInfoQuestions.map((item, index) => (
                  <div
                    className="border border-[#1C1C1C]/10 bg-white px-4 py-4"
                    key={`${item.field}-${index}`}
                  >
                    <p className="text-sm leading-relaxed text-[#1C1C1C]">{item.question}</p>
                  </div>
                ))}
              </div>
            </PaperSection>
          ) : null}
          {Object.values(draftSections).map((section) => (
            <PaperSection
              key={section.key}
              title={section.label}
              eyebrow={section.selected ? "已选中" : "未选中"}
              accentClassName={section.selected ? "bg-[#10bf7a]" : "bg-[#f13798]"}
            >
              <div className="space-y-4">
                <PaperCheckbox
                  checked={section.selected}
                  label="应用此区块"
                  onChange={(checked) =>
                    setDraftSections((current) => ({
                      ...current,
                      [section.key]: {
                        ...current[section.key],
                        selected: checked,
                      },
                    }))
                  }
                />
                <div>
                  <p className="mb-2 text-[11px] font-bold uppercase tracking-[0.18em] text-black/45">
                    当前内容
                  </p>
                  <PaperTextarea
                    value={section.original_text}
                    onChange={(event) =>
                      setDraftSections((current) => ({
                        ...current,
                        [section.key]: {
                          ...current[section.key],
                          original_text: event.target.value,
                        },
                      }))
                    }
                  />
                </div>
                <div>
                  <p className="mb-2 text-[11px] font-bold uppercase tracking-[0.18em] text-black/45">
                    建议草案
                  </p>
                  <PaperTextarea
                    className="min-h-[144px]"
                    value={section.suggested_text}
                    onChange={(event) =>
                      setDraftSections((current) => ({
                        ...current,
                        [section.key]: {
                          ...current[section.key],
                          suggested_text: event.target.value,
                        },
                      }))
                    }
                  />
                </div>
              </div>
            </PaperSection>
          ))}
        </div>

        <PaperSection title="应用与回流" eyebrow="Apply & Feedback" accentClassName="bg-[#1C1C1C]">
          <div className="space-y-4">
            <div className="border border-[#1C1C1C]/10 bg-white p-4">
              <p className="text-sm font-medium text-[#1C1C1C]">
                {session.optimizer_context.job_title}
              </p>
              <p className="mt-2 text-sm leading-relaxed text-[#1C1C1C]/60">
                {session.optimizer_context.company || "未填写公司"} ·{" "}
                {getFitBandLabel(session.optimizer_context.fit_band)}
              </p>
              <p className="mt-1 text-sm text-[#1C1C1C]/40">
                简历 v{session.source_resume_version} / 岗位 v{session.source_job_version}
              </p>
            </div>
            <div className="border border-[#1C1C1C]/10 bg-white p-4">
              <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[#1C1C1C]/60">
                岗位摘要
              </p>
              <p className="mt-2 text-sm leading-relaxed text-[#1C1C1C]/60">
                {session.optimizer_context.target_summary || "暂无"}
              </p>
            </div>
            <div className="border border-[#1C1C1C]/10 bg-white p-4">
              <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[#1C1C1C]/60">
                原始短板
              </p>
              <p className="mt-2 text-sm leading-relaxed text-[#1C1C1C]/60">
                {session.optimizer_context.gap_summary.join("、") || "暂无"}
              </p>
            </div>
            <div className="space-y-3">
              <Button
                className="w-full border-b border-[#1C1C1C]/20 bg-[#1C1C1C] px-5 py-3 text-sm font-medium text-white transition-colors hover:bg-[#1C1C1C]/90 disabled:cursor-not-allowed disabled:opacity-60"
                disabled={isGenerating}
                onClick={handleGenerateSuggestions}
                type="button"
              >
                {isGenerating ? "生成中..." : "生成/刷新草案"}
                <WandSparkles className="ml-2 size-4" />
              </Button>
              <Button
                className="w-full border-b border-[#1C1C1C]/20 bg-white px-5 py-3 text-sm font-medium text-[#1C1C1C] transition-colors hover:bg-[#1C1C1C]/5 disabled:cursor-not-allowed disabled:opacity-60"
                disabled={isSaving}
                onClick={handleSaveDraft}
                type="button"
              >
                {isSaving ? "保存中..." : "保存草案"}
              </Button>
              <Button
                className="w-full border-b border-[#1C1C1C]/20 bg-white px-5 py-3 text-sm font-medium text-[#1C1C1C] transition-colors hover:bg-[#1C1C1C]/5 disabled:cursor-not-allowed disabled:opacity-60"
                disabled={!session.has_downloadable_markdown || isDownloading}
                onClick={handleDownloadMarkdown}
                type="button"
              >
                {isDownloading ? "下载中..." : "下载 Markdown"}
                <Download className="ml-2 size-4" />
              </Button>
              <Button
                className="w-full border-b border-[#1C1C1C]/20 bg-[#1C1C1C] px-5 py-3 text-sm font-medium text-white transition-colors hover:bg-[#1C1C1C]/90 disabled:cursor-not-allowed disabled:opacity-60"
                disabled={isApplying || session.is_stale}
                onClick={handleApply}
                type="button"
              >
                {isApplying ? "应用中..." : "应用到当前简历"}
                <CheckCircle2 className="ml-2 size-4" />
              </Button>
              <Button
                className="w-full border-b border-[#1C1C1C]/20 bg-white px-5 py-3 text-sm font-medium text-[#1C1C1C] transition-colors hover:bg-[#1C1C1C]/5 disabled:cursor-not-allowed disabled:opacity-60"
                disabled={session.is_stale}
                onClick={() =>
                  router.push(
                    `/dashboard/interviews?reportId=${session.match_report_id}&optimizationSessionId=${session.id}&jobId=${session.jd_id}`,
                  )
                }
                type="button"
              >
                去模拟面试
                <Sparkles className="ml-2 size-4" />
              </Button>
              {statusMessage ? (
                <p className="text-sm leading-relaxed text-[#1C1C1C]/60">{statusMessage}</p>
              ) : null}
            </div>
            {session.applied_resume_version ? (
              <p className="text-sm text-[#1C1C1C]/50">
                最近已应用到简历 v{session.applied_resume_version}
              </p>
            ) : null}
          </div>
        </PaperSection>
      </section>
    </div>
  );
}
