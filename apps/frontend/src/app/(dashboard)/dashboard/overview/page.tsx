"use client";

import Link from "next/link";
import {
  ArrowRight,
  ArrowUpRight,
  FileText,
  Sparkles,
  Target,
} from "lucide-react";

import {
  MetaChip,
  PageHeader,
  PageShell,
  PaperSection,
} from "@/components/brutalist/page-shell";
import { Button } from "@/components/ui/button";

const workflowSteps = [
  {
    step: "01",
    title: "主简历工作台",
    description:
      "上传、转换并整理你的母版简历，形成后续所有求职动作的统一基础。",
    href: "/dashboard/resume",
    cta: "进入简历工作台",
  },
  {
    step: "02",
    title: "目标岗位上下文",
    description:
      "把岗位 JD 固定下来，让简历定制和面试训练都围绕同一目标展开。",
    href: "/dashboard/resume",
    cta: "填写岗位描述",
  },
  {
    step: "03",
    title: "定制简历产出",
    description:
      "基于主简历与目标岗位生成更贴近投递场景的 Markdown 简历成品。",
    href: "/dashboard/resume",
    cta: "生成定制简历",
  },
  {
    step: "04",
    title: "模拟面试训练",
    description:
      "沿用同一份岗位与简历上下文进入问答、追问与复盘，避免重复输入。",
    href: "/dashboard/interviews",
    cta: "进入模拟面试",
  },
];

const modules = [
  {
    title: "专属简历",
    description:
      "适合先完成信息整理、岗位对齐和定制产出，作为整个工作流的起点。",
    href: "/dashboard/resume",
    icon: FileText,
    input: "主简历 + 目标岗位",
    output: "可下载的定制 Markdown 简历",
  },
  {
    title: "模拟面试",
    description:
      "适合在已有岗位上下文后继续推进，用同一份材料完成问答训练和复盘。",
    href: "/dashboard/interviews",
    icon: Sparkles,
    input: "定制简历上下文 + 目标岗位",
    output: "追问、薄弱点与改写建议",
  },
];

const workspacePrinciples = [
  "先把主简历和岗位上下文收拢到同一处，再做后续生成与训练。",
  "每个模块只解决当前阶段问题，但共享同一份求职上下文。",
  "默认先做简历，再进入面试；如果已有材料，也能直接跳到训练。",
];

const workspaceSignals = [
  "单一工作区",
  "单色工作流导航",
  "Resume → Interview 连续推进",
];

