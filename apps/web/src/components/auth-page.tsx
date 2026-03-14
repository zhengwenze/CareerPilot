import Link from "next/link";

import { GuestRoute } from "@/components/guards/guest-route";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

import { AuthForm } from "./auth-form";

type AuthPageProps = {
  mode: "login" | "register";
};

export function AuthPage({ mode }: AuthPageProps) {
  const isRegister = mode === "register";

  return (
    <GuestRoute>
      <main className="auth-layout">
        <Card className="surface-card relative overflow-hidden border-0 bg-card/80 py-0 shadow-2xl shadow-amber-950/8 backdrop-blur-xl">
          <div className="absolute inset-x-0 top-0 h-44 bg-[radial-gradient(circle_at_top_left,rgba(245,158,11,0.26),transparent_62%)]" />
          <CardHeader className="relative space-y-6 px-6 py-6 sm:px-8 sm:py-8">
            <Link
              className="inline-flex items-center gap-2 text-sm text-muted-foreground transition hover:text-foreground"
              href="/"
            >
              <Badge className="rounded-full bg-white/75 px-3 py-1 text-primary hover:bg-white/75">
                CareerPilot
              </Badge>
              返回首页
            </Link>

            <div className="space-y-5">
              <p className="eyebrow">求职驾驶舱</p>
              <CardTitle className="max-w-lg text-4xl font-semibold leading-tight tracking-tight text-foreground sm:text-5xl">
                {isRegister
                  ? "先注册账号，再把简历优化、JD 匹配和模拟面试接起来。"
                  : "继续你的求职节奏，把登录态接回到工作台。"}
              </CardTitle>
              <CardDescription className="max-w-xl text-base leading-8 text-muted-foreground">
                当前前端已经正式接入后端认证接口：注册会调用{" "}
                <code>/auth/register</code>， 登录会调用 <code>/auth/login</code>
                ，登录态恢复依赖 <code>/auth/me</code>， 退出会调用{" "}
                <code>/auth/logout</code>。
              </CardDescription>
            </div>
          </CardHeader>

          <CardContent className="relative grid gap-4 px-6 pb-6 sm:grid-cols-2 sm:px-8 sm:pb-8">
            <Card className="rounded-[28px] border border-border/70 bg-white/68 py-0 shadow-none">
              <CardHeader className="px-5 py-5">
                <CardTitle className="text-lg font-semibold text-foreground">
                  登录态恢复
                </CardTitle>
                <CardDescription className="text-sm leading-7 text-muted-foreground">
                  浏览器会保存访问令牌，刷新页面后自动调用 <code>/auth/me</code>{" "}
                  校验并恢复用户信息。
                </CardDescription>
              </CardHeader>
            </Card>
            <Card className="rounded-[28px] border border-border/70 bg-white/68 py-0 shadow-none">
              <CardHeader className="px-5 py-5">
                <CardTitle className="text-lg font-semibold text-foreground">
                  后续扩展准备
                </CardTitle>
                <CardDescription className="text-sm leading-7 text-muted-foreground">
                  这套状态管理可以直接给“简历上传、JD
                  匹配、模拟面试记录”复用，不用重写用户上下文。
                </CardDescription>
              </CardHeader>
            </Card>
          </CardContent>
        </Card>

        <AuthForm mode={mode} />
      </main>
    </GuestRoute>
  );
}
