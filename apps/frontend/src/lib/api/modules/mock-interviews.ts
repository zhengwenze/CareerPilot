import { apiRequest } from "@/lib/api/client";

export type MockInterviewMode =
  | "general"
  | "behavioral"
  | "project_deep_dive"
  | "technical"
  | "hr_fit";

export type MockInterviewQuestionRubricItem = {
  dimension: string;
  weight: number;
  criteria: string;
};

export type MockInterviewFocusArea = {
  topic: string;
  reason: string;
  priority: "high" | "medium" | "low";
};

export type MockInterviewQuestionPlanItem = {
  group_index: number;
  source: "strength" | "gap" | "behavioral_general";
  topic: string;
  question_text: string;
  intent: string;
  follow_up_rule: string | null;
  rubric: MockInterviewQuestionRubricItem[];
};

export type MockInterviewPlanRecord = {
  session_summary: string;
  mode: string;
  target_role: string | null;
  focus_areas: MockInterviewFocusArea[];
  question_plan: MockInterviewQuestionPlanItem[];
  ending_rule: {
    max_questions: number;
    max_follow_ups_per_question: number;
  };
};

export type MockInterviewEvaluationRecord = {
  dimension_scores: {
    relevance: number;
    specificity: number;
    evidence: number;
    structure: number;
    communication: number;
  };
  summary: string;
  strengths: string[];
  gaps: string[];
  evidence_used: string[];
};

export type MockInterviewDecisionRecord = {
  type: "follow_up" | "next_question" | "finish_and_review";
  reason: string;
  next_question: {
    topic: string;
    question_text: string;
    intent: string;
  } | null;
};

export type MockInterviewTurnRecord = {
  id: string;
  session_id: string;
  turn_index: number;
  question_group_index: number;
  question_source: string;
  question_topic: string;
  question_text: string;
  question_intent: string | null;
  question_rubric_json: MockInterviewQuestionRubricItem[];
  answer_text: string | null;
  answer_latency_seconds: number | null;
  status: string;
  evaluation_json: MockInterviewEvaluationRecord | null;
  decision_json: MockInterviewDecisionRecord | null;
  asked_at: string | null;
  answered_at: string | null;
  evaluated_at: string | null;
  created_at: string;
  updated_at: string;
};

export type MockInterviewInsightItem = {
  label: string;
  reason: string;
  severity: "high" | "medium" | "low";
};

export type MockInterviewQuestionReview = {
  question_group_index: number;
  source: string;
  question_text: string;
  summary: string;
  strengths: string[];
  gaps: string[];
  suggested_better_answer: string;
};

export type MockInterviewFollowUpTask = {
  title: string;
  task_type: "resume" | "interview";
  instruction: string;
  target_section: string | null;
  reason: string;
  source: string;
};

export type MockInterviewReviewRecord = {
  overall_score: number;
  overall_summary: string;
  dimension_scores: {
    relevance: number;
    specificity: number;
    evidence: number;
    structure: number;
    communication: number;
  };
  strengths: MockInterviewInsightItem[];
  weaknesses: MockInterviewInsightItem[];
  question_reviews: MockInterviewQuestionReview[];
  follow_up_tasks: MockInterviewFollowUpTask[];
  job_readiness_signal: {
    status: string;
    reason: string;
  };
};

export type MockInterviewSessionRecord = {
  id: string;
  user_id: string;
  resume_id: string;
  jd_id: string;
  match_report_id: string;
  optimization_session_id: string | null;
  source_resume_version: number;
  source_job_version: number;
  mode: string;
  status: string;
  current_question_index: number;
  current_follow_up_count: number;
  max_questions: number;
  max_follow_ups_per_question: number;
  plan_json: MockInterviewPlanRecord | null;
  review_json: MockInterviewReviewRecord | null;
  follow_up_tasks_json: MockInterviewFollowUpTask[];
  overall_score: string | null;
  error_message: string | null;
  current_turn: MockInterviewTurnRecord | null;
  turns: MockInterviewTurnRecord[];
  created_at: string;
  updated_at: string;
};

export type MockInterviewReviewResponse = {
  session_id: string;
  status: string;
  overall_score: string | null;
  review_json: MockInterviewReviewRecord | null;
  follow_up_tasks_json: MockInterviewFollowUpTask[];
};

export type MockInterviewAnswerSubmitResponse = {
  session_id: string;
  submitted_turn_id: string;
  submitted_turn_evaluation: MockInterviewEvaluationRecord;
  next_action: {
    type?: "follow_up" | "next_question" | "finish_and_review";
    reason?: string;
    turn?: MockInterviewTurnRecord;
    review?: MockInterviewReviewResponse;
  } & Record<string, unknown>;
};

export async function createMockInterviewSession(
  token: string,
  payload: {
    matchReportId: string;
    mode?: MockInterviewMode;
    optimizationSessionId?: string;
  }
): Promise<MockInterviewSessionRecord> {
  return apiRequest<MockInterviewSessionRecord>("/mock-interviews", {
    method: "POST",
    token,
    body: JSON.stringify({
      match_report_id: payload.matchReportId,
      mode: payload.mode ?? "general",
      optimization_session_id: payload.optimizationSessionId,
    }),
  });
}

export async function listMockInterviewSessions(
  token: string,
  filters: {
    jobId?: string;
    resumeId?: string;
    status?: string;
    mode?: MockInterviewMode;
  } = {}
): Promise<MockInterviewSessionRecord[]> {
  const params = new URLSearchParams();
  if (filters.jobId) {
    params.set("job_id", filters.jobId);
  }
  if (filters.resumeId) {
    params.set("resume_id", filters.resumeId);
  }
  if (filters.status) {
    params.set("status", filters.status);
  }
  if (filters.mode) {
    params.set("mode", filters.mode);
  }

  const suffix = params.toString() ? `?${params.toString()}` : "";
  return apiRequest<MockInterviewSessionRecord[]>(`/mock-interviews${suffix}`, {
    method: "GET",
    token,
  });
}

export async function fetchMockInterviewSession(
  token: string,
  sessionId: string
): Promise<MockInterviewSessionRecord> {
  return apiRequest<MockInterviewSessionRecord>(`/mock-interviews/${sessionId}`, {
    method: "GET",
    token,
  });
}

export async function submitMockInterviewAnswer(
  token: string,
  sessionId: string,
  turnId: string,
  answerText: string
): Promise<MockInterviewAnswerSubmitResponse> {
  return apiRequest<MockInterviewAnswerSubmitResponse>(
    `/mock-interviews/${sessionId}/turns/${turnId}/answer`,
    {
      method: "POST",
      token,
      body: JSON.stringify({
        answer_text: answerText,
      }),
    }
  );
}

export async function finishMockInterviewSession(
  token: string,
  sessionId: string
): Promise<MockInterviewReviewResponse> {
  return apiRequest<MockInterviewReviewResponse>(
    `/mock-interviews/${sessionId}/finish`,
    {
      method: "POST",
      token,
    }
  );
}

export async function fetchMockInterviewReview(
  token: string,
  sessionId: string
): Promise<MockInterviewReviewResponse> {
  return apiRequest<MockInterviewReviewResponse>(
    `/mock-interviews/${sessionId}/review`,
    {
      method: "GET",
      token,
    }
  );
}

export async function deleteMockInterviewSession(
  token: string,
  sessionId: string
): Promise<{ message: string }> {
  return apiRequest<{ message: string }>(`/mock-interviews/${sessionId}`, {
    method: "DELETE",
    token,
  });
}
