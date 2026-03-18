"use client";

import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";

import { JobFormCard } from "@/components/jobs/job-form-card";
import { JobList } from "@/components/jobs/job-list";
import { MatchReportPanel } from "@/components/jobs/match-report-panel";
import {
  PageEmptyState,
  PageErrorState,
  PageLoadingState,
} from "@/components/page-state";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/components/auth-provider";
import { ApiError } from "@/lib/api/client";
import {
  createEmptyJobDraft,
  createJob,
  createJobMatchReport,
  deleteJob,
  deleteMatchReport,
  fetchJobList,
  fetchJobMatchReports,
  parseJob,
  toJobDraft,
  updateJob,
  type JobDraft,
  type JobRecord,
  type MatchReportRecord,
} from "@/lib/api/modules/jobs";
import { fetchResumeList, type ResumeRecord } from "@/lib/api/modules/resume";

function getErrorMessage(error: unknown) {
  if (error instanceof ApiError) {
    return error.message;
  }
  if (error instanceof Error) {
    return error.message;
  }
  return "操作失败，请稍后重试。";
}

function isInFlight(status: string | null | undefined) {
  return status === "pending" || status === "processing";
}

export default function DashboardJobsPage() {
  const { token } = useAuth();
  const searchParams = useSearchParams();
  const preferredJobIdFromQuery = searchParams.get("jobId");
  const [jobs, setJobs] = useState<JobRecord[]>([]);
  const [resumes, setResumes] = useState<ResumeRecord[]>([]);
  const [reports, setReports] = useState<MatchReportRecord[]>([]);
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null);
  const [selectedReportId, setSelectedReportId] = useState<string | null>(null);
  const [selectedResumeId, setSelectedResumeId] = useState("");
  const [jobDraft, setJobDraft] = useState<JobDraft>(createEmptyJobDraft());
  const [isPageLoading, setIsPageLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [isParsing, setIsParsing] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [isDeletingReport, setIsDeletingReport] = useState(false);
  const [pageError, setPageError] = useState("");

  const selectedJob = jobs.find((item) => item.id === selectedJobId) ?? null;

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

        setJobs(nextJobs);
        setResumes(nextResumes);

        const nextJobId =
          preferredJobIdFromQuery &&
          nextJobs.some((item) => item.id === preferredJobIdFromQuery)
            ? preferredJobIdFromQuery
            : nextJobs[0]?.id ?? null;
        setSelectedJobId(nextJobId);
        setJobDraft(
          nextJobId
            ? toJobDraft(nextJobs.find((item) => item.id === nextJobId)!)
            : createEmptyJobDraft()
        );

        const nextSelectedResumeId =
          nextJobs.find((item) => item.id === nextJobId)?.recommended_resume_id ??
          nextResumes.find((item) => item.parse_status === "success")?.id ??
          "";
        setSelectedResumeId(nextSelectedResumeId);
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
      if (!selectedJobId) {
        return;
      }
      try {
        const nextReports = await fetchJobMatchReports(accessToken, selectedJobId);
        if (cancelled) {
          return;
        }
        setReports(nextReports);
        setSelectedReportId((current) =>
          current && nextReports.some((item) => item.id === current)
            ? current
            : nextReports[0]?.id ?? null
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
    if (!selectedJob) {
      return;
    }
    if (selectedJob.recommended_resume_id) {
      setSelectedResumeId(selectedJob.recommended_resume_id);
      return;
    }
    if (!selectedResumeId) {
      const fallbackResumeId =
        resumes.find((item) => item.parse_status === "success")?.id ?? "";
      setSelectedResumeId(fallbackResumeId);
    }
  }, [resumes, selectedJob, selectedResumeId]);

  useEffect(() => {
    if (!token) {
      return;
    }

    const hasActiveJob = jobs.some((item) => isInFlight(item.parse_status));
    const hasActiveReport = reports.some((item) => isInFlight(item.status));
    if (!hasActiveJob && !hasActiveReport) {
      return;
    }

    const accessToken = token;
    let cancelled = false;
    const timer = window.setInterval(() => {
      void (async () => {
        try {
          const [nextJobs, nextResumes] = await Promise.all([
            fetchJobList(accessToken),
            fetchResumeList(accessToken),
          ]);
          if (cancelled) {
            return;
          }
          setJobs(nextJobs);
          setResumes(nextResumes);

          const activeJobId =
            selectedJobId && nextJobs.some((item) => item.id === selectedJobId)
              ? selectedJobId
              : nextJobs[0]?.id ?? null;
          setSelectedJobId(activeJobId);
          if (activeJobId) {
            const nextReports = await fetchJobMatchReports(accessToken, activeJobId);
            if (cancelled) {
              return;
            }
            setReports(nextReports);
            setSelectedReportId((current) =>
              current && nextReports.some((item) => item.id === current)
                ? current
                : nextReports[0]?.id ?? null
            );
          } else {
            setReports([]);
            setSelectedReportId(null);
          }
        } catch (error) {
          if (!cancelled) {
            setPageError(getErrorMessage(error));
          }
        }
      })();
    }, 4000);

    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, [jobs, reports, selectedJobId, token]);

  if (!token) {
    return null;
  }

  if (isPageLoading) {
    return (
      <PageLoadingState
        title="正在加载目标岗位工作台"
        description="我们正在同步岗位画像、简历资产和匹配快照。"
      />
    );
  }

  if (pageError && jobs.length === 0) {
    return (
      <PageErrorState
        actionLabel="重新加载"
        description={pageError}
        onAction={() => window.location.reload()}
        title="岗位工作台加载失败"
      />
    );
  }

  function updateDraft(field: keyof JobDraft, value: string) {
    setJobDraft((current) => ({
      ...current,
      [field]: value,
    }));
  }

  async function reloadJobs(preferredJobId?: string | null) {
    if (!token) {
      return;
    }
    const nextJobs = await fetchJobList(token);
    setJobs(nextJobs);

    const nextSelectedId =
      preferredJobId && nextJobs.some((item) => item.id === preferredJobId)
        ? preferredJobId
        : nextJobs[0]?.id ?? null;

    setSelectedJobId(nextSelectedId);
    setJobDraft(
      nextSelectedId
        ? toJobDraft(nextJobs.find((item) => item.id === nextSelectedId)!)
        : createEmptyJobDraft()
    );
  }

  async function handleSaveJob() {
    if (!token) {
      return;
    }

    setIsSaving(true);
    setPageError("");

    try {
      const savedJob = selectedJobId
        ? await updateJob(token, selectedJobId, jobDraft)
        : await createJob(token, jobDraft);

      await reloadJobs(savedJob.id);
    } catch (error) {
      setPageError(getErrorMessage(error));
    } finally {
      setIsSaving(false);
    }
  }

  async function handleParseJob() {
    if (!token || !selectedJobId) {
      return;
    }

    setIsParsing(true);
    setPageError("");

    try {
      await parseJob(token, selectedJobId);
      await reloadJobs(selectedJobId);
    } catch (error) {
      setPageError(getErrorMessage(error));
    } finally {
      setIsParsing(false);
    }
  }

  async function handleDeleteJob() {
    if (!token || !selectedJobId || !selectedJob) {
      return;
    }

    const confirmed = window.confirm(
      `确认删除 JD《${selectedJob.title}》吗？若已有关联报告，系统会拒绝删除。`
    );
    if (!confirmed) {
      return;
    }

    setIsDeleting(true);
    setPageError("");

    try {
      await deleteJob(token, selectedJobId);
      await reloadJobs();
      setReports([]);
      setSelectedReportId(null);
    } catch (error) {
      setPageError(getErrorMessage(error));
    } finally {
      setIsDeleting(false);
    }
  }

  async function handleGenerateReport() {
    if (!token || !selectedJobId || !selectedResumeId) {
      return;
    }

    setIsGenerating(true);
    setPageError("");

    try {
      const report = await createJobMatchReport(token, selectedJobId, selectedResumeId);
      const nextReports = await fetchJobMatchReports(token, selectedJobId);
      setReports(nextReports);
      setSelectedReportId(report.id);
    } catch (error) {
      setPageError(getErrorMessage(error));
    } finally {
      setIsGenerating(false);
    }
  }

  async function handleDeleteReport() {
    if (!token || !selectedReportId || !selectedJobId) {
      return;
    }

    const confirmed = window.confirm("确认删除这份匹配报告吗？");
    if (!confirmed) {
      return;
    }

    setIsDeletingReport(true);
    setPageError("");

    try {
      await deleteMatchReport(token, selectedReportId);
      const nextReports = await fetchJobMatchReports(token, selectedJobId);
      setReports(nextReports);
      setSelectedReportId(nextReports[0]?.id ?? null);
      await reloadJobs(selectedJobId);
    } catch (error) {
      setPageError(getErrorMessage(error));
    } finally {
      setIsDeletingReport(false);
    }
  }

  return (
    <div className="space-y-8">
      {pageError ? (
        <Alert className="rounded-[1.5rem] border-[#ff3b30]/20 bg-[#fff5f5]">
          <AlertTitle className="text-black">操作提示</AlertTitle>
          <AlertDescription className="text-black/72">{pageError}</AlertDescription>
        </Alert>
      ) : null}

      <section className="grid gap-5 xl:grid-cols-[300px_minmax(0,1fr)_minmax(0,1.08fr)]">
        <div className="space-y-5">
          <Button
            className="w-full rounded-full bg-[#0071E3] text-white hover:bg-[#0077ED]"
            onClick={() => {
              setSelectedJobId(null);
              setReports([]);
              setSelectedReportId(null);
              setJobDraft(createEmptyJobDraft());
              setPageError("");
            }}
            type="button"
          >
            新建目标岗位
          </Button>

          {jobs.length === 0 ? (
            <PageEmptyState
              description="先创建一条 JD，系统会异步生成岗位画像并承接后续匹配。"
              title="还没有目标岗位"
            />
          ) : (
            <JobList
              items={jobs}
              onSelect={(jobId) => {
                setSelectedJobId(jobId);
                const nextJob = jobs.find((item) => item.id === jobId);
                setJobDraft(nextJob ? toJobDraft(nextJob) : createEmptyJobDraft());
                setSelectedResumeId(
                  nextJob?.recommended_resume_id ||
                    resumes.find((item) => item.parse_status === "success")?.id ||
                    ""
                );
                setPageError("");
              }}
              selectedJobId={selectedJobId}
            />
          )}
        </div>

        <JobFormCard
          draft={jobDraft}
          isDeleting={isDeleting}
          isParsing={isParsing}
          isSaving={isSaving}
          onChange={updateDraft}
          onCreateNew={() => {
            setSelectedJobId(null);
            setReports([]);
            setSelectedReportId(null);
            setJobDraft(createEmptyJobDraft());
            setPageError("");
          }}
          onDelete={handleDeleteJob}
          onParse={handleParseJob}
          onSave={handleSaveJob}
          pageError=""
          selectedJob={selectedJob}
        />

        <MatchReportPanel
          isDeletingReport={isDeletingReport}
          isGenerating={isGenerating}
          onDeleteReport={handleDeleteReport}
          onGenerate={handleGenerateReport}
          onSelectReport={setSelectedReportId}
          onSelectResume={setSelectedResumeId}
          reports={reports}
          resumes={resumes}
          selectedJob={selectedJob}
          selectedReportId={selectedReportId}
          selectedResumeId={selectedResumeId}
        />
      </section>
    </div>
  );
}
