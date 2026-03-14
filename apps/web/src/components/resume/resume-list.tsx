"use client";

import { FileText } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import type { ResumeRecord } from "@/lib/api/modules/resume";

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
                "rounded-[28px] border py-0 shadow-none transition-all",
                isActive
                  ? "border-primary/35 bg-primary/5"
                  : "border-border/70 bg-white/72 hover:border-primary/20"
              )}
            >
              <CardContent className="space-y-3 px-5 py-5">
                <div className="flex items-start gap-3">
                  <div className="mt-0.5 flex size-10 shrink-0 items-center justify-center rounded-2xl bg-secondary text-secondary-foreground">
                    <FileText className="size-4" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-semibold text-foreground">
                      {item.file_name}
                    </p>
                    <p className="mt-1 text-xs text-muted-foreground">
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
                  <span className="text-xs text-muted-foreground">
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
