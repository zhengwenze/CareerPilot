'use client';
import Link from 'next/link';
import { ArrowUpRight, FileText, Settings, Sparkles } from 'lucide-react';
import { MetaChip, PageHeader, PageShell, PaperSection } from '@/components/brutalist/page-shell';
import { Button } from '@/components/ui/button';

const flowSteps = [
  { label: 'Step 1', value: '主简历' },
  { label: 'Step 2', value: '岗位 JD' },
  { label: 'Step 3', value: '定制简历' },
  { label: 'Step 4', value: '模拟面试' },
];

const modules = [
  {
    title: '专属简历',
    description: '上传主简历，保存岗位，生成定制结果。',
    href: '/dashboard/resume',
    action: '进入专属简历',
    icon: FileText,
  },
  {
    title: '模拟面试',
    description: '继续当前岗位上下文，直接进入问答训练。',
    href: '/dashboard/interviews',
    action: '进入模拟面试',
    icon: Sparkles,
  },
  {
    title: '设置',
    description: '查看账户信息',
    href: '/dashboard/setting',
    action: '进入设置',
    icon: Settings,
  },
];

export default function DashboardOverviewPage() {
  return (
    <div className="h-screen overflow-hidden">
      <PageShell className="gap-8 py-4 md:py-6">
        <PageHeader
          eyebrow="Workbench"
          title="下一步先做专属简历。"
          description="先整理主简历和岗位，再继续面试。"
          meta={
            <>
              <MetaChip>Overview</MetaChip>
              <MetaChip>Monochrome</MetaChip>
              <MetaChip>Workspace</MetaChip>
            </>
          }
        >
          <div className="bw-workbench-hero">
            <div className="bw-flow-strip">
              {flowSteps.map(step => (
                <div key={step.label} className="bw-flow-step">
                  <strong>{step.label}</strong>
                  <span>{step.value}</span>
                </div>
              ))}
            </div>

            <div className="flex flex-wrap gap-2">
              <Button asChild size="lg" variant="outline">
                <Link href="/dashboard/resume">
                  专属简历
                  <ArrowUpRight className="size-4" />
                </Link>
              </Button>
              <Button asChild size="lg" variant="outline">
                <Link href="/dashboard/interviews">
                  模拟面试
                  <ArrowUpRight className="size-4" />
                </Link>
              </Button>
            </div>
          </div>
        </PageHeader>

        <PaperSection eyebrow="Modules" title="工作台入口" bodyClassName="p-0">
          <div className="grid gap-px bg-[#e5e5e5] md:grid-cols-3">
            {modules.map(module => {
              const Icon = module.icon;

              return (
                <div key={module.title} className="bw-module-card">
                  <div className="flex size-10 items-center justify-center border border-[#e5e5e5] bg-[#fafafa]">
                    <Icon className="size-4 text-[#111111]" />
                  </div>
                  <div>
                    <h2 className="text-xl font-semibold text-[#111111]">{module.title}</h2>
                    <p className="mt-2 text-sm leading-6 text-[#666666]">{module.description}</p>
                  </div>
                  <div className="mt-auto">
                    <Button asChild variant="outline">
                      <Link href={module.href}>
                        {module.action}
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
    </div>
  );
}
