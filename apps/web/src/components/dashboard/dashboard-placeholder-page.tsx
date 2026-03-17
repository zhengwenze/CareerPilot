import { ArrowUpRight } from "lucide-react";
import Link from "next/link";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

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
      <div className="max-w-3xl">
        <p className="text-sm font-medium tracking-[0.18em] text-black uppercase">
          {eyebrow}
        </p>
        <h1 className="mt-3 text-3xl font-semibold tracking-[-0.05em] text-black sm:text-4xl">
          {title}
        </h1>
        <p className="mt-3 text-sm leading-7 text-black/68">{description}</p>
      </div>

      <Card className="max-w-3xl rounded-[2rem] border border-black/10 bg-white py-0 shadow-[0_16px_40px_rgba(0,0,0,0.05)]">
        <CardContent className="space-y-4 px-6 py-6">
          <p className="text-sm font-medium text-black">当前状态</p>
          <p className="text-sm leading-7 text-black/68">
            该页面暂未接入真实业务能力，当前只保留入口与必要上下文。
          </p>
          {highlights.length ? (
            <div className="space-y-2">
              {highlights.map((item) => (
                <p className="text-sm leading-7 text-black/68" key={item}>
                  {item}
                </p>
              ))}
            </div>
          ) : null}
          <p className="text-xs text-black/45">{routeLabel}</p>
          <Button
            asChild
            variant="outline"
            className="h-11 w-fit rounded-full border-[#0071E3] bg-white px-5 text-[#0071E3] hover:bg-[#F5F9FF] hover:text-[#0071E3]"
          >
            <Link href="/dashboard/overview">
              返回概览
              <ArrowUpRight className="size-4" />
            </Link>
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
