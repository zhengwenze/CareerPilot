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
  const filledCount = [
    form.nickname,
    form.jobDirection,
    form.targetCity,
    form.targetRole,
  ].filter((item) => item.trim()).length;
  const completion = Math.round((filledCount / 4) * 100);

  useEffect(() => {
    if (!token) {
      return;
    }
    const authToken: string = token;

    let cancelled = false;

    async function loadProfile() {
      setIsLoading(true);
      setError("");

      try {
        const currentProfile = await fetchMyProfile(authToken);
        if (cancelled) {
          return;
        }

        setProfile(currentProfile);
        setForm(toFormState(currentProfile));
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
    const authToken: string = token;

    setIsSubmitting(true);
    setError("");
    setSuccessMessage("");

    try {
      const nextProfile = await updateMyProfile(authToken, {
        nickname: form.nickname.trim() || undefined,
        job_direction: form.jobDirection.trim() || undefined,
        target_city: form.targetCity.trim() || undefined,
        target_role: form.targetRole.trim() || undefined,
      });

      setProfile(nextProfile);
      setForm(toFormState(nextProfile));
      setSuccessMessage("资料已保存，后续简历和面试模块都可以直接复用这些偏好。");
      await refreshCurrentUser();
    } catch (submitError) {
      setError(getErrorMessage(submitError));
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="space-y-8">
      <section className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_320px] lg:items-end">
        <div className="max-w-4xl">
          <p className="text-sm font-medium tracking-[0.18em] text-black uppercase">
            Profile
          </p>
          <h1 className="mt-4 text-4xl font-semibold tracking-[-0.05em] text-black sm:text-5xl">
            把偏好信息整理清楚，后续建议才会更准确。
          </h1>
          <p className="mt-5 max-w-3xl text-base leading-8 text-black/72">
            个人资料是简历推荐、岗位匹配和模拟面试的输入上下文。这里保留必要字段和保存动作，不再放无实际作用的解释性卡片。
          </p>
        </div>

        <Card className="rounded-[2rem] border border-black/10 bg-[#f5f5f7] py-0 shadow-none">
          <CardContent className="px-6 py-6">
            <p className="text-xs font-medium tracking-[0.18em] text-black uppercase">
              Profile Completion
            </p>
            <p className="mt-4 text-3xl font-semibold tracking-[-0.05em] text-black">
              {completion}%
            </p>
            <div className="mt-4 h-2 overflow-hidden rounded-full bg-white">
              <div
                className="h-full rounded-full bg-[#0071E3]"
                style={{ width: `${completion}%` }}
              />
            </div>
            <p className="mt-4 text-sm leading-7 text-black/65">{profile.email}</p>
          </CardContent>
        </Card>
      </section>

      <section className="grid gap-5 xl:grid-cols-[1.1fr_0.9fr]">
        <Card className="rounded-[2rem] border border-black/10 bg-white py-0 shadow-[0_18px_48px_rgba(0,0,0,0.05)]">
          <CardContent className="px-6 py-6 sm:px-8 sm:py-8">
            <div className="mb-8">
              <p className="text-2xl font-semibold tracking-[-0.04em] text-black">
                编辑个人资料
              </p>
              <p className="mt-3 text-sm leading-7 text-black/62">
                保存后会直接更新数据库中的个人资料，并被后续模块复用。
              </p>
            </div>

            <form className="space-y-5" onSubmit={handleSubmit}>
              <div className="grid gap-2">
                <Label htmlFor="nickname" className="text-black">昵称</Label>
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
                <Label htmlFor="jobDirection" className="text-black">求职方向</Label>
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
                <Label htmlFor="targetCity" className="text-black">目标城市</Label>
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
                <Label htmlFor="targetRole" className="text-black">期望岗位</Label>
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
                <Alert className="rounded-[1.5rem] border-[#ff3b30]/20 bg-[#fff5f5] px-4 py-3" variant="destructive">
                  <AlertTitle className="text-black">保存失败</AlertTitle>
                  <AlertDescription className="text-black/72">{error}</AlertDescription>
                </Alert>
              ) : null}

              {successMessage ? (
                <Alert className="rounded-[1.5rem] border-[#0071E3]/15 bg-[#F5F9FF] px-4 py-3">
                  <AlertTitle className="text-black">保存成功</AlertTitle>
                  <AlertDescription className="text-black/72">{successMessage}</AlertDescription>
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
            </form>
          </CardContent>
        </Card>

        <Card className="rounded-[2rem] border border-black/10 bg-[#f5f5f7] py-0 shadow-none">
          <CardContent className="space-y-4 px-6 py-6 sm:px-8 sm:py-8">
            <p className="text-2xl font-semibold tracking-[-0.04em] text-black">
              当前资料摘要
            </p>
            {[
              { label: "账号邮箱", value: profile.email },
              { label: "求职方向", value: form.jobDirection || "暂未填写" },
              { label: "目标城市", value: form.targetCity || "暂未填写" },
              { label: "期望岗位", value: form.targetRole || "暂未填写" },
            ].map((item) => (
              <div
                key={item.label}
                className="rounded-[1.5rem] border border-black/10 bg-white px-4 py-4"
              >
                <p className="text-xs font-medium tracking-[0.14em] text-black/45 uppercase">
                  {item.label}
                </p>
                <p className="mt-2 text-sm leading-7 text-black">{item.value}</p>
              </div>
            ))}
          </CardContent>
        </Card>
      </section>
    </div>
  );
}