export default function DashboardOverviewPage() {
  return (
    <PageShell className="gap-8 py-6 md:py-10">
      <PageHeader
        eyebrow="Workspace Overview"
        title="从一份主简历，推进到一场更像真的面试。"
        description="Career Pilot 不是分散的工具集合，而是一条连续工作流。先整理主简历与岗位，再生成定制版本，最后把同一份上下文直接带进模拟面试。"
        meta={
          <>
            <MetaChip>主流程入口</MetaChip>
            <MetaChip>单色工作台</MetaChip>
            <MetaChip>同一上下文复用</MetaChip>
          </>
        }
      />

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1.9fr)_minmax(320px,1fr)]">
        <section className="border border-[#e5e5e5] bg-white p-6 md:p-8">
          <div className="flex flex-col gap-6">
            <div>
              <p className="text-xs uppercase tracking-[0.18em] text-[#888888]">
                Recommended Next Step
              </p>
              <h2 className="mt-3 text-3xl font-semibold tracking-[-0.03em] text-[#111111] md:text-4xl">
                先完成专属简历工作台，再继续进入面试训练。
              </h2>
              <p className="mt-4 max-w-2xl text-sm leading-7 text-[#666666] md:text-base">
                这样可以确保岗位 JD、主简历内容和后续生成结果处于同一条链路里，减少重复输入，也让面试训练更贴近真实投递场景。
              </p>
            </div>

            <div className="flex flex-col gap-3 sm:flex-row">
              <Button asChild size="lg">
                <Link href="/dashboard/resume">
                  进入专属简历
                  <ArrowUpRight className="size-4" />
                </Link>
              </Button>
              <Button asChild size="lg" variant="outline">
                <Link href="/dashboard/interviews">
                  直接进入模拟面试
                  <ArrowRight className="size-4" />
                </Link>
              </Button>
            </div>

            <div className="grid gap-3 border-t border-[#e5e5e5] pt-6 md:grid-cols-3">
              {workspaceSignals.map((signal) => (
                <div key={signal} className="border border-[#e5e5e5] bg-[#fafafa] px-4 py-4">
                  <p className="text-xs uppercase tracking-[0.16em] text-[#888888]">
                    Workspace Signal
                  </p>
                  <p className="mt-2 text-sm font-medium text-[#111111]">{signal}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        <aside className="border border-[#e5e5e5] bg-[#fafafa] p-6">
          <div className="flex items-center gap-3">
            <div className="flex size-10 items-center justify-center border border-[#d4d4d4] bg-white">
              <Target className="size-4 text-[#111111]" />
            </div>
            <div>
              <p className="text-xs uppercase tracking-[0.18em] text-[#888888]">
                Workspace Logic
              </p>
              <h3 className="mt-1 text-lg font-semibold text-[#111111]">
                入口页负责定方向，不负责替代业务页。
              </h3>
            </div>
          </div>

          <div className="mt-6 space-y-4">
            {workspacePrinciples.map((principle, index) => (
              <div
                key={principle}
                className="border border-[#e5e5e5] bg-white p-4"
              >
                <p className="text-xs uppercase tracking-[0.18em] text-[#888888]">
                  0{index + 1}
                </p>
                <p className="mt-2 text-sm leading-7 text-[#111111]">
                  {principle}
                </p>
              </div>
            ))}
          </div>
        </aside>
      </div>

      <PaperSection
        title="四步工作流地图"
        eyebrow="Workflow Map"
        bodyClassName="p-0"
      >
        <div className="grid md:grid-cols-2 xl:grid-cols-4">
          {workflowSteps.map((item, index) => (
            <div
              key={item.step}
              className="flex h-full flex-col border-t border-[#e5e5e5] p-6 first:border-t-0 md:border-l md:first:border-l-0 md:first:border-t md:[&:nth-child(-n+2)]:border-t-0 xl:[&:nth-child(-n+4)]:border-t-0"
            >
              <p className="text-xs uppercase tracking-[0.18em] text-[#888888]">
                Step {item.step}
              </p>
              <h3 className="mt-3 text-xl font-semibold tracking-[-0.02em] text-[#111111]">
                {item.title}
              </h3>
              <p className="mt-3 flex-1 text-sm leading-7 text-[#666666]">
                {item.description}
              </p>
              <div className="mt-6 flex items-center justify-between border-t border-[#e5e5e5] pt-4">
                <span className="text-xs uppercase tracking-[0.16em] text-[#888888]">
                  {index === 0 ? "建议先完成" : "继续推进"}
                </span>
                <Button asChild size="sm" variant="ghost">
                  <Link href={item.href}>
                    {item.cta}
                    <ArrowRight className="size-4" />
                  </Link>
                </Button>
              </div>
            </div>
          ))}
        </div>
      </PaperSection>

      <PaperSection
        title="两个核心模块"
        eyebrow="Primary Modules"
        bodyClassName="p-0"
      >
        <div className="grid gap-px bg-[#e5e5e5] md:grid-cols-2">
          {modules.map((mod) => {
            const Icon = mod.icon;

            return (
              <div key={mod.title} className="bg-white p-6 md:p-8">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex size-12 shrink-0 items-center justify-center border border-[#e5e5e5] bg-[#fafafa]">
                    <Icon className="size-5 text-[#111111]" />
                  </div>
                  <MetaChip className="bg-white">{mod.output}</MetaChip>
                </div>

                <h3 className="mt-6 text-2xl font-semibold tracking-[-0.03em] text-[#111111]">
                  {mod.title}
                </h3>
                <p className="mt-3 text-sm leading-7 text-[#666666] md:text-base">
                  {mod.description}
                </p>

                <div className="mt-6 space-y-3 border-t border-[#e5e5e5] pt-5 text-sm">
                  <div className="flex items-start justify-between gap-4">
                    <span className="text-[#888888]">输入</span>
                    <span className="text-right text-[#111111]">{mod.input}</span>
                  </div>
                  <div className="flex items-start justify-between gap-4">
                    <span className="text-[#888888]">产出</span>
                    <span className="text-right text-[#111111]">{mod.output}</span>
                  </div>
                </div>

                <div className="mt-6">
                  <Button asChild variant="outline">
                    <Link href={mod.href}>
                      打开模块
                      <ArrowUpRight className="size-4" />
                    </Link>
                  </Button>
                </div>
              </div>
            );
          })}
        </div>
      </PaperSection>
    </PageShell>
  );
}
