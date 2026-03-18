"use client";

import { Download, RefreshCw, Save, Trash2 } from "lucide-react";

import { PageEmptyState } from "@/components/page-state";
import { ResumeStructuredEditor } from "@/components/resume/resume-structured-editor";
import {
  getResumeAIStatusMeta,
  getResumeStatusMeta,
} from "@/components/resume/status-meta";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";
import type {
  ResumeParseJob,
  ResumeRecord,
  ResumeStructuredData,
} from "@/lib/api/modules/resume";

function formatDate(value: string) {
  return new Intl.DateTimeFormat("zh-CN", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

function getAIMessageTone(status: string | null | undefined) {
  if (status === "pending") {
    return "text-[#0071E3]";
  }
  if (status === "fallback_rule") {
    return "text-[#B26A00]";
  }
  if (status === "skipped") {
    return "text-black/58";
  }
  return "text-black/62";
}

export function ResumeDetailPanel({
  resume,
  parseJobs,
  structuredValue,
  isStructuredDirty,
  isSaving,
  isRetrying,
  isDeleting,
  onChangeStructured,
  onSave,
  onRetry,
  onDownload,
  onDelete,
}: {
  resume: ResumeRecord | null;
  parseJobs: ResumeParseJob[];
  structuredValue: ResumeStructuredData;
  isStructuredDirty: boolean;
  isSaving: boolean;
  isRetrying: boolean;
  isDeleting: boolean;
  onChangeStructured: (value: ResumeStructuredData) => void;
  onSave: () => void;
  onRetry: () => void;
  onDownload: () => void;
  onDelete: () => void;
}) {
  if (!resume) {
    return (
      <PageEmptyState
        description="左侧上传或选择一份简历后，这里会展示解析状态、原文预览和结构化编辑区。"
        title="还没有选中简历"
      />
    );
  }

  const statusMeta = getResumeStatusMeta(resume.parse_status);
  const aiStatusMeta = getResumeAIStatusMeta(
    resume.latest_parse_job?.ai_status,
    resume.latest_parse_job?.ai_message
  );
  const latestAIMessage =
    resume.latest_parse_job?.ai_message?.trim() || "";
  const showLatestAIMessage =
    Boolean(latestAIMessage) &&
    ["pending", "fallback_rule", "skipped"].includes(
      resume.latest_parse_job?.ai_status ?? ""
    );

  return (
    <div className="space-y-5">
      <Card className="rounded-[2rem] border border-black/10 bg-white py-0 shadow-[0_18px_48px_rgba(0,0,0,0.05)]">
        <CardContent className="px-6 py-6 sm:px-8 sm:py-8">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
            <div className="space-y-3">
              <div className="flex flex-wrap items-center gap-2">
                <Badge
                  className={cn(
                    "rounded-full px-3 py-1 hover:bg-inherit",
                    statusMeta.className
                  )}
                >
                  {statusMeta.label}
                </Badge>
                {aiStatusMeta ? (
                  <Badge
                    className={cn(
                      "rounded-full px-3 py-1 hover:bg-inherit",
                      aiStatusMeta.className
                    )}
                  >
                    {aiStatusMeta.label}
                  </Badge>
                ) : null}
                {isStructuredDirty ? (
                  <Badge className="rounded-full bg-[#FFF7E6] px-3 py-1 text-[#B26A00] hover:bg-[#FFF7E6]">
                    有未保存修改
                  </Badge>
                ) : null}
              </div>
              <div className="space-y-2">
                <h2 className="text-3xl font-semibold tracking-[-0.04em] text-black">
                  {resume.file_name}
                </h2>
                <p className="text-sm leading-7 text-black/62">
                  上传时间 {formatDate(resume.created_at)}，文件大小{" "}
                  {(resume.file_size / 1024).toFixed(1)} KB，当前版本 v
                  {resume.latest_version}
                </p>
              </div>
              {showLatestAIMessage ? (
                <p
                  className={cn(
                    "text-sm",
                    getAIMessageTone(resume.latest_parse_job?.ai_status)
                  )}
                >
                  {latestAIMessage}
                </p>
              ) : null}
            </div>

            <div className="flex flex-wrap gap-2">
              <Button
                className="rounded-full border-black/10 bg-white text-black hover:bg-[#f5f5f7]"
                disabled={isRetrying}
                onClick={onRetry}
                type="button"
                variant="outline"
              >
                {isRetrying ? "重新解析中..." : "重试解析"}
                <RefreshCw className="size-4" />
              </Button>
              <Button
                className="rounded-full border-black/10 bg-white text-black hover:bg-[#f5f5f7]"
                onClick={onDownload}
                type="button"
                variant="outline"
              >
                下载原文件
                <Download className="size-4" />
              </Button>
              <Button
                className="rounded-full"
                disabled={isDeleting}
                onClick={onDelete}
                type="button"
                variant="destructive"
              >
                {isDeleting ? "删除中..." : "删除简历"}
                <Trash2 className="size-4" />
              </Button>
              <Button
                className="rounded-full bg-[#0071E3] text-white hover:bg-[#0077ED]"
                disabled={isSaving || !isStructuredDirty}
                onClick={onSave}
                type="button"
              >
                {isSaving
                  ? "保存中..."
                  : isStructuredDirty
                    ? "保存人工修正"
                    : "暂无待保存修改"}
                <Save className="size-4" />
              </Button>
            </div>
          </div>

          {resume.parse_error ? (
            <Alert className="mt-5 rounded-[1.5rem] border-[#ff3b30]/20 bg-[#fff5f5]">
              <AlertTitle className="text-black">解析失败</AlertTitle>
              <AlertDescription className="text-black/72">
                {resume.parse_error}
              </AlertDescription>
            </Alert>
          ) : null}
        </CardContent>
      </Card>

      <section className="grid gap-5 xl:grid-cols-[1.05fr_0.95fr]">
        <Card className="rounded-[2rem] border border-black/10 bg-[#f5f5f7] py-0 shadow-none">
          <CardHeader className="px-6 py-6">
            <CardTitle className="text-2xl font-semibold tracking-[-0.04em] text-black">
              原始文本预览
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-5 px-6 pb-6">
            <Textarea
              className="min-h-[360px] rounded-[1.75rem] border-black/10 bg-white font-mono text-xs leading-6 text-black focus-visible:border-[#0071E3] focus-visible:ring-[#0071E3]/20"
              readOnly
              value={
                resume.raw_text ??
                "解析尚未完成，完成后这里会展示抽取出来的原始文本。"
              }
            />

            <div className="space-y-3">
              <p className="text-sm font-medium text-black">解析任务记录</p>
              <div className="space-y-3">
                {parseJobs.length === 0 ? (
                  <div className="rounded-[1.5rem] border border-dashed border-black/12 bg-white px-4 py-4 text-sm text-black/58">
                    还没有解析任务记录。
                  </div>
                ) : null}
                {parseJobs.map((job) => {
                  const jobStatusMeta = getResumeStatusMeta(job.status);
                  const jobAiStatusMeta = getResumeAIStatusMeta(
                    job.ai_status,
                    job.ai_message
                  );

                  return (
                    <div
                      className="rounded-[1.5rem] border border-black/10 bg-white px-4 py-4"
                      key={job.id}
                    >
                      <div className="flex flex-wrap items-center justify-between gap-3">
                        <div className="flex flex-wrap items-center gap-2">
                          <Badge
                            className={cn(
                              "rounded-full px-3 py-1 hover:bg-inherit",
                              jobStatusMeta.className
                            )}
                          >
                            {jobStatusMeta.label}
                          </Badge>
                          {jobAiStatusMeta ? (
                            <Badge
                              className={cn(
                                "rounded-full px-3 py-1 hover:bg-inherit",
                                jobAiStatusMeta.className
                              )}
                            >
                              {jobAiStatusMeta.label}
                            </Badge>
                          ) : null}
                        </div>
                        <span className="text-xs text-black/45">
                          尝试 {job.attempt_count} 次
                        </span>
                      </div>
                      <p className="mt-3 text-xs leading-6 text-black/55">
                        创建于 {formatDate(job.created_at)}
                        {job.finished_at ? `，结束于 ${formatDate(job.finished_at)}` : ""}
                      </p>
                      {job.ai_message &&
                      ["pending", "fallback_rule", "skipped"].includes(
                        job.ai_status ?? ""
                      ) ? (
                        <p
                          className={cn(
                            "mt-2 text-sm",
                            getAIMessageTone(job.ai_status)
                          )}
                        >
                          {job.ai_message}
                        </p>
                      ) : null}
                      {job.error_message ? (
                        <p className="mt-2 text-sm text-[#D93025]">
                          {job.error_message}
                        </p>
                      ) : null}
                    </div>
                  );
                })}
              </div>
            </div>
          </CardContent>
        </Card>

        <ResumeStructuredEditor
          onChange={onChangeStructured}
          value={structuredValue}
        />
      </section>
    </div>
  );
}
