"use client";

import { FileText } from "lucide-react";

import { getResumeStatusMeta } from "@/components/resume/status-meta";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import type { ResumeRecord } from "@/lib/api/modules/resume";

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
    <div className="space-y-0">
      {items.map((item) => {
        const isActive = item.id === selectedResumeId;
        const statusMeta = getResumeStatusMeta(item.parse_status);

        return (
          <button
            className="block w-full text-left transition-none"
            key={item.id}
            onClick={() => onSelect(item.id)}
            type="button"
          >
            <div
              className={cn(
                "border-2 border-black p-4",
                isActive
                  ? "bg-black text-white"
                  : "bg-white text-black hover:bg-gray-100"
              )}
            >
              <div className="flex items-start gap-3">
                <div className="mt-0.5 flex size-8 shrink-0 items-center justify-center border-2 border-black bg-white">
                  <FileText className="size-4 text-black" />
                </div>
                <div className="min-w-0 flex-1">
                  <p className="truncate font-mono text-sm font-bold text-black">
                    {item.file_name}
                  </p>
                  <p className="mt-1 font-mono text-xs text-black">
                    上传于 {formatDate(item.created_at)}
                  </p>
                </div>
              </div>

              <div className="mt-3 flex items-center justify-between gap-3">
                <Badge className={cn("font-mono text-xs", statusMeta.className)}>
                  {statusMeta.label}
                </Badge>
                <span className="font-mono text-xs text-black">
                  v{item.latest_version}
                </span>
              </div>
            </div>
          </button>
        );
      })}
    </div>
  );
}
