import { apiRequest } from "@/lib/api/client";

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
  structuredJson: ResumeStructuredData
): Promise<ResumeRecord> {
  logResumeApi("save-structured:start", {
    resumeId,
    educationCount: structuredJson.education.length,
    workCount: structuredJson.work_experience.length,
    projectCount: structuredJson.projects.length,
  });
  const response = await apiRequest<ResumeRecord>(
    `/resumes/${resumeId}/structured`,
    {
      method: "PUT",
      token,
      body: JSON.stringify({
        structured_json: structuredJson,
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
