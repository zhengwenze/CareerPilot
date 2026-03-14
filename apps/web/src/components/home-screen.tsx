"use client";

import { ArrowRight, LogOut, Sparkles, UserRoundCheck } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useDeferredValue, useTransition } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

import { useAuth } from "./auth-provider";

export function HomeScreen() {
  const router = useRouter();
  const { user, logout, isAuthenticated, isBootstrapping } = useAuth();
  const [isRouting, startTransition] = useTransition();
  const deferredUser = useDeferredValue(user);

  async function handleLogout() {
    await logout();
    startTransition(() => {
      router.push("/login");
      router.refresh();
    });
  }

  if (isBootstrapping) {
    return (
      <main className="page-shell">
        <Card className="surface-card max-w-3xl border-0 bg-card/85 py-0 shadow-2xl shadow-emerald-950/8">
          <CardHeader className="space-y-4 px-6 py-6 sm:px-8">
            <Badge className="w-fit rounded-full bg-primary/10 px-3 py-1 text-primary hover:bg-primary/10">
              正在恢复登录态
            </Badge>
            <CardTitle className="text-3xl font-semibold tracking-tight text-foreground">
              CareerPilot 正在从后端校验当前用户信息
            </CardTitle>
            <CardDescription className="max-w-2xl text-base leading-8 text-muted-foreground">
              我们会自动读取浏览器中的登录凭证，并调用 <code>/auth/me</code> 恢复你的求职工作台。
            </CardDescription>
          </CardHeader>
        </Card>
      </main>
    );
  }

  if (!isAuthenticated || !deferredUser) {
    return (
      <main className="page-shell">
        <Card className="surface-card border-0 bg-card/85 py-0 shadow-2xl shadow-amber-950/8">
          <CardContent className="px-6 py-6 sm:px-8 sm:py-8">
            <div className="flex flex-col gap-10 lg:flex-row lg:items-end lg:justify-between">
              <div className="max-w-3xl space-y-6">
                <p className="eyebrow">AI 求职工作台</p>
                <h1 className="text-5xl font-semibold leading-tight tracking-tight text-foreground sm:text-6xl">
                  把简历优化、岗位匹配和模拟面试，收拢到一个稳定的登录入口里。
                </h1>
                <p className="max-w-2xl text-lg leading-9 text-muted-foreground">
                  前端已经接好了注册、登录、退出和登录态恢复。你现在可以先创建账号，后面继续无缝接入简历上传、
                  JD 匹配和面试记录。
                </p>
              </div>

              <div className="grid gap-3 sm:grid-cols-2">
                <Button asChild className="h-11 rounded-full px-5 shadow-lg shadow-emerald-950/10">
                  <Link href="/register">
                    立即注册
                    <ArrowRight className="size-4" />
                  </Link>
                </Button>
                <Button
                  asChild
                  className="h-11 rounded-full border-border/70 bg-white/72 px-5"
                  variant="outline"
                >
                  <Link href="/login">已有账号，去登录</Link>
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>

        <section className="grid gap-5 lg:grid-cols-[1.2fr_0.8fr]">
          <Card className="surface-card border-0 bg-card/78 py-0 shadow-xl shadow-emerald-950/5">
            <CardHeader className="px-6 py-6 sm:px-8">
              <Badge className="w-fit rounded-full bg-primary/10 px-3 py-1 text-primary hover:bg-primary/10">
                已接入接口
              </Badge>
            </CardHeader>
            <CardContent className="grid gap-4 px-6 pb-6 sm:grid-cols-2 sm:px-8 sm:pb-8">
              {[
                { title: "注册", endpoint: "POST /auth/register", detail: "创建账号并返回 JWT" },
                { title: "登录", endpoint: "POST /auth/login", detail: "校验邮箱密码并进入工作台" },
                { title: "当前用户", endpoint: "GET /auth/me", detail: "刷新后恢复登录态" },
                { title: "退出", endpoint: "POST /auth/logout", detail: "将当前 token 拉入黑名单" },
              ].map((item) => (
                <Card
                  className="rounded-[28px] border border-border/70 bg-white/72 py-0 shadow-none"
                  key={item.endpoint}
                >
                  <CardHeader className="space-y-2 px-5 py-5">
                    <CardDescription className="text-sm text-muted-foreground">
                      {item.title}
                    </CardDescription>
                    <CardTitle className="text-xl font-semibold text-foreground">
                      {item.endpoint}
                    </CardTitle>
                    <CardDescription className="text-sm leading-7 text-muted-foreground">
                      {item.detail}
                    </CardDescription>
                  </CardHeader>
                </Card>
              ))}
            </CardContent>
          </Card>

          <Card className="surface-card border-0 bg-card/78 py-0 shadow-xl shadow-emerald-950/5">
            <CardHeader className="space-y-4 px-6 py-6 sm:px-8">
              <Badge className="w-fit rounded-full bg-secondary px-3 py-1 text-secondary-foreground">
                下一步建议
              </Badge>
              <CardDescription className="text-sm leading-8 text-muted-foreground">
                你现在已经有了一套完整的登录入口，后续页面只需要复用同一个用户上下文和 shadcn 组件体系。
              </CardDescription>
            </CardHeader>
            <CardContent className="px-6 pb-6 sm:px-8">
              <ol className="space-y-4 text-sm leading-7 text-muted-foreground">
                <li>1. 注册一个测试账号，确认前后端都已启动。</li>
                <li>2. 登录后在首页看到个人信息卡片，说明登录态恢复成功。</li>
                <li>3. 下一阶段就可以把简历上传、JD 列表等接口接到同一个用户上下文里。</li>
              </ol>
            </CardContent>
          </Card>
        </section>
      </main>
    );
  }

  return (
    <main className="page-shell">
      <Card className="surface-card border-0 bg-card/85 py-0 shadow-2xl shadow-emerald-950/8">
        <CardContent className="px-6 py-6 sm:px-8 sm:py-8">
          <div className="flex flex-col gap-8 lg:flex-row lg:items-start lg:justify-between">
            <div className="max-w-3xl space-y-4">
              <Badge className="w-fit rounded-full bg-primary/10 px-3 py-1 text-primary hover:bg-primary/10">
                已登录
              </Badge>
              <h1 className="text-4xl font-semibold tracking-tight text-foreground sm:text-5xl">
                欢迎回来，{deferredUser.nickname || deferredUser.email}
              </h1>
              <p className="max-w-2xl text-base leading-8 text-muted-foreground">
                前端已经通过 <code>/auth/me</code> 恢复了你的登录态。接下来你可以继续把 CareerPilot
                扩展成完整的求职工作台。
              </p>
            </div>

            <div className="flex flex-wrap gap-3">
              <Button
                asChild
                className="h-11 rounded-full border-border/70 bg-white/72 px-5"
                variant="outline"
              >
                <Link href="/register">再注册一个测试账号</Link>
              </Button>
              <Button
                className="h-11 rounded-full px-5 shadow-lg shadow-emerald-950/10"
                disabled={isRouting}
                onClick={() => void handleLogout()}
                type="button"
              >
                {isRouting ? "退出中..." : "退出登录"}
                <LogOut className="size-4" />
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      <section className="grid gap-5 lg:grid-cols-[0.9fr_1.1fr]">
        <Card className="surface-card border-0 bg-card/78 py-0 shadow-xl shadow-emerald-950/5">
          <CardHeader className="space-y-4 px-6 py-6 sm:px-8">
            <Badge className="w-fit rounded-full bg-secondary px-3 py-1 text-secondary-foreground">
              账号快照
            </Badge>
          </CardHeader>
          <CardContent className="space-y-4 px-6 pb-6 text-sm sm:px-8 sm:pb-8">
            {[
              { label: "邮箱", value: deferredUser.email, icon: Sparkles },
              { label: "角色", value: deferredUser.role, icon: UserRoundCheck },
              { label: "状态", value: deferredUser.status, icon: LogOut },
            ].map((item) => (
              <Card
                className="rounded-[24px] border border-border/70 bg-white/72 py-0 shadow-none"
                key={item.label}
              >
                <CardContent className="flex items-start gap-4 px-5 py-5">
                  <div className="rounded-2xl bg-primary/10 p-3 text-primary">
                    <item.icon className="size-4" />
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">{item.label}</p>
                    <p className="mt-2 text-base font-medium text-foreground">{item.value}</p>
                  </div>
                </CardContent>
              </Card>
            ))}
          </CardContent>
        </Card>

        <Card className="surface-card border-0 bg-card/78 py-0 shadow-xl shadow-emerald-950/5">
          <CardHeader className="space-y-4 px-6 py-6 sm:px-8">
            <Badge className="w-fit rounded-full bg-primary/10 px-3 py-1 text-primary hover:bg-primary/10">
              登录链路状态
            </Badge>
          </CardHeader>
          <CardContent className="grid gap-4 px-6 pb-6 sm:grid-cols-2 sm:px-8 sm:pb-8">
            {[
              "注册接口已返回 JWT 与用户信息",
              "登录接口已打通密码校验",
              "退出接口已接入 token 黑名单",
              "当前用户接口已接入前端恢复流程",
            ].map((item) => (
              <Card
                className="rounded-[28px] border border-border/70 bg-white/72 py-0 shadow-none"
                key={item}
              >
                <CardContent className="px-5 py-5 text-sm leading-7 text-muted-foreground">
                  {item}
                </CardContent>
              </Card>
            ))}
          </CardContent>
        </Card>
      </section>
    </main>
  );
}
