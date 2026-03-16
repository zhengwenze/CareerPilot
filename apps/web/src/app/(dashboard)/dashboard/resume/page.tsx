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
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
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
  value?: Partial<ResumeStructuredData> | null
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
  preferredResumeId?: string | null
) {
  logResumePage("load-list:start", { preferredResumeId });
  const items = await fetchResumeList(token);
  const nextSelectedId =
    preferredResumeId && items.some((item) => item.id === preferredResumeId)
      ? preferredResumeId
      : items[0]?.id ?? null;

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
  const jobs =
    jobsResult[0].status === "fulfilled" ? jobsResult[0].value : [];

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

export default function DashboardResumePage() {
  const { token } = useAuth();
  const [resumes, setResumes] = useState<ResumeRecord[]>([]);
  const [selectedResumeId, setSelectedResumeId] = useState<string | null>(null);
  const [selectedResume, setSelectedResume] = useState<ResumeRecord | null>(
    null
  );
  const [parseJobs, setParseJobs] = useState<ResumeParseJob[]>([]);
  const [structuredValue, setStructuredValue] = useState<ResumeStructuredData>(
    createEmptyStructuredResume()
  );
  const [isPageLoading, setIsPageLoading] = useState(true);
  const [isUploading, setIsUploading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [isRetrying, setIsRetrying] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [pageError, setPageError] = useState("");
  const [bannerMessage, setBannerMessage] = useState("");
  const [isStructuredDirty, setIsStructuredDirty] = useState(false);

  function applyResumeDetail(
    detail: Awaited<ReturnType<typeof loadResumeDetailData>>,
    options?: {
      preserveDraft?: boolean;
    }
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

    if (!options?.preserveDraft) {
      setStructuredValue(normalizeStructuredResume(detail.resume.structured_json));
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

        if (result?.nextSelectedId) {
          const detail = await loadResumeDetailData(
            accessToken,
            result.nextSelectedId
          );
          if (cancelled) {
            return;
          }

          applyResumeDetail(detail);
        } else {
          setSelectedResume(null);
          setParseJobs([]);
          setStructuredValue(createEmptyStructuredResume());
          setIsStructuredDirty(false);
        }
      } catch (error) {
        logResumePage("bootstrap:error", {
          message: getErrorMessage(error),
        });
        if (!cancelled) {
          setPageError(getErrorMessage(error));
        }
      } finally {
        logResumePage("bootstrap:done");
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
    const activeResumeId = selectedResumeId;

    async function syncDetail() {
      try {
        logResumePage("sync-detail:start", { resumeId: activeResumeId });
        const detail = await loadResumeDetailData(accessToken, activeResumeId);
        if (cancelled) {
          return;
        }

        applyResumeDetail(detail);
      } catch (error) {
        logResumePage("sync-detail:error", {
          resumeId: activeResumeId,
          message: getErrorMessage(error),
        });
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
      const activeResumeId = selectedResumeId;
      void (async () => {
        try {
          logResumePage("poll:start", {
            resumeId: activeResumeId,
            currentStatus: selectedResume.parse_status,
            preserveDraft: isStructuredDirty,
          });
          const result = await loadResumeListData(accessToken, activeResumeId);
          if (cancelled) {
            return;
          }

          setResumes(result.items);
          setSelectedResumeId(result.nextSelectedId);

          if (result?.nextSelectedId) {
            const detail = await loadResumeDetailData(
              accessToken,
              result.nextSelectedId
            );
            if (cancelled) {
              return;
            }

            applyResumeDetail(detail, { preserveDraft: isStructuredDirty });
          }
        } catch (error) {
          logResumePage("poll:error", {
            resumeId: activeResumeId,
            message: getErrorMessage(error),
          });
          if (!cancelled) {
            setPageError(getErrorMessage(error));
          }
        }
      })();
    }, 5000);

    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, [
    isStructuredDirty,
    selectedResume,
    selectedResumeId,
    token,
  ]);

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

    logResumePage("upload:start", {
      fileName: file.name,
      fileSize: file.size,
    });
    setIsUploading(true);
    setPageError("");
    setBannerMessage("");

    try {
      const uploadedResume = await uploadResume(token, file);
      const result = await loadResumeListData(token, uploadedResume.id);
      setResumes(result.items);
      setSelectedResumeId(result.nextSelectedId);

      if (result?.nextSelectedId) {
        const detail = await loadResumeDetailData(token, result.nextSelectedId);
        applyResumeDetail(detail);
      }
      setBannerMessage("简历已上传，系统正在自动解析。");
    } catch (error) {
      logResumePage("upload:error", {
        fileName: file.name,
        message: getErrorMessage(error),
      });
      setPageError(getErrorMessage(error));
    } finally {
      logResumePage("upload:done", {
        fileName: file.name,
      });
      setIsUploading(false);
    }
  }

  async function handleSelectResume(resumeId: string) {
    if (resumeId === selectedResumeId) {
      return;
    }

    logResumePage("select-resume", {
      fromResumeId: selectedResumeId,
      toResumeId: resumeId,
      hasDirtyDraft: isStructuredDirty,
    });
    if (isStructuredDirty) {
      const confirmed = window.confirm(
        "当前简历有未保存的人工修改，切换后会丢失这些内容。确认继续吗？"
      );
      if (!confirmed) {
        return;
      }
    }

    setSelectedResumeId(resumeId);
    setPageError("");
    setBannerMessage("");
  }

  async function handleSaveStructured() {
    if (!token || !selectedResumeId) {
      return;
    }

    setIsSaving(true);
    setPageError("");
    setBannerMessage("");
    logResumePage("save-structured:start", {
      resumeId: selectedResumeId,
      educationCount: structuredValue.education.length,
      workCount: structuredValue.work_experience.length,
      projectCount: structuredValue.projects.length,
    });

    try {
      const updatedResume = await updateResumeStructuredData(
        token,
        selectedResumeId,
        structuredValue
      );
      setSelectedResume(updatedResume);
      setStructuredValue(normalizeStructuredResume(updatedResume.structured_json));
      setIsStructuredDirty(false);
      const result = await loadResumeListData(token, selectedResumeId);
      setResumes(result.items);
      setSelectedResumeId(result.nextSelectedId);
      setBannerMessage(
        "人工修正已保存，后续匹配和面试模块会直接使用这份结构化结果。"
      );
    } catch (error) {
      logResumePage("save-structured:error", {
        resumeId: selectedResumeId,
        message: getErrorMessage(error),
      });
      setPageError(getErrorMessage(error));
    } finally {
      logResumePage("save-structured:done", {
        resumeId: selectedResumeId,
      });
      setIsSaving(false);
    }
  }

  async function handleRetryParse() {
    if (!token || !selectedResumeId) {
      return;
    }

    setIsRetrying(true);
    setPageError("");
    setBannerMessage("");
    setIsStructuredDirty(false);
    logResumePage("retry:start", {
      resumeId: selectedResumeId,
    });

    try {
      const retryResult = await retryResumeParse(token, selectedResumeId);
      setSelectedResume(retryResult);
      const result = await loadResumeListData(token, selectedResumeId);
      setResumes(result.items);
      setSelectedResumeId(result.nextSelectedId);

      const detail = await loadResumeDetailData(token, selectedResumeId);
      applyResumeDetail(detail);
      setBannerMessage("已经重新触发解析任务，请稍候查看最新结果。");
    } catch (error) {
      logResumePage("retry:error", {
        resumeId: selectedResumeId,
        message: getErrorMessage(error),
      });
      setPageError(getErrorMessage(error));
    } finally {
      logResumePage("retry:done", {
        resumeId: selectedResumeId,
      });
      setIsRetrying(false);
    }
  }

  async function handleDownload() {
    if (!token || !selectedResumeId) {
      return;
    }

    try {
      logResumePage("download:start", {
        resumeId: selectedResumeId,
      });
      const payload = await fetchResumeDownloadUrl(token, selectedResumeId);
      window.open(payload.download_url, "_blank", "noopener,noreferrer");
    } catch (error) {
      logResumePage("download:error", {
        resumeId: selectedResumeId,
        message: getErrorMessage(error),
      });
      setPageError(getErrorMessage(error));
    }
  }

  async function handleDelete() {
    if (!token || !selectedResumeId || !selectedResume) {
      return;
    }

    const confirmed = window.confirm(
      `确认删除简历《${selectedResume.file_name}》吗？这会同时删除 MinIO 中的原始文件。`
    );
    if (!confirmed) {
      return;
    }

    setIsDeleting(true);
    setPageError("");
    setBannerMessage("");
    logResumePage("delete:start", {
      resumeId: selectedResumeId,
      fileName: selectedResume.file_name,
    });

    try {
      const deletedResumeId = selectedResumeId;
      const payload = await deleteResume(token, deletedResumeId);
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

      setBannerMessage(
        payload.message === "Resume deleted successfully"
          ? "简历已删除，列表和存储文件都已同步清理。"
          : payload.message
      );
      if (deletedResumeId === selectedResumeId) {
        setPageError("");
      }
    } catch (error) {
      logResumePage("delete:error", {
        resumeId: selectedResumeId,
        message: getErrorMessage(error),
      });
      setPageError(getErrorMessage(error));
    } finally {
      logResumePage("delete:done", {
        resumeId: selectedResumeId,
      });
      setIsDeleting(false);
    }
  }

  return (
    <>
      <Card className="surface-card border-0 bg-card/85 py-0 shadow-2xl shadow-emerald-950/8">
        <CardContent className="px-6 py-6 sm:px-8 sm:py-8">
          <div className="flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
            <div className="max-w-3xl space-y-4">
              <Badge className="w-fit rounded-full bg-primary/10 px-3 py-1 text-primary hover:bg-primary/10">
                Resume Center
              </Badge>
              <div className="space-y-3">
                <h2 className="text-4xl font-semibold tracking-tight text-foreground sm:text-5xl">
                  简历上传、解析与人工校正
                </h2>
                <p className="max-w-2xl text-base leading-8 text-muted-foreground">
                  这里是简历中心的第一版真实工作流：上传 PDF
                  后自动解析文本和结构化结果，解析失败可重试，解析成功后可以直接人工修正并保存。
                </p>
              </div>
            </div>

            <div className="rounded-[28px] border border-border/70 bg-white/72 p-4 shadow-sm">
              <p className="text-sm text-muted-foreground">当前路由</p>
              <p className="mt-2 text-base font-medium text-foreground">
                /dashboard/resume
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

      <section className="grid gap-5 xl:grid-cols-[360px_minmax(0,1fr)]">
        <div className="space-y-5">
          <ResumeUploadCard isUploading={isUploading} onUpload={handleUpload} />
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
        </div>

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
      </section>
    </>
  );
}
