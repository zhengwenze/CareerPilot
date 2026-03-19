"use client";

import { startTransition, useEffect, useState } from "react";
import { Save } from "lucide-react";

import { useAuth } from "@/components/auth-provider";
import { PageErrorState, PageLoadingState } from "@/components/page-state";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ApiError } from "@/lib/api/client";
import {
  fetchMyProfile,
  updateMyProfile,
  type UserProfile,
} from "@/lib/api/modules/profile";

type ProfileFormState = {
  nickname: string;
  jobDirection: string;
  targetCity: string;
  targetRole: string;
};

function toFormState(profile: UserProfile): ProfileFormState {
  return {
    nickname: profile.nickname ?? "",
    jobDirection: profile.job_direction ?? "",
    targetCity: profile.target_city ?? "",
    targetRole: profile.target_role ?? "",
  };
}

function getErrorMessage(error: unknown) {
  if (error instanceof ApiError) {
    return error.message;
  }
  if (error instanceof Error) {
    return error.message;
  }
  return "保存失败，请稍后重试。";
}

export default function DashboardProfilePage() {
  const { token, refreshCurrentUser } = useAuth();
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [form, setForm] = useState<ProfileFormState>({
    nickname: "",
    jobDirection: "",
    targetCity: "",
    targetRole: "",
  });
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [successMessage, setSuccessMessage] = useState("");

  useEffect(() => {
    if (!token) {
      return;
    }
    const authToken = token;
    let cancelled = false;

    async function loadProfile() {
      setIsLoading(true);
      setError("");

      try {
        const currentProfile = await fetchMyProfile(authToken);
        if (!cancelled) {
          setProfile(currentProfile);
          setForm(toFormState(currentProfile));
        }
      } catch (loadError) {
        if (!cancelled) {
          setError(getErrorMessage(loadError));
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    }

    void loadProfile();

    return () => {
      cancelled = true;
    };
  }, [token]);

  if (!token) {
    return null;
  }

  if (isLoading) {
    return (
      <PageLoadingState
        title="正在加载个人资料"
        description="我们正在同步你的基础信息和求职偏好。"
      />
    );
  }

  if (error && !profile) {
    return (
      <PageErrorState
        actionLabel="重新加载"
        description={error}
        onAction={() => {
          startTransition(() => {
            setProfile(null);
            setIsLoading(true);
          });
        }}
        title="个人资料加载失败"
      />
    );
  }

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!token) {
      return;
    }

    setIsSubmitting(true);
    setError("");
    setSuccessMessage("");

    try {
      const nextProfile = await updateMyProfile(token, {
        nickname: form.nickname.trim() || undefined,
        job_direction: form.jobDirection.trim() || undefined,
        target_city: form.targetCity.trim() || undefined,
        target_role: form.targetRole.trim() || undefined,
      });

      setProfile(nextProfile);
      setForm(toFormState(nextProfile));
      setSuccessMessage("资料已保存，后续模块会直接复用这些偏好。");
      await refreshCurrentUser();
    } catch (submitError) {
      setError(getErrorMessage(submitError));
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="space-y-6">
      <Card className="max-w-3xl rounded-[2rem] border border-black/10 bg-white py-0 shadow-[0_18px_48px_rgba(0,0,0,0.05)]">
        <CardContent className="px-6 py-6 sm:px-8 sm:py-8">
          <div className="mb-8">
            <p className="text-3xl font-semibold tracking-[-0.04em] text-black">
              编辑个人资料
            </p>
            <p className="mt-3 text-sm leading-7 text-black/62">
              这些字段会被后续简历、岗位匹配和面试模块直接复用。
            </p>
            <p className="mt-2 text-sm text-black/52">{profile?.email}</p>
          </div>

          <form className="space-y-5" onSubmit={handleSubmit}>
            <div className="grid gap-2">
              <Label htmlFor="nickname" className="text-black">
                昵称
              </Label>
              <Input
                className="h-12 rounded-2xl border-black/10 bg-[#f5f5f7] px-4 text-black placeholder:text-black/40 focus-visible:border-[#0071E3] focus-visible:ring-[#0071E3]/20"
                id="nickname"
                onChange={(event) =>
                  setForm((current) => ({
                    ...current,
                    nickname: event.target.value,
                  }))
                }
                placeholder="例如：阿泽"
                value={form.nickname}
              />
            </div>

            <div className="grid gap-2">
              <Label htmlFor="jobDirection" className="text-black">
                求职方向
              </Label>
              <Input
                className="h-12 rounded-2xl border-black/10 bg-[#f5f5f7] px-4 text-black placeholder:text-black/40 focus-visible:border-[#0071E3] focus-visible:ring-[#0071E3]/20"
                id="jobDirection"
                onChange={(event) =>
                  setForm((current) => ({
                    ...current,
                    jobDirection: event.target.value,
                  }))
                }
                placeholder="例如：数据分析 / 前端开发 / 产品经理"
                value={form.jobDirection}
              />
            </div>

            <div className="grid gap-2">
              <Label htmlFor="targetCity" className="text-black">
                目标城市
              </Label>
              <Input
                className="h-12 rounded-2xl border-black/10 bg-[#f5f5f7] px-4 text-black placeholder:text-black/40 focus-visible:border-[#0071E3] focus-visible:ring-[#0071E3]/20"
                id="targetCity"
                onChange={(event) =>
                  setForm((current) => ({
                    ...current,
                    targetCity: event.target.value,
                  }))
                }
                placeholder="例如：上海 / 北京 / 杭州"
                value={form.targetCity}
              />
            </div>

            <div className="grid gap-2">
              <Label htmlFor="targetRole" className="text-black">
                期望岗位
              </Label>
              <Input
                className="h-12 rounded-2xl border-black/10 bg-[#f5f5f7] px-4 text-black placeholder:text-black/40 focus-visible:border-[#0071E3] focus-visible:ring-[#0071E3]/20"
                id="targetRole"
                onChange={(event) =>
                  setForm((current) => ({
                    ...current,
                    targetRole: event.target.value,
                  }))
                }
                placeholder="例如：高级数据分析师"
                value={form.targetRole}
              />
            </div>

            {error ? (
              <Alert
                className="rounded-[1.5rem] border-[#ff3b30]/20 bg-[#fff5f5] px-4 py-3"
                variant="destructive"
              >
                <AlertTitle className="text-black">保存失败</AlertTitle>
                <AlertDescription className="text-black/72">{error}</AlertDescription>
              </Alert>
            ) : null}

            <Button
              className="h-12 rounded-full bg-[#0071E3] px-5 text-white hover:bg-[#0077ED]"
              disabled={isSubmitting}
              type="submit"
            >
              {isSubmitting ? "保存中..." : "保存个人资料"}
              <Save className="size-4" />
            </Button>
            {successMessage ? (
              <p className="text-sm leading-7 text-black/62">{successMessage}</p>
            ) : null}
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
