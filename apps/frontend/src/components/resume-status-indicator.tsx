import type { ResumeRecord } from "@/lib/api/modules/resume";
import { StatusIndicator } from "./status-indicator";

interface ResumeStatusIndicatorProps {
  resume: ResumeRecord;
}

type ResumeStatus = "pending" | "processing" | "success" | "failed";

export function ResumeStatusIndicator({ resume }: ResumeStatusIndicatorProps) {
  const labels: Record<string, string> = {
    pending: "待转 MD",
    processing: "转 MD 中",
    success: "已可用",
    failed: "转 MD 失败",
  };

  const label = labels[resume.parse_status] ?? resume.parse_status;

  return <StatusIndicator status={resume.parse_status as ResumeStatus} label={label} />;
}
