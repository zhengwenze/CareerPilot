import { apiRequest } from "@/lib/api/client";

export type JobStructuredData = {
  basic: {
    title: string;
    company: string | null;
    job_city: string | null;
    employment_type: string | null;
  };
  requirements: {
    required_skills: string[];
    preferred_skills: string[];
    required_keywords: string[];
    education: string | null;
    experience_min_years: number | null;
  };
  responsibilities: string[];
  benefits: string[];
  raw_summary: string | null;
};

export type JobRecord = {
  id: string;
  user_id: string;
  title: string;
  company: string | null;
  job_city: string | null;
  employment_type: string | null;
  source_name: string | null;
  source_url: string | null;
  jd_text: string;
  parse_status: string;
  parse_error: string | null;
  structured_json: JobStructuredData | null;
  created_at: string;
  updated_at: string;
};

export type MatchInsightItem = {
  label: string;
  reason: string;
  severity: string;
};

export type MatchActionItem = {
  priority: number;
  title: string;
  description: string;
};

export type MatchReportRecord = {
  id: string;
  user_id: string;
  resume_id: string;
  jd_id: string;
  status: string;
  overall_score: string;
  rule_score: string;
  model_score: string;
  dimension_scores_json: Record<string, number>;
  gap_json: {
    strengths: MatchInsightItem[];
    gaps: MatchInsightItem[];
    actions: MatchActionItem[];
  };
  evidence_json: {
    matched_resume_fields: Record<string, string[]>;
    matched_jd_fields: Record<string, string[]>;
    missing_items: string[];
    notes: string[];
    ai_correction: Record<string, unknown>;
  };
  error_message: string | null;
  created_at: string;
  updated_at: string;
};

export type JobDraft = {
  title: string;
  company: string;
  job_city: string;
  employment_type: string;
  source_name: string;
  source_url: string;
  jd_text: string;
};

export function createEmptyJobDraft(): JobDraft {
  return {
    title: "",
    company: "",
    job_city: "",
    employment_type: "",
    source_name: "",
    source_url: "",
    jd_text: "",
  };
}

export function toJobDraft(job: JobRecord): JobDraft {
  return {
    title: job.title,
    company: job.company ?? "",
    job_city: job.job_city ?? "",
    employment_type: job.employment_type ?? "",
    source_name: job.source_name ?? "",
    source_url: job.source_url ?? "",
    jd_text: job.jd_text,
  };
}

function normalizeDraft(draft: JobDraft) {
  return {
    title: draft.title.trim(),
    company: draft.company.trim() || undefined,
    job_city: draft.job_city.trim() || undefined,
    employment_type: draft.employment_type.trim() || undefined,
    source_name: draft.source_name.trim() || undefined,
    source_url: draft.source_url.trim() || undefined,
    jd_text: draft.jd_text.trim(),
  };
}

export async function fetchJobList(token: string): Promise<JobRecord[]> {
  return apiRequest<JobRecord[]>("/jobs", {
    method: "GET",
    token,
  });
}

export async function createJob(
  token: string,
  draft: JobDraft
): Promise<JobRecord> {
  return apiRequest<JobRecord>("/jobs", {
    method: "POST",
    token,
    body: JSON.stringify(normalizeDraft(draft)),
  });
}

export async function updateJob(
  token: string,
  jobId: string,
  draft: JobDraft
): Promise<JobRecord> {
  return apiRequest<JobRecord>(`/jobs/${jobId}`, {
    method: "PUT",
    token,
    body: JSON.stringify(normalizeDraft(draft)),
  });
}

export async function parseJob(
  token: string,
  jobId: string
): Promise<JobRecord> {
  return apiRequest<JobRecord>(`/jobs/${jobId}/parse`, {
    method: "POST",
    token,
  });
}

export async function deleteJob(
  token: string,
  jobId: string
): Promise<{ message: string }> {
  return apiRequest<{ message: string }>(`/jobs/${jobId}`, {
    method: "DELETE",
    token,
  });
}

export async function fetchJobMatchReports(
  token: string,
  jobId: string
): Promise<MatchReportRecord[]> {
  return apiRequest<MatchReportRecord[]>(`/jobs/${jobId}/match-reports`, {
    method: "GET",
    token,
  });
}

export async function createJobMatchReport(
  token: string,
  jobId: string,
  resumeId: string
): Promise<MatchReportRecord> {
  return apiRequest<MatchReportRecord>(`/jobs/${jobId}/match-reports`, {
    method: "POST",
    token,
    body: JSON.stringify({
      resume_id: resumeId,
      force_refresh: true,
    }),
  });
}

export async function deleteMatchReport(
  token: string,
  reportId: string
): Promise<{ message: string }> {
  return apiRequest<{ message: string }>(`/match-reports/${reportId}`, {
    method: "DELETE",
    token,
  });
}
