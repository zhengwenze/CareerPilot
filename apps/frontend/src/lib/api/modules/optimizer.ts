import { apiRequest, apiRequestBlob } from "@/lib/api/client";

export type ResumeOptimizationTaskState = {
  key: string;
  title: string;
  instruction: string;
  target_section: string;
  priority: number;
  selected: boolean;
};

export type ResumeOptimizationSectionDraft = {
  key: string;
  label: string;
  selected: boolean;
  original_text: string;
  suggested_text: string;
  mode: string;
};

export type ResumeOptimizationSessionRecord = {
  id: string;
  user_id: string;
  resume_id: string;
  jd_id: string;
  match_report_id: string;
  source_resume_version: number;
  source_job_version: number;
  applied_resume_version: number | null;
  status: string;
  optimizer_context: {
    job_id: string;
    match_report_id: string;
    job_title: string;
    company: string | null;
    fit_band: string;
    stale_status: string;
    target_summary: string | null;
    must_add_evidence: string[];
    gap_summary: string[];
  };
  tailoring_plan_snapshot: Record<string, unknown>;
  draft_sections: Record<string, ResumeOptimizationSectionDraft>;
  selected_tasks: ResumeOptimizationTaskState[];
  optimized_resume_md: string;
  has_downloadable_markdown: boolean;
  downloadable_file_name: string | null;
  is_stale: boolean;
  created_at: string;
  updated_at: string;
};

export async function createResumeOptimizationSession(
  token: string,
  matchReportId: string
): Promise<ResumeOptimizationSessionRecord> {
  return apiRequest<ResumeOptimizationSessionRecord>("/resume-optimization-sessions", {
    method: "POST",
    token,
    body: JSON.stringify({
      match_report_id: matchReportId,
    }),
  });
}

export async function fetchResumeOptimizationSession(
  token: string,
  sessionId: string
): Promise<ResumeOptimizationSessionRecord> {
  return apiRequest<ResumeOptimizationSessionRecord>(
    `/resume-optimization-sessions/${sessionId}`,
    {
      method: "GET",
      token,
    }
  );
}

export async function generateResumeOptimizationSuggestions(
  token: string,
  sessionId: string
): Promise<ResumeOptimizationSessionRecord> {
  return apiRequest<ResumeOptimizationSessionRecord>(
    `/resume-optimization-sessions/${sessionId}/suggestions`,
    {
      method: "POST",
      token,
    }
  );
}

export async function updateResumeOptimizationSession(
  token: string,
  sessionId: string,
  payload: {
    draft_sections: Record<string, ResumeOptimizationSectionDraft>;
    selected_tasks: ResumeOptimizationTaskState[];
  }
): Promise<ResumeOptimizationSessionRecord> {
  return apiRequest<ResumeOptimizationSessionRecord>(
    `/resume-optimization-sessions/${sessionId}`,
    {
      method: "PUT",
      token,
      body: JSON.stringify(payload),
    }
  );
}

export async function applyResumeOptimizationSession(
  token: string,
  sessionId: string
): Promise<{
  session_id: string;
  resume_id: string;
  applied_resume_version: number;
}> {
  return apiRequest<{
    session_id: string;
    resume_id: string;
    applied_resume_version: number;
  }>(`/resume-optimization-sessions/${sessionId}/apply`, {
    method: "POST",
    token,
  });
}

export async function downloadResumeOptimizationMarkdown(
  token: string,
  sessionId: string
): Promise<{ blob: Blob; fileName: string | null }> {
  return apiRequestBlob(
    `/resume-optimization-sessions/${sessionId}/download-markdown`,
    {
      method: "GET",
      token,
    }
  );
}
