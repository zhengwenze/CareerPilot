"use client";

import { Plus, RefreshCw, Save, Trash2 } from "lucide-react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import type { JobDraft, JobRecord } from "@/lib/api/modules/jobs";

function getStageLabel(stage: string) {
  const labels: Record<string, string> = {
    draft: "待解析",
    analyzed: "已分析",
    matched: "已匹配",
    tailoring_needed: "待改简历",
    interview_ready: "可练面试",
    training_in_progress: "训练中",
    ready_to_apply: "可投递",
  };
  return labels[stage] ?? stage;
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat("zh-CN", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

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
      <Card className="rounded-[2rem] border border-black/10 bg-white py-0 shadow-[0_18px_48px_rgba(0,0,0,0.05)]">
        <CardHeader className="space-y-4 px-6 py-6">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <CardTitle className="text-2xl font-semibold tracking-[-0.04em] text-black">
              {selectedJob ? "编辑目标岗位" : "创建目标岗位"}
            </CardTitle>

            <div className="flex flex-wrap gap-2">
              <Button
                className="rounded-full border-black/10 bg-white text-black hover:bg-[#f5f5f7]"
                onClick={onCreateNew}
                type="button"
                variant="outline"
              >
                新建 JD
                <Plus className="size-4" />
              </Button>
              <Button
                className="rounded-full bg-[#0071E3] text-white hover:bg-[#0077ED]"
                disabled={isSaving}
                onClick={onSave}
                type="button"
              >
                {isSaving ? "保存中..." : selectedJob ? "保存修改" : "创建 JD"}
                <Save className="size-4" />
              </Button>
              <Button
                className="rounded-full border-black/10 bg-white text-black hover:bg-[#f5f5f7]"
                disabled={!selectedJob || isParsing}
                onClick={onParse}
                type="button"
                variant="outline"
              >
                {isParsing ? "重跑中..." : "重跑解析"}
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
              <Label htmlFor="job-title" className="text-black">
                岗位标题
              </Label>
              <Input
                className="h-12 rounded-2xl border-black/10 bg-[#f5f5f7] px-4 text-black placeholder:text-black/40 focus-visible:border-[#0071E3] focus-visible:ring-[#0071E3]/20"
                id="job-title"
                onChange={(event) => onChange("title", event.target.value)}
                placeholder="例如：高级数据分析师"
                value={draft.title}
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="job-company" className="text-black">
                公司
              </Label>
              <Input
                className="h-12 rounded-2xl border-black/10 bg-[#f5f5f7] px-4 text-black placeholder:text-black/40 focus-visible:border-[#0071E3] focus-visible:ring-[#0071E3]/20"
                id="job-company"
                onChange={(event) => onChange("company", event.target.value)}
                placeholder="例如：CareerPilot"
                value={draft.company}
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="job-city" className="text-black">
                城市
              </Label>
              <Input
                className="h-12 rounded-2xl border-black/10 bg-[#f5f5f7] px-4 text-black placeholder:text-black/40 focus-visible:border-[#0071E3] focus-visible:ring-[#0071E3]/20"
                id="job-city"
                onChange={(event) => onChange("job_city", event.target.value)}
                placeholder="例如：上海"
                value={draft.job_city}
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="job-type" className="text-black">
                用工类型
              </Label>
              <Input
                className="h-12 rounded-2xl border-black/10 bg-[#f5f5f7] px-4 text-black placeholder:text-black/40 focus-visible:border-[#0071E3] focus-visible:ring-[#0071E3]/20"
                id="job-type"
                onChange={(event) => onChange("employment_type", event.target.value)}
                placeholder="例如：全职 / 实习"
                value={draft.employment_type}
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="job-source-name" className="text-black">
                来源平台
              </Label>
              <Input
                className="h-12 rounded-2xl border-black/10 bg-[#f5f5f7] px-4 text-black placeholder:text-black/40 focus-visible:border-[#0071E3] focus-visible:ring-[#0071E3]/20"
                id="job-source-name"
                onChange={(event) => onChange("source_name", event.target.value)}
                placeholder="例如：Boss直聘"
                value={draft.source_name}
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="job-source-url" className="text-black">
                来源链接
              </Label>
              <Input
                className="h-12 rounded-2xl border-black/10 bg-[#f5f5f7] px-4 text-black placeholder:text-black/40 focus-visible:border-[#0071E3] focus-visible:ring-[#0071E3]/20"
                id="job-source-url"
                onChange={(event) => onChange("source_url", event.target.value)}
                placeholder="https://example.com/job/123"
                value={draft.source_url}
              />
            </div>
          </div>

          <div className="grid gap-2">
            <Label htmlFor="job-jd-text" className="text-black">
              JD 原文
            </Label>
            <Textarea
              className="min-h-[220px] rounded-[1.75rem] border-black/10 bg-[#f5f5f7] text-black placeholder:text-black/40 focus-visible:border-[#0071E3] focus-visible:ring-[#0071E3]/20"
              id="job-jd-text"
              onChange={(event) => onChange("jd_text", event.target.value)}
              placeholder="把完整职位描述粘贴到这里。系统会异步完成结构化和后续匹配。"
              value={draft.jd_text}
            />
          </div>

          {pageError ? (
            <Alert
              className="rounded-[1.5rem] border-[#ff3b30]/20 bg-[#fff5f5]"
              variant="destructive"
            >
              <AlertTitle className="text-black">操作失败</AlertTitle>
              <AlertDescription className="text-black/72">
                {pageError}
              </AlertDescription>
            </Alert>
          ) : null}
        </CardContent>
      </Card>

      <Card className="rounded-[2rem] border border-black/10 bg-[#f5f5f7] py-0 shadow-none">
        <CardHeader className="space-y-3 px-6 py-6">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <CardTitle className="text-2xl font-semibold tracking-[-0.04em] text-black">
                岗位画像
              </CardTitle>
              <p className="mt-2 text-sm leading-7 text-black/62">
                只保留匹配和后续动作会直接使用的关键信息。
              </p>
            </div>
            {selectedJob ? (
              <div className="text-sm text-black/62">
                阶段 {getStageLabel(selectedJob.status_stage)} · 解析{" "}
                {selectedJob.parse_status}
              </div>
            ) : null}
          </div>
        </CardHeader>
        <CardContent className="space-y-4 px-6 pb-6">
          {!selectedJob ? (
            <div className="rounded-[1.5rem] border border-dashed border-black/12 bg-white px-4 py-4 text-sm text-black/58">
              先创建或选择一个 JD，这里会显示岗位画像、解析进度和最近准备度变化。
            </div>
          ) : null}

          {selectedJob ? (
            <div className="grid gap-4 lg:grid-cols-3">
              <div className="rounded-[1.5rem] border border-black/10 bg-white px-4 py-4">
                <p className="text-sm font-medium text-black">解析信号</p>
                <p className="mt-2 text-sm leading-7 text-black/68">
                  版本 v{selectedJob.latest_version} · 优先级 P{selectedJob.priority}
                </p>
                <p className="text-sm leading-7 text-black/68">
                  置信度 {selectedJob.parse_confidence ?? "待生成"}
                </p>
                <p className="text-sm leading-7 text-black/68">
                  最近任务 {selectedJob.latest_parse_job?.status ?? "暂无"}
                </p>
              </div>

              <div className="rounded-[1.5rem] border border-black/10 bg-white px-4 py-4">
                <p className="text-sm font-medium text-black">经验约束</p>
                <p className="mt-2 text-sm leading-7 text-black/68">
                  {structured?.experience_constraints.education || "未识别学历"} ·{" "}
                  {structured?.experience_constraints.experience_min_years
                    ? `${structured.experience_constraints.experience_min_years} 年以上`
                    : "未识别年限"}
                </p>
                <p className="text-sm leading-7 text-black/68">
                  {structured?.experience_constraints.location ||
                    selectedJob.job_city ||
                    "地点未填"}
                </p>
              </div>

              <div className="rounded-[1.5rem] border border-black/10 bg-white px-4 py-4">
                <p className="text-sm font-medium text-black">最新动作</p>
                <p className="mt-2 text-sm leading-7 text-black/68">
                  推荐简历 {selectedJob.recommended_resume_id ? "已锁定" : "待选择"}
                </p>
                <p className="text-sm leading-7 text-black/68">
                  最新报告 {selectedJob.latest_match_report?.fit_band ?? "待生成"}
                </p>
                <p className="text-sm leading-7 text-black/68">
                  {selectedJob.latest_match_report?.stale_status === "stale"
                    ? "当前报告已过期"
                    : "当前报告为最新"}
                </p>
              </div>

              <div className="rounded-[1.5rem] border border-black/10 bg-white px-4 py-4">
                <p className="text-sm font-medium text-black">必备能力</p>
                <p className="mt-2 text-sm leading-7 text-black/68">
                  {structured?.must_have.join("、") ||
                    structured?.requirements.required_skills.join("、") ||
                    "暂无"}
                </p>
              </div>

              <div className="rounded-[1.5rem] border border-black/10 bg-white px-4 py-4">
                <p className="text-sm font-medium text-black">加分项</p>
                <p className="mt-2 text-sm leading-7 text-black/68">
                  {structured?.nice_to_have.join("、") ||
                    structured?.requirements.preferred_skills.join("、") ||
                    "暂无"}
                </p>
              </div>

              <div className="rounded-[1.5rem] border border-black/10 bg-white px-4 py-4">
                <p className="text-sm font-medium text-black">领域关键词</p>
                <p className="mt-2 text-sm leading-7 text-black/68">
                  {structured?.domain_context.keywords.join("、") ||
                    structured?.requirements.required_keywords.join("、") ||
                    "暂无"}
                </p>
              </div>

              <div className="rounded-[1.5rem] border border-black/10 bg-white px-4 py-4 lg:col-span-2">
                <p className="text-sm font-medium text-black">职责语义簇</p>
                <div className="mt-3 space-y-3">
                  {structured?.responsibility_clusters.length ? (
                    structured.responsibility_clusters.map((cluster) => (
                      <div key={cluster.name}>
                        <p className="text-sm font-medium text-black">
                          {cluster.name}
                        </p>
                        <p className="text-sm leading-7 text-black/68">
                          {cluster.items.join("；")}
                        </p>
                      </div>
                    ))
                  ) : (
                    <p className="text-sm text-black/58">暂无职责聚类。</p>
                  )}
                </div>
              </div>

              <div className="rounded-[1.5rem] border border-black/10 bg-white px-4 py-4">
                <p className="text-sm font-medium text-black">准备度时间线</p>
                <div className="mt-3 space-y-3">
                  {selectedJob.recent_readiness_events.length === 0 ? (
                    <p className="text-sm text-black/58">还没有事件记录。</p>
                  ) : (
                    selectedJob.recent_readiness_events.map((event) => (
                      <div key={event.id}>
                        <p className="text-sm font-medium text-black">
                          {event.status_from ? `${event.status_from} -> ` : ""}
                          {event.status_to}
                        </p>
                        <p className="text-sm leading-7 text-black/68">
                          {event.reason || "状态更新"} · {formatDate(event.created_at)}
                        </p>
                      </div>
                    ))
                  )}
                </div>
              </div>
            </div>
          ) : null}
        </CardContent>
      </Card>
    </div>
  );
}
