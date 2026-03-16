import { AlertTriangle, Inbox, LoaderCircle } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

type PageStateProps = {
  title: string;
  description: string;
  actionLabel?: string;
  onAction?: () => void;
  tone?: "loading" | "empty" | "error";
};

function PageStateCard({
  title,
  description,
  actionLabel,
  onAction,
  tone = "loading",
}: PageStateProps) {
  const icon =
    tone === "error" ? (
      <AlertTriangle className="size-5" />
    ) : tone === "empty" ? (
      <Inbox className="size-5" />
    ) : (
      <LoaderCircle className="size-5 animate-spin" />
    );

  return (
    <Card className="rounded-[2rem] border border-black/10 bg-white py-0 shadow-[0_18px_48px_rgba(0,0,0,0.06)]">
      <CardHeader className="px-6 py-6 sm:px-8">
        <div className="flex size-12 items-center justify-center rounded-2xl bg-[#f5f5f7] text-black">
          {icon}
        </div>
        <CardTitle className="pt-4 text-2xl font-semibold text-black">
          {title}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4 px-6 pb-6 text-sm leading-7 text-black/70 sm:px-8 sm:pb-8">
        <p>{description}</p>
        {actionLabel && onAction ? (
          <Button
            className="rounded-full bg-[#0071E3] px-5 text-white hover:bg-[#0077ED]"
            onClick={onAction}
            type="button"
          >
            {actionLabel}
          </Button>
        ) : null}
      </CardContent>
    </Card>
  );
}

export function PageLoadingState({
  title = "页面正在加载",
  description = "我们正在恢复登录态并同步你需要的数据。",
}: {
  title?: string;
  description?: string;
}) {
  return <PageStateCard description={description} title={title} tone="loading" />;
}

export function PageEmptyState({
  title,
  description,
  actionLabel,
  onAction,
}: PageStateProps) {
  return (
    <PageStateCard
      actionLabel={actionLabel}
      description={description}
      onAction={onAction}
      title={title}
      tone="empty"
    />
  );
}

export function PageErrorState({
  title,
  description,
  actionLabel,
  onAction,
}: PageStateProps) {
  return (
    <PageStateCard
      actionLabel={actionLabel}
      description={description}
      onAction={onAction}
      title={title}
      tone="error"
    />
  );
}
