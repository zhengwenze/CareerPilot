"use client";

import Link from "next/link";
import {
  useEffect,
  useRef,
  useState,
  type ChangeEvent,
  type ReactNode,
} from "react";
import { useRouter, useSearchParams } from "next/navigation";
import {
  ArrowUpRight,
  Download,
  FileUp,
  RefreshCcw,
  Sparkles,
} from "lucide-react";

import { useAuth } from "@/components/auth-provider";
import {
  PaperInput,
  PaperTextarea,
} from "@/components/brutalist/form-controls";
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
import { cn } from "@/lib/utils";
import {
  createEmptyJobDraft,
  toJobDraft,
  type JobDraft,
} from "@/lib/api/modules/jobs";
import {
  downloadTailoredResumeMarkdown,
  fetchTailoredResumeWorkflows,
  fetchResumeDetail,
  fetchResumeList,
  generateTailoredResume,
  type ResumeRecord,
  uploadPrimaryResume,
  type TailoredResumeWorkflowRecord,
} from "@/lib/api/modules/resume";

const POLL_INTERVAL_MS = 2500;

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

function getResumeStatusLabel(status: string) {
  const labels: Record<string, string> = {
    pending: "待解析",
    processing: "解析中",
    success: "已完成",
    failed: "解析失败",
  };
  return labels[status] ?? status;
}

function getFitBandLabel(value: string) {
  const labels: Record<string, string> = {
    excellent: "强适配",
    strong: "较强适配",
    partial: "部分适配",
    weak: "低适配",
    unknown: "待评估",
  };
  return labels[value] ?? value;
}

function getGenerateBlockedReason(
  selectedResume: ResumeRecord | null,
  jobDraft: JobDraft,
) {
  if (!selectedResume) {
    return "请先选择一份主简历。";
  }
  if (selectedResume.parse_status !== "success") {
    return "主简历尚未解析完成，暂时无法生成专属简历。";
  }
  if (!jobDraft.title.trim()) {
    return "请先填写目标岗位标题。";
  }
  if (!jobDraft.jd_text.trim()) {
    return "请先粘贴目标岗位 JD。";
  }
  return null;
}

function upsertResume(current: ResumeRecord[], next: ResumeRecord) {
  const existingIndex = current.findIndex((item) => item.id === next.id);
  if (existingIndex === -1) {
    return [next, ...current];
  }

  return current.map((item) => (item.id === next.id ? next : item));
}

function upsertWorkflow(
  current: TailoredResumeWorkflowRecord[],
  next: TailoredResumeWorkflowRecord,
) {
  const filtered = current.filter(
    (item) =>
      item.tailored_resume.session_id !== next.tailored_resume.session_id,
  );
  return [next, ...filtered];
}

function ResumeMarkdownPreview({ markdown }: { markdown: string }) {
  const lines = markdown.split("\n");
  const nodes: ReactNode[] = [];
  let listItems: string[] = [];

  const flushList = (key: string) => {
    if (!listItems.length) {
      return;
    }
    nodes.push(
      <ul
        key={key}
        className="my-3 list-disc space-y-2 pl-5 text-sm leading-7 text-[#1C1C1C]"
      >
        {listItems.map((item, index) => (
          <li key={`${key}-${index}`}>{item}</li>
        ))}
      </ul>,
    );
    listItems = [];
  };

  lines.forEach((rawLine, index) => {
    const line = rawLine.trim();
    if (!line) {
      flushList(`list-${index}`);
      return;
    }

    if (line.startsWith("- ")) {
      listItems.push(line.slice(2).trim());
      return;
    }

    flushList(`list-${index}`);

    if (line.startsWith("### ")) {
      nodes.push(
        <h3
          key={`h3-${index}`}
          className="mt-5 text-base font-semibold text-[#1C1C1C]"
        >
          {line.slice(4)}
        </h3>,
      );
      return;
    }

    if (line.startsWith("## ")) {
      nodes.push(
        <h2
          key={`h2-${index}`}
          className="mt-6 border-t border-[#1C1C1C]/10 pt-6 text-lg font-semibold text-[#1C1C1C]"
        >
          {line.slice(3)}
        </h2>,
      );
      return;
    }

    if (line.startsWith("# ")) {
      nodes.push(
        <h1
          key={`h1-${index}`}
          className="text-2xl font-semibold text-[#1C1C1C]"
        >
          {line.slice(2)}
        </h1>,
      );
      return;
    }

    nodes.push(
      <p
        key={`p-${index}`}
        className={cn(
          "text-sm leading-7 text-[#1C1C1C]/80",
          /^\d{4}[./-]\d{1,2}\s*-\s*/.test(line) ||
            /^\d{4}\s*-\s*\d{4}/.test(line)
            ? "font-medium text-[#1C1C1C]"
            : "",
        )}
      >
        {line}
      </p>,
    );
  });

  flushList("list-final");

  return <div className="space-y-1">{nodes}</div>;
}

