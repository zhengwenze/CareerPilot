"use client";

import Link from "next/link";
import {
  useEffect,
  useRef,
  useState,
  type ChangeEvent,
  type ReactNode,
} from "react";
import { ArrowUpRight, Download, FileUp, Sparkles } from "lucide-react";

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
import { PageEmptyState } from "@/components/page-state";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { ApiError } from "@/lib/api/client";
import {
  createJob,
  createEmptyJobDraft,
  fetchJobDetail,
  fetchJobList,
  type JobDraft,
  type JobRecord,
  toJobDraft,
  updateJob,
} from "@/lib/api/modules/jobs";
import {
  convertResumePdfToMarkdown,
  downloadTailoredResumeMarkdown,
  fetchResumeDetail,
  fetchResumeList,
  fetchTailoredResumeWorkflows,
  optimizeTailoredResume,
  updateResumeStructuredData,
  uploadPrimaryResume,
  type ResumeRecord,
  type ResumeStructuredData,
  type TailoredResumeWorkflowRecord,
} from "@/lib/api/modules/resume";
import { cn } from "@/lib/utils";
import { ResumeStatusIndicator } from "@/components/resume-status-indicator";
import { JobStatusIndicator } from "@/components/job-status-indicator";

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

function formatDuration(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${mins.toString().padStart(2, "0")}:${secs.toString().padStart(2, "0")}`;
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

function getCanonicalResumeMarkdown(resume: ResumeRecord | null) {
  if (!resume) {
    return "";
  }
  return (
    resume.parse_artifacts_json?.canonical_resume_md?.trim() ||
    resume.raw_text?.trim() ||
    ""
  );
}

function normalizeMarkdown(md: string) {
  return md.replace(/\r\n/g, "\n").trim();
}

function pickSection(markdown: string, names: string[]) {
  const lines = normalizeMarkdown(markdown).split("\n");
  const sections = new Map<string, string[]>();
  let current = "__root__";
  sections.set(current, []);

  for (const rawLine of lines) {
    const line = rawLine.trimEnd();
    const headingMatch = line.match(/^##\s+(.+)$/);
    if (headingMatch) {
      current = headingMatch[1].trim().toLowerCase();
      sections.set(current, []);
      continue;
    }
    sections.get(current)?.push(line);
  }

  for (const name of names) {
    const value = sections.get(name.toLowerCase());
    if (value) {
      return value;
    }
  }
  return [];
}

function cleanList(lines: string[]) {
  return lines
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => line.replace(/^[-*]\s*/, "").trim())
    .filter(Boolean);
}

function markdownToStructuredResume(markdown: string): ResumeStructuredData {
  const normalized = normalizeMarkdown(markdown);
  const lines = normalized.split("\n");
  const name =
    lines
      .find((line) => line.trim().startsWith("# "))
      ?.replace(/^#\s+/, "")
      .trim() ?? "";
  const introLines: string[] = [];
  for (const line of lines.slice(1)) {
    if (line.trim().startsWith("## ")) {
      break;
    }
    introLines.push(line.trim());
  }

  const infoMap = new Map<string, string>();
  for (const line of introLines) {
    const bullet = line.replace(/^[-*]\s*/, "").trim();
    const [label, ...rest] = bullet.split("：");
    if (rest.length > 0) {
      infoMap.set(label.trim(), rest.join("：").trim());
    }
  }

  const skills = cleanList(
    pickSection(normalized, ["专业技能", "技能", "skills"]).flatMap((line) =>
      line.split(/[,，]/),
    ),
  );
  const education = cleanList(
    pickSection(normalized, ["教育经历", "education"]),
  );
  const workExperience = cleanList(
    pickSection(normalized, ["工作经验", "work experience"]),
  );
  const projects = cleanList(pickSection(normalized, ["项目经历", "projects"]));
  const certifications = cleanList(
    pickSection(normalized, ["证书", "certificates"]),
  );

  return {
    basic_info: {
      name,
      email: infoMap.get("邮箱") ?? "",
      phone: infoMap.get("电话") ?? "",
      location: infoMap.get("所在地") ?? "",
      summary: infoMap.get("求职方向") ?? "",
    },
    education,
    work_experience: workExperience,
    projects,
    skills: {
      technical: skills,
      tools: [],
      languages: [],
    },
    certifications,
  };
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
  const uploadInputRef = useRef<HTMLInputElement | null>(null);

  const [resume, setResume] = useState<ResumeRecord | null>(null);
  const [resumeMarkdown, setResumeMarkdown] = useState("");
  const [jobDraft, setJobDraft] = useState<JobDraft>(createEmptyJobDraft());
  const [savedJob, setSavedJob] = useState<JobRecord | null>(null);
  const [workflow, setWorkflow] = useState<TailoredResumeWorkflowRecord | null>(
    null,
  );
  const [pageError, setPageError] = useState("");
  const [statusMessage, setStatusMessage] = useState("");
  const [isUploading, setIsUploading] = useState(false);
  const [isConverting, setIsConverting] = useState(false);
  const [isSavingResume, setIsSavingResume] = useState(false);
  const [isSavingJob, setIsSavingJob] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [isDownloading, setIsDownloading] = useState(false);
  const [generateStartTime, setGenerateStartTime] = useState<number | null>(
    null,
  );

  useEffect(() => {
    if (!token) {
      return;
    }

    let cancelled = false;

    async function bootstrap() {
      setPageError("");

      try {
        const [resumes, jobs, workflows] = await Promise.all([
          fetchResumeList(token!),
          fetchJobList(token!),
          fetchTailoredResumeWorkflows(token!).catch(() => []),
        ]);
        if (cancelled) {
          return;
        }

        const nextResume = resumes[0] ?? null;
        const nextSavedJob = jobs[0] ?? null;
        const nextWorkflow =
          workflows.find(
            (item) =>
              item.resume.id === nextResume?.id &&
              item.target_job.id === nextSavedJob?.id,
          ) ?? null;

        setResume(nextResume);
        setResumeMarkdown(
          (current) => current || getCanonicalResumeMarkdown(nextResume),
        );
        setSavedJob(nextSavedJob);
        setJobDraft(
          nextSavedJob ? toJobDraft(nextSavedJob) : createEmptyJobDraft(),
        );
        setWorkflow(nextWorkflow);
      } catch (error) {
        if (!cancelled) {
          setPageError(getErrorMessage(error));
        }
      }
    }

    void bootstrap();
    return () => {
      cancelled = true;
    };
  }, [token]);

  useEffect(() => {
    if (!token || !resume?.id) {
      return;
    }
    if (!["pending", "processing"].includes(resume.parse_status)) {
      return;
    }

    const timer = window.setInterval(async () => {
      try {
        const nextResume = await fetchResumeDetail(token, resume.id);
        setResume(nextResume);
        const nextMarkdown = getCanonicalResumeMarkdown(nextResume);
        if (nextMarkdown) {
          setResumeMarkdown(nextMarkdown);
        }
      } catch {
        // keep the last visible state until the next retry
      }
    }, 2000);

    return () => window.clearInterval(timer);
  }, [resume?.id, resume?.parse_status, token]);

  useEffect(() => {
    if (!token || !savedJob?.id) {
      return;
    }
    if (!["pending", "processing"].includes(savedJob.parse_status)) {
      return;
    }

    const timer = window.setInterval(async () => {
      try {
        const nextJob = await fetchJobDetail(token, savedJob.id);
        setSavedJob(nextJob);
        setJobDraft((current) =>
          current.jd_text.trim() ? current : toJobDraft(nextJob),
        );
      } catch {
        // keep the last visible state until the next retry
      }
    }, 2000);

    return () => window.clearInterval(timer);
  }, [savedJob?.id, savedJob?.parse_status, token]);

  useEffect(() => {
    if (!isGenerating || generateStartTime === null) {
      return;
    }

    const timer = window.setInterval(() => {
      setGenerateStartTime((current) => current);
    }, 1000);

    return () => window.clearInterval(timer);
  }, [isGenerating, generateStartTime]);

  const canSaveResume = Boolean(
    token && resume?.id && normalizeMarkdown(resumeMarkdown),
  );
  const canSaveJob = Boolean(
    token && jobDraft.title.trim() && jobDraft.jd_text.trim(),
  );
  const canGenerate = Boolean(
    token &&
    resume?.id &&
    resume.parse_status === "success" &&
    savedJob?.id &&
    savedJob.parse_status === "success",
  );

  if (!token) {
    return null;
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
      setResume(uploaded);
      setIsConverting(true);

      const converted = await convertResumePdfToMarkdown(token, file);
      const nextMarkdown = normalizeMarkdown(converted.markdown);
      setResumeMarkdown(nextMarkdown);
      setIsSavingResume(true);

      const autoSaved = await updateResumeStructuredData(
        token,
        uploaded.id,
        markdownToStructuredResume(nextMarkdown),
        nextMarkdown,
      );
      setResume(autoSaved);
      setResumeMarkdown(getCanonicalResumeMarkdown(autoSaved) || nextMarkdown);
      setWorkflow(null);
      setStatusMessage(
        "PDF 已上传、自动转换为 Markdown，并已保存到当前用户账户。",
      );
    } catch (error) {
      setPageError(getErrorMessage(error));
    } finally {
      setIsUploading(false);
      setIsConverting(false);
      setIsSavingResume(false);
    }
  }

  async function handleSaveResume() {
    if (!token || !resume?.id || !normalizeMarkdown(resumeMarkdown)) {
      return;
    }

    setIsSavingResume(true);
    setPageError("");
    setStatusMessage("");

    try {
      const payload = markdownToStructuredResume(resumeMarkdown);
      const saved = await updateResumeStructuredData(
        token,
        resume.id,
        payload,
        normalizeMarkdown(resumeMarkdown),
      );
      const nextMarkdown =
        getCanonicalResumeMarkdown(saved) || normalizeMarkdown(resumeMarkdown);
      setResume(saved);
      setResumeMarkdown(nextMarkdown);
      setStatusMessage("简历已保存，可继续保存岗位 JD 并生成优化简历。");
    } catch (error) {
      setPageError(getErrorMessage(error));
    } finally {
      setIsSavingResume(false);
    }
  }

  async function handleSaveJob() {
    if (!token || !canSaveJob) {
      return;
    }

    setIsSavingJob(true);
    setPageError("");
    setStatusMessage("");

    try {
      const nextJob = savedJob
        ? await updateJob(token, savedJob.id, jobDraft)
        : await createJob(token, jobDraft);
      setSavedJob(nextJob);
      setStatusMessage(
        savedJob
          ? "岗位 JD 已更新，后端正在重新解析。"
          : "岗位 JD 已保存，后端正在解析。",
      );
    } catch (error) {
      setPageError(getErrorMessage(error));
    } finally {
      setIsSavingJob(false);
    }
  }

  async function handleGenerateTailoredResume() {
    if (!token || !resume?.id || !savedJob?.id) {
      setPageError("请先完成简历保存和岗位 JD 保存。");
      return;
    }

    setIsGenerating(true);
    setGenerateStartTime(Date.now());
    setPageError("");
    setStatusMessage("");

    try {
      const generated = await optimizeTailoredResume(token, {
        resume_id: resume.id,
        job_id: savedJob.id,
        force_refresh: true,
      });
      setWorkflow(generated);
      setStatusMessage("优化简历已生成，可直接下载 Markdown。");
    } catch (error) {
      setPageError(getErrorMessage(error));
    } finally {
      setIsGenerating(false);
      setGenerateStartTime(null);
    }
  }

  async function handleDownload() {
    if (!token || !workflow) {
      return;
    }

    setIsDownloading(true);
    setPageError("");
    setStatusMessage("");

    try {
      const result = await downloadTailoredResumeMarkdown(
        token,
        workflow.tailored_resume.session_id,
      );
      const objectUrl = window.URL.createObjectURL(result.blob);
      const link = document.createElement("a");
      link.href = objectUrl;
      link.download =
        result.fileName ||
        workflow.tailored_resume.downloadable_file_name ||
        "optimized_resume.md";
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(objectUrl);
      setStatusMessage("Markdown 已下载。");
    } catch (error) {
      setPageError(getErrorMessage(error));
    } finally {
      setIsDownloading(false);
    }
  }

  return (
    <PageShell className="gap-6">
      <PageHeader
        eyebrow="Tailored Resume"
        title="专属简历"
        description="这个页面只串你最终保留的接口：上传 PDF、直转 MD、保存简历、保存岗位 JD、生成优化简历、下载 Markdown。"
        meta={
          <>
            <MetaChip>{resume ? "已上传简历" : "未上传简历"}</MetaChip>
            <MetaChip>{savedJob ? "已保存 JD" : "未保存 JD"}</MetaChip>
            <MetaChip>
              {workflow ? "已生成优化简历" : "未生成优化简历"}
            </MetaChip>
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
        eyebrow="Resume"
        title="上传、转 MD、保存简历"
        rightSlot={
          <div className="flex gap-2">
            <input
              ref={uploadInputRef}
              className="hidden"
              type="file"
              accept=".pdf,application/pdf"
              onChange={handleUploadResume}
            />
            <Button
              disabled={isUploading || isConverting}
              size="sm"
              type="button"
              onClick={() => uploadInputRef.current?.click()}
            >
              <FileUp className="size-4" />
              {isUploading || isConverting ? "上传并解析中" : "上传 PDF"}
            </Button>
            <Button
              disabled={!canSaveResume || isSavingResume}
              size="sm"
              type="button"
              variant="secondary"
              onClick={() => void handleSaveResume()}
            >
              {isSavingResume ? "保存中" : "保存简历"}
            </Button>
          </div>
        }
      >
        {resume ? (
          <div className="space-y-4">
            <div className="flex flex-wrap gap-2">
              <MetaChip>
                <ResumeStatusIndicator resume={resume} />
              </MetaChip>
              <MetaChip>{resume.file_name}</MetaChip>
              <MetaChip>{formatDate(resume.updated_at)}</MetaChip>
            </div>
            <PaperTextarea
              value={resumeMarkdown}
              onChange={(event) => setResumeMarkdown(event.target.value)}
              placeholder="上传 PDF 或点击重新转 MD 后，这里会出现可编辑的 Markdown 简历。"
              className="min-h-[320px]"
            />
            {normalizeMarkdown(resumeMarkdown) ? (
              <div className="rounded-2xl border border-[#1C1C1C]/10 bg-[#FAFAF8] p-5">
                <ResumeMarkdownPreview
                  markdown={normalizeMarkdown(resumeMarkdown)}
                />
              </div>
            ) : null}
          </div>
        ) : (
          <PageEmptyState
            title="还没有主简历"
            description="先上传 PDF，系统会自动把 PDF 转成可编辑的 Markdown。"
          />
        )}
      </PaperSection>

      <PaperSection
        eyebrow="Job"
        title="保存或更新岗位 JD"
        rightSlot={
          <div className="flex items-center gap-2">
            {savedJob ? (
              <MetaChip>
                <JobStatusIndicator job={savedJob} />
              </MetaChip>
            ) : null}
            <Button
              disabled={!canSaveJob || isSavingJob}
              size="sm"
              type="button"
              onClick={() => void handleSaveJob()}
            >
              {isSavingJob ? "保存中" : savedJob ? "更新 JD" : "保存 JD"}
            </Button>
          </div>
        }
      >
        <div className="space-y-4">
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
                placeholder="例如：高级前端工程师"
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
              placeholder="粘贴完整岗位描述。首次点击保存会走 POST /jobs，之后更新会走 PUT /jobs/{job_id}。"
              className="min-h-[240px]"
            />
          </div>
        </div>
      </PaperSection>

      <PaperSection
        eyebrow="Tailored"
        title="生成并下载优化简历"
        rightSlot={
          <div className="flex gap-2">
            <Button
              disabled={!canGenerate || isGenerating}
              size="sm"
              type="button"
              onClick={() => void handleGenerateTailoredResume()}
            >
              <Sparkles className="size-4" />
              {isGenerating && generateStartTime !== null ? (
                <>
                  生成中{" "}
                  {formatDuration(
                    Math.floor((Date.now() - generateStartTime) / 1000),
                  )}
                </>
              ) : (
                "生成优化简历"
              )}
            </Button>
            <Button
              disabled={!workflow || isDownloading}
              size="sm"
              type="button"
              variant="secondary"
              onClick={() => void handleDownload()}
            >
              <Download className="size-4" />
              {isDownloading ? "下载中" : "下载 MD"}
            </Button>
            {workflow ? (
              <Button asChild size="sm" type="button" variant="secondary">
                <Link
                  href={`/dashboard/interviews?jobId=${workflow.target_job.id}&optimizationSessionId=${workflow.tailored_resume.session_id}`}
                >
                  开始模拟面试
                  <ArrowUpRight className="size-4" />
                </Link>
              </Button>
            ) : null}
          </div>
        }
      >
        {!canGenerate ? (
          <div className="rounded-2xl border border-[#1C1C1C]/10 bg-[#F9F8F6] px-4 py-3 text-sm text-[#1C1C1C]/70">
            先完成 1. 上传并等待简历解析成功 / 或保存直转 Markdown 2. 保存岗位
            JD 并等待解析成功，然后才能生成优化简历。
          </div>
        ) : null}

        {workflow ? (
          <div className="space-y-4">
            <div className="flex flex-wrap gap-2">
              <MetaChip>{workflow.target_job.title}</MetaChip>
              <MetaChip>
                {getFitBandLabel(workflow.tailored_resume.fit_band)}
              </MetaChip>
              <MetaChip>
                Score {workflow.tailored_resume.overall_score}
              </MetaChip>
            </div>
            <PaperTextarea
              value={workflow.tailored_resume.document.markdown}
              readOnly
              className="min-h-[320px]"
            />
          </div>
        ) : (
          <PageEmptyState
            title="还没有优化后的简历"
            description="保存简历和 JD 后，点击生成优化简历。"
          />
        )}
      </PaperSection>
    </PageShell>
  );
}
