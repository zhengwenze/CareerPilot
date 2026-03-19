import { apiRequest } from "@/lib/api/client";

export type JobStructuredData = {
  basic: {
    title: string;
    company: string | null;
    job_city: string | null;
    employment_type: string | null;
  };
  must_have: string[];
  nice_to_have: string[];
  responsibility_clusters: Array<{
    name: string;
    items: string[];
  }>;
  experience_constraints: {
    education: string | null;
    experience_min_years: number | null;
    location: string | null;
    employment_type: string | null;
  };
  domain_context: {
    keywords: string[];
    seniority_hint: string | null;
    summary: string | null;
    benefits: string[];
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

export type JobParseJobRecord = {
  id: string;
  status: string;
  attempt_count: number;
  error_message: string | null;
  started_at: string | null;
  finished_at: string | null;
  created_at: string;
  updated_at: string;
};

export type JobReadinessEventRecord = {
  id: string;
  user_id: string;
  job_id: string;
  resume_id: string | null;
  match_report_id: string | null;
  status_from: string | null;
  status_to: string;
  reason: string | null;
  metadata_json: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type JobLatestMatchReportSummary = {
  id: string;
  status: string;
  overall_score: string;
  fit_band: string;
  stale_status: string;
  resume_id: string;
  resume_version: number;
  created_at: string;
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
  latest_version: number;
  priority: number;
  status_stage: string;
  recommended_resume_id: string | null;
  latest_match_report_id: string | null;
  parse_confidence: string | null;
  competency_graph_json: Record<string, unknown>;
  parse_status: string;
  parse_error: string | null;
  structured_json: JobStructuredData | null;
  latest_parse_job: JobParseJobRecord | null;
  latest_match_report: JobLatestMatchReportSummary | null;
  recent_readiness_events: JobReadinessEventRecord[];
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
  resume_version: number;
  job_version: number;
  status: string;
  fit_band: string;
  stale_status: string;
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
  scorecard_json: {
    overall_score?: number;
    rule_score?: number;
    ai_score?: number;
    fit_band?: string;
    confidence?: number;
    summary?: string;
    reasoning?: string;
    generation_mode?: string;
    dimension_scores?: Record<string, number>;
  } & Record<string, unknown>;
  evidence_map_json: {
    matched_resume_fields?: Record<string, string[]>;
    matched_jd_fields?: Record<string, string[]>;
    missing_items?: string[];
    notes?: string[];
    candidate_profile?: Record<string, unknown>;
    resume_version?: number;
    job_version?: number;
  };
  gap_taxonomy_json: {
    must_fix?: MatchInsightItem[];
    should_fix?: MatchInsightItem[];
    watchlist?: Array<Record<string, string>>;
  };
  action_pack_json: {
    resume_tailoring_tasks?: Array<Record<string, unknown>>;
    interview_focus_areas?: Array<Record<string, unknown>>;
    missing_user_inputs?: Array<Record<string, string>>;
  };
  tailoring_plan_json: {
    target_summary?: string;
    rewrite_tasks?: Array<Record<string, unknown>>;
    must_add_evidence?: string[];
    missing_info_questions?: Array<Record<string, string>>;
  };
  interview_blueprint_json: {
    target_role?: string;
    focus_areas?: Array<Record<string, unknown>>;
    question_pack?: Array<Record<string, unknown>>;
    follow_up_rules?: string[];
    rubric?: Array<Record<string, unknown>>;
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

export async function fetchJobDetail(
  token: string,
  jobId: string
): Promise<JobRecord> {
  return apiRequest<JobRecord>(`/jobs/${jobId}`, {
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

export async function fetchMatchReportDetail(
  token: string,
  reportId: string
): Promise<MatchReportRecord> {
  return apiRequest<MatchReportRecord>(`/match-reports/${reportId}`, {
    method: "GET",
    token,
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
