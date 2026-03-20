"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";

import { useAuth } from "@/components/auth-provider";
import {
  PaperInput,
  PaperSelect,
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
import { ApiError } from "@/lib/api/client";
import {
  createEmptyJobDraft,
  createJob,
  createJobMatchReport,
  deleteJob,
  deleteMatchReport,
  fetchJobDetail,
  fetchJobList,
  fetchJobMatchReports,
  fetchMatchReportDetail,
  parseJob,
  toJobDraft,
  updateJob,
  type JobDraft,
  type JobRecord,
  type MatchReportRecord,
} from "@/lib/api/modules/jobs";
import { createResumeOptimizationSession } from "@/lib/api/modules/optimizer";
import { fetchResumeList, type ResumeRecord } from "@/lib/api/modules/resume";

type WorkflowStatus =
  | "idle"
  | "saving_job"
  | "parsing_job"
  | "creating_report"
  | "waiting_report"
  | "ready"
  | "failed";

const WORKFLOW_TIMEOUT_MS = 120_000;
const POLL_INTERVAL_MS = 2_500;

function getErrorMessage(error: unknown) {
  if (error instanceof ApiError) {
    return error.message;
  }
  if (error instanceof Error) {
    return error.message;
  }
  return "操作失败，请稍后重试。";
}

function sleep(ms: number) {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat("zh-CN", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
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

function getWorkflowLabel(status: WorkflowStatus) {
  const labels: Record<WorkflowStatus, string> = {
    idle: "",
    saving_job: "正在保存岗位信息",
    parsing_job: "正在结构化岗位目标",
    creating_report: "正在创建匹配任务",
    waiting_report: "Minimax 正在生成匹配报告",
    ready: "匹配报告已生成",
    failed: "匹配报告生成失败",
  };
  return labels[status];
}

function normalizeDraft(draft: JobDraft) {
  return {
    title: draft.title.trim(),
    company: draft.company.trim(),
    job_city: draft.job_city.trim(),
    employment_type: draft.employment_type.trim(),
    source_name: draft.source_name.trim(),
    source_url: draft.source_url.trim(),
    jd_text: draft.jd_text.trim(),
  };
}

function isDraftDirty(job: JobRecord | null, draft: JobDraft) {
  if (!job) {
    const normalized = normalizeDraft(draft);
    return Boolean(normalized.title || normalized.jd_text);
  }

  const current = normalizeDraft(toJobDraft(job));
  const next = normalizeDraft(draft);
  return Object.keys(current).some((key) => {
    const typedKey = key as keyof typeof current;
    return current[typedKey] !== next[typedKey];
  });
}

function getPreferredResumeId(job: JobRecord | null, resumes: ResumeRecord[]) {
  return (
    job?.recommended_resume_id ??
    [...resumes]
      .filter((item) => item.parse_status === "success")
      .sort((a, b) => +new Date(b.updated_at) - +new Date(a.updated_at))[0]
      ?.id ??
    ""
  );
}

function PaperButton({
  children,
  variant = "primary",
  className = "",
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary" | "danger";
}) {
  const variantClassName =
    variant === "primary"
      ? "border-2 border-black bg-black text-white hover:bg-black/80"
      : variant === "danger"
        ? "border-2 border-black bg-white text-black hover:bg-gray-100"
        : "border-2 border-black bg-white text-black hover:bg-gray-100";

  return (
    <button
      {...props}
      className={`px-5 py-2 font-mono text-sm font-bold transition-colors disabled:cursor-not-allowed disabled:opacity-60 ${variantClassName} ${className}`}
    >
      {children}
    </button>
  );
}

export default function DashboardJobsPage() {
  const { token } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();
  const preferredJobIdFromQuery = searchParams.get("jobId");

  const [jobs, setJobs] = useState<JobRecord[]>([]);
  const [resumes, setResumes] = useState<ResumeRecord[]>([]);
  const [reports, setReports] = useState<MatchReportRecord[]>([]);
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null);
  const [selectedReportId, setSelectedReportId] = useState<string | null>(null);
  const [selectedResumeId, setSelectedResumeId] = useState("");
  const [jobDraft, setJobDraft] = useState<JobDraft>(createEmptyJobDraft());
  const [workflowStatus, setWorkflowStatus] = useState<WorkflowStatus>("idle");
  const [isPageLoading, setIsPageLoading] = useState(true);
  const [isOpeningOptimizer, setIsOpeningOptimizer] = useState(false);
  const [isDeletingJob, setIsDeletingJob] = useState(false);
  const [isDeletingReportId, setIsDeletingReportId] = useState<string | null>(
    null,
  );
  const [pageError, setPageError] = useState("");
  const [statusMessage, setStatusMessage] = useState("");
  const [showMoreInfo, setShowMoreInfo] = useState(false);
  const [showResumePicker, setShowResumePicker] = useState(false);
  const [showHistory, setShowHistory] = useState(false);

  const selectedJob = jobs.find((item) => item.id === selectedJobId) ?? null;
  const selectedReport =
    reports.find((item) => item.id === selectedReportId) ?? reports[0] ?? null;
  const availableResumes = [...resumes]
    .filter((item) => item.parse_status === "success")
    .sort((a, b) => +new Date(b.updated_at) - +new Date(a.updated_at));

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
        const [nextJobs, nextResumes] = await Promise.all([
          fetchJobList(accessToken),
          fetchResumeList(accessToken),
        ]);
        if (cancelled) {
          return;
        }

        const nextJobId =
          preferredJobIdFromQuery &&
          nextJobs.some((item) => item.id === preferredJobIdFromQuery)
            ? preferredJobIdFromQuery
            : (nextJobs[0]?.id ?? null);
        const nextJob = nextJobs.find((item) => item.id === nextJobId) ?? null;

        setJobs(nextJobs);
        setResumes(nextResumes);
        setSelectedJobId(nextJobId);
        setJobDraft(nextJob ? toJobDraft(nextJob) : createEmptyJobDraft());
        setSelectedResumeId(getPreferredResumeId(nextJob, nextResumes));
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
  }, [preferredJobIdFromQuery, token]);

  useEffect(() => {
    if (!token || !selectedJobId) {
      setReports([]);
      setSelectedReportId(null);
      return;
    }

    const accessToken = token;
    let cancelled = false;

    async function loadReports() {
      const jobId = selectedJobId;
      if (!jobId) {
        return;
      }
      try {
        const nextReports = await fetchJobMatchReports(accessToken, jobId);
        if (cancelled) {
          return;
        }
        setReports(nextReports);
        setSelectedReportId((current) =>
          current && nextReports.some((item) => item.id === current)
            ? current
            : (nextReports[0]?.id ?? null),
        );
      } catch (error) {
        if (!cancelled) {
          setPageError(getErrorMessage(error));
        }
      }
    }

    void loadReports();

    return () => {
      cancelled = true;
    };
  }, [selectedJobId, token]);

  useEffect(() => {
    if (!token || !selectedJobId) {
      return;
    }
    if (
      workflowStatus !== "idle" &&
      workflowStatus !== "ready" &&
      workflowStatus !== "failed"
    ) {
      return;
    }
    if (
      selectedJob?.parse_status !== "pending" &&
      selectedJob?.parse_status !== "processing"
    ) {
      return;
    }

    const accessToken = token;
    let cancelled = false;
    const timer = window.setInterval(() => {
      void (async () => {
        try {
          const nextJob = await fetchJobDetail(accessToken, selectedJobId);
          if (cancelled) {
            return;
          }
          setJobs((current) =>
            current.map((item) => (item.id === nextJob.id ? nextJob : item)),
          );
        } catch {
          // Ignore background refresh failures.
        }
      })();
    }, 4000);

    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, [selectedJob, selectedJobId, token, workflowStatus]);

  if (!token) {
    return null;
  }

  if (isPageLoading) {
    return (
      <PageLoadingState
        title="正在加载岗位匹配"
        description="我们正在同步岗位、简历和最近一次匹配结果。"
      />
    );
  }

  if (pageError && jobs.length === 0) {
    return (
      <PageErrorState
        actionLabel="重新加载"
        description={pageError}
        onAction={() => window.location.reload()}
        title="岗位匹配加载失败"
      />
    );
  }

  async function refreshPageState(
    preferredJobId?: string | null,
    preferredReportId?: string | null,
  ) {
    if (!token) {
      return;
    }

    const [nextJobs, nextResumes] = await Promise.all([
      fetchJobList(token),
      fetchResumeList(token),
    ]);
    const nextSelectedJobId =
      preferredJobId && nextJobs.some((item) => item.id === preferredJobId)
        ? preferredJobId
        : (nextJobs[0]?.id ?? null);
    const nextJob =
      nextJobs.find((item) => item.id === nextSelectedJobId) ?? null;
    const nextReports = nextSelectedJobId
      ? await fetchJobMatchReports(token, nextSelectedJobId)
      : [];

    setJobs(nextJobs);
    setResumes(nextResumes);
    setSelectedJobId(nextSelectedJobId);
    setJobDraft(nextJob ? toJobDraft(nextJob) : createEmptyJobDraft());
    setSelectedResumeId(
      (current) => current || getPreferredResumeId(nextJob, nextResumes),
    );
    setReports(nextReports);
    setSelectedReportId(
      preferredReportId &&
        nextReports.some((item) => item.id === preferredReportId)
        ? preferredReportId
        : (nextReports[0]?.id ?? null),
    );
  }

  async function waitForJobParse(jobId: string) {
    if (!token) {
      throw new Error("未登录，无法继续。");
    }

    const startedAt = Date.now();
    while (Date.now() - startedAt < WORKFLOW_TIMEOUT_MS) {
      const job = await fetchJobDetail(token, jobId);
      setJobs((current) => {
        const exists = current.some((item) => item.id === job.id);
        if (!exists) {
          return [job, ...current];
        }
        return current.map((item) => (item.id === job.id ? job : item));
      });

      if (job.parse_status === "success") {
        return job;
      }
      if (job.parse_status === "failed") {
        throw new Error(job.parse_error || "岗位结构化失败。");
      }
      await sleep(POLL_INTERVAL_MS);
    }

    throw new Error("岗位结构化超时，请稍后重试。");
  }

  async function waitForReportReady(reportId: string) {
    if (!token) {
      throw new Error("未登录，无法继续。");
    }

    const startedAt = Date.now();
    while (Date.now() - startedAt < WORKFLOW_TIMEOUT_MS) {
      const report = await fetchMatchReportDetail(token, reportId);
      setReports((current) => {
        const exists = current.some((item) => item.id === report.id);
        if (!exists) {
          return [report, ...current];
        }
        return current.map((item) => (item.id === report.id ? report : item));
      });

      if (report.status === "success") {
        return report;
      }
      if (report.status === "failed") {
        throw new Error(report.error_message || "匹配报告生成失败。");
      }
      await sleep(POLL_INTERVAL_MS);
    }

    throw new Error("匹配报告生成超时，请稍后重试。");
  }

  function updateDraft(field: keyof JobDraft, value: string) {
    setJobDraft((current) => ({
      ...current,
      [field]: value,
    }));
  }

  function resetToNewJob() {
    setSelectedJobId(null);
    setSelectedReportId(null);
    setReports([]);
    setJobDraft(createEmptyJobDraft());
    setPageError("");
    setStatusMessage("");
    setWorkflowStatus("idle");
    setSelectedResumeId(getPreferredResumeId(null, resumes));
    setShowMoreInfo(false);
    setShowHistory(false);
  }

  async function handleGenerateReport() {
    if (!token) {
      return;
    }

    const normalized = normalizeDraft(jobDraft);
    if (!normalized.title || !normalized.jd_text) {
      setPageError("请至少填写岗位标题和 JD 原文。");
      setWorkflowStatus("failed");
      return;
    }

    const effectiveResumeId =
      selectedResumeId || getPreferredResumeId(selectedJob, resumes);
    if (!effectiveResumeId) {
      setPageError("请先完成至少一份简历解析，再生成匹配报告。");
      setWorkflowStatus("failed");
      return;
    }

    setPageError("");
    setStatusMessage("");

    try {
      let workingJob: JobRecord;
      const draftChanged = isDraftDirty(selectedJob, jobDraft);

      if (!selectedJob) {
        setWorkflowStatus("saving_job");
        workingJob = await createJob(token, jobDraft);
      } else if (draftChanged) {
        setWorkflowStatus("saving_job");
        workingJob = await updateJob(token, selectedJob.id, jobDraft);
      } else {
        workingJob = await fetchJobDetail(token, selectedJob.id);
      }

      setSelectedJobId(workingJob.id);

      if (workingJob.parse_status !== "success") {
        setWorkflowStatus("parsing_job");
        if (
          selectedJob &&
          !draftChanged &&
          selectedJob.id === workingJob.id &&
          selectedJob.parse_status === "failed"
        ) {
          workingJob = await parseJob(token, workingJob.id);
        }
        workingJob = await waitForJobParse(workingJob.id);
      }

      setWorkflowStatus("creating_report");
      const createdReport = await createJobMatchReport(
        token,
        workingJob.id,
        effectiveResumeId,
      );
      setSelectedResumeId(effectiveResumeId);
      setSelectedReportId(createdReport.id);

      setWorkflowStatus("waiting_report");
      const readyReport = await waitForReportReady(createdReport.id);

      await refreshPageState(workingJob.id, readyReport.id);
      setWorkflowStatus("ready");
      setStatusMessage(
        "匹配报告已生成，你现在可以直接查看结论并进入简历优化。",
      );
    } catch (error) {
      setWorkflowStatus("failed");
      setPageError(getErrorMessage(error));
    }
  }

  async function handleDeleteJob() {
    if (!token || !selectedJob) {
      return;
    }

    const confirmed = window.confirm(`确认删除《${selectedJob.title}》吗？`);
    if (!confirmed) {
      return;
    }

    setIsDeletingJob(true);
    setPageError("");

    try {
      await deleteJob(token, selectedJob.id);
      await refreshPageState();
      setStatusMessage("岗位已删除。");
      setWorkflowStatus("idle");
      if (jobs.length <= 1) {
        resetToNewJob();
      }
    } catch (error) {
      setPageError(getErrorMessage(error));
    } finally {
      setIsDeletingJob(false);
    }
  }

  async function handleRetryParse() {
    if (!token || !selectedJob) {
      return;
    }

    setPageError("");
    setStatusMessage("");

    try {
      setWorkflowStatus("parsing_job");
      await parseJob(token, selectedJob.id);
      await waitForJobParse(selectedJob.id);
      await refreshPageState(selectedJob.id);
      setWorkflowStatus("ready");
      setStatusMessage("岗位目标已重新结构化。");
    } catch (error) {
      setWorkflowStatus("failed");
      setPageError(getErrorMessage(error));
    }
  }

  async function handleDeleteReport(reportId: string) {
    if (!token || !selectedJobId) {
      return;
    }

    const confirmed = window.confirm("确认删除这份匹配报告吗？");
    if (!confirmed) {
      return;
    }

    setIsDeletingReportId(reportId);
    setPageError("");

    try {
      await deleteMatchReport(token, reportId);
      await refreshPageState(selectedJobId);
      setStatusMessage("报告已删除。");
    } catch (error) {
      setPageError(getErrorMessage(error));
    } finally {
      setIsDeletingReportId(null);
    }
  }

  async function handleOpenOptimizer() {
    if (!token || !selectedJobId || !selectedReport) {
      setPageError("请先生成一份成功的匹配报告。");
      return;
    }

    if (selectedReport.status !== "success") {
      setPageError(
        `当前报告状态为 ${selectedReport.status}，请完成后再进入简历优化。`,
      );
      return;
    }

    setIsOpeningOptimizer(true);
    setPageError("");

    try {
      const session = await createResumeOptimizationSession(
        token,
        selectedReport.id,
      );
      router.push(
        `/dashboard/optimizer?sessionId=${session.id}&jobId=${selectedJobId}&reportId=${selectedReport.id}`,
      );
    } catch (error) {
      setPageError(getErrorMessage(error));
    } finally {
      setIsOpeningOptimizer(false);
    }
  }

  function handleOpenInterview() {
    if (!selectedReport) {
      setPageError("请先生成一份成功的匹配报告。");
      return;
    }

    if (selectedReport.status !== "success") {
      setPageError(
        `当前报告状态为 ${selectedReport.status}，请完成后再进入模拟面试。`,
      );
      return;
    }

    router.push(
      `/dashboard/interviews?reportId=${selectedReport.id}&jobId=${selectedJobId}`,
    );
  }

  return (
    <PageShell className="gap-6">
      <PageHeader
        description="把 JD 转成岗位目标，并基于已解析简历生成一份可执行的匹配报告。"
        eyebrow="Job Matching"
        meta={
          <>
            <MetaChip>{jobs.length} 个岗位</MetaChip>
            <MetaChip>{reports.length} 份报告</MetaChip>
          </>
        }
        title="岗位匹配"
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

      {workflowStatus !== "idle" && workflowStatus !== "ready" ? (
        <Alert className="border border-[#1C1C1C]/10 bg-[#F9F8F6] text-[#1C1C1C]">
          <AlertTitle className="text-base font-semibold tracking-tight text-[#1C1C1C]">
            {getWorkflowLabel(workflowStatus)}
          </AlertTitle>
          <AlertDescription className="text-sm leading-relaxed text-[#1C1C1C]/60">
            当前流程会自动完成保存、结构化和 Minimax 报告生成，请不要重复点击。
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

      <section className="grid gap-6 xl:grid-cols-[420px_minmax(0,1fr)]">
        <div className="space-y-6">
          <PaperSection
            title="输入岗位目标"
            eyebrow="Job Input"
            rightSlot={
              <div className="flex flex-wrap gap-3">
                {jobs.length > 0 ? (
                  <div className="min-w-[180px]">
                    <PaperSelect
                      onChange={(event) => {
                        const nextJobId = event.target.value;
                        if (!nextJobId) {
                          resetToNewJob();
                          return;
                        }
                        const nextJob =
                          jobs.find((item) => item.id === nextJobId) ?? null;
                        setSelectedJobId(nextJobId);
                        setJobDraft(
                          nextJob ? toJobDraft(nextJob) : createEmptyJobDraft(),
                        );
                        setSelectedResumeId(
                          getPreferredResumeId(nextJob, resumes),
                        );
                        setPageError("");
                        setStatusMessage("");
                        setWorkflowStatus("idle");
                      }}
                      value={selectedJobId ?? ""}
                    >
                      <option value="">新建岗位</option>
                      {jobs.map((job) => (
                        <option key={job.id} value={job.id}>
                          {job.title}
                        </option>
                      ))}
                    </PaperSelect>
                  </div>
                ) : null}

                <PaperButton
                  onClick={resetToNewJob}
                  type="button"
                  variant="secondary"
                >
                  新建岗位
                </PaperButton>
              </div>
            }
          >
            <div className="space-y-5">
              <div className="grid gap-2">
                <label
                  className="text-sm font-medium text-black"
                  htmlFor="job-title"
                >
                  岗位标题
                </label>
                <PaperInput
                  id="job-title"
                  onChange={(event) => updateDraft("title", event.target.value)}
                  placeholder="例如：增长数据分析师"
                  value={jobDraft.title}
                />
              </div>

              <div className="grid gap-2">
                <label
                  className="text-sm font-medium text-black"
                  htmlFor="job-jd-text"
                >
                  JD 原文
                </label>
                <PaperTextarea
                  id="job-jd-text"
                  onChange={(event) =>
                    updateDraft("jd_text", event.target.value)
                  }
                  placeholder="直接粘贴完整职位描述。点击一次后，系统会自动完成结构化与 Minimax 匹配。"
                  value={jobDraft.jd_text}
                />
              </div>

              <button
                className="text-sm font-semibold text-[#2f55d4]"
                onClick={() => setShowMoreInfo((current) => !current)}
                type="button"
              >
                {showMoreInfo ? "收起更多信息" : "编辑更多信息"}
              </button>

              {showMoreInfo ? (
                <div className="grid gap-4 md:grid-cols-2">
                  <div className="grid gap-2">
                    <label
                      className="text-sm font-medium text-black"
                      htmlFor="job-company"
                    >
                      公司
                    </label>
                    <PaperInput
                      id="job-company"
                      onChange={(event) =>
                        updateDraft("company", event.target.value)
                      }
                      value={jobDraft.company}
                    />
                  </div>

                  <div className="grid gap-2">
                    <label
                      className="text-sm font-medium text-black"
                      htmlFor="job-city"
                    >
                      城市
                    </label>
                    <PaperInput
                      id="job-city"
                      onChange={(event) =>
                        updateDraft("job_city", event.target.value)
                      }
                      value={jobDraft.job_city}
                    />
                  </div>

                  <div className="grid gap-2">
                    <label
                      className="text-sm font-medium text-black"
                      htmlFor="job-type"
                    >
                      用工类型
                    </label>
                    <PaperInput
                      id="job-type"
                      onChange={(event) =>
                        updateDraft("employment_type", event.target.value)
                      }
                      value={jobDraft.employment_type}
                    />
                  </div>

                  <div className="grid gap-2">
                    <label
                      className="text-sm font-medium text-black"
                      htmlFor="job-source-name"
                    >
                      来源平台
                    </label>
                    <PaperInput
                      id="job-source-name"
                      onChange={(event) =>
                        updateDraft("source_name", event.target.value)
                      }
                      value={jobDraft.source_name}
                    />
                  </div>

                  <div className="grid gap-2 md:col-span-2">
                    <label
                      className="text-sm font-medium text-black"
                      htmlFor="job-source-url"
                    >
                      来源链接
                    </label>
                    <PaperInput
                      id="job-source-url"
                      onChange={(event) =>
                        updateDraft("source_url", event.target.value)
                      }
                      value={jobDraft.source_url}
                    />
                  </div>
                </div>
              ) : null}
            </div>
          </PaperSection>

          <PaperSection
            title="生成匹配报告"
            eyebrow="Matching Workflow"
            rightSlot={
              <PaperButton
                disabled={
                  workflowStatus !== "idle" &&
                  workflowStatus !== "ready" &&
                  workflowStatus !== "failed"
                }
                onClick={handleGenerateReport}
                type="button"
                variant="primary"
              >
                {workflowStatus === "saving_job" ||
                workflowStatus === "parsing_job" ||
                workflowStatus === "creating_report" ||
                workflowStatus === "waiting_report"
                  ? getWorkflowLabel(workflowStatus)
                  : "生成匹配报告"}
              </PaperButton>
            }
          >
            <div className="space-y-5">
              {availableResumes.length === 0 ? (
                <div className="border border-dashed border-[#1C1C1C]/20 bg-[#F9F8F6]/50 px-4 py-4 text-sm leading-relaxed text-[#1C1C1C]/60">
                  当前没有可用简历。请先到{" "}
                  <Link
                    className="font-medium text-[#1C1C1C] underline underline-offset-4"
                    href="/dashboard/resume"
                  >
                    简历中心
                  </Link>{" "}
                  完成至少一份解析。
                </div>
              ) : (
                <>
                  <div className="border border-[#1C1C1C]/10 bg-white px-4 py-4">
                    <p className="text-sm font-medium text-[#1C1C1C]">
                      默认使用的简历
                    </p>
                    <p className="mt-2 text-sm leading-relaxed text-[#1C1C1C]/60">
                      {availableResumes.find(
                        (item) => item.id === selectedResumeId,
                      )?.file_name || availableResumes[0]?.file_name}
                    </p>
                    <button
                      className="mt-3 text-sm font-medium text-[#1C1C1C] underline underline-offset-4"
                      onClick={() => setShowResumePicker((current) => !current)}
                      type="button"
                    >
                      {showResumePicker ? "收起简历选择" : "切换简历"}
                    </button>
                  </div>

                  {showResumePicker ? (
                    <div className="grid gap-2">
                      <label
                        className="text-sm font-medium text-black"
                        htmlFor="resume-select"
                      >
                        参与匹配的简历
                      </label>
                      <PaperSelect
                        id="resume-select"
                        onChange={(event) =>
                          setSelectedResumeId(event.target.value)
                        }
                        value={
                          selectedResumeId || availableResumes[0]?.id || ""
                        }
                      >
                        {availableResumes.map((resume) => (
                          <option key={resume.id} value={resume.id}>
                            {resume.file_name}
                          </option>
                        ))}
                      </PaperSelect>
                    </div>
                  ) : null}

                  <div className="flex flex-wrap gap-3">
                    {selectedJob ? (
                      <PaperButton
                        onClick={handleRetryParse}
                        type="button"
                        variant="secondary"
                      >
                        重跑 JD 解析
                      </PaperButton>
                    ) : null}

                    {selectedJob ? (
                      <PaperButton
                        onClick={() => setShowHistory((current) => !current)}
                        type="button"
                        variant="secondary"
                      >
                        {showHistory ? "收起历史报告" : "查看历史报告"}
                      </PaperButton>
                    ) : null}

                    {selectedJob ? (
                      <PaperButton
                        disabled={isDeletingJob}
                        onClick={handleDeleteJob}
                        type="button"
                        variant="danger"
                      >
                        {isDeletingJob ? "删除中..." : "删除 JD"}
                      </PaperButton>
                    ) : null}
                  </div>
                </>
              )}
            </div>
          </PaperSection>

          {showHistory && reports.length > 0 ? (
            <PaperSection title="历史报告" eyebrow="Report Archive">
              <div className="space-y-3">
                {reports.map((report) => {
                  const isActive = report.id === selectedReportId;
                  return (
                    <div
                      className={`flex flex-wrap items-center justify-between gap-3 border border-[#1C1C1C]/10 px-4 py-4 ${
                        isActive
                          ? "bg-[#1C1C1C] text-white"
                          : "bg-white text-[#1C1C1C]"
                      }`}
                      key={report.id}
                    >
                      <button
                        className="min-w-0 flex-1 text-left"
                        onClick={() => setSelectedReportId(report.id)}
                        type="button"
                      >
                        <p className="text-sm font-semibold">
                          {report.status === "success"
                            ? `${getFitBandLabel(report.fit_band)} · ${report.overall_score}`
                            : `状态 ${report.status}`}
                        </p>
                        <p
                          className={`mt-1 text-xs leading-6 ${
                            isActive ? "text-white/80" : "text-black/52"
                          }`}
                        >
                          v{report.resume_version}/v{report.job_version} ·{" "}
                          {formatDate(report.created_at)}
                          {report.stale_status === "stale" ? " · 已过期" : ""}
                        </p>
                      </button>

                      <PaperButton
                        disabled={isDeletingReportId === report.id}
                        onClick={() => void handleDeleteReport(report.id)}
                        type="button"
                        variant={isActive ? "secondary" : "danger"}
                        className={isActive ? "bg-white text-black" : ""}
                      >
                        {isDeletingReportId === report.id
                          ? "删除中..."
                          : "删除"}
                      </PaperButton>
                    </div>
                  );
                })}
              </div>
            </PaperSection>
          ) : null}
        </div>

        <div className="space-y-6">
          {!selectedReport ? (
            <PageEmptyState
              description="输入岗位标题和 JD 后，点击一次即可生成完整的匹配报告。"
              title="还没有匹配报告"
            />
          ) : (
            <>
              <PaperSection
                title={
                  selectedReport.status === "success"
                    ? `${getFitBandLabel(selectedReport.fit_band)} · 总分 ${selectedReport.overall_score}`
                    : `报告状态：${selectedReport.status}`
                }
                eyebrow="Match Report"
                rightSlot={
                  <div className="flex flex-wrap gap-3">
                    <PaperButton
                      disabled={selectedReport.status !== "success"}
                      onClick={handleOpenInterview}
                      type="button"
                      variant="secondary"
                    >
                      去模拟面试
                    </PaperButton>
                    <PaperButton
                      disabled={
                        selectedReport.status !== "success" ||
                        isOpeningOptimizer
                      }
                      onClick={handleOpenOptimizer}
                      type="button"
                      variant="primary"
                    >
                      {isOpeningOptimizer ? "进入中..." : "去简历优化"}
                    </PaperButton>
                  </div>
                }
              >
                <p className="text-sm leading-7 text-black/68">
                  {String(
                    selectedReport.scorecard_json.summary ||
                      selectedReport.error_message ||
                      "",
                  )}
                </p>
              </PaperSection>

              <section className="grid gap-4 md:grid-cols-3">
                <div className="border border-[#1C1C1C]/10 bg-white px-4 py-4">
                  <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#1C1C1C]/60">
                    总体判断
                  </p>
                  <p className="mt-2 text-sm leading-relaxed text-[#1C1C1C]/60">
                    {String(
                      selectedReport.scorecard_json.reasoning ||
                        selectedReport.scorecard_json.summary ||
                        "暂无结论",
                    )}
                  </p>
                </div>

                <div className="border border-[#1C1C1C]/10 bg-white px-4 py-4">
                  <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#1C1C1C]/60">
                    置信度
                  </p>
                  <p className="mt-2 text-2xl font-semibold tracking-tight text-[#1C1C1C]">
                    {selectedReport.scorecard_json.confidence != null
                      ? `${Math.round(Number(selectedReport.scorecard_json.confidence) * 100)}%`
                      : "待补充"}
                  </p>
                </div>

                <div className="border border-[#1C1C1C]/10 bg-white px-4 py-4">
                  <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#1C1C1C]/60">
                    生成时间
                  </p>
                  <p className="mt-2 text-sm leading-relaxed text-[#1C1C1C]/60">
                    {formatDate(selectedReport.created_at)}
                  </p>
                </div>
              </section>

              <section className="grid gap-5 md:grid-cols-2">
                <PaperSection title="匹配证据" eyebrow="Evidence">
                  <p className="text-xs font-bold uppercase tracking-[0.18em] text-black/45">
                    已命中的 JD 关键项
                  </p>
                  <p className="mt-2 text-sm leading-7 text-black/68">
                    {Object.values(
                      selectedReport.evidence_map_json.matched_jd_fields ?? {},
                    )
                      .flat()
                      .join("、") || "暂无"}
                  </p>

                  <p className="mt-5 text-xs font-bold uppercase tracking-[0.18em] text-black/45">
                    证据备注
                  </p>
                  <p className="mt-2 text-sm leading-7 text-black/68">
                    {selectedReport.evidence_map_json.notes?.join("；") ||
                      "暂无"}
                  </p>
                </PaperSection>

                <PaperSection title="差距分析" eyebrow="Gap Analysis">
                  <div className="space-y-3">
                    {(selectedReport.gap_taxonomy_json.must_fix ?? [])
                      .slice(0, 3)
                      .map((item) => (
                        <div key={`must-${item.label}-${item.reason}`}>
                          <p className="text-sm font-semibold text-black">
                            必须补：{item.label}
                          </p>
                          <p className="text-sm leading-7 text-black/68">
                            {item.reason}
                          </p>
                        </div>
                      ))}

                    {(selectedReport.gap_taxonomy_json.should_fix ?? [])
                      .slice(0, 3)
                      .map((item) => (
                        <div key={`should-${item.label}-${item.reason}`}>
                          <p className="text-sm font-semibold text-black">
                            建议补：{item.label}
                          </p>
                          <p className="text-sm leading-7 text-black/68">
                            {item.reason}
                          </p>
                        </div>
                      ))}

                    {selectedReport.evidence_map_json.missing_items?.length ? (
                      <p className="text-sm leading-7 text-black/68">
                        缺失项：
                        {selectedReport.evidence_map_json.missing_items.join(
                          "、",
                        )}
                      </p>
                    ) : null}
                  </div>
                </PaperSection>
              </section>

              <PaperSection title="下一步动作" eyebrow="Tailoring Plan">
                <div className="space-y-3">
                  {(selectedReport.tailoring_plan_json.rewrite_tasks ?? [])
                    .slice(0, 3)
                    .map((task, index) => (
                      <div key={`${String(task.title)}-${index}`}>
                        <p className="text-sm font-semibold text-black">
                          P{String(task.priority ?? index + 1)} ·{" "}
                          {String(task.title ?? "定制任务")}
                        </p>
                        <p className="text-sm leading-7 text-black/68">
                          {String(task.instruction ?? "")}
                        </p>
                      </div>
                    ))}

                  {(selectedReport.tailoring_plan_json.rewrite_tasks ?? [])
                    .length === 0 ? (
                    <p className="text-sm text-black/58">
                      当前报告还没有生成可执行任务。
                    </p>
                  ) : null}
                </div>
              </PaperSection>
            </>
          )}
        </div>
      </section>
    </PageShell>
  );
}
