import { apiRequest, apiRequestBlob } from "@/lib/api/client";
import type { JobRecord } from "@/lib/api/modules/jobs";

export type TaskStateRecord = {
  status:
    | "pending"
    | "processing"
    | "success"
    | "failed"
    | "ready"
    | "cancelled"
    | "returned"
    | "aborted";
  phase: string;
  message: string;
  current_step: number;
  total_steps: number;
  started_at: string | null;
  first_completed_at: string | null;
  completed_at: string | null;
  last_updated_at: string | null;
  metrics: Record<string, unknown>;
};

export type SegmentExplanationRecord = {
  what: string;
  why: string;
  value: string;
};

export type ContentChangeItemRecord = {
  id: string;
  segment_key: string;
  section_label: string;
  item_label: string;
  change_type: "rewrite" | "reorder" | "trim" | "highlight" | "unchanged";
  before_text: string;
  after_text: string;
  why: string;
  suggestion: string;
  evidence: string[];
};

export type ContentSegmentRecord = {
  key: string;
  label: string;
  sequence: number;
  status:
    | "pending"
    | "processing"
    | "success"
    | "failed"
    | "cancelled"
    | "returned"
    | "aborted";
  original_text: string;
  suggested_text: string;
  markdown: string;
  explanation: SegmentExplanationRecord;
  error_message: string | null;
  generated_at: string | null;
};

/**
 * 简历结构化数据类型
 * 包含基本信息、教育经历、工作经历、项目经历、技能和证书
 */
export type ResumeStructuredData = {
  basic_info: {
    name: string;
    email: string;
    phone: string;
    location: string;
    summary: string;
  };
  education: string[];
  work_experience: string[];
  projects: string[];
  skills: {
    technical: string[];
    tools: string[];
    languages: string[];
  };
  certifications: string[];
};

/**
 * 简历解析任务记录类型
 * 记录每次解析任务的状态和执行信息
 */
export type ResumeParseJob = {
  id: string;
  status: string;
  attempt_count: number;
  ai_status: string | null;
  ai_message: string | null;
  error_message: string | null;
  started_at: string | null;
  finished_at: string | null;
  created_at: string;
  updated_at: string;
};

export type ResumeParseArtifacts = {
  canonical_resume_md: string;
  meta: {
    source_type?: string;
    parser_version?: string;
    ai_correction_applied?: boolean;
    ai_fallback_used?: boolean;
    ai_error_category?: string | null;
    ai_error_message?: string | null;
  };
};

/**
 * 简历记录类型
 * 包含简历的完整信息和最新的解析任务
 */
export type ResumeRecord = {
  id: string;
  user_id: string;
  file_name: string;
  file_url: string;
  storage_bucket: string;
  storage_object_key: string;
  content_type: string;
  file_size: number;
  parse_status: string;
  parse_error: string | null;
  raw_text: string | null;
  structured_json: ResumeStructuredData | null;
  parse_artifacts_json: ResumeParseArtifacts | null;
  latest_version: number;
  created_at: string;
  updated_at: string;
  latest_parse_job: ResumeParseJob | null;
  download_url: string | null;
};

/**
 * 下载链接响应类型
 * 包含临时下载URL和过期时间
 */
export type ResumeDownloadUrlResponse = {
  download_url: string;
  expires_in: number;
};

