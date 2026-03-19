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
    <section className="border-2 border-black bg-[#f4f1e8] shadow-[8px_8px_0_0_#000]">
      <div className="border-b-2 border-black px-5 py-4 sm:px-6">
        {eyebrow ? (
          <div className="mb-3 flex items-center gap-3">
            <span className="size-2.5 bg-[#2f55d4]" />
            <p className="text-[11px] font-bold uppercase tracking-[0.18em] text-black/45">
              {eyebrow}
            </p>
          </div>
        ) : null}
        <h2 className="text-xl font-semibold tracking-[-0.05em] text-black">
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
  accent,
}: {
  title: string;
  description: string;
  href: string;
  icon: React.ComponentType<{ className?: string }>;
  accent: string;
}) {
  return (
    <Link
      href={href}
      className="group border-2 border-black bg-[#f9f7f0] p-5 shadow-[5px_5px_0_0_#000] transition-transform hover:-translate-x-[2px] hover:-translate-y-[2px] hover:shadow-[8px_8px_0_0_#000]"
    >
      <div
        className={`
          inline-flex items-center gap-3 border-2 border-black px-3 py-2 shadow-[3px_3px_0_0_#000]
          ${accent}
        `}
      >
        <Icon className="size-4" />
        <span className="text-sm font-semibold tracking-[-0.02em]">模块</span>
      </div>

      <h2 className="mt-5 text-xl font-semibold tracking-[-0.05em] text-black">
        {title}
      </h2>

      <p className="mt-2 text-sm leading-6 text-black/70">{description}</p>

      <div
        className="
          mt-5 inline-flex items-center gap-2 border-2 border-black
          bg-white px-4 py-2 text-sm font-semibold text-black
          shadow-[3px_3px_0_0_#000]
        "
      >
        进入模块
        <ArrowRight className="size-4" />
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
      accent: "bg-[#2f55d4] text-white",
    },
    {
      title: "岗位匹配",
      description:
        "维护 JD、生成匹配报告，并把岗位要求和简历能力放在同一张面板里。",
      href: "/dashboard/jobs",
      icon: Target,
      accent: "bg-[#f13798] text-white",
    },
    {
      title: "简历优化",
      description:
        "基于岗位快照生成可编辑的改写草案，并把确认后的建议应用到结构化简历。",
      href: "/dashboard/optimizer",
      icon: WandSparkles,
      accent: "bg-[#10bf7a] text-white",
    },
    {
      title: "个人信息",
      description:
        "维护求职方向、目标城市和岗位偏好，为后续建议提供更准确的上下文。",
      href: "/dashboard/profile",
      icon: Settings,
      accent: "bg-[#ff7a10] text-white",
    },
    {
      title: "投递追踪",
      description:
        "准备承接投递状态、跟进记录和时间线，入口已经统一到顶部导航。",
      href: "/dashboard/applications",
      icon: BriefcaseBusiness,
      accent: "bg-[#000000] text-white",
    },
    {
      title: "模拟面试",
      description:
        "后续会接入练习题、AI 反馈和复盘记录，保持与其他模块同一视觉语言。",
      href: "/dashboard/interviews",
      icon: Sparkles,
      accent: "bg-[#000000] text-white",
    },
  ];

  return (
    <div className="space-y-6">
      <header className="border-2 border-black bg-[#f4f1e8] shadow-[8px_8px_0_0_#000]">
        <div className="flex flex-col gap-6 px-6 py-6 sm:px-8 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <div className="inline-flex items-center border-2 border-black bg-[#f9f7f0] px-5 py-3 shadow-[4px_4px_0_0_#000]">
              <span className="mr-4 text-2xl leading-none text-[#2f55d4]">
                *
              </span>
              <span className="text-[1.55rem] font-black uppercase tracking-[-0.06em] text-black sm:text-[1.8rem]">
                Dashboard
              </span>
            </div>

            <div className="mt-6 inline-block border-2 border-black bg-[#2f55d4] px-4 py-2 shadow-[5px_5px_0_0_#000]">
              <h1 className="text-3xl font-semibold tracking-[-0.08em] text-white sm:text-4xl">
                求职工作台
              </h1>
            </div>

            <p className="mt-5 max-w-3xl text-base leading-8 text-[#38445a] sm:text-[1.05rem]">
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
