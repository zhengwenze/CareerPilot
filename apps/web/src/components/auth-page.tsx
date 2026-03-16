import Link from "next/link";

import { GuestRoute } from "@/components/guards/guest-route";
import { Badge } from "@/components/ui/badge";

import { AuthForm } from "./auth-form";

type AuthPageProps = {
  mode: "login" | "register";
};

export function AuthPage({ mode }: AuthPageProps) {
  const isRegister = mode === "register";

  return (
    <GuestRoute>
      <main className="min-h-screen w-full bg-white text-black">
        <div className="flex min-h-screen flex-col items-center justify-center px-4 py-12">
          <div className="w-full max-w-md space-y-12">
            <div className="flex flex-col items-center space-y-6 text-center">
              <Link
                href="/"
                className="group inline-flex items-center gap-2 text-sm font-medium text-black transition-colors hover:text-gray-500"
              >
                <Badge className="rounded-full border border-black bg-transparent px-3 py-1 text-black transition-colors hover:bg-black hover:text-white">
                  CareerPilot
                </Badge>
                <span className="transition-transform group-hover:-translate-y-0.5">
                  返回首页
                </span>
              </Link>

              <div className="space-y-4">
                <h1 className="text-5xl font-bold tracking-tight text-black sm:text-6xl">
                  {isRegister
                    ? "创建你的求职工作台"
                    : "登录继续你的求职计划"}
                </h1>
                <p className="text-lg text-gray-600">
                  {isRegister
                    ? "注册后会直接调用后端注册接口，完成账号创建并自动进入已登录状态。"
                    : "登录后会自动校验当前用户信息，并在本地恢复登录态。"}
                </p>
              </div>
            </div>

            <AuthForm mode={mode} />

            <div className="border-t border-gray-200 pt-8 text-center">
              <p className="text-sm text-gray-600">
                {isRegister ? "已经有账号？" : "还没有账号？"}
                <Link
                  href={isRegister ? "/login" : "/register"}
                  className="font-medium text-black transition-colors hover:text-gray-500"
                >
                  {isRegister ? "去登录" : "去注册"}
                </Link>
              </p>
            </div>
          </div>
        </div>
      </main>
    </GuestRoute>
  );
}
