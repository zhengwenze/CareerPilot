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
      <header className="border-2 border-black bg-[#f4f1e8] shadow-[8px_8px_0_0_#000]">
        <div className="flex flex-col gap-6 px-6 py-6 sm:px-8 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <div className="inline-flex items-center border-2 border-black bg-[#f9f7f0] px-5 py-3 shadow-[4px_4px_0_0_#000]">
              <span className="mr-4 text-2xl leading-none text-[#2f55d4]">*</span>
              <span className="text-[1.55rem] font-black uppercase tracking-[-0.06em] text-black sm:text-[1.8rem]">
                {eyebrow}
              </span>
            </div>

            <div className="mt-6 inline-block border-2 border-black bg-[#2f55d4] px-4 py-2 shadow-[5px_5px_0_0_#000]">
              <h1 className="text-3xl font-semibold tracking-[-0.08em] text-white sm:text-4xl">
                {title}
              </h1>
            </div>

            <p className="mt-5 max-w-3xl text-base leading-8 text-[#38445a] sm:text-[1.05rem]">
              {description}
            </p>
          </div>
        </div>
      </header>

      <section className="border-2 border-black bg-[#f4f1e8] shadow-[8px_8px_0_0_#000]">
        <div className="border-b-2 border-black px-5 py-4 sm:px-6">
          <div className="mb-3 flex items-center gap-3">
            <span className="size-2.5 bg-[#ff7a10]" />
            <p className="text-[11px] font-bold uppercase tracking-[0.18em] text-black/45">
              当前状态
            </p>
          </div>
          <h2 className="text-xl font-semibold tracking-[-0.05em] text-black">
            功能暂未开放
          </h2>
        </div>
        <div className="px-5 py-5 sm:px-6">
          <p className="text-sm leading-7 text-black/70">
            该页面暂未接入真实业务能力，当前只保留入口与必要上下文。
          </p>
          {highlights.length ? (
            <ul className="mt-4 space-y-2">
              {highlights.map((item) => (
                <li className="flex items-start gap-2 text-sm leading-7 text-black/70" key={item}>
                  <span className="mt-2 size-1.5 shrink-0 bg-black/45" />
                  {item}
                </li>
              ))}
            </ul>
          ) : null}
          <div className="mt-6 flex flex-wrap items-center gap-4">
            <div className="border-2 border-black bg-[#f9f7f0] px-4 py-2 text-sm font-medium text-black/60 shadow-[3px_3px_0_0_#000]">
              {routeLabel}
            </div>
            <Button
              asChild
              className="border-2 border-black bg-white px-5 py-2 text-sm font-semibold text-black shadow-[4px_4px_0_0_#000] hover:-translate-x-px hover:-translate-y-px hover:shadow-[5px_5px_0_0_#000]"
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