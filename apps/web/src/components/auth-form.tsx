"use client";

import { AlertCircle, ArrowRight } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState, useTransition } from "react";

import { ApiError } from "@/lib/auth";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

import { useAuth } from "./auth-provider";

type AuthFormProps = {
  mode: "login" | "register";
};

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
  const { login, register, isAuthenticated, isBootstrapping } = useAuth();
  const [isRouting, startTransition] = useTransition();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [nickname, setNickname] = useState("");
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    if (!isBootstrapping && isAuthenticated) {
      router.replace("/");
    }
  }, [isAuthenticated, isBootstrapping, router]);

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
        router.push("/");
        router.refresh();
      });
    } catch (submissionError) {
      setError(getErrorMessage(submissionError));
    } finally {
      setIsSubmitting(false);
    }
  }

  const isPending = isSubmitting || isRouting || isBootstrapping;
  const title = mode === "register" ? "创建你的求职工作台" : "登录继续你的求职计划";
  const subtitle =
    mode === "register"
      ? "注册后会直接调用后端注册接口，完成账号创建并自动进入已登录状态。"
      : "登录后会自动校验当前用户信息，并在本地恢复登录态。";

  return (
    <Card className="surface-card w-full max-w-xl border-0 bg-card/85 py-0 shadow-2xl shadow-emerald-950/8 backdrop-blur-xl">
      <CardHeader className="space-y-4 border-b border-border/70 px-6 py-6 sm:px-8">
        <Badge className="w-fit rounded-full bg-primary/10 px-3 py-1 text-primary hover:bg-primary/10">
          CareerPilot Auth
        </Badge>
        <div className="space-y-3">
          <CardTitle className="text-3xl font-semibold tracking-tight text-foreground sm:text-4xl">
            {title}
          </CardTitle>
          <CardDescription className="max-w-lg text-sm leading-7 text-muted-foreground sm:text-base">
            {subtitle}
          </CardDescription>
        </div>
      </CardHeader>

      <CardContent className="px-6 py-6 sm:px-8">
        <form className="space-y-5" onSubmit={handleSubmit}>
          {mode === "register" ? (
            <div className="grid gap-2">
              <Label htmlFor="nickname">昵称</Label>
              <Input
                className="h-11 rounded-2xl border-border/70 bg-white/80 px-4"
                id="nickname"
                placeholder="比如：阿泽 / 数据分析求职者"
                value={nickname}
                onChange={(event) => setNickname(event.target.value)}
              />
            </div>
          ) : null}

          <div className="grid gap-2">
            <Label htmlFor="email">邮箱</Label>
            <Input
              className="h-11 rounded-2xl border-border/70 bg-white/80 px-4"
              id="email"
              type="email"
              placeholder="you@example.com"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              required
            />
          </div>

          <div className="grid gap-2">
            <Label htmlFor="password">密码</Label>
            <Input
              className="h-11 rounded-2xl border-border/70 bg-white/80 px-4"
              id="password"
              type="password"
              placeholder="至少 8 位，建议包含字母和数字"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              minLength={8}
              required
            />
          </div>

          {error ? (
            <Alert
              className="rounded-2xl border-destructive/20 bg-destructive/5 px-4 py-3"
              variant="destructive"
            >
              <AlertCircle className="mt-0.5 size-4" />
              <AlertTitle>提交失败</AlertTitle>
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          ) : null}

          <Button
            className="h-11 w-full rounded-full text-sm font-semibold shadow-lg shadow-emerald-950/10"
            disabled={isPending}
            type="submit"
          >
            {isPending
              ? "处理中..."
              : mode === "register"
                ? "注册并进入工作台"
                : "登录并恢复工作台"}
            <ArrowRight className="size-4" />
          </Button>
        </form>
      </CardContent>

      <CardFooter className="flex flex-col gap-3 border-t border-border/70 bg-muted/35 px-6 py-5 text-sm text-muted-foreground sm:flex-row sm:items-center sm:justify-between sm:px-8">
        <span>{mode === "register" ? "已经有账号？" : "还没有账号？"}</span>
        <Button
          asChild
          className="h-auto rounded-full px-0 py-0 text-primary hover:text-primary/80"
          variant="link"
        >
          <Link href={mode === "register" ? "/login" : "/register"}>
            {mode === "register" ? "去登录" : "去注册"}
          </Link>
        </Button>
      </CardFooter>
    </Card>
  );
}
