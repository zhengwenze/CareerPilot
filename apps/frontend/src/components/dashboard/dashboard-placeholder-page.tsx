import { ArrowUpRight } from "lucide-react";
import Link from "next/link";

import { Button } from "@/components/ui/button";

type DashboardPlaceholderPageProps = {
  eyebrow: string;
  title: string;
  description: string;
  routeLabel: string;
  highlights: string[];
};

export function DashboardPlaceholderPage({
  eyebrow,
  title,
  description,
  routeLabel,
  highlights,
}: DashboardPlaceholderPageProps) {
  return (
    <div className="space-y-6">
      <header className="border-b border-[#1C1C1C]/10 bg-[#F9F8F6]">
        <div className="flex flex-col gap-6 px-6 py-6 sm:px-8 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <div className="inline-flex items-center border border-[#1C1C1C]/10 bg-white px-5 py-3">
              <span className="mr-4 text-2xl leading-none text-[#1C1C1C]">*</span>
              <span className="text-[1.55rem] font-semibold uppercase tracking-tight text-[#1C1C1C] sm:text-[1.8rem]">
                {eyebrow}
              </span>
            </div>

            <div className="mt-6">
              <h1 className="text-3xl font-semibold tracking-tight text-[#1C1C1C] sm:text-4xl">
                {title}
              </h1>
            </div>

            <p className="mt-5 max-w-3xl text-base leading-relaxed text-[#1C1C1C]/60 sm:text-[1.05rem]">
              {description}
            </p>
          </div>
        </div>
      </header>

      <section className="border-b border-[#1C1C1C]/10 bg-[#F9F8F6]">
        <div className="border-b border-[#1C1C1C]/10 px-5 py-4 sm:px-6">
          <div className="mb-3 flex items-center gap-3">
            <span className="size-2.5 bg-[#1C1C1C]" />
            <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[#1C1C1C]/60">
              当前状态
            </p>
          </div>
          <h2 className="text-xl font-semibold tracking-tight text-[#1C1C1C]">
            功能暂未开放
          </h2>
        </div>
        <div className="px-5 py-5 sm:px-6">
          <p className="text-sm leading-relaxed text-[#1C1C1C]/60">
            该页面暂未接入真实业务能力，当前只保留入口与必要上下文。
          </p>
          {highlights.length ? (
            <ul className="mt-4 space-y-2">
              {highlights.map((item) => (
                <li className="flex items-start gap-2 text-sm leading-relaxed text-[#1C1C1C]/60" key={item}>
                  <span className="mt-2 size-1.5 shrink-0 bg-[#1C1C1C]/60" />
                  {item}
                </li>
              ))}
            </ul>
          ) : null}
          <div className="mt-6 flex flex-wrap items-center gap-4">
            <div className="border border-[#1C1C1C]/10 bg-white px-4 py-2 text-sm font-medium text-[#1C1C1C]/60">
              {routeLabel}
            </div>
            <Button
              asChild
              className="border-b border-[#1C1C1C]/20 bg-white px-5 py-2 text-sm font-medium text-[#1C1C1C] transition-colors hover:bg-[#1C1C1C]/5"
            >
              <Link href="/dashboard/overview">
                返回概览
                <ArrowUpRight className="size-4" />
              </Link>
            </Button>
          </div>
        </div>
      </section>
    </div>
  );
}