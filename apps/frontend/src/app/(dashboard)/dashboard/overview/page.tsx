"use client";

import Link from "next/link";
import { FileText, Sparkles } from "lucide-react";

import { Button } from "@/components/ui/button";

const modules = [
  {
    title: "专属简历",
    description:
      "围绕一份主简历和目标岗位 JD，一键生成岗位定制版简历成品，并直接下载 Markdown。",
    href: "/dashboard/resume",
    icon: FileText,
  },
  {
    title: "模拟面试",
    description:
      "基于专属简历背后的岗位上下文进入真实问答训练，获取追问、复盘结论与后续改进建议。",
    href: "/dashboard/interviews",
    icon: Sparkles,
  },
]

export default function DashboardOverviewPage() {
  return (
    <div className="min-h-screen bg-white py-12">
      <div className="max-w-4xl mx-auto px-4">
        <div className="mb-8">
          <div className="bw-kicker">Dashboard</div>
          <h1 className="bw-page-title mt-2">欢迎回来</h1>
          <p className="bw-page-lead mt-3">
            选一个模块，开始你的求职之旅
          </p>
        </div>

        <div className="grid gap-6 md:grid-cols-2">
          {modules.map((mod, i) => {
            const Icon = mod.icon
            return (
              <Link
                key={i}
                href={mod.href}
                className="group block no-underline"
              >
                <div className="flex items-start gap-5 border border-[#e5e5e5] p-6 transition-colors group-hover:border-[#111111] group-hover:bg-[#fafafa]">
                  <div className="flex size-12 shrink-0 items-center justify-center border border-[#e5e5e5] bg-[#fafafa]">
                    <Icon className="size-5 text-[#666666]" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <h3 className="text-lg font-semibold text-[#111111] mb-2" style={{ fontFamily: "var(--font-heading)", letterSpacing: "-0.02em" }}>
                      {mod.title}
                    </h3>
                    <p className="text-sm leading-relaxed text-[#666666]">
                      {mod.description}
                    </p>
                    <div className="mt-4">
                      <Button variant="ghost" size="sm" className="text-xs">
                        进入模块
                        <span className="ml-1">→</span>
                      </Button>
                    </div>
                  </div>
                </div>
              </Link>
            )
          })}
        </div>
      </div>
    </div>
  )
}
