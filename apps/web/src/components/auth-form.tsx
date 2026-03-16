"use client";

import { AlertCircle, ArrowRight } from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState, useTransition } from "react";

import { ApiError } from "@/lib/api/client";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

import { useAuth } from "./auth-provider";

type AuthFormProps = {
  mode: "login" | "register";
};

const DASHBOARD_ENTRY_PATH = "/dashboard/overview";

function getErrorMessage(error: unknown) {
  if (error instanceof ApiError) {
    return error.message;
  }

  if (error instanceof Error) {
    return error.message;
  }

  return "操作失败，请稍后再试。";
}

export function AuthForm({ mode }: AuthFormProps) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { login, register, isAuthenticated, isBootstrapping } = useAuth();
  const [isRouting, startTransition] = useTransition();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [nickname, setNickname] = useState("");
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const redirectTarget = searchParams.get("next");
  const nextPath =
    redirectTarget && redirectTarget.startsWith("/")
      ? redirectTarget
      : DASHBOARD_ENTRY_PATH;

  useEffect(() => {
    if (!isBootstrapping && isAuthenticated) {
      router.replace(nextPath);
    }
  }, [isAuthenticated, isBootstrapping, nextPath, router]);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setIsSubmitting(true);

    try {
      if (mode === "register") {
        await register({
          email,
          password,
          nickname: nickname.trim() || undefined,
        });
      } else {
        await login({ email, password });
      }

      startTransition(() => {
        router.replace(nextPath);
        router.refresh();
      });
    } catch (submissionError) {
      setError(getErrorMessage(submissionError));
    } finally {
      setIsSubmitting(false);
    }
  }

  const isPending = isSubmitting || isRouting || isBootstrapping;

  return (
    <div className="w-full space-y-6 rounded-2xl bg-white p-8 shadow-sm ring-1 ring-gray-900/5 sm:p-12">
      <div className="space-y-2">
        <div className="inline-flex items-center rounded-full border border-gray-200 bg-gray-50 px-3 py-1 text-xs font-medium text-gray-700">
          CareerPilot Auth
        </div>
      </div>

      <form className="space-y-5" onSubmit={handleSubmit}>
        {mode === "register" && (
          <div className="space-y-2">
            <Label
              htmlFor="nickname"
              className="text-sm font-medium text-gray-900"
            >
              昵称
            </Label>
            <Input
              id="nickname"
              placeholder="比如：阿泽 / 数据分析求职者"
              value={nickname}
              onChange={(event) => setNickname(event.target.value)}
              className="h-11 rounded-xl border-gray-300 bg-gray-50 text-base placeholder:text-gray-400 focus:border-black focus:ring-black"
            />
          </div>
        )}

        <div className="space-y-2">
          <Label htmlFor="email" className="text-sm font-medium text-gray-900">
            邮箱
          </Label>
          <Input
            id="email"
            type="email"
            placeholder="you@example.com"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            required
            className="h-11 rounded-xl border-gray-300 bg-gray-50 text-base placeholder:text-gray-400 focus:border-black focus:ring-black"
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="password" className="text-sm font-medium text-gray-900">
            密码
          </Label>
          <Input
            id="password"
            type="password"
            placeholder="至少 8 位，建议包含字母和数字"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            minLength={8}
            required
            className="h-11 rounded-xl border-gray-300 bg-gray-50 text-base placeholder:text-gray-400 focus:border-black focus:ring-black"
          />
        </div>

        {error && (
          <Alert variant="destructive" className="rounded-xl border-red-200 bg-red-50/50 px-4 py-3">
            <AlertCircle className="mt-0.5 size-4" />
            <AlertTitle className="text-sm">提交失败</AlertTitle>
            <AlertDescription className="text-sm">{error}</AlertDescription>
          </Alert>
        )}

        <Button
          className="h-11 w-full rounded-xl bg-black text-sm font-medium text-white hover:bg-gray-800 focus:ring-black focus:ring-offset-1 disabled:opacity-60"
          disabled={isPending}
          type="submit"
        >
          {isPending
            ? "处理中..."
            : mode === "register"
            ? "注册并进入工作台"
            : "登录并恢复工作台"}
          <ArrowRight className="ml-2 size-4" />
        </Button>
      </form>
    </div>
  );
}
