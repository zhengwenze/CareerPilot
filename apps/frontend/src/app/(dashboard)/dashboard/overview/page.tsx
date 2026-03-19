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
      accent: "bg-[#2850d9] text-white",
    },
    {
      title: "岗位匹配",
      description:
        "维护 JD、生成匹配报告，并把岗位要求和简历能力放在同一张面板里。",
      href: "/dashboard/jobs",
      icon: Target,
      accent: "bg-[#ef3b9a] text-white",
    },
    {
      title: "简历优化",
      description:
        "基于岗位快照生成可编辑的改写草案，并把确认后的建议应用到结构化简历。",
      href: "/dashboard/optimizer",
      icon: WandSparkles,
      accent: "bg-[#11c27f] text-white",
    },
    {
      title: "个人信息",
      description:
        "维护求职方向、目标城市和岗位偏好，为后续建议提供更准确的上下文。",
      href: "/dashboard/profile",
      icon: Settings,
      accent: "bg-[#ff7a12] text-white",
    },
    {
      title: "投递追踪",
      description:
        "准备承接投递状态、跟进记录和时间线，入口已经统一到顶部导航。",
      href: "/dashboard/applications",
      icon: BriefcaseBusiness,
      accent: "bg-[#ffffff] text-black",
    },
    {
      title: "模拟面试",
      description:
        "后续会接入练习题、AI 反馈和复盘记录，保持与其他模块同一视觉语言。",
      href: "/dashboard/interviews",
      icon: Sparkles,
      accent: "bg-[#ffffff] text-black",
    },
  ];

  return (
    <div
      className="
        min-h-screen px-4 py-6 sm:px-6 lg:px-10
        bg-[#ebe8df]
        bg-[linear-gradient(to_right,rgba(120,120,120,0.10)_1px,transparent_1px),linear-gradient(to_bottom,rgba(120,120,120,0.10)_1px,transparent_1px)]
        bg-[length:56px_56px]
      "
    >
      <div
        className="
          mx-auto max-w-7xl border-2 border-black bg-[#f3f0e7]
          shadow-[8px_8px_0_0_#000]
        "
      >
        <div className="border-b-2 border-black px-6 py-6 sm:px-8 sm:py-8">
          <div className="max-w-3xl">
            <div className="inline-block border-2 border-black bg-[#2850d9] px-4 py-2 shadow-[4px_4px_0_0_#000]">
              <span className="text-2xl font-semibold tracking-[-0.05em] text-white sm:text-3xl">
                求职工作台
              </span>
            </div>

            <p className="mt-6 max-w-2xl text-base leading-8 text-black/70">
              管理简历、岗位匹配、优化建议与投递过程。整体界面采用浅米色方格纸风格，
              让各功能模块像贴在工作台上的信息卡片一样清晰可见。
            </p>
          </div>
        </div>

        <section className="px-6 py-6 sm:px-8 sm:py-8">
          <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-3">
            {sections.map((section) => {
              const Icon = section.icon;

              return (
                <Link
                  key={section.href}
                  href={section.href}
                  className="
                    group border-2 border-black bg-[#f7f4ec] p-6
                    shadow-[6px_6px_0_0_#000]
                    transition-transform duration-150
                    hover:-translate-x-[2px] hover:-translate-y-[2px]
                    hover:shadow-[8px_8px_0_0_#000]
                  "
                >
                  <div
                    className={`
                      inline-flex items-center gap-3 border-2 border-black px-3 py-2 shadow-[3px_3px_0_0_#000]
                      ${section.accent}
                    `}
                  >
                    <Icon className="size-4" />
                    <span className="text-sm font-semibold tracking-[-0.02em]">
                      模块
                    </span>
                  </div>

                  <h2 className="mt-7 text-2xl font-semibold tracking-[-0.05em] text-black">
                    {section.title}
                  </h2>

                  <p className="mt-3 text-sm leading-7 text-black/70">
                    {section.description}
                  </p>

                  <div
                    className="
                      mt-8 inline-flex items-center gap-2 border-2 border-black
                      bg-white px-4 py-2 text-sm font-medium text-black
                      shadow-[3px_3px_0_0_#000]
                      transition-transform group-hover:translate-x-[1px]
                    "
                  >
                    进入模块
                    <ArrowRight className="size-4" />
                  </div>
                </Link>
              );
            })}
          </div>
        </section>
      </div>
    </div>
  );
}
