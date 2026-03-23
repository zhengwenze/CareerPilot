import { apiRequest } from "@/lib/api/client";
import type { TaskStateRecord } from "@/lib/api/modules/resume";

export type MockInterviewReviewRecord = {
  strengths: string[];
  risks: string[];
  next_steps: string[];
};

export type MockInterviewSessionRecord = {
  id: string;
  user_id: string;
  job_id: string;
  resume_optimization_session_id: string | null;
  source_resume_version: number;
  source_job_version: number;
  status: string;
  question_count: number;
  main_question_index: number;
  followup_count_for_current_main: number;
  max_questions: number;
  max_followups_per_main: number;
  prep_state: TaskStateRecord;
  ending_text: string | null;
  error_message: string | null;
  current_turn: MockInterviewTurnRecord | null;
  turns: MockInterviewTurnRecord[];
  review: MockInterviewReviewRecord;
  created_at: string;
  updated_at: string;
};

export type MockInterviewTurnRecord = {
  id: string;
  session_id: string;
  turn_index: number;
  question_text: string;
  question_type: "main" | "followup";
  main_question_id: string;
  answer_text: string | null;
  comment_text: string | null;
  decision_json: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type MockInterviewAnswerSubmitResponse = {
  session_id: string;
  submitted_turn_id: string;
  next_action: Record<string, unknown>;
};

export async function createMockInterviewSession(
  token: string,
  payload: {
    jobId: string;
    optimizationSessionId: string;
  }
): Promise<MockInterviewSessionRecord> {
  return apiRequest<MockInterviewSessionRecord>("/mock-interviews", {
    method: "POST",
    token,
    body: JSON.stringify({
      job_id: payload.jobId,
      resume_optimization_session_id: payload.optimizationSessionId,
    }),
  });
}

export async function listMockInterviewSessions(
  token: string,
  filters: {
    jobId?: string;
  } = {}
): Promise<MockInterviewSessionRecord[]> {
  const params = new URLSearchParams();
  if (filters.jobId) {
    params.set("job_id", filters.jobId);
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
): Promise<MockInterviewSessionRecord> {
  return apiRequest<MockInterviewSessionRecord>(
    `/mock-interviews/${sessionId}/finish`,
    {
      method: "POST",
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

export async function retryMockInterviewPrep(
  token: string,
  sessionId: string
): Promise<{ recorded: boolean }> {
  return apiRequest<{ recorded: boolean }>(
    `/mock-interviews/${sessionId}/retry-prep`,
    {
      method: "POST",
      token,
    }
  );
}

export async function recordMockInterviewEvent(
  token: string,
  sessionId: string,
  payload: {
    event_type: string;
    payload?: Record<string, unknown>;
  }
): Promise<{ recorded: boolean }> {
  return apiRequest<{ recorded: boolean }>(`/mock-interviews/${sessionId}/events`, {
    method: "POST",
    token,
    body: JSON.stringify(payload),
  });
}
