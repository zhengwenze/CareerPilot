import type { ApiErrorResponse, ApiSuccessResponse } from "./contracts";

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

export class ApiError extends Error {
  status: number;
  code: string;
  details?: unknown;
  requestId?: string;

  constructor(
    message: string,
    options: {
      status: number;
      code?: string;
      details?: unknown;
      requestId?: string;
    }
  ) {
    super(message);
    this.name = "ApiError";
    this.status = options.status;
    this.code = options.code ?? "UNKNOWN_ERROR";
    this.details = options.details;
    this.requestId = options.requestId;
  }
}

async function parseError(response: Response): Promise<never> {
  try {
    const payload = (await response.json()) as
      | ApiErrorResponse
      | { detail?: string | { message?: string } };

    if (
      "error" in payload &&
      payload.error &&
      typeof payload.error.message === "string"
    ) {
      throw new ApiError(payload.error.message, {
        status: response.status,
        code: payload.error.code,
        details: payload.error.details,
        requestId: payload.meta?.request_id,
      });
    }

    if ("detail" in payload) {
      const detail =
        typeof payload.detail === "string"
          ? payload.detail
          : payload.detail && typeof payload.detail.message === "string"
            ? payload.detail.message
            : null;

      if (detail) {
        throw new ApiError(detail, {
          status: response.status,
        });
      }
    }

    throw new ApiError(`请求失败 (${response.status})`, {
      status: response.status,
    });
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }

    throw new ApiError("服务暂时不可用，请检查后端是否已启动。", {
      status: response.status,
    });
  }
}

type ApiRequestInit = RequestInit & { token?: string };

async function performRequest(
  path: string,
  init: ApiRequestInit = {}
): Promise<Response> {
  const { token, headers, ...rest } = init;
  const hasJsonBody = rest.body != null && !(rest.body instanceof FormData);
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...rest,
    cache: "no-store",
    headers: {
      ...(hasJsonBody ? { "Content-Type": "application/json" } : {}),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(headers ?? {}),
    },
  });

  if (!response.ok) {
    await parseError(response);
  }

  return response;
}

function parseContentDispositionFileName(
  contentDisposition: string | null
): string | null {
  if (!contentDisposition) {
    return null;
  }

  const utf8Match = contentDisposition.match(/filename\*=UTF-8''([^;]+)/i);
  if (utf8Match?.[1]) {
    return decodeURIComponent(utf8Match[1]);
  }

  const quotedMatch = contentDisposition.match(/filename=\"([^\"]+)\"/i);
  if (quotedMatch?.[1]) {
    return quotedMatch[1];
  }

  const plainMatch = contentDisposition.match(/filename=([^;]+)/i);
  return plainMatch?.[1]?.trim() ?? null;
}

export async function apiRequest<T>(
  path: string,
  init: ApiRequestInit = {}
): Promise<T> {
  const response = await performRequest(path, init);

  if (response.status === 204) {
    return undefined as T;
  }

  const payload = (await response.json()) as ApiSuccessResponse<T>;
  return payload.data;
}

export async function apiRequestBlob(
  path: string,
  init: ApiRequestInit = {}
): Promise<{ blob: Blob; fileName: string | null }> {
  const response = await performRequest(path, init);
  return {
    blob: await response.blob(),
    fileName: parseContentDispositionFileName(
      response.headers.get("Content-Disposition")
    ),
  };
}
