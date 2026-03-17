"use client";

import Link from "next/link";
import { ArrowUpRight, Sparkles, Trash2 } from "lucide-react";

import { PageEmptyState } from "@/components/page-state";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { JobRecord, MatchReportRecord } from "@/lib/api/modules/jobs";
import type { ResumeRecord } from "@/lib/api/modules/resume";

function formatDate(value: string) {
  return new Intl.DateTimeFormat("zh-CN", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

function getFitBandLabel(value: string) {
  const labels: Record<string, string> = {
    excellent: "强适配",
    strong: "较强适配",
    partial: "部分适配",
    weak: "低适配",
    unknown: "待生成",
  };
  return labels[value] ?? value;
}

export function MatchReportPanel({
  selectedJob,
  resumes,
  selectedResumeId,
  reports,
  selectedReportId,
  isGenerating,
  isDeletingReport,
  onSelectResume,
  onGenerate,
  onSelectReport,
  onDeleteReport,
}: {
  selectedJob: JobRecord | null;
  resumes: ResumeRecord[];
  selectedResumeId: string;
  reports: MatchReportRecord[];
  selectedReportId: string | null;
  isGenerating: boolean;
  isDeletingReport: boolean;
  onSelectResume: (resumeId: string) => void;
  onGenerate: () => void;
  onSelectReport: (reportId: string) => void;
  onDeleteReport: () => void;
}) {
  const availableResumes = resumes.filter((item) => item.parse_status === "success");
  const selectedReport =
    reports.find((item) => item.id === selectedReportId) ?? reports[0] ?? null;
  const isJobReadyForMatch = selectedJob?.parse_status === "success";

  if (!selectedJob) {
    return (
      <PageEmptyState
        description="先在中间区域创建或选择一个 JD，右侧才会显示匹配生成与行动包。"
        title="还没有选中 JD"
      />
    );
  }

  return (
    <div className="space-y-5">
      <Card className="rounded-[2rem] border border-black/10 bg-white py-0 shadow-[0_18px_48px_rgba(0,0,0,0.05)]">
        <CardHeader className="space-y-4 px-6 py-6">
          <CardTitle className="text-2xl font-semibold tracking-[-0.04em] text-black">
            匹配与后续动作
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4 px-6 pb-6">
          {!isJobReadyForMatch ? (
            <div className="rounded-[1.5rem] border border-dashed border-black/12 bg-[#f5f5f7] px-4 py-4 text-sm text-black/58">
              先等待 JD 解析完成，再生成匹配快照。
            </div>
          ) : availableResumes.length === 0 ? (
            <div className="rounded-[1.5rem] border border-dashed border-black/12 bg-[#f5f5f7] px-4 py-4 text-sm text-black/58">
              还没有可用简历。请先到简历中心完成至少一份简历解析。
            </div>
          ) : (
            <>
              <div className="grid gap-2">
                <label className="text-sm font-medium text-black" htmlFor="resume-select">
                  参与匹配的简历
                </label>
                <select
                  className="h-12 rounded-2xl border border-black/10 bg-[#f5f5f7] px-4 text-sm text-black outline-none focus:border-[#0071E3]"
                  id="resume-select"
                  onChange={(event) => onSelectResume(event.target.value)}
                  value={selectedResumeId}
                >
                  {availableResumes.map((resume) => (
                    <option key={resume.id} value={resume.id}>
                      {resume.file_name}
                    </option>
                  ))}
                </select>
              </div>

              <div className="grid gap-3 md:grid-cols-3">
                <Button
                  className="rounded-full bg-[#0071E3] text-white hover:bg-[#0077ED]"
                  disabled={!selectedResumeId || isGenerating}
                  onClick={onGenerate}
                  type="button"
                >
                  {isGenerating ? "生成中..." : "更新匹配"}
                  <Sparkles className="size-4" />
                </Button>
                <Button
                  asChild
                  className="rounded-full border-black/10 bg-white text-black hover:bg-[#f5f5f7]"
                  type="button"
                  variant="outline"
                >
                  <Link
                    href={`/dashboard/optimizer?jobId=${selectedJob.id}${selectedReport ? `&reportId=${selectedReport.id}` : ""}`}
                  >
                    去简历优化
                    <ArrowUpRight className="size-4" />
                  </Link>
                </Button>
                <Button
                  asChild
                  className="rounded-full border-black/10 bg-white text-black hover:bg-[#f5f5f7]"
                  type="button"
                  variant="outline"
                >
                  <Link
                    href={`/dashboard/interviews?jobId=${selectedJob.id}${selectedReport ? `&reportId=${selectedReport.id}` : ""}`}
                  >
                    开始模拟面试
                    <ArrowUpRight className="size-4" />
                  </Link>
                </Button>
              </div>
            </>
          )}
        </CardContent>
      </Card>

      <section className="grid gap-5 xl:grid-cols-[260px_minmax(0,1fr)]">
        <Card className="rounded-[2rem] border border-black/10 bg-[#f5f5f7] py-0 shadow-none">
          <CardHeader className="px-6 py-6">
            <CardTitle className="text-xl font-semibold text-black">
              快照时间线
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 px-6 pb-6">
            {reports.length === 0 ? (
              <div className="rounded-[1.5rem] border border-dashed border-black/12 bg-white px-4 py-4 text-sm text-black/58">
                还没有报告，生成一次后这里会保留岗位快照历史。
              </div>
            ) : (
              reports.map((report) => {
                const isActive = report.id === selectedReport?.id;
                return (
                  <button
                    className="block w-full rounded-[1.5rem] border px-4 py-4 text-left transition-colors"
                    key={report.id}
                    onClick={() => onSelectReport(report.id)}
                    type="button"
                  >
                    <div
                      className={
                        isActive
                          ? "rounded-[1.25rem] border border-[#0071E3]/30 bg-[#F5F9FF] px-4 py-4"
                          : "rounded-[1.25rem] border border-black/10 bg-white px-4 py-4"
                      }
                    >
                      <p className="text-sm font-semibold text-black">
                        {report.status === "success"
                          ? `${getFitBandLabel(report.fit_band)} · ${report.overall_score}`
                          : `状态 ${report.status}`}
                      </p>
                      <p className="mt-2 text-xs leading-6 text-black/52">
                        v{report.resume_version}/v{report.job_version} ·{" "}
                        {formatDate(report.created_at)}
                      </p>
                      {report.stale_status === "stale" ? (
                        <p className="mt-2 text-xs text-[#D93025]">已过期</p>
                      ) : null}
                    </div>
                  </button>
                );
              })
            )}
          </CardContent>
        </Card>

        {!selectedReport ? (
          <PageEmptyState
            description="生成匹配快照后，这里会展示证据、差距分类、定制任务和面试蓝图。"
            title="还没有报告详情"
          />
        ) : (
          <Card className="rounded-[2rem] border border-black/10 bg-white py-0 shadow-[0_18px_48px_rgba(0,0,0,0.05)]">
            <CardHeader className="space-y-4 px-6 py-6">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <CardTitle className="text-2xl font-semibold tracking-[-0.04em] text-black">
                  {selectedReport.status === "success"
                    ? `${getFitBandLabel(selectedReport.fit_band)} · 总分 ${selectedReport.overall_score}`
                    : `报告${selectedReport.status}`}
                </CardTitle>
                <Button
                  className="rounded-full"
                  disabled={isDeletingReport}
                  onClick={onDeleteReport}
                  type="button"
                  variant="destructive"
                >
                  {isDeletingReport ? "删除中..." : "删除报告"}
                  <Trash2 className="size-4" />
                </Button>
              </div>
            </CardHeader>
            <CardContent className="space-y-5 px-6 pb-6">
              <div className="grid gap-3 md:grid-cols-4">
                {[
                  ["总分", selectedReport.overall_score],
                  ["规则分", selectedReport.rule_score],
                  ["AI 修正", selectedReport.model_score],
                  ["档位", getFitBandLabel(selectedReport.fit_band)],
                ].map(([key, value]) => (
                  <div
                    className="rounded-[1.5rem] border border-black/10 bg-[#f5f5f7] px-4 py-4"
                    key={key}
                  >
                    <p className="text-xs font-medium tracking-[0.12em] text-black/45 uppercase">
                      {key}
                    </p>
                    <p className="mt-2 text-2xl font-semibold text-black">{value}</p>
                  </div>
                ))}
              </div>

              <div className="grid gap-5 xl:grid-cols-2">
                <div className="rounded-[1.5rem] border border-black/10 bg-[#f5f5f7] px-4 py-4">
                  <p className="text-sm font-medium text-black">证据映射</p>
                  <p className="mt-3 text-xs font-medium tracking-[0.12em] text-black/45 uppercase">
                    命中 JD 字段
                  </p>
                  <p className="mt-2 text-sm leading-7 text-black/68">
                    {Object.values(selectedReport.evidence_map_json.matched_jd_fields ?? {})
                      .flat()
                      .join("、") || "暂无"}
                  </p>
                  <p className="mt-4 text-xs font-medium tracking-[0.12em] text-black/45 uppercase">
                    缺失项
                  </p>
                  <p className="mt-2 text-sm leading-7 text-black/68">
                    {selectedReport.evidence_map_json.missing_items?.join("、") ||
                      "暂无"}
                  </p>
                </div>

                <div className="rounded-[1.5rem] border border-black/10 bg-[#f5f5f7] px-4 py-4">
                  <p className="text-sm font-medium text-black">差距分类</p>
                  <div className="mt-3 space-y-3">
                    {(selectedReport.gap_taxonomy_json.must_fix ?? []).map((item) => (
                      <div key={`${item.label}-${item.reason}`}>
                        <p className="text-sm font-medium text-black">
                          必须补：{item.label}
                        </p>
                        <p className="text-sm leading-7 text-black/68">
                          {item.reason}
                        </p>
                      </div>
                    ))}
                    {(selectedReport.gap_taxonomy_json.should_fix ?? []).map((item) => (
                      <div key={`${item.label}-${item.reason}`}>
                        <p className="text-sm font-medium text-black">
                          建议补：{item.label}
                        </p>
                        <p className="text-sm leading-7 text-black/68">
                          {item.reason}
                        </p>
                      </div>
                    ))}
                    {selectedReport.gap_taxonomy_json.must_fix?.length ||
                    selectedReport.gap_taxonomy_json.should_fix?.length ? null : (
                      <p className="text-sm text-black/58">暂无差距分类。</p>
                    )}
                  </div>
                </div>
              </div>

              <div
                className="rounded-[1.5rem] border border-black/10 bg-[#f5f5f7] px-4 py-4"
                id="tailoring-plan"
              >
                <p className="text-sm font-medium text-black">简历定制任务包</p>
                <div className="mt-3 space-y-3">
                  {(selectedReport.tailoring_plan_json.rewrite_tasks ?? []).map((item, index) => (
                    <div key={`${String(item.title)}-${index}`}>
                      <p className="text-sm font-medium text-black">
                        P{String(item.priority ?? index + 1)} ·{" "}
                        {String(item.title ?? "定制任务")}
                      </p>
                      <p className="text-sm leading-7 text-black/68">
                        {String(item.instruction ?? item.description ?? "")}
                      </p>
                    </div>
                  ))}
                  {selectedReport.tailoring_plan_json.must_add_evidence?.length ? (
                    <p className="text-sm leading-7 text-black/68">
                      必须补证据：
                      {selectedReport.tailoring_plan_json.must_add_evidence.join("、")}
                    </p>
                  ) : null}
                  {(selectedReport.tailoring_plan_json.rewrite_tasks ?? []).length === 0 ? (
                    <p className="text-sm text-black/58">当前没有生成简历定制任务。</p>
                  ) : null}
                </div>
              </div>

              <div className="rounded-[1.5rem] border border-black/10 bg-[#f5f5f7] px-4 py-4">
                <p className="text-sm font-medium text-black">模拟面试蓝图</p>
                <div className="mt-3 grid gap-4 md:grid-cols-2">
                  <div>
                    <p className="text-xs font-medium tracking-[0.12em] text-black/45 uppercase">
                      训练重点
                    </p>
                    <div className="mt-2 space-y-2">
                      {(selectedReport.interview_blueprint_json.focus_areas ?? []).map(
                        (item, index) => (
                          <p
                            className="text-sm leading-7 text-black/68"
                            key={`${String(item.topic)}-${index}`}
                          >
                            {String(item.topic)} · {String(item.reason ?? "")}
                          </p>
                        )
                      )}
                    </div>
                  </div>
                  <div>
                    <p className="text-xs font-medium tracking-[0.12em] text-black/45 uppercase">
                      题包预览
                    </p>
                    <div className="mt-2 space-y-2">
                      {(selectedReport.interview_blueprint_json.question_pack ?? [])
                        .slice(0, 3)
                        .map((item, index) => (
                          <p
                            className="text-sm leading-7 text-black/68"
                            key={`${String(item.question)}-${index}`}
                          >
                            {String(item.question)}
                          </p>
                        ))}
                    </div>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        )}
      </section>
    </div>
  );
}
