import Link from "next/link";

import { GuestRoute } from "@/components/guards/guest-route";

import { AuthForm } from "./auth-form";

type AuthPageProps = {
  mode: "login" | "register";
};

export function AuthPage({ mode }: AuthPageProps) {
  const isRegister = mode === "register";
  const title = isRegister
    ? "创建账号，开始管理求职流程。"
    : "登录后继续处理你的求职工作流。";
  const description = isRegister
    ? "账号创建完成后，你可以在同一个工作台中处理简历解析、岗位匹配、简历优化和模拟面试。"
    : "登录后继续查看简历、岗位报告和训练记录，避免在不同页面之间反复切换。";

  return (
    <GuestRoute>
      <main className="min-h-screen w-full bg-white text-[#111111]">
        <header className="border-b border-[#e5e5e5] bg-white">
          <div className="mx-auto flex w-full max-w-6xl flex-col gap-4 px-4 py-4 sm:px-6 lg:flex-row lg:items-start lg:justify-between lg:gap-6">
            <Link
              href="/"
              className="text-2xl font-semibold text-[#111111] no-underline hover:text-[#666666]"
              style={{
                fontFamily: "var(--font-heading)",
                letterSpacing: "-0.02em",
              }}
            >
              CareerPilot
            </Link>

            <nav className="bw-link-row">
              <a href="#product">产品</a>
              <a href="#workflow">能力</a>
              <a href="#auth-form">{isRegister ? "创建账号" : "立即登录"}</a>
              <Link href={isRegister ? "/login" : "/register"}>
                {isRegister ? "登录" : "注册"}
              </Link>
            </nav>
          </div>
        </header>

        <div className="mx-auto grid w-full max-w-6xl gap-0 px-4 py-12 sm:px-6 lg:grid-cols-[1fr_400px] lg:gap-8 lg:py-16">
          <section
            id="product"
            className="border border-[#e5e5e5] p-8 lg:border-r-0 lg:py-12"
          >
            <div className="bw-kicker">CareerPilot Access</div>
            <h1
              className="mt-6 text-3xl font-semibold text-[#111111] sm:text-4xl"
              style={{
                fontFamily: "var(--font-heading)",
                letterSpacing: "-0.02em",
              }}
            >
              {title}
            </h1>
            <p className="mt-4 max-w-xl text-sm leading-7 text-[#666666]">
              {description}
            </p>
            <div id="workflow" className="mt-8 border-t border-[#e5e5e5] pt-8">
              <p className="bw-panel-kicker">What You Can Manage</p>
              <ul className="bw-rule-list mt-4 text-sm leading-7 text-[#666666]">
                <li>上传 PDF 简历并查看解析状态。</li>
                <li>维护岗位 JD 并生成匹配报告。</li>
                <li>根据岗位快照生成优化草案并回写到简历。</li>
                <li>进入模拟面试并保存训练与复盘记录。</li>
              </ul>
            </div>
          </section>

          <section
            id="auth-form"
            className="border border-[#e5e5e5] p-8 lg:py-12"
          >
            <AuthForm mode={mode} />
          </section>
        </div>
      </main>
    </GuestRoute>
  );
}
