import { apiRequest } from "@/lib/api/client";

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

export type ResumeParseJob = {
  id: string;
  status: string;
  attempt_count: number;
  error_message: string | null;
  started_at: string | null;
  finished_at: string | null;
  created_at: string;
  updated_at: string;
};

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

export type ResumeDownloadUrlResponse = {
  download_url: string;
  expires_in: number;
};

export type ResumeDeleteResponse = {
  message: string;
};

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

export async function uploadResume(
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

export async function fetchResumeList(token: string): Promise<ResumeRecord[]> {
  return apiRequest<ResumeRecord[]>("/resumes", {
    method: "GET",
    token,
  });
}

export async function fetchResumeDetail(
  token: string,
  resumeId: string
): Promise<ResumeRecord> {
  return apiRequest<ResumeRecord>(`/resumes/${resumeId}`, {
    method: "GET",
    token,
  });
}

export async function fetchResumeParseJobs(
  token: string,
  resumeId: string
): Promise<ResumeParseJob[]> {
  return apiRequest<ResumeParseJob[]>(`/resumes/${resumeId}/parse-jobs`, {
    method: "GET",
    token,
  });
}

export async function retryResumeParse(
  token: string,
  resumeId: string
): Promise<ResumeRecord> {
  return apiRequest<ResumeRecord>(`/resumes/${resumeId}/parse`, {
    method: "POST",
    token,
  });
}

export async function updateResumeStructuredData(
  token: string,
  resumeId: string,
  structuredJson: ResumeStructuredData
): Promise<ResumeRecord> {
  return apiRequest<ResumeRecord>(`/resumes/${resumeId}/structured`, {
    method: "PUT",
    token,
    body: JSON.stringify({
      structured_json: structuredJson,
    }),
  });
}

export async function fetchResumeDownloadUrl(
  token: string,
  resumeId: string
): Promise<ResumeDownloadUrlResponse> {
  return apiRequest<ResumeDownloadUrlResponse>(
    `/resumes/${resumeId}/download-url`,
    {
      method: "GET",
      token,
    }
  );
}

export async function deleteResume(
  token: string,
  resumeId: string
): Promise<ResumeDeleteResponse> {
  return apiRequest<ResumeDeleteResponse>(`/resumes/${resumeId}`, {
    method: "DELETE",
    token,
  });
}