export type TailoredResumeArtifactRecord = {
  document: {
    matchSummary: {
      targetRole: string;
      optimizationLevel: "conservative";
      matchedKeywords: string[];
      missingButImportantKeywords: string[];
      overallStrategy: string;
    };
    basic: {
      name: string;
      title: string;
      email: string;
      phone: string;
      location: string;
      links: string[];
    };
    summary: string;
    education: Array<{
      school: string;
      major: string;
      degree: string;
      startDate: string;
      endDate: string;
      description: string[];
    }>;
    experience: Array<{
      company: string;
      position: string;
      startDate: string;
      endDate: string;
      bullets: string[];
    }>;
    projects: Array<{
      name: string;
      role: string;
      startDate: string;
      endDate: string;
      bullets: string[];
      link: string;
    }>;
    skills: string[];
    certificates: string[];
    languages: string[];
    awards: string[];
    customSections: Array<{
      title: string;
      items: Array<{
        title: string;
        subtitle: string;
        years: string;
        description: string[];
      }>;
    }>;
    markdown: string;
    audit: {
      truthfulnessStatus: "passed" | "warning";
      warnings: string[];
      changedSections: string[];
      addedKeywordsOnlyFromEvidence: boolean;
    };
  };
  session_id: string;
  match_report_id: string;
  status: string;
  display_status:
    | "idle"
    | "processing"
    | "segment_progress"
    | "success"
    | "failed"
    | "cancelled"
    | "returned"
    | "aborted"
    | "empty_result";
  fit_band: string;
  overall_score: string;
  task_state: TaskStateRecord;
  segments: ContentSegmentRecord[];
  change_items: ContentChangeItemRecord[];
  error_message: string | null;
  retryable: boolean;
  downloadable: boolean;
  result_is_empty: boolean;
  downloadable_file_name: string | null;
  has_downloadable_markdown: boolean;
  created_at: string;
  updated_at: string;
};

export type TailoredResumeWorkflowRecord = {
  resume: ResumeRecord;
  target_job: JobRecord;
  tailored_resume: TailoredResumeArtifactRecord;
};

/**
 * 删除简历响应类型
 * 包含删除操作的结果消息
 */
export type ResumeDeleteResponse = {
  message: string;
};

/**
 * 打印简历API调用日志
 * @param event 事件名称
 * @param payload 事件数据
 */
function logResumeApi(event: string, payload?: Record<string, unknown>) {
  console.log(`[resume-api] ${event}`, payload ?? {});
}

/**
 * 创建空的简历结构化数据
 * 用于初始化表单或重置状态
 * @returns 空的简历结构化数据对象
 */
export function createEmptyStructuredResume(): ResumeStructuredData {
  return {
    basic_info: {
      name: "",
      email: "",
      phone: "",
      location: "",
      summary: "",
    },
    education: [],
    work_experience: [],
    projects: [],
    skills: {
      technical: [],
      tools: [],
      languages: [],
    },
    certifications: [],
  };
}

/**
 * 上传简历文件
 * 上传PDF文件到服务器，触发自动解析流程
 * @param token 用户认证token
 * @param file 简历文件（PDF格式）
 * @returns 上传后的简历记录，包含解析任务信息
 */
export async function uploadResume(
  token: string,
  file: File
): Promise<ResumeRecord> {
  const formData = new FormData();
  formData.append("file", file);

  logResumeApi("upload:start", {
    fileName: file.name,
    fileSize: file.size,
    fileType: file.type,
  });

  const response = await apiRequest<ResumeRecord>("/resumes/upload", {
    method: "POST",
    token,
    body: formData,
  });
  logResumeApi("upload:success", {
    resumeId: response.id,
    parseStatus: response.parse_status,
    latestParseJobId: response.latest_parse_job?.id ?? null,
  });
  return response;
}

function normalizeOptionalText(value: string | undefined) {
  const normalized = value?.trim();
  return normalized ? normalized : undefined;
}

export async function uploadPrimaryResume(
  token: string,
  file: File
): Promise<ResumeRecord> {
  const formData = new FormData();
  formData.append("file", file);

  return apiRequest<ResumeRecord>("/resumes/upload", {
    method: "POST",
    token,
    body: formData,
  });
}

export async function convertResumePdfToMarkdown(
  token: string,
  file: File
): Promise<{ file_name: string; markdown: string }> {
  const formData = new FormData();
  formData.append("file", file);

  return apiRequest<{ file_name: string; markdown: string }>(
    "/tailored-resumes/pdf-to-md",
    {
      method: "POST",
      token,
      body: formData,
    }
  );
}

export async function fetchTailoredResumeWorkflows(
  token: string
): Promise<TailoredResumeWorkflowRecord[]> {
  return apiRequest<TailoredResumeWorkflowRecord[]>(
    "/tailored-resumes/workflows",
    {
      method: "GET",
      token,
    }
  );
}

