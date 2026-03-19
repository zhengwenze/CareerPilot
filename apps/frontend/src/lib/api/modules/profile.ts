import { apiRequest } from "@/lib/api/client";

/**
 * 用户个人资料类型
 * 包含用户的基本信息和职业意向
 */
export type UserProfile = {
  user_id: string;
  email: string;
  nickname: string | null;
  job_direction: string | null;
  target_city: string | null;
  target_role: string | null;
  created_at: string;
  updated_at: string;
};

/**
 * 更新个人资料请求体类型
 * 所有字段都是可选的
 */
export type UpdateProfilePayload = {
  nickname?: string;
  job_direction?: string;
  target_city?: string;
  target_role?: string;
};

/**
 * 获取当前用户个人资料
 * @param token 用户认证token
 * @returns 用户个人资料
 */
export async function fetchMyProfile(token: string): Promise<UserProfile> {
  return apiRequest<UserProfile>("/profile/me", {
    method: "GET",
    token,
  });
}

/**
 * 更新当前用户个人资料
 * @param token 用户认证token
 * @param payload 更新的数据（可包含nickname、job_direction、target_city、target_role）
 * @returns 更新后的用户个人资料
 */
export async function updateMyProfile(
  token: string,
  payload: UpdateProfilePayload
): Promise<UserProfile> {
  return apiRequest<UserProfile>("/profile/me", {
    method: "PUT",
    token,
    body: JSON.stringify(payload),
  });
}
