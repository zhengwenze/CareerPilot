import { ArrowRight, BriefcaseBusiness, FileText, Settings, Sparkles, Target } from "lucide-react";
import Link from "next/link";

export default function DashboardOverviewPage() {
  const sections = [
    {
      title: "简历中心",
      description: "上传 PDF、查看解析状态，并直接在结构化编辑区修正结果。",
      href: "/dashboard/resume",
      icon: FileText,
    },
    {
      title: "岗位匹配",
      description: "维护 JD、生成匹配报告，并把岗位要求和简历能力放在同一张面板里。",
      href: "/dashboard/jobs",
      icon: Target,
    },
    {
      title: "个人信息",
      description: "维护求职方向、目标城市和岗位偏好，为后续建议提供更准确的上下文。",
      href: "/dashboard/profile",
      icon: Settings,
    },
    {
      title: "投递追踪",
      description: "准备承接投递状态、跟进记录和时间线，入口已经统一到顶部导航。",
      href: "/dashboard/applications",
      icon: BriefcaseBusiness,
    },
    {
      title: "模拟面试",
      description: "后续会接入练习题、AI 反馈和复盘记录，保持与其他模块同一视觉语言。",
      href: "/dashboard/interviews",
      icon: Sparkles,
    },
  ];

  return (
    <div className="space-y-10">
      <section className="grid gap-8 lg:grid-cols-[minmax(0,1fr)_360px] lg:items-end">
        <div className="max-w-4xl">
          <p className="text-sm font-medium tracking-[0.18em] text-black uppercase">
            Overview
          </p>
          <h1 className="mt-4 text-4xl font-semibold tracking-[-0.06em] text-black sm:text-5xl lg:text-6xl">
            把求职流程收成一条清楚、克制、可执行的工作流。
          </h1>
          <p className="mt-6 max-w-3xl text-base leading-8 text-black/72">
            这里不再堆叠说明卡片，而是直接给出当前已经可用的模块入口。上传简历、维护岗位、完善个人偏好，都可以从顶部导航或下面的卡片直接进入。
          </p>
        </div>

        <div className="rounded-[2rem] border border-black/10 bg-[#f5f5f7] p-6">
          <p className="text-xs font-medium tracking-[0.18em] text-black uppercase">
            Workspace Focus
          </p>
          <div className="mt-5 space-y-4">
            <div className="rounded-[1.5rem] bg-white px-5 py-4">
              <p className="text-sm font-medium text-black">上传并解析简历</p>
            </div>
            <div className="rounded-[1.5rem] bg-white px-5 py-4">
              <p className="text-sm font-medium text-black">录入目标岗位并生成匹配报告</p>
            </div>
            <div className="rounded-[1.5rem] bg-white px-5 py-4">
              <p className="text-sm font-medium text-black">维护求职方向与偏好</p>
            </div>
          </div>
        </div>
      </section>

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {sections.map((section) => {
          const Icon = section.icon;

          return (
            <Link
              key={section.href}
              href={section.href}
              className="group rounded-[2rem] border border-black/10 bg-white p-6 shadow-[0_18px_48px_rgba(0,0,0,0.05)] transition-all hover:-translate-y-0.5 hover:shadow-[0_24px_60px_rgba(0,0,0,0.08)]"
            >
              <div className="flex size-12 items-center justify-center rounded-2xl bg-[#f5f5f7] text-black">
                <Icon className="size-5" />
              </div>
              <h2 className="mt-8 text-2xl font-semibold tracking-[-0.04em] text-black">
                {section.title}
              </h2>
              <p className="mt-3 text-sm leading-7 text-black/68">
                {section.description}
              </p>
              <div className="mt-8 inline-flex items-center gap-2 text-sm font-medium text-[#0071E3]">
                进入模块
                <ArrowRight className="size-4 transition-transform group-hover:translate-x-0.5" />
              </div>
            </Link>
          );
        })}
      </section>
    </div>
  );
}
