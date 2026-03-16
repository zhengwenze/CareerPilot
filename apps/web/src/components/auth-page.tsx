import { ArrowRight, BriefcaseBusiness, FileText, Sparkles } from "lucide-react";
import Link from "next/link";

import { GuestRoute } from "@/components/guards/guest-route";
import { Button } from "@/components/ui/button";

import { AuthForm } from "./auth-form";

type AuthPageProps = {
  mode: "login" | "register";
};

export function AuthPage({ mode }: AuthPageProps) {
  const isRegister = mode === "register";
  const title = isRegister ? "求职，从一个清晰的起点开始。" : "继续你的下一段职业升级。";
  const description = isRegister
    ? "创建账号后即可集中管理简历、岗位追踪与投递节奏，让求职流程像产品界面一样清晰。"
    : "登录后继续查看简历解析、职位进展与求职任务，把关键信息收拢到同一个工作台。";

  return (
    <GuestRoute>
      <main className="min-h-screen w-full bg-white text-black">
        <header className="border-b border-black/8 bg-white">
          <div className="mx-auto flex w-full max-w-7xl items-center justify-between px-6 py-5 lg:px-10">
            <Link
              href="/"
              className="text-lg font-semibold tracking-[-0.03em] text-black transition-opacity hover:opacity-65"
            >
              CareerPilot
            </Link>

            <nav className="hidden items-center gap-8 text-sm font-medium text-black md:flex">
              <a href="#product" className="transition-opacity hover:opacity-65">
                产品
              </a>
              <a href="#workflow" className="transition-opacity hover:opacity-65">
                能力
              </a>
              <a href="#auth-form" className="transition-opacity hover:opacity-65">
                {isRegister ? "创建账号" : "立即登录"}
              </a>
            </nav>

            <Link
              href={isRegister ? "/login" : "/register"}
              className="text-sm font-medium text-black transition-opacity hover:opacity-65"
            >
              {isRegister ? "登录" : "注册"}
            </Link>
          </div>
        </header>

        <div className="mx-auto flex w-full max-w-7xl flex-col px-6 pb-20 pt-10 lg:px-10 lg:pb-24 lg:pt-16">
          <section className="mx-auto flex max-w-4xl flex-col items-center text-center">
            <div className="inline-flex items-center rounded-full border border-black/10 px-4 py-2 text-xs font-medium tracking-[0.18em] text-black uppercase">
              CareerPilot Auth Experience
            </div>

            <h1 className="mt-8 max-w-4xl text-5xl font-semibold tracking-[-0.06em] text-black sm:text-6xl lg:text-7xl">
              {title}
            </h1>

            <p className="mt-6 max-w-2xl text-base leading-7 text-black sm:text-lg">
              {description}
            </p>

            <div className="mt-10 flex flex-col items-center gap-4 sm:flex-row">
              <Button
                asChild
                className="h-12 rounded-full bg-[#0071E3] px-8 text-sm font-medium text-white shadow-none hover:bg-[#0077ED] focus-visible:ring-[#0071E3]/30"
              >
                <a href="#auth-form">
                  {isRegister ? "开始创建账号" : "继续登录"}
                </a>
              </Button>

              <Button
                asChild
                variant="outline"
                className="h-12 rounded-full border-[#0071E3] bg-white px-8 text-sm font-medium text-[#0071E3] hover:bg-[#F5F9FF] hover:text-[#0071E3]"
              >
                <Link href={isRegister ? "/login" : "/register"}>
                  {isRegister ? "已有账号，去登录" : "没有账号，去注册"}
                </Link>
              </Button>
            </div>
          </section>

          <section id="product" className="mt-16 sm:mt-20">
            <div className="mx-auto w-full max-w-6xl rounded-[2rem] border border-black/10 bg-white p-3 shadow-[0_24px_80px_rgba(0,0,0,0.08)] sm:p-4">
              <div className="overflow-hidden rounded-[1.75rem] border border-black/10 bg-[#f5f5f7] p-4 sm:p-6">
                <div className="rounded-[1.5rem] border border-black/10 bg-white p-4 shadow-[0_18px_40px_rgba(0,0,0,0.05)] sm:p-6">
                  <div className="flex items-center justify-between border-b border-black/8 pb-4">
                    <div className="flex items-center gap-2">
                      <span className="size-2.5 rounded-full bg-black/15" />
                      <span className="size-2.5 rounded-full bg-black/15" />
                      <span className="size-2.5 rounded-full bg-black/15" />
                    </div>
                    <span className="text-xs font-medium tracking-[0.18em] text-black uppercase">
                      CareerPilot Workspace
                    </span>
                  </div>

                  <div className="mt-6 grid gap-4 lg:grid-cols-[220px_minmax(0,1fr)]">
                    <div className="rounded-[1.5rem] border border-black/8 bg-[#f5f5f7] p-4">
                      <div className="space-y-3">
                        <div className="h-10 rounded-2xl bg-white" />
                        <div className="h-10 rounded-2xl bg-white" />
                        <div className="h-10 rounded-2xl bg-white" />
                      </div>

                      <div className="mt-8 rounded-[1.5rem] border border-black/8 bg-white p-4">
                        <p className="text-sm font-medium text-black">简历状态</p>
                        <p className="mt-3 text-3xl font-semibold tracking-[-0.05em] text-black">
                          12
                        </p>
                        <p className="mt-2 text-sm leading-6 text-black">
                          已解析、可追踪、可持续优化。
                        </p>
                      </div>
                    </div>

                    <div className="grid gap-4">
                      <div className="grid gap-4 sm:grid-cols-3">
                        <div className="rounded-[1.5rem] border border-black/8 bg-white p-5">
                          <div className="flex items-center gap-3">
                            <FileText className="size-5 text-black" />
                            <span className="text-sm font-medium text-black">
                              简历解析
                            </span>
                          </div>
                          <p className="mt-6 text-2xl font-semibold tracking-[-0.05em] text-black">
                            Pending
                          </p>
                        </div>

                        <div className="rounded-[1.5rem] border border-black/8 bg-white p-5">
                          <div className="flex items-center gap-3">
                            <BriefcaseBusiness className="size-5 text-black" />
                            <span className="text-sm font-medium text-black">
                              岗位追踪
                            </span>
                          </div>
                          <p className="mt-6 text-2xl font-semibold tracking-[-0.05em] text-black">
                            Active
                          </p>
                        </div>

                        <div className="rounded-[1.5rem] border border-black/8 bg-white p-5">
                          <div className="flex items-center gap-3">
                            <Sparkles className="size-5 text-black" />
                            <span className="text-sm font-medium text-black">
                              AI 建议
                            </span>
                          </div>
                          <p className="mt-6 text-2xl font-semibold tracking-[-0.05em] text-black">
                            Ready
                          </p>
                        </div>
                      </div>

                      <div className="rounded-[1.75rem] border border-black/8 bg-[#f5f5f7] p-5 sm:p-6">
                        <div className="grid gap-4 sm:grid-cols-[minmax(0,1.15fr)_minmax(0,0.85fr)]">
                          <div className="rounded-[1.5rem] border border-black/8 bg-white p-5">
                            <div className="flex items-end justify-between">
                              <div>
                                <p className="text-sm font-medium text-black">
                                  求职节奏
                                </p>
                                <p className="mt-3 text-3xl font-semibold tracking-[-0.05em] text-black">
                                  87%
                                </p>
                              </div>
                              <div className="flex h-24 items-end gap-2">
                                <span className="w-5 rounded-full bg-black/10" style={{ height: "42%" }} />
                                <span className="w-5 rounded-full bg-black/20" style={{ height: "68%" }} />
                                <span className="w-5 rounded-full bg-[#0071E3]" style={{ height: "92%" }} />
                                <span className="w-5 rounded-full bg-black/15" style={{ height: "56%" }} />
                              </div>
                            </div>
                          </div>

                          <div className="rounded-[1.5rem] border border-black/8 bg-white p-5">
                            <p className="text-sm font-medium text-black">
                              投递建议
                            </p>
                            <div className="mt-4 space-y-3">
                              <div className="rounded-2xl bg-[#f5f5f7] px-4 py-3 text-sm text-black">
                                优先完善最近一份经历描述
                              </div>
                              <div className="rounded-2xl bg-[#f5f5f7] px-4 py-3 text-sm text-black">
                                本周新增 3 个目标岗位更合适
                              </div>
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </section>

          <section
            id="workflow"
            className="mt-16 grid gap-8 lg:mt-20 lg:grid-cols-[minmax(0,1fr)_440px] lg:items-start"
          >
            <div className="space-y-8">
              <div className="max-w-2xl">
                <p className="text-sm font-medium tracking-[0.18em] text-black uppercase">
                  Designed For Focus
                </p>
                <h2 className="mt-4 text-3xl font-semibold tracking-[-0.05em] text-black sm:text-4xl">
                  把复杂的求职流程，整理成一块安静、清楚、可执行的面板。
                </h2>
              </div>

              <div className="grid gap-4 sm:grid-cols-3">
                <div className="rounded-[2rem] border border-black/10 bg-[#f5f5f7] p-6">
                  <p className="text-lg font-semibold text-black">上传即开始</p>
                  <p className="mt-3 text-sm leading-6 text-black">
                    PDF 上传、解析与结果回写在同一条链路中完成。
                  </p>
                </div>

                <div className="rounded-[2rem] border border-black/10 bg-[#f5f5f7] p-6">
                  <p className="text-lg font-semibold text-black">状态持续可见</p>
                  <p className="mt-3 text-sm leading-6 text-black">
                    从 pending 到 success，关键状态都有清晰反馈。
                  </p>
                </div>

                <div className="rounded-[2rem] border border-black/10 bg-[#f5f5f7] p-6">
                  <p className="text-lg font-semibold text-black">建议立即可用</p>
                  <p className="mt-3 text-sm leading-6 text-black">
                    登录后继续你的求职上下文，不需要重新整理信息。
                  </p>
                </div>
              </div>
            </div>

            <div id="auth-form" className="scroll-mt-24">
              <AuthForm mode={mode} />
            </div>
          </section>

          <div className="mt-10 flex items-center justify-center gap-2 text-sm text-black">
            <span>{isRegister ? "已经有账号？" : "还没有账号？"}</span>
            <Link
              href={isRegister ? "/login" : "/register"}
              className="inline-flex items-center gap-1 font-medium text-black transition-opacity hover:opacity-65"
            >
              {isRegister ? "去登录" : "去注册"}
              <ArrowRight className="size-4" />
            </Link>
          </div>
        </div>
      </main>
    </GuestRoute>
  );
}
