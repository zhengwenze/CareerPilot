"use client";

import { Plus, RefreshCw, Save, Trash2 } from "lucide-react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import type { JobDraft, JobRecord } from "@/lib/api/modules/jobs";

export function JobFormCard({
  draft,
  selectedJob,
  isSaving,
  isParsing,
  isDeleting,
  pageError,
  onChange,
  onCreateNew,
  onSave,
  onParse,
  onDelete,
}: {
  draft: JobDraft;
  selectedJob: JobRecord | null;
  isSaving: boolean;
  isParsing: boolean;
  isDeleting: boolean;
  pageError: string;
  onChange: (field: keyof JobDraft, value: string) => void;
  onCreateNew: () => void;
  onSave: () => void;
  onParse: () => void;
  onDelete: () => void;
}) {
  const structured = selectedJob?.structured_json;

  return (
    <div className="space-y-5">
      <Card className="surface-card border-0 bg-card/82 py-0 shadow-xl shadow-emerald-950/5">
        <CardHeader className="space-y-4 px-6 py-6">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="space-y-2">
              <Badge className="w-fit rounded-full bg-secondary px-3 py-1 text-secondary-foreground">
                JD Editor
              </Badge>
              <CardTitle className="text-2xl font-semibold text-foreground">
                {selectedJob ? "编辑目标岗位" : "创建目标岗位"}
              </CardTitle>
            </div>

            <div className="flex flex-wrap gap-2">
              <Button
                className="rounded-full"
                onClick={onCreateNew}
                type="button"
                variant="outline"
              >
                新建 JD
                <Plus className="size-4" />
              </Button>
              <Button
                className="rounded-full"
                disabled={isSaving}
                onClick={onSave}
                type="button"
              >
                {isSaving ? "保存中..." : selectedJob ? "保存修改" : "创建 JD"}
                <Save className="size-4" />
              </Button>
              <Button
                className="rounded-full"
                disabled={!selectedJob || isParsing}
                onClick={onParse}
                type="button"
                variant="outline"
              >
                {isParsing ? "重试中..." : "重试结构化"}
                <RefreshCw className="size-4" />
              </Button>
              <Button
                className="rounded-full"
                disabled={!selectedJob || isDeleting}
                onClick={onDelete}
                type="button"
                variant="destructive"
              >
                {isDeleting ? "删除中..." : "删除 JD"}
                <Trash2 className="size-4" />
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-5 px-6 pb-6">
          <div className="grid gap-4 md:grid-cols-2">
            <div className="grid gap-2">
              <Label htmlFor="job-title">岗位标题</Label>
              <Input
                id="job-title"
                onChange={(event) => onChange("title", event.target.value)}
                placeholder="例如：高级数据分析师"
                value={draft.title}
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="job-company">公司</Label>
              <Input
                id="job-company"
                onChange={(event) => onChange("company", event.target.value)}
                placeholder="例如：CareerPilot"
                value={draft.company}
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="job-city">城市</Label>
              <Input
                id="job-city"
                onChange={(event) => onChange("job_city", event.target.value)}
                placeholder="例如：上海"
                value={draft.job_city}
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="job-type">用工类型</Label>
              <Input
                id="job-type"
                onChange={(event) =>
                  onChange("employment_type", event.target.value)
                }
                placeholder="例如：全职 / 实习"
                value={draft.employment_type}
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="job-source-name">来源平台</Label>
              <Input
                id="job-source-name"
                onChange={(event) => onChange("source_name", event.target.value)}
                placeholder="例如：Boss直聘"
                value={draft.source_name}
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="job-source-url">来源链接</Label>
              <Input
                id="job-source-url"
                onChange={(event) => onChange("source_url", event.target.value)}
                placeholder="https://example.com/job/123"
                value={draft.source_url}
              />
            </div>
          </div>

          <div className="grid gap-2">
            <Label htmlFor="job-jd-text">JD 原文</Label>
            <Textarea
              className="min-h-[220px]"
              id="job-jd-text"
              onChange={(event) => onChange("jd_text", event.target.value)}
              placeholder="把完整职位描述粘贴到这里。保存后会自动结构化。"
              value={draft.jd_text}
            />
          </div>

          {pageError ? (
            <Alert
              className="rounded-2xl border-destructive/20 bg-destructive/5"
              variant="destructive"
            >
              <AlertTitle>操作失败</AlertTitle>
              <AlertDescription>{pageError}</AlertDescription>
            </Alert>
          ) : null}
        </CardContent>
      </Card>

      <Card className="surface-card border-0 bg-card/82 py-0 shadow-xl shadow-emerald-950/5">
        <CardHeader className="space-y-3 px-6 py-6">
          <Badge className="w-fit rounded-full bg-primary/10 px-3 py-1 text-primary hover:bg-primary/10">
            Structured Preview
          </Badge>
          <CardTitle className="text-2xl font-semibold text-foreground">
            结构化结果预览
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4 px-6 pb-6">
          {!selectedJob ? (
            <div className="rounded-2xl border border-dashed border-border/70 px-4 py-4 text-sm text-muted-foreground">
              先创建或选择一个 JD，这里会显示结构化后的技能、关键词和职责摘要。
            </div>
          ) : null}

          {selectedJob?.parse_error ? (
            <Alert
              className="rounded-2xl border-destructive/20 bg-destructive/5"
              variant="destructive"
            >
              <AlertTitle>结构化失败</AlertTitle>
              <AlertDescription>{selectedJob.parse_error}</AlertDescription>
            </Alert>
          ) : null}

          {structured ? (
            <div className="grid gap-4 lg:grid-cols-2">
              <div className="rounded-[24px] border border-border/70 bg-white/72 px-4 py-4">
                <p className="text-sm font-medium text-foreground">必备技能</p>
                <p className="mt-2 text-sm leading-7 text-muted-foreground">
                  {structured.requirements.required_skills.join("、") || "暂无"}
                </p>
              </div>
              <div className="rounded-[24px] border border-border/70 bg-white/72 px-4 py-4">
                <p className="text-sm font-medium text-foreground">加分技能</p>
                <p className="mt-2 text-sm leading-7 text-muted-foreground">
                  {structured.requirements.preferred_skills.join("、") || "暂无"}
                </p>
              </div>
              <div className="rounded-[24px] border border-border/70 bg-white/72 px-4 py-4">
                <p className="text-sm font-medium text-foreground">核心关键词</p>
                <p className="mt-2 text-sm leading-7 text-muted-foreground">
                  {structured.requirements.required_keywords.join("、") || "暂无"}
                </p>
              </div>
              <div className="rounded-[24px] border border-border/70 bg-white/72 px-4 py-4">
                <p className="text-sm font-medium text-foreground">学历 / 年限</p>
                <p className="mt-2 text-sm leading-7 text-muted-foreground">
                  {structured.requirements.education || "未识别学历"} ·{" "}
                  {structured.requirements.experience_min_years
                    ? `${structured.requirements.experience_min_years} 年`
                    : "未识别年限"}
                </p>
              </div>
              <div className="rounded-[24px] border border-border/70 bg-white/72 px-4 py-4 lg:col-span-2">
                <p className="text-sm font-medium text-foreground">职责摘要</p>
                <p className="mt-2 text-sm leading-7 text-muted-foreground">
                  {structured.responsibilities.join("；") || structured.raw_summary || "暂无"}
                </p>
              </div>
            </div>
          ) : null}
        </CardContent>
      </Card>
    </div>
  );
}
