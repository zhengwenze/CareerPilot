"use client";

import {
  ArrowRight,
  BriefcaseBusiness,
  FileText,
  Settings,
  Sparkles,
  Target,
  WandSparkles,
} from "lucide-react";
import Link from "next/link";

function PaperSection({
  title,
  eyebrow,
  children,
}: {
  title: string;
  eyebrow?: string;
  children: React.ReactNode;
}) {
  return (
    <section className="border-b border-[#1C1C1C]/10 bg-[#F9F8F6]">
      <div className="border-b border-[#1C1C1C]/10 px-5 py-4 sm:px-6">
        {eyebrow ? (
          <div className="mb-3 flex items-center gap-3">
            <span className="size-2.5 bg-[#1C1C1C]" />
            <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[#1C1C1C]/60">
              {eyebrow}
            </p>
          </div>
        ) : null}
        <h2 className="text-xl font-semibold tracking-tight text-[#1C1C1C]">
          {title}
        </h2>
      </div>
      <div className="px-5 py-5 sm:px-6">{children}</div>
    </section>
  );
}

function ModuleCard({
  title,
  description,
  href,
  icon: Icon,
}: {
  title: string;
  description: string;
  href: string;
  icon: React.ComponentType<{ className?: string }>;
}) {
  return (
    <Link
      href={href}
      className="group border border-[#1C1C1C]/10 bg-white p-5 transition-colors hover:border-[#1C1C1C]/20 hover:bg-[#1C1C1C]/[0.02]"
    >
      <div className="mb-4 inline-flex items-center gap-3 text-[#1C1C1C]/60">
        <Icon className="size-4" />
        <span className="text-xs font-semibold uppercase tracking-[0.16em]">模块</span>
      </div>

      <h2 className="text-xl font-semibold tracking-tight text-[#1C1C1C]">
        {title}
      </h2>

      <p className="mt-2 text-sm leading-relaxed text-[#1C1C1C]/60">{description}</p>

      <div className="mt-5 text-sm font-medium text-[#1C1C1C] group-hover:text-[#1C1C1C]/70">
        <span className="relative pb-1 after:absolute after:w-full after:h-px after:bottom-0 after:left-0 after:bg-current after:origin-bottom-right after:scale-x-0 group-hover:after:origin-bottom-left group-hover:after:scale-x-100 after:transition-transform after:duration-500">
          进入模块
        </span>
        <ArrowRight className="ml-2 inline-block size-4" />
      </div>
    </Link>
  );
}

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
      description:
        "维护 JD、生成匹配报告，并把岗位要求和简历能力放在同一张面板里。",
      href: "/dashboard/jobs",
      icon: Target,
    },
    {
      title: "简历优化",
      description:
        "基于岗位快照生成可编辑的改写草案，并把确认后的建议应用到结构化简历。",
      href: "/dashboard/optimizer",
      icon: WandSparkles,
    },
    {
      title: "个人信息",
      description:
        "维护求职方向、目标城市和岗位偏好，为后续建议提供更准确的上下文。",
      href: "/dashboard/profile",
      icon: Settings,
    },
    {
      title: "投递追踪",
      description:
        "准备承接投递状态、跟进记录和时间线，入口已经统一到顶部导航。",
      href: "/dashboard/applications",
      icon: BriefcaseBusiness,
    },
    {
      title: "模拟面试",
      description:
        "后续会接入练习题、AI 反馈和复盘记录，保持与其他模块同一视觉语言。",
      href: "/dashboard/interviews",
      icon: Sparkles,
    },
  ];

  return (
    <div className="space-y-6">
      <header className="border-b border-[#1C1C1C]/10 bg-[#F9F8F6]">
        <div className="flex flex-col gap-6 px-6 py-6 sm:px-8 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <div className="inline-flex items-center border border-[#1C1C1C]/10 bg-white px-5 py-3">
              <span className="mr-4 text-2xl leading-none text-[#1C1C1C]">
                *
              </span>
              <span className="text-[1.55rem] font-semibold uppercase tracking-tight text-[#1C1C1C] sm:text-[1.8rem]">
                Dashboard
              </span>
            </div>

            <div className="mt-6">
              <h1 className="text-3xl font-semibold tracking-tight text-[#1C1C1C] sm:text-4xl">
                求职工作台
              </h1>
            </div>

            <p className="mt-5 max-w-3xl text-base leading-relaxed text-[#1C1C1C]/60 sm:text-[1.05rem]">
              管理简历、岗位匹配、优化建议与投递过程，统一的工作台界面让各功能模块清晰可见。
            </p>
          </div>
        </div>
      </header>

      <PaperSection title="功能模块" eyebrow="Feature Modules">
        <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-3">
          {sections.map((section) => (
            <ModuleCard key={section.href} {...section} />
          ))}
        </div>
      </PaperSection>
    </div>
  );
}