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
    <div className="space-y-10">
      <section className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_320px] lg:items-end">
        <div className="max-w-3xl">
          <p className="text-sm font-medium tracking-[0.18em] text-black uppercase">
            {eyebrow}
          </p>
          <h1 className="mt-4 text-4xl font-semibold tracking-[-0.05em] text-black sm:text-5xl">
            {title}
          </h1>
          <p className="mt-5 max-w-2xl text-base leading-8 text-black/72">
            {description}
          </p>
        </div>

        <Card className="rounded-[2rem] border border-black/10 bg-[#f5f5f7] py-0 shadow-none">
          <CardContent className="px-6 py-6">
            <p className="text-xs font-medium tracking-[0.18em] text-black uppercase">
              Module Status
            </p>
            <p className="mt-4 text-2xl font-semibold tracking-[-0.04em] text-black">
              即将接入真实内容
            </p>
            <p className="mt-3 text-sm leading-7 text-black/65">{routeLabel}</p>
          </CardContent>
        </Card>
      </section>

      <section className="grid gap-4 md:grid-cols-3">
        {highlights.map((item) => (
          <Card
            key={item}
            className="rounded-[2rem] border border-black/10 bg-white py-0 shadow-[0_16px_40px_rgba(0,0,0,0.05)]"
          >
            <CardContent className="px-6 py-6">
              <p className="text-base leading-8 text-black">{item}</p>
            </CardContent>
          </Card>
        ))}
      </section>

      <Button
        asChild
        variant="outline"
        className="h-12 w-fit rounded-full border-[#0071E3] bg-white px-6 text-[#0071E3] hover:bg-[#F5F9FF] hover:text-[#0071E3]"
      >
        <Link href="/dashboard/overview">
          返回概览
          <ArrowUpRight className="size-4" />
        </Link>
      </Button>
    </div>
  );
}
