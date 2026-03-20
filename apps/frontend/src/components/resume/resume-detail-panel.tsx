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
    return "text-black";
  }
  if (status === "fallback_rule") {
    return "text-black";
  }
  if (status === "skipped") {
    return "text-black";
  }
  return "text-black";
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
    <div className="space-y-0">
      <div className="border-2 border-black bg-white p-6">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div className="space-y-3">
            <div className="flex flex-wrap items-center gap-2">
              <Badge className={cn("font-mono text-xs", statusMeta.className)}>
                {statusMeta.label}
              </Badge>
              {aiStatusMeta ? (
                <Badge className={cn("font-mono text-xs", aiStatusMeta.className)}>
                  {aiStatusMeta.label}
                </Badge>
              ) : null}
              {isStructuredDirty ? (
                <Badge className="border-2 border-black bg-white font-mono text-xs text-black">
                  有未保存修改
                </Badge>
              ) : null}
            </div>
            <div className="space-y-2">
              <h2 className="font-serif text-3xl font-bold tracking-tight text-black">
                {resume.file_name}
              </h2>
              <p className="font-mono text-sm leading-7 text-black">
                上传时间 {formatDate(resume.created_at)}，文件大小{" "}
                {(resume.file_size / 1024).toFixed(1)} KB，当前版本 v
                {resume.latest_version}
              </p>
            </div>
            {showLatestAIMessage ? (
              <p
                className={cn(
                  "font-mono text-sm",
                  getAIMessageTone(resume.latest_parse_job?.ai_status)
                )}
              >
                {latestAIMessage}
              </p>
            ) : null}
          </div>

          <div className="flex flex-wrap gap-2">
            <Button
              disabled={isRetrying}
              onClick={onRetry}
              type="button"
              variant="secondary"
            >
              {isRetrying ? "重新解析中..." : "重试解析"}
              <RefreshCw className="ml-2 size-4" />
            </Button>
            <Button
              onClick={onDownload}
              type="button"
              variant="secondary"
            >
              下载原文件
              <Download className="ml-2 size-4" />
            </Button>
            <Button
              onClick={onDelete}
              type="button"
              variant="destructive"
            >
              {isDeleting ? "删除中..." : "删除简历"}
              <Trash2 className="ml-2 size-4" />
            </Button>
            <Button
              disabled={isSaving || !isStructuredDirty}
              onClick={onSave}
              type="button"
            >
              {isSaving
                ? "保存中..."
                : isStructuredDirty
                  ? "保存人工修正"
                  : "暂无待保存修改"}
              <Save className="ml-2 size-4" />
            </Button>
          </div>
        </div>

        {resume.parse_error ? (
          <Alert className="mt-5 border-2 border-black bg-white font-mono">
            <AlertTitle className="font-serif text-lg font-bold text-black">
              解析失败
            </AlertTitle>
            <AlertDescription className="font-mono text-sm leading-7 text-black">
              {resume.parse_error}
            </AlertDescription>
          </Alert>
        ) : null}
      </div>

      <div className="grid gap-0 lg:grid-cols-2">
        <div className="border-2 border-t-0 border-black p-6">
          <h3 className="font-serif text-xl font-bold text-black">
            原始文本预览
          </h3>
          <Textarea
            className="mt-4 min-h-[360px] border-2 border-black bg-white font-mono text-xs leading-6 text-black focus:bg-[#ffffcc]"
            readOnly
            value={
              resume.raw_text ??
              "解析尚未完成，完成后这里会展示抽取出来的原始文本。"
            }
          />

          <div className="mt-6">
            <h4 className="font-mono text-sm font-bold uppercase text-black">
              解析任务记录
            </h4>
            <div className="mt-3 space-y-3">
              {parseJobs.length === 0 ? (
                <div className="border-2 border-dashed border-black bg-white p-4 font-mono text-sm text-black">
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
                    className="border-2 border-black bg-white p-4"
                    key={job.id}
                  >
                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <div className="flex flex-wrap items-center gap-2">
                        <Badge
                          className={cn(
                            "font-mono text-xs",
                            jobStatusMeta.className
                          )}
                        >
                          {jobStatusMeta.label}
                        </Badge>
                        {jobAiStatusMeta ? (
                          <Badge
                            className={cn(
                              "font-mono text-xs",
                              jobAiStatusMeta.className
                            )}
                          >
                            {jobAiStatusMeta.label}
                          </Badge>
                        ) : null}
                      </div>
                      <span className="font-mono text-xs text-black">
                        尝试 {job.attempt_count} 次
                      </span>
                    </div>
                    <p className="mt-3 font-mono text-xs leading-6 text-black">
                      创建于 {formatDate(job.created_at)}
                      {job.finished_at ? `，结束于 ${formatDate(job.finished_at)}` : ""}
                    </p>
                    {job.ai_message &&
                    ["pending", "fallback_rule", "skipped"].includes(
                      job.ai_status ?? ""
                    ) ? (
                      <p
                        className={cn(
                          "mt-2 font-mono text-sm",
                          getAIMessageTone(job.ai_status)
                        )}
                      >
                        {job.ai_message}
                      </p>
                    ) : null}
                    {job.error_message ? (
                      <p className="mt-2 font-mono text-sm text-black">
                        {job.error_message}
                      </p>
                    ) : null}
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        <div className="border-2 border-t-0 border-l-0 border-black p-6">
          <h3 className="font-serif text-xl font-bold text-black">
            结构化数据编辑
          </h3>
          <div className="mt-1 font-mono text-xs text-black">
            直接编辑下方字段，人工修正会自动保存
          </div>
          <div className="mt-4">
            <ResumeStructuredEditor
              onChange={onChangeStructured}
              value={structuredValue}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
