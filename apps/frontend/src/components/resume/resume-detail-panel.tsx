"use client";

import { useRef, useState } from "react";
import {
  ChevronDown,
  ChevronUp,
  Download,
  FileUp,
  RefreshCw,
  Save,
  Trash2,
} from "lucide-react";

import { PageEmptyState } from "@/components/page-state";
import { ResumeStructuredEditor } from "@/components/resume/resume-structured-editor";
import {
  getResumeAIStatusMeta,
  getResumeStatusMeta,
} from "@/components/resume/status-meta";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
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
  resumes,
  parseJobs,
  structuredValue,
  isStructuredDirty,
  isSaving,
  isRetrying,
  isDeleting,
  isUploading,
  onChangeStructured,
  onSave,
  onRetry,
  onDownload,
  onDelete,
  onUpload,
  onSelectResume,
}: {
  resume: ResumeRecord | null;
  resumes: ResumeRecord[];
  parseJobs: ResumeParseJob[];
  structuredValue: ResumeStructuredData;
  isStructuredDirty: boolean;
  isSaving: boolean;
  isRetrying: boolean;
  isDeleting: boolean;
  isUploading: boolean;
  onChangeStructured: (value: ResumeStructuredData) => void;
  onSave: () => void;
  onRetry: () => void;
  onDownload: () => void;
  onDelete: () => void;
  onUpload: (file: File) => void;
  onSelectResume: (resumeId: string) => void;
}) {
  const [isListExpanded, setIsListExpanded] = useState(false);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  if (!resume) {
    return (
      <div className="flex h-full flex-col border-2 border-black bg-white">
        <div className="flex flex-col items-center justify-center p-8">
          <PageEmptyState
            description="上传 PDF 简历，系统会自动解析并生成结构化结果。"
            title="还没有简历"
          />
          <div className="mt-6">
            <input
              accept="application/pdf,.pdf"
              className="hidden"
              disabled={isUploading}
              onChange={(event) => {
                const file = event.target.files?.[0];
                if (!file) return;
                onUpload(file);
                event.currentTarget.value = "";
              }}
              ref={fileInputRef}
              type="file"
            />
            <Button
              disabled={isUploading}
              onClick={() => fileInputRef.current?.click()}
              type="button"
            >
              {isUploading ? "上传中..." : "选择 PDF 文件"}
              <FileUp className="ml-2 size-4" />
            </Button>
          </div>
        </div>
      </div>
    );
  }

  const statusMeta = getResumeStatusMeta(resume.parse_status);
  const aiStatusMeta = getResumeAIStatusMeta(
    resume.latest_parse_job?.ai_status,
    resume.latest_parse_job?.ai_message,
  );
  const latestAIMessage = resume.latest_parse_job?.ai_message?.trim() || "";
  const showLatestAIMessage =
    Boolean(latestAIMessage) &&
    ["pending", "fallback_rule", "skipped"].includes(
      resume.latest_parse_job?.ai_status ?? "",
    );

  return (
    <div className="flex h-full flex-col">
      <div className="border-2 border-black bg-white p-4">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div className="space-y-2">
            <div className="flex flex-wrap items-center gap-2">
              <Badge className={cn("font-mono text-xs", statusMeta.className)}>
                {statusMeta.label}
              </Badge>
              {aiStatusMeta ? (
                <Badge
                  className={cn("font-mono text-xs", aiStatusMeta.className)}
                >
                  {aiStatusMeta.label}
                </Badge>
              ) : null}
              {isStructuredDirty ? (
                <Badge className="border-2 border-black bg-white font-mono text-xs text-black">
                  有未保存修改
                </Badge>
              ) : null}
            </div>
            <div className="flex items-center gap-2">
              <button
                className="flex items-center gap-2 font-serif text-2xl font-bold tracking-tight text-black transition-none hover:underline"
                onClick={() => setIsListExpanded((prev) => !prev)}
                type="button"
              >
                {resume.file_name}
                {isListExpanded ? (
                  <ChevronUp className="size-5 shrink-0" />
                ) : (
                  <ChevronDown className="size-5 shrink-0" />
                )}
              </button>
              {resumes.length > 1 && (
                <span className="font-mono text-xs text-black">
                  共 {resumes.length} 份
                </span>
              )}
            </div>
            <p className="font-mono text-xs text-black">
              上传于 {formatDate(resume.created_at)}，版本 v
              {resume.latest_version}
              {resume.parse_error
                ? null
                : `，${(resume.file_size / 1024).toFixed(1)} KB`}
            </p>
            {showLatestAIMessage ? (
              <p
                className={cn(
                  "font-mono text-sm",
                  getAIMessageTone(resume.latest_parse_job?.ai_status),
                )}
              >
                {latestAIMessage}
              </p>
            ) : null}
          </div>

          <div className="flex flex-wrap gap-2">
            <input
              accept="application/pdf,.pdf"
              className="hidden"
              disabled={isUploading}
              onChange={(event) => {
                const file = event.target.files?.[0];
                if (!file) return;
                onUpload(file);
                event.currentTarget.value = "";
              }}
              ref={fileInputRef}
              type="file"
            />
            <Button
              disabled={isUploading}
              onClick={() => fileInputRef.current?.click()}
              type="button"
              variant="secondary"
            >
              {isUploading ? "上传中..." : "上传简历"}
              <FileUp className="ml-2 size-4" />
            </Button>
            <Button
              disabled={isRetrying}
              onClick={onRetry}
              type="button"
              variant="secondary"
            >
              {isRetrying ? "重新解析中..." : "重试解析"}
              <RefreshCw className="ml-2 size-4" />
            </Button>
            <Button onClick={onDownload} type="button" variant="secondary">
              下载原文件
              <Download className="ml-2 size-4" />
            </Button>
            <Button onClick={onDelete} type="button" variant="destructive">
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
                  ? "保存修改"
                  : "暂无修改"}
              <Save className="ml-2 size-4" />
            </Button>
          </div>
        </div>

        {isListExpanded && resumes.length > 0 && (
          <div className="mt-4 space-y-2">
            <p className="font-mono text-xs text-black">切换简历：</p>
            {resumes.map((r) => {
              const rStatusMeta = getResumeStatusMeta(r.parse_status);
              const isActive = r.id === resume.id;
              return (
                <button
                  className={cn(
                    "block w-full border-2 p-3 font-mono text-sm text-left transition-none",
                    isActive
                      ? "border-black bg-black text-white"
                      : "border-black bg-white text-black hover:bg-gray-100",
                  )}
                  key={r.id}
                  onClick={() => {
                    onSelectResume(r.id);
                    setIsListExpanded(false);
                  }}
                  type="button"
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="truncate">{r.file_name}</span>
                    <Badge
                      className={cn(
                        "font-mono text-xs shrink-0",
                        rStatusMeta.className,
                      )}
                    >
                      {rStatusMeta.label}
                    </Badge>
                  </div>
                </button>
              );
            })}
          </div>
        )}

        {resume.parse_error ? (
          <Alert className="mt-4 border-2 border-black bg-white font-mono">
            <AlertTitle className="font-serif text-sm font-bold text-black">
              解析失败
            </AlertTitle>
            <AlertDescription className="font-mono text-xs leading-6 text-black">
              {resume.parse_error}
            </AlertDescription>
          </Alert>
        ) : null}

        {parseJobs.length > 0 ? (
          <div className="mt-3 flex flex-wrap items-center gap-3">
            <span className="font-mono text-xs text-black">解析记录：</span>
            {parseJobs.slice(0, 3).map((job) => {
              const jobStatusMeta = getResumeStatusMeta(job.status);
              return (
                <Badge
                  key={job.id}
                  className={cn("font-mono text-xs", jobStatusMeta.className)}
                >
                  {jobStatusMeta.label}（尝试 {job.attempt_count} 次）
                </Badge>
              );
            })}
            {parseJobs.length > 3 && (
              <span className="font-mono text-xs text-black">
                +{parseJobs.length - 3} 条更早记录
              </span>
            )}
          </div>
        ) : null}
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto border-2 border-t-0 border-black bg-white p-4">
        <div className="mt-4">
          <ResumeStructuredEditor
            onChange={onChangeStructured}
            value={structuredValue}
          />
        </div>
      </div>
    </div>
  );
}
