"use client";

import { Download, RefreshCw, Save, Trash2 } from "lucide-react";

import { PageEmptyState } from "@/components/page-state";
import { ResumeStructuredEditor } from "@/components/resume/resume-structured-editor";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import type {
  ResumeParseJob,
  ResumeRecord,
  ResumeStructuredData,
} from "@/lib/api/modules/resume";

function getStatusTone(status: string) {
  if (status === "success") {
    return "bg-emerald-100 text-emerald-700";
  }
  if (status === "failed") {
    return "bg-rose-100 text-rose-700";
  }
  if (status === "processing") {
    return "bg-amber-100 text-amber-700";
  }
  return "bg-slate-100 text-slate-700";
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat("zh-CN", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

export function ResumeDetailPanel({
  resume,
  parseJobs,
  structuredValue,
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

  return (
    <div className="space-y-5">
      <Card className="surface-card border-0 bg-card/85 py-0 shadow-2xl shadow-emerald-950/6">
        <CardContent className="px-6 py-6 sm:px-8 sm:py-8">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
            <div className="space-y-3">
              <Badge className={`rounded-full px-3 py-1 hover:bg-inherit ${getStatusTone(resume.parse_status)}`}>
                {resume.parse_status}
              </Badge>
              <div className="space-y-2">
                <h2 className="text-3xl font-semibold tracking-tight text-foreground">
                  {resume.file_name}
                </h2>
                <p className="text-sm leading-7 text-muted-foreground">
                  上传时间 {formatDate(resume.created_at)}，文件大小{" "}
                  {(resume.file_size / 1024).toFixed(1)} KB，当前版本 v
                  {resume.latest_version}
                </p>
              </div>
            </div>

            <div className="flex flex-wrap gap-2">
              <Button
                className="rounded-full"
                disabled={isRetrying}
                onClick={onRetry}
                type="button"
                variant="outline"
              >
                {isRetrying ? "重新解析中..." : "重试解析"}
                <RefreshCw className="size-4" />
              </Button>
              <Button
                className="rounded-full"
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
                className="rounded-full"
                disabled={isSaving}
                onClick={onSave}
                type="button"
              >
                {isSaving ? "保存中..." : "保存人工修正"}
                <Save className="size-4" />
              </Button>
            </div>
          </div>

          {resume.parse_error ? (
            <Alert className="mt-5 rounded-2xl border-destructive/20 bg-destructive/5">
              <AlertTitle>解析失败</AlertTitle>
              <AlertDescription>{resume.parse_error}</AlertDescription>
            </Alert>
          ) : null}
        </CardContent>
      </Card>

      <section className="grid gap-5 xl:grid-cols-[1.05fr_0.95fr]">
        <Card className="surface-card border-0 bg-card/80 py-0 shadow-xl shadow-emerald-950/5">
          <CardHeader className="px-6 py-6">
            <CardTitle className="text-2xl font-semibold text-foreground">
              原始文本预览
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-5 px-6 pb-6">
            <Textarea
              className="min-h-[360px] rounded-[28px] border-border/70 bg-white/80 font-mono text-xs leading-6"
              readOnly
              value={resume.raw_text ?? "解析尚未完成，完成后这里会展示抽取出来的原始文本。"}
            />

            <div className="space-y-3">
              <p className="text-sm font-medium text-foreground">解析任务记录</p>
              <div className="space-y-3">
                {parseJobs.length === 0 ? (
                  <div className="rounded-2xl border border-dashed border-border/70 px-4 py-4 text-sm text-muted-foreground">
                    还没有解析任务记录。
                  </div>
                ) : null}
                {parseJobs.map((job) => (
                  <div
                    className="rounded-2xl border border-border/70 bg-white/72 px-4 py-4"
                    key={job.id}
                  >
                    <div className="flex items-center justify-between gap-3">
                      <Badge className={`rounded-full px-3 py-1 hover:bg-inherit ${getStatusTone(job.status)}`}>
                        {job.status}
                      </Badge>
                      <span className="text-xs text-muted-foreground">
                        尝试 {job.attempt_count} 次
                      </span>
                    </div>
                    <p className="mt-3 text-xs leading-6 text-muted-foreground">
                      创建于 {formatDate(job.created_at)}
                      {job.finished_at ? `，结束于 ${formatDate(job.finished_at)}` : ""}
                    </p>
                    {job.error_message ? (
                      <p className="mt-2 text-sm text-rose-700">{job.error_message}</p>
                    ) : null}
                  </div>
                ))}
              </div>
            </div>
          </CardContent>
        </Card>

        <ResumeStructuredEditor onChange={onChangeStructured} value={structuredValue} />
      </section>
    </div>
  );
}
