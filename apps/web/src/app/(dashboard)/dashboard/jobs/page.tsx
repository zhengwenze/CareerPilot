"use client";

import { useEffect, useState } from "react";

import { JobFormCard } from "@/components/jobs/job-form-card";
import { JobList } from "@/components/jobs/job-list";
import { MatchReportPanel } from "@/components/jobs/match-report-panel";
import {
  PageEmptyState,
  PageErrorState,
  PageLoadingState,
} from "@/components/page-state";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
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
import {
  fetchResumeList,
  type ResumeRecord,
} from "@/lib/api/modules/resume";

function getErrorMessage(error: unknown) {
  if (error instanceof ApiError) {
    return error.message;
  }

  if (error instanceof Error) {
    return error.message;
  }

  return "操作失败，请稍后重试。";
}

export default function DashboardJobsPage() {
  const { token } = useAuth();
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
  const [bannerMessage, setBannerMessage] = useState("");

  const selectedJob =
    jobs.find((item) => item.id === selectedJobId) ?? null;

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

        const nextJobId = nextJobs[0]?.id ?? null;
        setSelectedJobId(nextJobId);
        setJobDraft(nextJobId ? toJobDraft(nextJobs[0]) : createEmptyJobDraft());

        const nextResumeId =
          nextResumes.find((item) => item.parse_status === "success")?.id ?? "";
        setSelectedResumeId(nextResumeId);
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
  }, [token]);

  useEffect(() => {
    if (!token || !selectedJobId) {
      setReports([]);
      setSelectedReportId(null);
      return;
    }

    const accessToken = token;
    const activeJobId = selectedJobId;
    let cancelled = false;

    async function loadReports() {
      try {
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

  if (!token) {
    return null;
  }

  if (isPageLoading) {
    return (
      <PageLoadingState
        title="正在加载岗位匹配模块"
        description="我们正在同步 JD 列表、简历列表和历史报告。"
      />
    );
  }

  if (pageError && jobs.length === 0) {
    return (
      <PageErrorState
        actionLabel="重新加载"
        description={pageError}
        onAction={() => window.location.reload()}
        title="岗位匹配模块加载失败"
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
    setBannerMessage("");

    try {
      const savedJob = selectedJobId
        ? await updateJob(token, selectedJobId, jobDraft)
        : await createJob(token, jobDraft);

      await reloadJobs(savedJob.id);
      setBannerMessage(
        selectedJobId
          ? "JD 已更新，并重新完成结构化。"
          : "JD 已创建，并完成第一版结构化。"
      );
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
    setBannerMessage("");

    try {
      await parseJob(token, selectedJobId);
      await reloadJobs(selectedJobId);
      setBannerMessage("JD 已重新执行结构化。");
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
    setBannerMessage("");

    try {
      const payload = await deleteJob(token, selectedJobId);
      await reloadJobs();
      setReports([]);
      setSelectedReportId(null);
      setBannerMessage(payload.message);
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
    setBannerMessage("");

    try {
      const report = await createJobMatchReport(token, selectedJobId, selectedResumeId);
      const nextReports = await fetchJobMatchReports(token, selectedJobId);
      setReports(nextReports);
      setSelectedReportId(report.id);
      setBannerMessage("新的匹配报告已生成。");
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
    setBannerMessage("");

    try {
      const payload = await deleteMatchReport(token, selectedReportId);
      const nextReports = await fetchJobMatchReports(token, selectedJobId);
      setReports(nextReports);
      setSelectedReportId(nextReports[0]?.id ?? null);
      setBannerMessage(payload.message);
    } catch (error) {
      setPageError(getErrorMessage(error));
    } finally {
      setIsDeletingReport(false);
    }
  }

  return (
    <>
      <Card className="surface-card border-0 bg-card/85 py-0 shadow-2xl shadow-emerald-950/8">
        <CardContent className="px-6 py-6 sm:px-8 sm:py-8">
          <div className="flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
            <div className="max-w-3xl space-y-4">
              <Badge className="w-fit rounded-full bg-primary/10 px-3 py-1 text-primary hover:bg-primary/10">
                Job Matching
              </Badge>
              <div className="space-y-3">
                <h2 className="text-4xl font-semibold tracking-tight text-foreground sm:text-5xl">
                  JD 结构化与岗位匹配分析
                </h2>
                <p className="max-w-2xl text-base leading-8 text-muted-foreground">
                  这里已经打通岗位匹配模块的第一版真实闭环：录入 JD、
                  自动结构化、选择简历、生成规则报告，并为后续 AI 修正预留接口。
                </p>
              </div>
            </div>

            <div className="rounded-[28px] border border-border/70 bg-white/72 p-4 shadow-sm">
              <p className="text-sm text-muted-foreground">当前路由</p>
              <p className="mt-2 text-base font-medium text-foreground">
                /dashboard/jobs
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {pageError ? (
        <Alert className="rounded-2xl border-destructive/20 bg-destructive/5">
          <AlertTitle>操作提示</AlertTitle>
          <AlertDescription>{pageError}</AlertDescription>
        </Alert>
      ) : null}

      {bannerMessage ? (
        <Alert className="rounded-2xl border-primary/20 bg-primary/5">
          <AlertTitle>状态更新</AlertTitle>
          <AlertDescription>{bannerMessage}</AlertDescription>
        </Alert>
      ) : null}

      <section className="grid gap-5 xl:grid-cols-[300px_minmax(0,1fr)_minmax(0,1.05fr)]">
        <div className="space-y-5">
          <Card className="surface-card border-0 bg-card/82 py-0 shadow-xl shadow-emerald-950/5">
            <CardContent className="space-y-4 px-5 py-5">
              <p className="text-sm leading-7 text-muted-foreground">
                左侧保留你的目标岗位列表，中间维护 JD 内容，右侧生成和查看匹配报告。
              </p>
              <Button
                className="w-full rounded-full"
                onClick={() => {
                  setSelectedJobId(null);
                  setReports([]);
                  setSelectedReportId(null);
                  setJobDraft(createEmptyJobDraft());
                  setBannerMessage("");
                  setPageError("");
                }}
                type="button"
                variant="outline"
              >
                新建目标岗位
              </Button>
            </CardContent>
          </Card>

          {jobs.length === 0 ? (
            <PageEmptyState
              description="先创建一条 JD，系统会自动完成第一版结构化。"
              title="还没有目标岗位"
            />
          ) : (
            <JobList
              items={jobs}
              onSelect={(jobId) => {
                setSelectedJobId(jobId);
                const nextJob = jobs.find((item) => item.id === jobId);
                setJobDraft(nextJob ? toJobDraft(nextJob) : createEmptyJobDraft());
                setBannerMessage("");
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
            setBannerMessage("");
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
    </>
  );
}