export async function fetchTailoredResumeWorkflowDetail(
  token: string,
  sessionId: string
): Promise<TailoredResumeWorkflowRecord> {
  return apiRequest<TailoredResumeWorkflowRecord>(
    `/tailored-resumes/workflows/${sessionId}`,
    {
      method: "GET",
      token,
    }
  );
}

export async function generateTailoredResume(
  token: string,
  payload: {
    resume_id: string;
    job_id?: string;
    title: string;
    company?: string;
    job_city?: string;
    employment_type?: string;
    source_name?: string;
    source_url?: string;
    priority: number;
    jd_text: string;
    force_refresh?: boolean;
    optimization_level?: "conservative";
  }
): Promise<TailoredResumeWorkflowRecord> {
  return apiRequest<TailoredResumeWorkflowRecord>("/tailored-resumes/workflows", {
    method: "POST",
    token,
    body: JSON.stringify({
      resume_id: payload.resume_id,
      job_id: payload.job_id,
      title: payload.title.trim(),
      company: normalizeOptionalText(payload.company),
      job_city: normalizeOptionalText(payload.job_city),
      employment_type: normalizeOptionalText(payload.employment_type),
      source_name: normalizeOptionalText(payload.source_name),
      source_url: normalizeOptionalText(payload.source_url),
      priority: payload.priority,
      jd_text: payload.jd_text.trim(),
      force_refresh: payload.force_refresh ?? false,
      optimization_level: payload.optimization_level ?? "conservative",
    }),
  });
}

export async function downloadTailoredResumeMarkdown(
  token: string,
  sessionId: string
): Promise<{ blob: Blob; fileName: string | null }> {
  return apiRequestBlob(
    `/tailored-resumes/workflows/${sessionId}/download-markdown`,
    {
      method: "GET",
      token,
    }
  );
}

export async function optimizeTailoredResume(
  token: string,
  payload: {
    resume_id: string;
    job_id: string;
    force_refresh?: boolean;
    optimization_level?: "conservative";
  }
): Promise<TailoredResumeWorkflowRecord> {
  return apiRequest<TailoredResumeWorkflowRecord>("/tailored-resumes/optimize", {
    method: "POST",
    token,
    body: JSON.stringify({
      resume_id: payload.resume_id,
      job_id: payload.job_id,
      force_refresh: payload.force_refresh ?? false,
      optimization_level: payload.optimization_level ?? "conservative",
    }),
  });
}

export async function retryTailoredResumeGeneration(
  token: string,
  sessionId: string
): Promise<TailoredResumeWorkflowRecord> {
  return apiRequest<TailoredResumeWorkflowRecord>(
    `/tailored-resumes/workflows/${sessionId}/retry`,
    {
      method: "POST",
      token,
    }
  );
}

export async function recordTailoredResumeEvent(
  token: string,
  sessionId: string,
  payload: {
    event_type: string;
    payload?: Record<string, unknown>;
  }
): Promise<{ recorded: boolean }> {
  return apiRequest<{ recorded: boolean }>(
    `/tailored-resumes/workflows/${sessionId}/events`,
    {
      method: "POST",
      token,
      body: JSON.stringify(payload),
    }
  );
}

/**
 * 获取简历列表
 * 获取当前用户的所有简历记录
 * @param token 用户认证token
 * @returns 简历列表
 */
export async function fetchResumeList(token: string): Promise<ResumeRecord[]> {
  logResumeApi("list:start");
  const response = await apiRequest<ResumeRecord[]>("/resumes", {
    method: "GET",
    token,
  });
  logResumeApi("list:success", {
    count: response.length,
    statuses: response.map((item) => ({
      id: item.id,
      status: item.parse_status,
      latestParseJobStatus: item.latest_parse_job?.status ?? null,
    })),
  });
  return response;
}

/**
 * 获取简历详情
 * 获取指定简历的完整信息和解析状态
 * @param token 用户认证token
 * @param resumeId 简历ID
 * @returns 简历详情记录
 */
