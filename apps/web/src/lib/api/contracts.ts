export type ApiMeta = {
  request_id: string;
  timestamp: string;
};

export type ApiSuccessResponse<T> = {
  success: true;
  data: T;
  meta: ApiMeta;
};

export type ApiErrorResponse = {
  success: false;
  error: {
    code: string;
    message: string;
    details?: unknown;
  };
  meta: ApiMeta;
};
