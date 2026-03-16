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
  const title = mode === "register" ? "创建账号" : "欢迎回来";
  const description =
    mode === "register"
      ? "输入基础信息后即可创建账号，并自动进入你的求职工作台。"
      : "输入邮箱与密码，继续访问你的简历解析和职位进展。";

  return (
    <div className="w-full rounded-[2rem] border border-black/10 bg-white p-8 shadow-[0_24px_60px_rgba(0,0,0,0.08)] sm:p-10">
      <div className="space-y-3">
        <div className="inline-flex items-center rounded-full border border-black/10 px-3 py-1 text-xs font-medium tracking-[0.16em] text-black uppercase">
          {mode === "register" ? "Create Account" : "Sign In"}
        </div>

        <div className="space-y-2">
          <h3 className="text-3xl font-semibold tracking-[-0.05em] text-black">
            {title}
          </h3>
          <p className="text-sm leading-6 text-black">{description}</p>
        </div>
      </div>

      <form className="mt-8 space-y-5" onSubmit={handleSubmit}>
        {mode === "register" && (
          <div className="space-y-2">
            <Label
              htmlFor="nickname"
              className="text-sm font-medium text-black"
            >
              昵称
            </Label>
            <Input
              id="nickname"
              placeholder="比如：阿泽 / 数据分析求职者"
              value={nickname}
              onChange={(event) => setNickname(event.target.value)}
              className="h-12 rounded-2xl border-black/10 bg-[#f5f5f7] px-4 text-base text-black placeholder:text-black/40 focus-visible:border-[#0071E3] focus-visible:ring-[#0071E3]/20"
            />
          </div>
        )}

        <div className="space-y-2">
          <Label htmlFor="email" className="text-sm font-medium text-black">
            邮箱
          </Label>
          <Input
            id="email"
            type="email"
            placeholder="you@example.com"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            required
            className="h-12 rounded-2xl border-black/10 bg-[#f5f5f7] px-4 text-base text-black placeholder:text-black/40 focus-visible:border-[#0071E3] focus-visible:ring-[#0071E3]/20"
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="password" className="text-sm font-medium text-black">
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
            className="h-12 rounded-2xl border-black/10 bg-[#f5f5f7] px-4 text-base text-black placeholder:text-black/40 focus-visible:border-[#0071E3] focus-visible:ring-[#0071E3]/20"
          />
        </div>

        {error && (
          <Alert
            variant="destructive"
            className="rounded-[1.5rem] border-[#ff3b30]/20 bg-[#fff5f5] px-4 py-3 text-black"
          >
            <AlertCircle className="mt-0.5 size-4 text-[#ff3b30]" />
            <AlertTitle className="text-sm text-black">提交失败</AlertTitle>
            <AlertDescription className="text-sm text-black">
              {error}
            </AlertDescription>
          </Alert>
        )}

        <Button
          className="h-12 w-full rounded-full bg-[#0071E3] text-sm font-medium text-white shadow-none hover:bg-[#0077ED] focus-visible:ring-[#0071E3]/30 focus-visible:ring-offset-2 disabled:opacity-60"
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

        <p className="text-center text-xs leading-6 text-black">
          点击继续即表示你将使用 CareerPilot 管理简历、岗位与求职进度。
        </p>
      </form>
    </div>
  );
}
