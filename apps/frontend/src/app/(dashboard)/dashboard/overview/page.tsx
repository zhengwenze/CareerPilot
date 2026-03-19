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
      title: "简历优化",
      description: "基于岗位快照生成可编辑的改写草案，并把确认后的建议应用到结构化简历。",
      href: "/dashboard/optimizer",
      icon: WandSparkles,
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
    <div className="space-y-6">
      <div className="max-w-3xl">
        <h1 className="text-3xl font-semibold tracking-[-0.05em] text-black sm:text-4xl">
          求职工作台
        </h1>
        <p className="mt-3 text-sm leading-7 text-black/68">
          只保留可直接进入的功能模块，不再展示统计、导览和额外焦点卡。
        </p>
      </div>

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
