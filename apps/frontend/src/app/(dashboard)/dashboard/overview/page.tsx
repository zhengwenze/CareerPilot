"use client";

import Link from "next/link";
import { FileText, Sparkles, Target, WandSparkles } from "lucide-react";

import { BrutalCard, BrutalSection, BrutalTag } from "@/components/ui/brutal";

const modules = [
  {
    title: "简历解析",
    description:
      "上传 PDF 简历，AI 自动抽取结构化信息，支持在线修正，一键同步到后续所有模块。",
    href: "/dashboard/resume",
    icon: FileText,
    color: "bg-[#ff006e]",
    textColor: "text-white",
  },
  {
    title: "岗位匹配",
    description:
      "维护 JD 文本或结构化要求，生成匹配报告，找出简历与岗位之间的能力差距。",
    href: "/dashboard/jobs",
    icon: Target,
    color: "bg-[#00d9ff]",
    textColor: "text-black",
  },
  {
    title: "简历优化",
    description:
      "基于目标岗位快照生成改写草案，人工确认后应用到结构化简历版本中。",
    href: "/dashboard/optimizer",
    icon: WandSparkles,
    color: "bg-[#ccff00]",
    textColor: "text-black",
  },
  {
    title: "模拟面试",
    description:
      "进入岗位相关的真实问答训练，获取 AI 追问、复盘结论与后续改进任务清单。",
    href: "/dashboard/interviews",
    icon: Sparkles,
    color: "bg-white",
    textColor: "text-black",
  },
];

export default function DashboardOverviewPage() {
  return (
    <div className="min-h-screen bg-white">
      <BrutalSection className="py-20 bg-white">
        <div className="max-w-6xl mx-auto px-4">
          <div className="grid md:grid-cols-2 gap-8">
            {modules.map((mod, i) => {
              const Icon = mod.icon;
              return (
                <Link
                  key={i}
                  href={mod.href}
                  className="block group no-underline"
                >
                  <BrutalCard
                    className={`p-8 transition-all group-hover:-translate-y-1 group-hover:shadow-[12px_12px_0px_0px_rgba(0,0,0,1)] ${mod.color} ${mod.textColor} no-underline`}
                  >
                    <div className="flex items-start gap-6">
                      <div
                        className={`shrink-0 w-16 h-16 border-4 border-black flex items-center justify-center ${mod.color}`}
                      >
                        <span className={mod.textColor}>
                          <Icon className="w-8 h-8" />
                        </span>
                      </div>
                      <div className="flex-1">
                        <h3 className="text-2xl font-black mb-2">
                          {mod.title}
                        </h3>
                        <p className="text-sm leading-relaxed opacity-80">
                          {mod.description}
                        </p>
                        <div className="mt-4 inline-flex items-center gap-2 font-black text-xs uppercase">
                          <span>进入模块</span>
                          <span>→</span>
                        </div>
                      </div>
                    </div>
                  </BrutalCard>
                </Link>
              );
            })}
          </div>
        </div>
      </BrutalSection>

      {/* <footer className="py-8 bg-black text-white border-t-4 border-[#ff006e]">
        <div className="max-w-6xl mx-auto px-4 text-center">
          <p className="font-mono text-sm">
            CareerPilot — 让每一次求职都有迹可循
          </p>
        </div>
      </footer> */}

      <BrutalSection className="py-12 bg-black text-white border-y-4 border-black">
        <div className="max-w-6xl mx-auto px-4">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-8 text-center">
            {[
              { value: "PDF", label: "简历解析" },
              { value: "JD", label: "岗位匹配" },
              { value: "Draft", label: "优化草案" },
              { value: "Q&A", label: "模拟面试" },
            ].map((stat, i) => (
              <div key={i}>
                <div className="text-4xl md:text-5xl font-black text-[#ccff00]">
                  {stat.value}
                </div>
                <div className="text-sm mt-1">{stat.label}</div>
              </div>
            ))}
          </div>
        </div>
      </BrutalSection>
    </div>
  );
}