export default function DashboardResumePage() {
  const { token } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();
  const preferredWorkflowId = searchParams.get("workflowId");

  const [resumes, setResumes] = useState<ResumeRecord[]>([]);
  const [workflows, setWorkflows] = useState<TailoredResumeWorkflowRecord[]>(
    [],
  );
  const [selectedResumeId, setSelectedResumeId] = useState<string | null>(null);
  const [selectedWorkflowId, setSelectedWorkflowId] = useState<string | null>(
    null,
  );
  const [jobDraft, setJobDraft] = useState<JobDraft>(createEmptyJobDraft());
  const [pageError, setPageError] = useState("");
  const [statusMessage, setStatusMessage] = useState("");
  const [isPageLoading, setIsPageLoading] = useState(true);
  const [isUploading, setIsUploading] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [isDownloading, setIsDownloading] = useState(false);
  const uploadInputRef = useRef<HTMLInputElement | null>(null);
  const selectedResume =
    resumes.find((item) => item.id === selectedResumeId) ?? null;
  const generateBlockedReason = getGenerateBlockedReason(
    selectedResume,
    jobDraft,
  );
  const selectedWorkflow =
    workflows.find(
      (item) => item.tailored_resume.session_id === selectedWorkflowId,
    ) ?? null;
  const selectedTailoredDocument = selectedWorkflow?.tailored_resume.document;
  const selectedTailoredMarkdown =
    selectedTailoredDocument?.markdown?.trim() ?? "";
  const canonicalResumeMd =
    selectedResume?.parse_artifacts_json?.canonical_resume_md?.trim() ?? "";
  const rawResumeText = selectedResume?.raw_text?.trim() ?? "";

  useEffect(() => {
    if (!token) {
      return;
    }

    const accessToken = token;
    let cancelled = false;

    async function bootstrap() {
      setIsPageLoading(true);
      setPageError("");

      try {
        const [resumeResult, workflowResult] = await Promise.allSettled([
          fetchResumeList(accessToken),
          fetchTailoredResumeWorkflows(accessToken),
        ]);
        if (cancelled) {
          return;
        }

        const nextResumes =
          resumeResult.status === "fulfilled" ? resumeResult.value : [];
        const nextWorkflows =
          workflowResult.status === "fulfilled" ? workflowResult.value : [];

        if (resumeResult.status === "rejected") {
          throw resumeResult.reason;
        }

        if (workflowResult.status === "rejected") {
          setPageError(
            `专属简历历史加载失败：${getErrorMessage(workflowResult.reason)}`,
          );
        }

        setResumes(nextResumes);
        setWorkflows(nextWorkflows);

        const nextWorkflow =
          (preferredWorkflowId &&
            nextWorkflows.find(
              (item) => item.tailored_resume.session_id === preferredWorkflowId,
            )) ||
          nextWorkflows[0] ||
          null;

        if (nextWorkflow) {
          setSelectedWorkflowId(nextWorkflow.tailored_resume.session_id);
          setSelectedResumeId(nextWorkflow.resume.id);
          setJobDraft(toJobDraft(nextWorkflow.target_job));
          return;
        }

        const nextResume =
          nextResumes.find((item) => item.parse_status === "success") ??
          nextResumes[0] ??
          null;
        setSelectedWorkflowId(null);
        setSelectedResumeId(nextResume?.id ?? null);
        setJobDraft(createEmptyJobDraft());
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
  }, [preferredWorkflowId, token]);

  useEffect(() => {
    if (!token || !selectedResumeId || !selectedResume) {
      return;
    }
    if (!["pending", "processing"].includes(selectedResume.parse_status)) {
      return;
    }

    const accessToken = token;
    let cancelled = false;
    const timer = window.setTimeout(async () => {
      try {
        const detail = await fetchResumeDetail(accessToken, selectedResumeId);
        if (cancelled) {
          return;
        }
        setResumes((current) => upsertResume(current, detail));
        if (detail.parse_status === "success") {
          setStatusMessage("主简历解析完成，可以开始生成专属简历。");
        }
      } catch (error) {
        if (!cancelled) {
          setPageError(getErrorMessage(error));
        }
      }
    }, POLL_INTERVAL_MS);

    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [selectedResume, selectedResumeId, token]);

  if (!token) {
    return null;
  }

  if (isPageLoading) {
    return (
      <PageLoadingState
        title="正在加载专属简历"
        description="我们正在同步主简历、目标岗位历史和最近生成的专属简历成品。"
      />
    );
  }

  if (pageError && resumes.length === 0 && workflows.length === 0) {
    return (
      <PageErrorState
        title="专属简历加载失败"
        description={pageError}
        actionLabel="重新进入"
        onAction={() => router.push("/dashboard/resume")}
      />
    );
  }

  async function handleUploadResume(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!token || !file) {
      return;
    }

    setIsUploading(true);
    setPageError("");
    setStatusMessage("");

    try {
      const uploaded = await uploadPrimaryResume(token, file);
      setResumes((current) => upsertResume(current, uploaded));
      setSelectedResumeId(uploaded.id);
      setStatusMessage("简历已上传，正在解析并生成规范化 Markdown 简历。");
    } catch (error) {
      setPageError(getErrorMessage(error));
    } finally {
      setIsUploading(false);
    }
  }

  function handleOpenUploadDialog() {
    if (isUploading) {
      return;
    }

    uploadInputRef.current?.click();
  }

  async function handleGenerateTailoredResume() {
    if (!token || !selectedResumeId || generateBlockedReason) {
      setPageError(generateBlockedReason ?? "请先选择一份主简历。");
      return;
    }

    setIsGenerating(true);
    setPageError("");
    setStatusMessage("");

    try {
      const workflow = await generateTailoredResume(token, {
        resume_id: selectedResumeId,
        job_id: selectedWorkflow?.target_job.id,
        title: jobDraft.title,
        company: jobDraft.company,
        job_city: jobDraft.job_city,
        employment_type: jobDraft.employment_type,
        source_name: jobDraft.source_name,
        source_url: jobDraft.source_url,
        priority: jobDraft.priority,
        jd_text: jobDraft.jd_text,
      });

      setWorkflows((current) => upsertWorkflow(current, workflow));
      setSelectedWorkflowId(workflow.tailored_resume.session_id);
      setSelectedResumeId(workflow.resume.id);
      setJobDraft(toJobDraft(workflow.target_job));
      router.replace(
        `/dashboard/resume?workflowId=${workflow.tailored_resume.session_id}`,
      );
      setStatusMessage("岗位定制版简历已生成，可直接下载 Markdown。");
    } catch (error) {
      setPageError(getErrorMessage(error));
    } finally {
      setIsGenerating(false);
    }
  }

  async function handleDownload() {
    if (!token || !selectedWorkflow) {
      return;
    }

    setIsDownloading(true);
    setPageError("");
    setStatusMessage("");

    try {
      const result = await downloadTailoredResumeMarkdown(
        token,
        selectedWorkflow.tailored_resume.session_id,
      );
      const objectUrl = window.URL.createObjectURL(result.blob);
      const link = document.createElement("a");
      link.href = objectUrl;
      link.download =
        result.fileName ||
        selectedWorkflow.tailored_resume.downloadable_file_name ||
        "optimized_resume.md";
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(objectUrl);
      setStatusMessage("Markdown 已下载，可直接用于投递。");
    } catch (error) {
      setPageError(getErrorMessage(error));
    } finally {
      setIsDownloading(false);
    }
  }

  function handleCreateNewTargetJob() {
    setSelectedWorkflowId(null);
    setJobDraft(createEmptyJobDraft());
    setPageError("");
    setStatusMessage("");
    router.replace("/dashboard/resume");
  }

  return (
    <PageShell className="gap-6">
      <PageHeader
        eyebrow="Tailored Resume"
        title="专属简历"
        description="上传文字 PDF 后，系统会完成规则解析、AI 审查和 Markdown 规范化，再基于这份主简历生成岗位定制版简历。"
        meta={
          <>
            <MetaChip>{resumes.length} 份主简历</MetaChip>
            <MetaChip>{workflows.length} 份专属简历</MetaChip>
          </>
        }
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

      <PaperSection
        eyebrow="Primary Resume"
        title="当前简历"
        rightSlot={
          <>
            <input
              id="resume-upload-input"
              ref={uploadInputRef}
              className="hidden"
              disabled={isUploading}
              onChange={handleUploadResume}
              type="file"
              accept=".pdf,application/pdf"
            />
            <Button
              disabled={isUploading}
              size="sm"
              type="button"
              onClick={handleOpenUploadDialog}
            >
              <FileUp className="size-4" />
              {isUploading ? "上传中" : "上传简历"}
            </Button>
            {/* <Button>重新解析</Button> */}
          </>
        }
      >
        {selectedResume ? (
          <div className="rounded-3xl border border-[#1C1C1C]/10 bg-white p-5">
            <div className="space-y-5">
              <div className="flex flex-wrap gap-2">
                <MetaChip>
                  {getResumeStatusLabel(selectedResume.parse_status)}
                </MetaChip>
                {/* <MetaChip>版本 v{selectedResume.latest_version}</MetaChip> */}
                <MetaChip>{formatDate(selectedResume.updated_at)}</MetaChip>
                <MetaChip>{selectedResume.file_name}</MetaChip>
              </div>

              <div>
                <p className="text-lg font-semibold text-[#1C1C1C]">
                  {selectedResume.structured_json?.basic_info.name ||
                    selectedResume.file_name}
                </p>
                <p className="mt-1 text-sm text-[#1C1C1C]/60">
                  当前工作流仅支持文字 PDF。上传完成后，系统会先做规则解析，再做
                  AI 审查，最后生成完整的规范化 Markdown 简历。
                </p>
              </div>

              {canonicalResumeMd ? (
                <div className="rounded-2xl border border-[#1C1C1C]/10 p-4">
                  <p className="text-sm font-semibold text-[#1C1C1C]">
                    规范化 Markdown 简历
                  </p>
                  <p className="mt-1 text-sm text-[#1C1C1C]/60">
                    这是规则解析和 AI 审查后的完整主简历成品。
                  </p>
                  <div className="mt-4 rounded-2xl border border-[#1C1C1C]/10 bg-[#FAFAF8] p-5">
                    <ResumeMarkdownPreview markdown={canonicalResumeMd} />
                  </div>
                </div>
              ) : null}

              {rawResumeText ? (
                <div className="rounded-2xl border border-[#1C1C1C]/10 p-4">
                  <p className="text-sm font-semibold text-[#1C1C1C]">
                    简历提取原文
                  </p>
                  <p className="mt-1 text-sm text-[#1C1C1C]/60">
                    原始 PDF
                    中提取到的全文内容会完整保留在这里，便于核对解析结果。
                  </p>
                  <pre className="mt-4 max-h-[420px] overflow-auto rounded-2xl border border-[#1C1C1C]/10 bg-[#FAFAF8] p-4 text-sm leading-7 text-[#1C1C1C] whitespace-pre-wrap">
                    {rawResumeText}
                  </pre>
                </div>
              ) : null}

              {!canonicalResumeMd && !rawResumeText ? (
                <div className="rounded-2xl border border-[#1C1C1C]/10 p-4 text-sm text-[#1C1C1C]/70">
                  {selectedResume.parse_status === "failed"
                    ? "这份简历暂未生成可展示内容，请检查解析错误后重新上传文字 PDF。"
                    : "正在等待解析产出完整 Markdown 与原文文本。"}
                </div>
              ) : null}

              {selectedResume.parse_error ? (
                <div className="rounded-2xl border border-[#1C1C1C]/10 p-4 text-sm text-[#1C1C1C]/70">
                  解析错误：{selectedResume.parse_error}
                </div>
              ) : null}
            </div>
          </div>
        ) : (
          <PageEmptyState
            title="请选择主简历"
            description="上传文字 PDF 后即可查看完整 Markdown 成品与提取原文。"
          />
        )}
      </PaperSection>

      <PaperSection
        eyebrow="Target Job"
        title="目标岗位"
        rightSlot={
          <div className="flex gap-2">
            <Button
              onClick={handleCreateNewTargetJob}
              size="sm"
              type="button"
              variant="secondary"
            >
              新建岗位
            </Button>
            <Button
              disabled={isGenerating || Boolean(generateBlockedReason)}
              onClick={() => void handleGenerateTailoredResume()}
              size="sm"
              type="button"
            >
              <Sparkles className="size-4" />
              {isGenerating ? "生成中" : "一键生成专属简历"}
            </Button>
          </div>
        }
      >
        <div className="space-y-4">
          {generateBlockedReason ? (
            <div className="rounded-2xl border border-[#1C1C1C]/10 bg-[#F9F8F6] px-4 py-3 text-sm text-[#1C1C1C]/70">
              {generateBlockedReason}
            </div>
          ) : null}

          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <p className="mb-2 text-sm font-medium text-[#1C1C1C]">
                岗位标题
              </p>
              <PaperInput
                value={jobDraft.title}
                onChange={(event) =>
                  setJobDraft((current) => ({
                    ...current,
                    title: event.target.value,
                  }))
                }
                placeholder="例如：增长数据分析师"
              />
            </div>
            <div>
              <p className="mb-2 text-sm font-medium text-[#1C1C1C]">
                公司名称
              </p>
              <PaperInput
                value={jobDraft.company}
                onChange={(event) =>
                  setJobDraft((current) => ({
                    ...current,
                    company: event.target.value,
                  }))
                }
                placeholder="例如：CareerPilot"
              />
            </div>
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <p className="mb-2 text-sm font-medium text-[#1C1C1C]">
                岗位地点
              </p>
              <PaperInput
                value={jobDraft.job_city}
                onChange={(event) =>
                  setJobDraft((current) => ({
                    ...current,
                    job_city: event.target.value,
                  }))
                }
                placeholder="例如：上海"
              />
            </div>
            <div>
              <p className="mb-2 text-sm font-medium text-[#1C1C1C]">
                来源链接
              </p>
              <PaperInput
                value={jobDraft.source_url}
                onChange={(event) =>
                  setJobDraft((current) => ({
                    ...current,
                    source_url: event.target.value,
                  }))
                }
                placeholder="可选"
              />
            </div>
          </div>

          <div>
            <p className="mb-2 text-sm font-medium text-[#1C1C1C]">
              目标岗位 JD
            </p>
            <PaperTextarea
              value={jobDraft.jd_text}
              onChange={(event) =>
                setJobDraft((current) => ({
                  ...current,
                  jd_text: event.target.value,
                }))
              }
              placeholder="粘贴完整 JD，系统会自动结构化并生成 match report，再产出岗位定制版简历。"
              className="min-h-[260px]"
            />
          </div>
        </div>
      </PaperSection>

      <PaperSection
        eyebrow="Tailored Resume Output"
        title="您的专属简历"
        rightSlot={
          selectedWorkflow ? (
            <div className="flex gap-2">
              <Button
                disabled={
                  isDownloading ||
                  !selectedWorkflow.tailored_resume.has_downloadable_markdown
                }
                onClick={() => void handleDownload()}
                size="sm"
                type="button"
                variant="secondary"
              >
                <Download className="size-4" />
                {isDownloading ? "下载中" : "下载 Markdown"}
              </Button>
              <Button
                disabled={isGenerating || Boolean(generateBlockedReason)}
                onClick={() => void handleGenerateTailoredResume()}
                size="sm"
                type="button"
                variant="secondary"
              >
                <RefreshCcw className="size-4" />
                重新生成
              </Button>
            </div>
          ) : null
        }
      >
        {selectedWorkflow ? (
          <div className="space-y-4">
            <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_220px]">
              <div className="rounded-3xl border border-[#1C1C1C]/10 bg-white p-5">
                <p className="text-sm font-semibold text-[#1C1C1C]">
                  {selectedWorkflow.target_job.title}
                  {selectedWorkflow.target_job.company
                    ? ` · ${selectedWorkflow.target_job.company}`
                    : ""}
                </p>
                <p className="mt-2 text-sm leading-relaxed text-[#1C1C1C]/60">
                  这是当前岗位的定制版简历成品。后台仍然会生成 match
                  report、rewrite tasks 和 fact
                  check，但它们不再作为用户主交付物展示。
                </p>
                <pre className="mt-5 overflow-x-auto rounded-2xl border border-[#1C1C1C]/10 bg-[#FAFAF8] p-4 text-sm leading-7 text-[#1C1C1C] whitespace-pre-wrap">
                  {selectedTailoredMarkdown ||
                    "这条历史记录缺少新的成品对象，请重新生成一次专属简历。"}
                </pre>
              </div>

              <div className="space-y-3">
                <div className="rounded-3xl border border-[#1C1C1C]/10 bg-white p-4">
                  <p className="text-sm font-semibold text-[#1C1C1C]">
                    关联对象
                  </p>
                  <p className="mt-3 text-sm text-[#1C1C1C]/60">
                    主简历：
                    {selectedWorkflow.resume.structured_json?.basic_info.name ||
                      selectedWorkflow.resume.file_name}
                  </p>
                  <p className="mt-1 text-sm text-[#1C1C1C]/60">
                    目标岗位：{selectedWorkflow.target_job.title}
                  </p>
                </div>

                <Button asChild size="sm" type="button">
                  <Link
                    href={`/dashboard/interviews?reportId=${selectedWorkflow.tailored_resume.match_report_id}&optimizationSessionId=${selectedWorkflow.tailored_resume.session_id}&jobId=${selectedWorkflow.target_job.id}`}
                  >
                    去模拟面试
                    <ArrowUpRight className="size-4" />
                  </Link>
                </Button>
              </div>
            </div>
          </div>
        ) : (
          <PageEmptyState
            title="专属简历成品还未生成"
            description="先选择主简历并填写目标岗位 JD，然后点击一键生成。"
          />
        )}
      </PaperSection>
    </PageShell>
  );
}
