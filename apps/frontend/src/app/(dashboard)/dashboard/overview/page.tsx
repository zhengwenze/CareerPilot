"use client";

import Link from "next/link";
import { FileText, Sparkles } from "lucide-react";

import { BrutalCard, BrutalSection } from "@/components/ui/brutal";

const modules = [
  {
    title: "专属简历",
    description:
      "围绕一份主简历和目标岗位 JD，一键生成岗位定制版简历成品，并直接下载 Markdown。",
    href: "/dashboard/resume",
    icon: FileText,
    color: "bg-[#ff006e]",
    textColor: "text-white",
  },
  {
    title: "模拟面试",
    description:
      "基于专属简历背后的岗位上下文进入真实问答训练，获取追问、复盘结论与后续改进建议。",
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
    </div>
  );
}