export async function fetchResumeDetail(
  token: string,
  resumeId: string
): Promise<ResumeRecord> {
  logResumeApi("detail:start", { resumeId });
  const response = await apiRequest<ResumeRecord>(`/resumes/${resumeId}`, {
    method: "GET",
    token,
  });
  logResumeApi("detail:success", {
    resumeId: response.id,
    parseStatus: response.parse_status,
    parseError: response.parse_error,
    hasRawText: Boolean(response.raw_text),
    rawTextLength: response.raw_text?.length ?? 0,
    hasStructuredJson: Boolean(response.structured_json),
    latestParseJobStatus: response.latest_parse_job?.status ?? null,
  });
  return response;
}

/**
 * 获取简历解析任务历史
 * 获取指定简历的所有解析任务记录
 * @param token 用户认证token
 * @param resumeId 简历ID
 * @returns 解析任务列表
 */
export async function fetchResumeParseJobs(
  token: string,
  resumeId: string
): Promise<ResumeParseJob[]> {
  logResumeApi("parse-jobs:start", { resumeId });
  const response = await apiRequest<ResumeParseJob[]>(
    `/resumes/${resumeId}/parse-jobs`,
    {
      method: "GET",
      token,
    }
  );
  logResumeApi("parse-jobs:success", {
    resumeId,
    count: response.length,
    jobs: response.map((job) => ({
      id: job.id,
      status: job.status,
      aiStatus: job.ai_status,
      attempts: job.attempt_count,
      startedAt: job.started_at,
      finishedAt: job.finished_at,
    })),
  });
  return response;
}

/**
 * 重试简历解析
 * 重新触发简历解析流程
 * @param token 用户认证token
 * @param resumeId 简历ID
 * @returns 重试后的简历记录
 */
export async function retryResumeParse(
  token: string,
  resumeId: string
): Promise<ResumeRecord> {
  logResumeApi("retry:start", { resumeId });
  const response = await apiRequest<ResumeRecord>(
    `/resumes/${resumeId}/parse`,
    {
      method: "POST",
      token,
    }
  );
  logResumeApi("retry:success", {
    resumeId: response.id,
    parseStatus: response.parse_status,
    latestParseJobId: response.latest_parse_job?.id ?? null,
    latestParseJobStatus: response.latest_parse_job?.status ?? null,
  });
  return response;
}

/**
 * 更新简历结构化数据
 * 保存用户手动编辑的简历结构化数据
 * @param token 用户认证token
 * @param resumeId 简历ID
 * @param structuredJson 结构化数据
 * @returns 更新后的简历记录
 */
export async function updateResumeStructuredData(
  token: string,
  resumeId: string,
  markdown: string
): Promise<ResumeRecord> {
  logResumeApi("save-structured:start", {
    resumeId,
    markdownLength: markdown.trim().length,
  });
  const response = await apiRequest<ResumeRecord>(
    `/resumes/${resumeId}/structured`,
    {
      method: "PUT",
      token,
      body: JSON.stringify({
        markdown: markdown.trim(),
      }),
    }
  );
  logResumeApi("save-structured:success", {
    resumeId: response.id,
    version: response.latest_version,
    parseStatus: response.parse_status,
  });
  return response;
}

/**
 * 获取简历下载链接
 * 获取简历PDF文件的临时下载URL
 * @param token 用户认证token
 * @param resumeId 简历ID
 * @returns 包含下载URL和过期时间的对象
 */
export async function fetchResumeDownloadUrl(
  token: string,
  resumeId: string
): Promise<ResumeDownloadUrlResponse> {
  logResumeApi("download-url:start", { resumeId });
  const response = await apiRequest<ResumeDownloadUrlResponse>(
    `/resumes/${resumeId}/download-url`,
    {
      method: "GET",
      token,
    }
  );
  logResumeApi("download-url:success", {
    resumeId,
    expiresIn: response.expires_in,
  });
  return response;
}

/**
 * 删除简历
 * 删除指定的简历记录
 * @param token 用户认证token
 * @param resumeId 简历ID
 * @returns 删除操作结果
 */
export async function deleteResume(
  token: string,
  resumeId: string
): Promise<ResumeDeleteResponse> {
  logResumeApi("delete:start", { resumeId });
  const response = await apiRequest<ResumeDeleteResponse>(
    `/resumes/${resumeId}`,
    {
      method: "DELETE",
      token,
    }
  );
  logResumeApi("delete:success", {
    resumeId,
    message: response.message,
  });
  return response;
}
