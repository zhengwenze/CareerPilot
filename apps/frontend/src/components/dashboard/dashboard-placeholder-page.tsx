import { ArrowUpRight } from "lucide-react";
import Link from "next/link";

import {
  MetaChip,
  PageHeader,
  PageShell,
  PaperSection,
} from "@/components/brutalist/page-shell";
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
    <PageShell>
      <PageHeader
        description={description}
        eyebrow={eyebrow}
        meta={<MetaChip>{routeLabel}</MetaChip>}
        title={title}
      />

      <PaperSection title="功能暂未开放" eyebrow="Current Status">
        <p className="bw-muted-text">
          该页面暂未接入真实业务能力，当前只保留入口与必要上下文。
        </p>

        {highlights.length ? (
          <ul className="bw-rule-list mt-4 text-sm leading-7">
            {highlights.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        ) : null}

        <div className="mt-6 flex flex-wrap items-center gap-4">
          <Link href="/dashboard/overview">
            <Button type="button">
              返回概览
              <ArrowUpRight className="ml-2 size-4" />
            </Button>
          </Link>
        </div>
      </PaperSection>
    </PageShell>
  );
}
