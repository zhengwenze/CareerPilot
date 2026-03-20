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

import {
  PageHeader,
  PageShell,
  PaperSection,
} from "@/components/brutalist/page-shell";

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
    title: "简历优化",
    description: "基于岗位快照生成可编辑的改写草案，并把确认后的建议应用到结构化简历。",
    href: "/dashboard/optimizer",
    icon: WandSparkles,
  },
  {
    title: "模拟面试",
    description: "基于岗位快照进入问答训练，获取 AI 反馈、复盘结论和后续改进任务。",
    href: "/dashboard/interviews",
    icon: Sparkles,
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
];

export default function DashboardOverviewPage() {
  return (
    <PageShell>
      <PageHeader
        description="管理简历、岗位匹配、优化建议与投递过程，统一的工作台界面让各功能模块清晰可见。"
        eyebrow="Dashboard"
        title="求职工作台"
      />

      <PaperSection title="功能模块" eyebrow="Modules" bodyClassName="p-0">
        <div className="grid gap-0 md:grid-cols-2 lg:grid-cols-3">
          {sections.map((section) => {
            const Icon = section.icon;
            return (
              <Link
                key={section.href}
                href={section.href}
                className="group border-b-2 border-r-0 border-black p-6 font-mono md:border-r-2"
              >
                <div className="mb-4 flex items-center gap-3 text-black">
                  <Icon className="size-4" />
                  <span className="text-xs font-bold uppercase">
                    模块
                  </span>
                </div>

                <h2 className="font-serif text-xl font-bold text-black">
                  {section.title}
                </h2>

                <p className="mt-2 text-sm leading-6 text-black">
                  {section.description}
                </p>

                <div className="mt-4 font-mono text-xs font-bold text-[#0000ff]">
                  <span className="underline">进入模块</span>
                  <ArrowRight className="ml-2 inline-block size-3" />
                </div>
              </Link>
            );
          })}
        </div>
      </PaperSection>
    </PageShell>
  );
}
