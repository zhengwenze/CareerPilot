"use client";

import { startTransition, useEffect, useState } from "react";
import { Save } from "lucide-react";

import { useAuth } from "@/components/auth-provider";
import { PageErrorState, PageLoadingState } from "@/components/page-state";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
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
    <>
      <Card className="surface-card border-0 bg-card/85 py-0 shadow-2xl shadow-emerald-950/8">
        <CardContent className="px-6 py-6 sm:px-8 sm:py-8">
          <div className="flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
            <div className="max-w-3xl space-y-4">
              <Badge className="w-fit rounded-full bg-primary/10 px-3 py-1 text-primary hover:bg-primary/10">
                Profile
              </Badge>
              <div className="space-y-3">
                <h2 className="text-4xl font-semibold tracking-tight text-foreground sm:text-5xl">
                  个人信息与求职偏好
                </h2>
                <p className="max-w-2xl text-base leading-8 text-muted-foreground">
                  这里是后续简历、岗位匹配、模拟面试都会复用的基础资料层。先把方向、城市和目标岗位填好，后面生成的建议会更贴近你的真实求职目标。
                </p>
              </div>
            </div>

            <div className="rounded-[28px] border border-border/70 bg-white/72 p-4 shadow-sm">
              <p className="text-sm text-muted-foreground">当前路由</p>
              <p className="mt-2 text-base font-medium text-foreground">
                /dashboard/profile
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      <section className="grid gap-5 xl:grid-cols-[1.15fr_0.85fr]">
        <Card className="surface-card border-0 bg-card/78 py-0 shadow-xl shadow-emerald-950/5">
          <CardHeader className="px-6 py-6 sm:px-8">
            <Badge className="w-fit rounded-full bg-secondary px-3 py-1 text-secondary-foreground">
              资料表单
            </Badge>
            <CardTitle className="text-2xl font-semibold text-foreground">
              保存后会直接写入数据库
            </CardTitle>
          </CardHeader>
          <CardContent className="px-6 pb-6 sm:px-8 sm:pb-8">
            <form className="space-y-5" onSubmit={handleSubmit}>
              <div className="grid gap-2">
                <Label htmlFor="nickname">昵称</Label>
                <Input
                  className="h-11 rounded-2xl border-border/70 bg-white/80 px-4"
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
                <Label htmlFor="jobDirection">求职方向</Label>
                <Input
                  className="h-11 rounded-2xl border-border/70 bg-white/80 px-4"
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
                <Label htmlFor="targetCity">目标城市</Label>
                <Input
                  className="h-11 rounded-2xl border-border/70 bg-white/80 px-4"
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
                <Label htmlFor="targetRole">期望岗位</Label>
                <Input
                  className="h-11 rounded-2xl border-border/70 bg-white/80 px-4"
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
                <Alert className="rounded-2xl border-destructive/20 bg-destructive/5 px-4 py-3" variant="destructive">
                  <AlertTitle>保存失败</AlertTitle>
                  <AlertDescription>{error}</AlertDescription>
                </Alert>
              ) : null}

              {successMessage ? (
                <Alert className="rounded-2xl border-primary/20 bg-primary/5 px-4 py-3">
                  <AlertTitle>保存成功</AlertTitle>
                  <AlertDescription>{successMessage}</AlertDescription>
                </Alert>
              ) : null}

              <Button
                className="h-11 rounded-full px-5"
                disabled={isSubmitting}
                type="submit"
              >
                {isSubmitting ? "保存中..." : "保存个人资料"}
                <Save className="size-4" />
              </Button>
            </form>
          </CardContent>
        </Card>

        <Card className="surface-card border-0 bg-card/78 py-0 shadow-xl shadow-emerald-950/5">
          <CardHeader className="space-y-4 px-6 py-6 sm:px-8">
            <Badge className="w-fit rounded-full bg-primary/10 px-3 py-1 text-primary hover:bg-primary/10">
              复用说明
            </Badge>
            <CardTitle className="text-2xl font-semibold text-foreground">
              这层数据会被后续模块直接消费
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 px-6 pb-6 sm:px-8 sm:pb-8">
            {[
              "简历中心：默认推荐与求职方向相符的简历版本。",
              "岗位匹配：结合目标城市和期望岗位生成更稳的匹配逻辑。",
              "模拟面试：用你的目标岗位和方向定制问题语境。",
              "Dashboard：把个人资料补全度纳入总览提醒。",
            ].map((item, index) => (
              <div
                className="flex items-start gap-3 rounded-[24px] border border-border/70 bg-white/72 px-4 py-4"
                key={item}
              >
                <span className="flex size-8 shrink-0 items-center justify-center rounded-2xl bg-secondary text-sm font-semibold text-secondary-foreground">
                  {index + 1}
                </span>
                <p className="pt-0.5 text-sm leading-7 text-muted-foreground">
                  {item}
                </p>
              </div>
            ))}
          </CardContent>
        </Card>
      </section>
    </>
  );
}
