"use client";

import { Sparkles, Trash2 } from "lucide-react";

import { PageEmptyState } from "@/components/page-state";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type {
  JobRecord,
  MatchReportRecord,
} from "@/lib/api/modules/jobs";
import type { ResumeRecord } from "@/lib/api/modules/resume";

function formatDate(value: string) {
  return new Intl.DateTimeFormat("zh-CN", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
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

  if (!selectedJob) {
    return (
      <PageEmptyState
        description="先在中间区域创建或选择一个 JD，右侧才会显示匹配生成与报告详情。"
        title="还没有选中 JD"
      />
    );
  }

  return (
    <div className="space-y-5">
      <Card className="rounded-[2rem] border border-black/10 bg-white py-0 shadow-[0_18px_48px_rgba(0,0,0,0.05)]">
        <CardHeader className="space-y-4 px-6 py-6">
          <Badge className="w-fit rounded-full border border-black/10 bg-[#f5f5f7] px-3 py-1 text-black hover:bg-[#f5f5f7]">
            Match Generator
          </Badge>
          <CardTitle className="text-2xl font-semibold tracking-[-0.04em] text-black">
            选择简历生成匹配报告
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4 px-6 pb-6">
          {availableResumes.length === 0 ? (
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
              <Button
                className="w-full rounded-full bg-[#0071E3] text-white hover:bg-[#0077ED]"
                disabled={!selectedResumeId || isGenerating}
                onClick={onGenerate}
                type="button"
              >
                {isGenerating ? "生成中..." : "生成新的匹配报告"}
                <Sparkles className="size-4" />
              </Button>
            </>
          )}
        </CardContent>
      </Card>

      <section className="grid gap-5 xl:grid-cols-[280px_minmax(0,1fr)]">
        <Card className="rounded-[2rem] border border-black/10 bg-[#f5f5f7] py-0 shadow-none">
          <CardHeader className="px-6 py-6">
            <CardTitle className="text-xl font-semibold text-black">
              历史报告
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 px-6 pb-6">
            {reports.length === 0 ? (
              <div className="rounded-[1.5rem] border border-dashed border-black/12 bg-white px-4 py-4 text-sm text-black/58">
                还没有报告，生成一次后这里会保留历史记录。
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
                        总分 {report.overall_score}
                      </p>
                      <p className="mt-2 text-xs leading-6 text-black/52">
                        {formatDate(report.created_at)}
                      </p>
                    </div>
                  </button>
                );
              })
            )}
          </CardContent>
        </Card>

        {!selectedReport ? (
          <PageEmptyState
            description="生成匹配报告后，这里会展示维度分、优势、短板、建议和 AI 修正信息。"
            title="还没有报告详情"
          />
        ) : (
          <Card className="rounded-[2rem] border border-black/10 bg-white py-0 shadow-[0_18px_48px_rgba(0,0,0,0.05)]">
            <CardHeader className="space-y-4 px-6 py-6">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div className="space-y-2">
                  <Badge className="w-fit rounded-full border border-black/10 bg-[#f5f5f7] px-3 py-1 text-black hover:bg-[#f5f5f7]">
                    Match Report
                  </Badge>
                  <CardTitle className="text-2xl font-semibold tracking-[-0.04em] text-black">
                    规则分 {selectedReport.rule_score} · AI 修正{" "}
                    {selectedReport.model_score}
                  </CardTitle>
                </div>
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
              <div className="grid gap-3 md:grid-cols-3">
                {Object.entries(selectedReport.dimension_scores_json).map(([key, value]) => (
                  <div
                    className="rounded-[1.5rem] border border-black/10 bg-[#f5f5f7] px-4 py-4"
                    key={key}
                  >
                    <p className="text-xs font-medium tracking-[0.12em] text-black/45 uppercase">
                      {key}
                    </p>
                    <p className="mt-2 text-2xl font-semibold text-black">
                      {value}
                    </p>
                  </div>
                ))}
              </div>

              <div className="grid gap-5 xl:grid-cols-3">
                <div className="rounded-[1.5rem] border border-black/10 bg-[#f5f5f7] px-4 py-4">
                  <p className="text-sm font-medium text-black">优势</p>
                  <div className="mt-3 space-y-3">
                    {selectedReport.gap_json.strengths.length === 0 ? (
                      <p className="text-sm text-black/58">暂无优势条目。</p>
                    ) : (
                      selectedReport.gap_json.strengths.map((item) => (
                        <div key={`${item.label}-${item.reason}`}>
                          <p className="text-sm font-medium text-black">
                            {item.label}
                          </p>
                          <p className="text-sm leading-7 text-black/68">
                            {item.reason}
                          </p>
                        </div>
                      ))
                    )}
                  </div>
                </div>

                <div className="rounded-[1.5rem] border border-black/10 bg-[#f5f5f7] px-4 py-4">
                  <p className="text-sm font-medium text-black">短板</p>
                  <div className="mt-3 space-y-3">
                    {selectedReport.gap_json.gaps.length === 0 ? (
                      <p className="text-sm text-black/58">暂无短板条目。</p>
                    ) : (
                      selectedReport.gap_json.gaps.map((item) => (
                        <div key={`${item.label}-${item.reason}`}>
                          <p className="text-sm font-medium text-black">
                            {item.label}
                          </p>
                          <p className="text-sm leading-7 text-black/68">
                            {item.reason}
                          </p>
                        </div>
                      ))
                    )}
                  </div>
                </div>

                <div className="rounded-[1.5rem] border border-black/10 bg-[#f5f5f7] px-4 py-4">
                  <p className="text-sm font-medium text-black">建议</p>
                  <div className="mt-3 space-y-3">
                    {selectedReport.gap_json.actions.map((item) => (
                      <div key={`${item.priority}-${item.title}`}>
                        <p className="text-sm font-medium text-black">
                          P{item.priority} · {item.title}
                        </p>
                        <p className="text-sm leading-7 text-black/68">
                          {item.description}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              <div className="rounded-[1.5rem] border border-black/10 bg-[#f5f5f7] px-4 py-4">
                <p className="text-sm font-medium text-black">证据与 AI 修正</p>
                <div className="mt-3 grid gap-4 md:grid-cols-2">
                  <div>
                    <p className="text-xs font-medium tracking-[0.12em] text-black/45 uppercase">
                      命中 JD 字段
                    </p>
                    <p className="mt-2 text-sm leading-7 text-black/68">
                      {Object.values(selectedReport.evidence_json.matched_jd_fields)
                        .flat()
                        .join("、") || "暂无"}
                    </p>
                  </div>
                  <div>
                    <p className="text-xs font-medium tracking-[0.12em] text-black/45 uppercase">
                      缺失项
                    </p>
                    <p className="mt-2 text-sm leading-7 text-black/68">
                      {selectedReport.evidence_json.missing_items.join("、") || "暂无"}
                    </p>
                  </div>
                </div>
                <p className="mt-4 text-sm leading-7 text-black/68">
                  AI 修正状态：{String(selectedReport.evidence_json.ai_correction.status || "unknown")}
                  {selectedReport.evidence_json.ai_correction.reasoning
                    ? ` · ${String(selectedReport.evidence_json.ai_correction.reasoning)}`
                    : ""}
                </p>
              </div>
            </CardContent>
          </Card>
        )}
      </section>
    </div>
  );
}
