"use client";

import { useEffect, useState } from "react";

import { useAuth } from "@/components/auth-provider";
import {
  PageEmptyState,
  PageErrorState,
  PageLoadingState,
} from "@/components/page-state";
import { ResumeDetailPanel } from "@/components/resume/resume-detail-panel";
import { ResumeList } from "@/components/resume/resume-list";
import { ResumeUploadCard } from "@/components/resume/resume-upload-card";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { ApiError } from "@/lib/api/client";
import {
  createEmptyStructuredResume,
  deleteResume,
  fetchResumeDetail,
  fetchResumeDownloadUrl,
  fetchResumeList,
  fetchResumeParseJobs,
  retryResumeParse,
  updateResumeStructuredData,
  uploadResume,
  type ResumeParseJob,
  type ResumeRecord,
  type ResumeStructuredData,
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

function logResumePage(event: string, payload?: Record<string, unknown>) {
  console.log(`[resume-page] ${event}`, payload ?? {});
}

function normalizeStructuredResume(
  value?: Partial<ResumeStructuredData> | null,
): ResumeStructuredData {
  const empty = createEmptyStructuredResume();

  return {
    basic_info: {
      ...empty.basic_info,
      ...(value?.basic_info ?? {}),
    },
    education: Array.isArray(value?.education) ? value.education : [],
    work_experience: Array.isArray(value?.work_experience)
      ? value.work_experience
      : [],
    projects: Array.isArray(value?.projects) ? value.projects : [],
    skills: {
      ...empty.skills,
      ...(value?.skills ?? {}),
      technical: Array.isArray(value?.skills?.technical)
        ? value.skills.technical
        : [],
      tools: Array.isArray(value?.skills?.tools) ? value.skills.tools : [],
      languages: Array.isArray(value?.skills?.languages)
        ? value.skills.languages
        : [],
    },
    certifications: Array.isArray(value?.certifications)
      ? value.certifications
      : [],
  };
}

async function loadResumeListData(
  token: string,
  preferredResumeId?: string | null,
) {
  logResumePage("load-list:start", { preferredResumeId });
  const items = await fetchResumeList(token);
  const nextSelectedId =
    preferredResumeId && items.some((item) => item.id === preferredResumeId)
      ? preferredResumeId
      : (items[0]?.id ?? null);

  logResumePage("load-list:done", {
    count: items.length,
    nextSelectedId,
  });
  return { items, nextSelectedId };
}

async function loadResumeDetailData(token: string, resumeId: string) {
  logResumePage("load-detail:start", { resumeId });
  const resume = await fetchResumeDetail(token, resumeId);
  const jobsResult = await Promise.allSettled([
    fetchResumeParseJobs(token, resumeId),
  ]);
  const jobs = jobsResult[0].status === "fulfilled" ? jobsResult[0].value : [];

  logResumePage("load-detail:done", {
    resumeId,
    parseStatus: resume.parse_status,
    parseError: resume.parse_error,
    hasStructuredJson: Boolean(resume.structured_json),
    jobsCount: jobs.length,
    parseJobsRequestOk: jobsResult[0].status === "fulfilled",
  });
  return { resume, jobs };
}

function upsertResumeRecord(items: ResumeRecord[], resume: ResumeRecord) {
  const index = items.findIndex((item) => item.id === resume.id);
  if (index === -1) {
    return [resume, ...items];
  }

  return items.map((item) => (item.id === resume.id ? resume : item));
}

function PaperSection({
  title,
  eyebrow,
  children,
}: {
  title: string;
  eyebrow?: string;
  children: React.ReactNode;
}) {
  return (
    <section className="border-b border-[#1C1C1C]/10 bg-[#F9F8F6]">
      <div className="border-b border-[#1C1C1C]/10 px-5 py-4 sm:px-6">
        {eyebrow ? (
          <div className="mb-3 flex items-center gap-3">
            <span className="size-2.5 bg-[#1C1C1C]" />
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

export default function DashboardResumePage() {
  const { token } = useAuth();
  const [resumes, setResumes] = useState<ResumeRecord[]>([]);
  const [selectedResumeId, setSelectedResumeId] = useState<string | null>(null);
  const [selectedResume, setSelectedResume] = useState<ResumeRecord | null>(
    null,
  );
  const [parseJobs, setParseJobs] = useState<ResumeParseJob[]>([]);
  const [structuredValue, setStructuredValue] = useState<ResumeStructuredData>(
    createEmptyStructuredResume(),
  );
  const [isPageLoading, setIsPageLoading] = useState(true);
  const [isUploading, setIsUploading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [isRetrying, setIsRetrying] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [pageError, setPageError] = useState("");
  const [isStructuredDirty, setIsStructuredDirty] = useState(false);

  function applyResumeDetail(
    detail: Awaited<ReturnType<typeof loadResumeDetailData>>,
    options?: {
      preserveDraft?: boolean;
    },
  ) {
    logResumePage("apply-detail", {
      resumeId: detail.resume.id,
      parseStatus: detail.resume.parse_status,
      parseError: detail.resume.parse_error,
      hasRawText: Boolean(detail.resume.raw_text),
      rawTextLength: detail.resume.raw_text?.length ?? 0,
      hasStructuredJson: Boolean(detail.resume.structured_json),
      preserveDraft: options?.preserveDraft ?? false,
      jobsCount: detail.jobs.length,
    });
    setSelectedResume(detail.resume);
    setParseJobs(detail.jobs);
    setResumes((current) => upsertResumeRecord(current, detail.resume));

    if (!options?.preserveDraft) {
      setStructuredValue(
        normalizeStructuredResume(detail.resume.structured_json),
      );
      setIsStructuredDirty(false);
    }
  }

  useEffect(() => {
    if (!token) {
      return;
    }

    const accessToken = token;
    let cancelled = false;

    async function bootstrap() {
      setIsPageLoading(true);
      setPageError("");
      logResumePage("bootstrap:start");

      try {
        const result = await loadResumeListData(accessToken);
        if (cancelled) {
          return;
        }

        setResumes(result.items);
        setSelectedResumeId(result.nextSelectedId);

        if (result.nextSelectedId) {
          const detail = await loadResumeDetailData(
            accessToken,
            result.nextSelectedId,
          );
          if (!cancelled) {
            applyResumeDetail(detail);
          }
        } else {
          setSelectedResume(null);
          setParseJobs([]);
          setStructuredValue(createEmptyStructuredResume());
          setIsStructuredDirty(false);
        }
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
    if (!token || !selectedResumeId) {
      return;
    }
    if (selectedResume?.id === selectedResumeId) {
      return;
    }

    const accessToken = token;
    let cancelled = false;

    async function syncDetail() {
      if (!selectedResumeId) {
        return;
      }
      try {
        const detail = await loadResumeDetailData(
          accessToken,
          selectedResumeId,
        );
        if (!cancelled) {
          applyResumeDetail(detail);
        }
      } catch (error) {
        if (!cancelled) {
          setPageError(getErrorMessage(error));
        }
      }
    }

    void syncDetail();

    return () => {
      cancelled = true;
    };
  }, [selectedResume?.id, selectedResumeId, token]);

  useEffect(() => {
    if (!token || !selectedResumeId || !selectedResume) {
      return;
    }
    if (!["pending", "processing"].includes(selectedResume.parse_status)) {
      return;
    }

    const accessToken = token;
    let cancelled = false;
    const timer = window.setInterval(() => {
      void (async () => {
        if (!selectedResumeId) {
          return;
        }
        try {
          const result = await loadResumeListData(
            accessToken,
            selectedResumeId,
          );
          if (cancelled) {
            return;
          }

          setResumes(result.items);
          setSelectedResumeId(result.nextSelectedId);

          if (result.nextSelectedId) {
            const detail = await loadResumeDetailData(
              accessToken,
              result.nextSelectedId,
            );
            if (!cancelled) {
              applyResumeDetail(detail, { preserveDraft: isStructuredDirty });
            }
          }
        } catch (error) {
          if (!cancelled) {
            setPageError(getErrorMessage(error));
          }
        }
      })();
    }, 3000);

    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, [isStructuredDirty, selectedResume, selectedResumeId, token]);

  if (!token) {
    return null;
  }

  if (isPageLoading) {
    return (
      <PageLoadingState
        title="正在加载简历中心"
        description="我们正在同步你的简历列表、解析状态和结构化结果。"
      />
    );
  }

  if (pageError && resumes.length === 0) {
    return (
      <PageErrorState
        actionLabel="重新加载"
        description={pageError}
        onAction={() => window.location.reload()}
        title="简历中心加载失败"
      />
    );
  }

  async function handleUpload(file: File) {
    if (!token) {
      return;
    }

    setIsUploading(true);
    setPageError("");

    try {
      const uploadedResume = await uploadResume(token, file);
      const result = await loadResumeListData(token, uploadedResume.id);
      setResumes(result.items);
      setSelectedResumeId(result.nextSelectedId);

      if (result.nextSelectedId) {
        const detail = await loadResumeDetailData(token, result.nextSelectedId);
        applyResumeDetail(detail);
      }
    } catch (error) {
      setPageError(getErrorMessage(error));
    } finally {
      setIsUploading(false);
    }
  }

  async function handleSelectResume(resumeId: string) {
    if (resumeId === selectedResumeId) {
      return;
    }

    if (isStructuredDirty) {
      const confirmed = window.confirm(
        "当前简历有未保存的人工修改，切换后会丢失这些内容。确认继续吗？",
      );
      if (!confirmed) {
        return;
      }
    }

    setSelectedResumeId(resumeId);
    setPageError("");
  }

  async function handleSaveStructured() {
    if (!token || !selectedResumeId) {
      return;
    }

    setIsSaving(true);
    setPageError("");

    try {
      const updatedResume = await updateResumeStructuredData(
        token,
        selectedResumeId,
        structuredValue,
      );
      setSelectedResume(updatedResume);
      setStructuredValue(
        normalizeStructuredResume(updatedResume.structured_json),
      );
      setIsStructuredDirty(false);
      const result = await loadResumeListData(token, selectedResumeId);
      setResumes(result.items);
      setSelectedResumeId(result.nextSelectedId);
    } catch (error) {
      setPageError(getErrorMessage(error));
    } finally {
      setIsSaving(false);
    }
  }

  async function handleRetryParse() {
    if (!token || !selectedResumeId) {
      return;
    }

    setIsRetrying(true);
    setPageError("");
    setIsStructuredDirty(false);

    try {
      await retryResumeParse(token, selectedResumeId);
      const result = await loadResumeListData(token, selectedResumeId);
      setResumes(result.items);
      setSelectedResumeId(result.nextSelectedId);

      const detail = await loadResumeDetailData(token, selectedResumeId);
      applyResumeDetail(detail);
    } catch (error) {
      setPageError(getErrorMessage(error));
    } finally {
      setIsRetrying(false);
    }
  }

  async function handleDownload() {
    if (!token || !selectedResumeId) {
      return;
    }

    try {
      const payload = await fetchResumeDownloadUrl(token, selectedResumeId);
      window.open(payload.download_url, "_blank", "noopener,noreferrer");
    } catch (error) {
      setPageError(getErrorMessage(error));
    }
  }

  async function handleDelete() {
    if (!token || !selectedResumeId || !selectedResume) {
      return;
    }

    const confirmed = window.confirm(
      `确认删除简历《${selectedResume.file_name}》吗？这会同时删除 MinIO 中的原始文件。`,
    );
    if (!confirmed) {
      return;
    }

    setIsDeleting(true);
    setPageError("");

    try {
      await deleteResume(token, selectedResumeId);
      const result = await loadResumeListData(token);

      setResumes(result.items);
      setSelectedResumeId(result.nextSelectedId);

      if (result.nextSelectedId) {
        const detail = await loadResumeDetailData(token, result.nextSelectedId);
        applyResumeDetail(detail);
      } else {
        setSelectedResume(null);
        setParseJobs([]);
        setStructuredValue(createEmptyStructuredResume());
        setIsStructuredDirty(false);
      }
    } catch (error) {
      setPageError(getErrorMessage(error));
    } finally {
      setIsDeleting(false);
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
                Resume Center
              </span>
            </div>

            <div className="mt-6">
              <h1 className="text-3xl font-semibold tracking-tight text-[#1C1C1C] sm:text-4xl">
                简历中心
              </h1>
            </div>

            <p className="mt-5 max-w-3xl text-base leading-relaxed text-[#1C1C1C]/60 sm:text-[1.05rem]">
              上传 PDF
              简历、查看解析状态、修正结构化结果，并从同一工作台完成下载、
              重试解析与删除等操作。
            </p>
          </div>

          <div className="flex flex-wrap gap-3">
            <div className="border border-[#1C1C1C]/10 bg-white px-4 py-2 text-sm font-medium text-[#1C1C1C]">
              {resumes.length} 份简历
            </div>
            <div className="border border-[#1C1C1C]/10 bg-white px-4 py-2 text-sm font-medium text-[#1C1C1C]">
              {selectedResume ? "已选中详情" : "等待选择"}
            </div>
          </div>
        </div>
      </header>

      {pageError ? (
        <Alert className="border border-[#1C1C1C]/10 bg-[#F9F8F6] text-[#1C1C1C]">
          <AlertTitle className="text-base font-semibold tracking-tight text-[#1C1C1C]">
            操作提示
          </AlertTitle>
          <AlertDescription className="text-sm leading-relaxed text-[#1C1C1C]/60">
            {pageError}
          </AlertDescription>
        </Alert>
      ) : null}

      <section className="grid gap-6 xl:grid-cols-[360px_minmax(0,1fr)]">
        <div className="space-y-6">
          <PaperSection title="上传入口" eyebrow="Resume Upload">
            <ResumeUploadCard
              isUploading={isUploading}
              onUpload={handleUpload}
            />
          </PaperSection>

          <PaperSection title="简历列表" eyebrow="Stored Files">
            {resumes.length === 0 ? (
              <PageEmptyState
                description="先上传一份 PDF 简历，系统会自动进入解析流程。"
                title="还没有简历"
              />
            ) : (
              <ResumeList
                items={resumes}
                onSelect={handleSelectResume}
                selectedResumeId={selectedResumeId}
              />
            )}
          </PaperSection>
        </div>

        <div className="border-b border-[#1C1C1C]/10 bg-[#F9F8F6]">
          <div className="border-b border-[#1C1C1C]/10 px-5 py-4 sm:px-6">
            <div className="mb-3 flex items-center gap-3">
              <span className="size-2.5 bg-[#1C1C1C]" />
              <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[#1C1C1C]/60">
                Structured Resume Workspace
              </p>
            </div>
            <h2 className="text-xl font-semibold tracking-tight text-[#1C1C1C]">
              简历详情与结构化编辑
            </h2>
          </div>

          <div className="px-5 py-5 sm:px-6">
            <ResumeDetailPanel
              isDeleting={isDeleting}
              isStructuredDirty={isStructuredDirty}
              isRetrying={isRetrying}
              isSaving={isSaving}
              onChangeStructured={(value) => {
                setStructuredValue(value);
                setIsStructuredDirty(true);
              }}
              onDelete={handleDelete}
              onDownload={handleDownload}
              onRetry={handleRetryParse}
              onSave={handleSaveStructured}
              parseJobs={parseJobs}
              resume={selectedResume}
              structuredValue={structuredValue}
            />
          </div>
        </div>
      </section>
    </div>
  );
}
