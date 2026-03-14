import { ArrowRight, FolderKanban, Sparkles } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

type DashboardPlaceholderPageProps = {
  eyebrow: string;
  title: string;
  description: string;
  routeLabel: string;
  nextSteps: string[];
};

export function DashboardPlaceholderPage({
  eyebrow,
  title,
  description,
  routeLabel,
  nextSteps,
}: DashboardPlaceholderPageProps) {
  return (
    <>
      <Card className="surface-card border-0 bg-card/85 py-0 shadow-2xl shadow-emerald-950/8">
        <CardContent className="px-6 py-6 sm:px-8 sm:py-8">
          <div className="flex flex-col gap-8 lg:flex-row lg:items-end lg:justify-between">
            <div className="max-w-3xl space-y-4">
              <Badge className="w-fit rounded-full bg-primary/10 px-3 py-1 text-primary hover:bg-primary/10">
                {eyebrow}
              </Badge>
              <h2 className="text-4xl font-semibold tracking-tight text-foreground sm:text-5xl">
                {title}
              </h2>
              <p className="max-w-2xl text-base leading-8 text-muted-foreground">
                {description}
              </p>
            </div>

            <div className="rounded-[28px] border border-border/70 bg-white/72 p-4 shadow-sm">
              <p className="text-sm text-muted-foreground">当前路由</p>
              <p className="mt-2 text-base font-medium text-foreground">{routeLabel}</p>
            </div>
          </div>
        </CardContent>
      </Card>

      <section className="grid gap-5 xl:grid-cols-[1.1fr_0.9fr]">
        <Card className="surface-card border-0 bg-card/78 py-0 shadow-xl shadow-emerald-950/5">
          <CardHeader className="px-6 py-6 sm:px-8">
            <Badge className="w-fit rounded-full bg-secondary px-3 py-1 text-secondary-foreground">
              页面状态
            </Badge>
            <CardTitle className="text-2xl font-semibold text-foreground">
              当前是结构占位页
            </CardTitle>
          </CardHeader>
          <CardContent className="grid gap-4 px-6 pb-6 sm:grid-cols-2 sm:px-8 sm:pb-8">
            {[
              "已接入 dashboard 公共布局",
              "已可通过左侧菜单直接访问",
              "后续只需替换本页内容区",
              "不会影响其他页面壳层复用",
            ].map((item) => (
              <Card
                className="rounded-[26px] border border-border/70 bg-white/72 py-0 shadow-none"
                key={item}
              >
                <CardContent className="flex items-start gap-3 px-5 py-5 text-sm leading-7 text-muted-foreground">
                  <span className="mt-1 rounded-2xl bg-primary/10 p-2 text-primary">
                    <FolderKanban className="size-4" />
                  </span>
                  <span>{item}</span>
                </CardContent>
              </Card>
            ))}
          </CardContent>
        </Card>

        <Card className="surface-card border-0 bg-card/78 py-0 shadow-xl shadow-emerald-950/5">
          <CardHeader className="space-y-4 px-6 py-6 sm:px-8">
            <Badge className="w-fit rounded-full bg-primary/10 px-3 py-1 text-primary hover:bg-primary/10">
              下一步
            </Badge>
            <CardTitle className="text-2xl font-semibold text-foreground">
              这里后面可以直接替换成正式业务页面
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 px-6 pb-6 sm:px-8 sm:pb-8">
            {nextSteps.map((item, index) => (
              <div
                className="flex items-start gap-3 rounded-[24px] border border-border/70 bg-white/72 px-4 py-4"
                key={item}
              >
                <span className="flex size-8 shrink-0 items-center justify-center rounded-2xl bg-secondary text-sm font-semibold text-secondary-foreground">
                  {index + 1}
                </span>
                <p className="pt-0.5 text-sm leading-7 text-muted-foreground">{item}</p>
              </div>
            ))}

            <Button className="mt-2 rounded-full px-5" disabled type="button">
              等待接入真实内容
              <ArrowRight className="size-4" />
            </Button>
          </CardContent>
        </Card>
      </section>

      <Card className="surface-card border-0 bg-card/70 py-0 shadow-lg shadow-emerald-950/5">
        <CardContent className="flex items-start gap-4 px-6 py-6 sm:px-8">
          <div className="rounded-2xl bg-primary/10 p-3 text-primary">
            <Sparkles className="size-4" />
          </div>
          <div className="space-y-2">
            <p className="text-base font-medium text-foreground">落地建议</p>
            <p className="text-sm leading-7 text-muted-foreground">
              后面开发真实页面时，优先保留当前标题区和卡片节奏，只替换业务组件，这样整体导航壳层和视觉节奏会保持稳定。
            </p>
          </div>
        </CardContent>
      </Card>
    </>
  );
}
