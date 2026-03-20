"use client";

import { useEffect, useState } from "react";
import { Save } from "lucide-react";

import { useAuth } from "@/components/auth-provider";
import { PageErrorState, PageLoadingState } from "@/components/page-state";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
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

function PaperInput(props: React.InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      {...props}
      className={`h-12 w-full border-b border-[#1C1C1C]/20 bg-transparent px-4 text-sm text-[#1C1C1C] outline-none placeholder:text-[#1C1C1C]/40 ${props.className ?? ""}`}
    />
  );
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
          setProfile(null);
          setIsLoading(true);
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
      <header className="border-b border-[#1C1C1C]/10 bg-[#F9F8F6]">
        <div className="flex flex-col gap-6 px-6 py-6 sm:px-8 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <div className="inline-flex items-center border border-[#1C1C1C]/10 bg-white px-5 py-3">
              <span className="mr-4 text-2xl leading-none text-[#1C1C1C]">
                *
              </span>
              <span className="text-[1.55rem] font-semibold uppercase tracking-tight text-[#1C1C1C] sm:text-[1.8rem]">
                Profile
              </span>
            </div>

            <div className="mt-6">
              <h1 className="text-3xl font-semibold tracking-tight text-[#1C1C1C] sm:text-4xl">
                个人资料
              </h1>
            </div>

            <p className="mt-5 max-w-3xl text-base leading-relaxed text-[#1C1C1C]/60 sm:text-[1.05rem]">
              这些字段会被后续简历、岗位匹配和面试模块直接复用。
            </p>
          </div>

          <div className="border border-[#1C1C1C]/10 bg-white px-4 py-2 text-sm font-medium text-[#1C1C1C]/60">
            {profile?.email}
          </div>
        </div>
      </header>

      <section className="border-b border-[#1C1C1C]/10 bg-[#F9F8F6]">
        <div className="border-b border-[#1C1C1C]/10 px-5 py-4 sm:px-6">
          <div className="mb-3 flex items-center gap-3">
            <span className="size-2.5 bg-[#1C1C1C]" />
            <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[#1C1C1C]/60">
              编辑资料
            </p>
          </div>
          <h2 className="text-xl font-semibold tracking-tight text-[#1C1C1C]">
            基本信息
          </h2>
        </div>
        <div className="px-5 py-5 sm:px-6">
          <form className="space-y-5" onSubmit={handleSubmit}>
            <div className="grid gap-2">
              <Label className="text-sm font-semibold text-black" htmlFor="nickname">
                昵称
              </Label>
              <PaperInput
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
              <Label className="text-sm font-semibold text-black" htmlFor="jobDirection">
                求职方向
              </Label>
              <PaperInput
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
              <Label className="text-sm font-semibold text-black" htmlFor="targetCity">
                目标城市
              </Label>
              <PaperInput
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
              <Label className="text-sm font-semibold text-black" htmlFor="targetRole">
                期望岗位
              </Label>
              <PaperInput
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
              <Alert className="border border-[#1C1C1C]/10 bg-[#F9F8F6] text-[#1C1C1C]">
                <AlertTitle className="text-base font-semibold tracking-tight text-[#1C1C1C]">
                  保存失败
                </AlertTitle>
                <AlertDescription className="text-sm leading-relaxed text-[#1C1C1C]/60">
                  {error}
                </AlertDescription>
              </Alert>
            ) : null}

            <Button
              className="border-b border-[#1C1C1C]/20 bg-[#1C1C1C] px-5 py-3 text-sm font-medium text-white transition-colors hover:bg-[#1C1C1C]/90 disabled:cursor-not-allowed disabled:opacity-60"
              disabled={isSubmitting}
              type="submit"
            >
              {isSubmitting ? "保存中..." : "保存个人资料"}
              <Save className="ml-2 size-4" />
            </Button>
            {successMessage ? (
              <p className="text-sm leading-7 text-black/70">{successMessage}</p>
            ) : null}
          </form>
        </div>
      </section>
    </div>
  );
}