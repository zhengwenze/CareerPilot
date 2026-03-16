"use client";

import { FileText } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import type { ResumeRecord } from "@/lib/api/modules/resume";

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

function formatDate(value: string) {
  return new Intl.DateTimeFormat("zh-CN", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

export function ResumeList({
  items,
  selectedResumeId,
  onSelect,
}: {
  items: ResumeRecord[];
  selectedResumeId: string | null;
  onSelect: (resumeId: string) => void;
}) {
  return (
    <div className="space-y-3">
      {items.map((item) => {
        const isActive = item.id === selectedResumeId;

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
                    <FileText className="size-4" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-semibold text-black">
                      {item.file_name}
                    </p>
                    <p className="mt-1 text-xs text-black/55">
                      上传于 {formatDate(item.created_at)}
                    </p>
                  </div>
                </div>

                <div className="flex items-center justify-between gap-3">
                  <Badge
                    className={cn(
                      "rounded-full px-3 py-1 hover:bg-inherit",
                      getStatusTone(item.parse_status)
                    )}
                  >
                    {item.parse_status}
                  </Badge>
                  <span className="text-xs text-black/45">
                    v{item.latest_version}
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
