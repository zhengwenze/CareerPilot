import { apiRequest } from "@/lib/api/client";

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

export type UpdateProfilePayload = {
  nickname?: string;
  job_direction?: string;
  target_city?: string;
  target_role?: string;
};

export async function fetchMyProfile(token: string): Promise<UserProfile> {
  return apiRequest<UserProfile>("/profile/me", {
    method: "GET",
    token,
  });
}

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
