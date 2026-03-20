import Link from "next/link";

import { GuestRoute } from "@/components/guards/guest-route";

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
      <main className="min-h-screen w-full bg-white text-black font-mono">
        <header className="border-b-2 border-black bg-white">
          <div className="mx-auto flex w-full max-w-7xl items-center justify-between px-6 py-4 lg:px-10">
            <Link
              href="/"
              className="font-serif text-xl font-bold tracking-[-0.03em] text-black transition-none hover:text-gray-600"
            >
              CareerPilot
            </Link>

            <nav className="hidden items-center gap-0 text-sm font-bold uppercase md:flex">
              <a
                href="#product"
                className="border-2 border-black border-r-0 px-4 py-2 text-black hover:bg-gray-100"
              >
                产品
              </a>
              <a
                href="#workflow"
                className="border-2 border-black border-r-0 px-4 py-2 text-black hover:bg-gray-100"
              >
                能力
              </a>
              <a
                href="#auth-form"
                className="border-2 border-black px-4 py-2 text-black hover:bg-gray-100"
              >
                {isRegister ? "创建账号" : "立即登录"}
              </a>
            </nav>

            <Link
              href={isRegister ? "/login" : "/register"}
              className="text-sm font-bold uppercase text-black hover:text-gray-600"
            >
              {isRegister ? "登录" : "注册"}
            </Link>
          </div>
        </header>

        <div className="mx-auto flex w-full max-w-7xl flex-col px-6 pb-20 pt-10 lg:px-10 lg:pb-24 lg:pt-16">
          <section className="mx-auto flex max-w-4xl flex-col items-center text-center">
            <div className="border-2 border-black px-4 py-2 font-mono text-xs font-bold uppercase tracking-widest text-black">
              CareerPilot Auth Experience
            </div>

            <h1 className="mt-8 max-w-4xl font-serif text-5xl font-bold tracking-[-0.06em] text-black sm:text-6xl lg:text-7xl">
              {title}
            </h1>

            <p className="mt-6 max-w-2xl text-base leading-7 text-black sm:text-lg">
              {description}
            </p>

            <div className="mt-10 flex flex-col items-center gap-4 sm:flex-row">
              <a
                href="#auth-form"
                className="inline-flex h-12 items-center border-2 border-black bg-black px-8 font-mono text-sm font-bold uppercase text-white transition-none hover:bg-gray-800"
              >
                {isRegister ? "开始创建账号" : "继续登录"}
              </a>

              <Link
                href={isRegister ? "/login" : "/register"}
                className="inline-flex h-12 items-center border-2 border-black bg-white px-8 font-mono text-sm font-bold uppercase text-black transition-none hover:bg-gray-100"
              >
                {isRegister ? "已有账号，去登录" : "没有账号，去注册"}
              </Link>
            </div>
          </section>

          <section id="auth-form" className="mt-16 flex justify-center">
            <AuthForm mode={mode} />
          </section>
        </div>
      </main>
    </GuestRoute>
  );
}
