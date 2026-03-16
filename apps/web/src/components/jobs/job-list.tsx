"use client";

import { Target } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import type { JobRecord } from "@/lib/api/modules/jobs";

function getStatusTone(status: string) {
  if (status === "success") {
    return "bg-[#E8F7EE] text-[#18864B]";
  }
  if (status === "failed") {
    return "bg-[#FFF1F0] text-[#D93025]";
  }
  if (status === "processing") {
    return "bg-[#FFF7E6] text-[#B26A00]";
  }
  return "bg-[#f2f2f2] text-black/65";
}

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

function getFitBandLabel(band: string | undefined) {
  const labels: Record<string, string> = {
    excellent: "强适配",
    strong: "较强适配",
    partial: "部分适配",
    weak: "低适配",
    unknown: "待生成",
  };
  return labels[band ?? "unknown"] ?? (band ?? "unknown");
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat("zh-CN", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

export function JobList({
  items,
  selectedJobId,
  onSelect,
}: {
  items: JobRecord[];
  selectedJobId: string | null;
  onSelect: (jobId: string) => void;
}) {
  return (
    <div className="space-y-3">
      {items.map((item) => {
        const isActive = item.id === selectedJobId;

        return (
          <button
            className="block w-full text-left"
            key={item.id}
            onClick={() => onSelect(item.id)}
            type="button"
          >
            <Card
              className={cn(
                "rounded-[2rem] border py-0 shadow-none transition-all",
                isActive
                  ? "border-[#0071E3]/30 bg-[#F5F9FF]"
                  : "border-black/10 bg-white hover:border-black/20"
              )}
            >
              <CardContent className="space-y-3 px-5 py-5">
                <div className="flex items-start gap-3">
                  <div className="mt-0.5 flex size-10 shrink-0 items-center justify-center rounded-2xl bg-[#f5f5f7] text-black">
                    <Target className="size-4.5" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-semibold text-black">
                      {item.title}
                    </p>
                    <p className="mt-1 truncate text-xs text-black/55">
                      {item.company || "未填写公司"} · {formatDate(item.updated_at)}
                    </p>
                  </div>
                </div>

                <div className="flex items-center justify-between gap-3">
                  <div className="flex flex-wrap gap-2">
                    <Badge
                      className={cn(
                        "rounded-full px-3 py-1 hover:bg-inherit",
                        getStatusTone(item.parse_status)
                      )}
                    >
                      {getStageLabel(item.status_stage)}
                    </Badge>
                    <Badge className="rounded-full border border-black/10 bg-white px-3 py-1 text-black hover:bg-white">
                      {getFitBandLabel(item.latest_match_report?.fit_band)}
                    </Badge>
                    {item.latest_match_report?.stale_status === "stale" ? (
                      <Badge className="rounded-full bg-[#FFF1F0] px-3 py-1 text-[#D93025] hover:bg-[#FFF1F0]">
                        待重跑
                      </Badge>
                    ) : null}
                  </div>
                  <span className="text-xs text-black/45">
                    P{item.priority} · {item.job_city || "城市未填"}
                  </span>
                </div>
              </CardContent>
            </Card>
          </button>
        );
      })}
    </div>
  );
}
