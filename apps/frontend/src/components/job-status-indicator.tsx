import type { JobRecord } from "@/lib/api/modules/jobs";
import { StatusIndicator } from "./status-indicator";

interface JobStatusIndicatorProps {
  job: JobRecord;
}

type JobStatus = "pending" | "processing" | "success" | "failed";

export function JobStatusIndicator({ job }: JobStatusIndicatorProps) {
  const labels: Record<string, string> = {
    pending: "待解析",
    processing: "解析中",
    success: "已可用",
    failed: "解析失败",
  };

  const label = labels[job.parse_status] ?? job.parse_status;

  return <StatusIndicator status={job.parse_status as JobStatus} label={label} />;
}
