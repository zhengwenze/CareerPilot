import Link from "next/link";

import { GuestRoute } from "@/components/guards/guest-route";

import { AuthForm } from "./auth-form";

type AuthPageProps = {
  mode: "login" | "register";
};

export function AuthPage({ mode }: AuthPageProps) {
  const isRegister = mode === "register";
  const title = isRegister ? "创建账号，开始管理求职流程。" : "登录后继续处理你的求职工作流。";
  const description = isRegister
    ? "账号创建完成后，你可以在同一个工作台中处理简历解析、岗位匹配、简历优化和模拟面试。"
    : "登录后继续查看简历、岗位报告和训练记录，避免在不同页面之间反复切换。";

  return (
    <GuestRoute>
      <main className="min-h-screen w-full bg-white font-mono text-black">
        <header className="border-b-2 border-black bg-white">
          <div className="mx-auto flex w-full max-w-6xl flex-col gap-3 px-4 py-4 sm:px-6 lg:flex-row lg:items-start lg:justify-between">
            <Link
              href="/"
              className="font-serif text-3xl font-bold text-black no-underline hover:text-[#0000ff]"
            >
              CareerPilot
            </Link>

            <nav className="bw-link-row">
              <a
                href="#product"
                className="text-[#0000ff]"
              >
                产品
              </a>
              <a
                href="#workflow"
                className="text-[#0000ff]"
              >
                能力
              </a>
              <a
                href="#auth-form"
                className="text-[#0000ff]"
              >
                {isRegister ? "创建账号" : "立即登录"}
              </a>
              <Link href={isRegister ? "/login" : "/register"}>
                {isRegister ? "登录" : "注册"}
              </Link>
            </nav>
          </div>
        </header>

        <div className="mx-auto grid w-full max-w-6xl gap-0 px-4 py-6 sm:px-6 lg:grid-cols-[minmax(0,1.1fr)_minmax(320px,420px)]">
          <section id="product" className="border-2 border-black border-b-0 p-6 lg:border-r-0 lg:border-b-2">
            <div className="bw-kicker">CareerPilot Access</div>
            <h1 className="mt-6 font-serif text-4xl font-bold text-black sm:text-5xl">
              {title}
            </h1>
            <p className="mt-4 max-w-2xl text-sm leading-7 text-black">
              {description}
            </p>
            <div id="workflow" className="mt-8 border-t-2 border-black pt-6">
              <p className="bw-panel-kicker">What You Can Manage</p>
              <ul className="bw-rule-list text-sm leading-7">
                <li>上传 PDF 简历并查看解析状态。</li>
                <li>维护岗位 JD 并生成匹配报告。</li>
                <li>根据岗位快照生成优化草案并回写到简历。</li>
                <li>进入模拟面试并保存训练与复盘记录。</li>
              </ul>
            </div>
          </section>

          <section id="auth-form" className="border-2 border-black p-6">
            <AuthForm mode={mode} />
          </section>
        </div>
      </main>
    </GuestRoute>
  );
}
