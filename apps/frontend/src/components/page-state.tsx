import { AlertTriangle, Inbox, LoaderCircle } from "lucide-react"

import { PaperSection } from "@/components/brutalist/page-shell"
import { Button } from "@/components/ui/button"

type PageStateProps = {
  title: string
  description: string
  actionLabel?: string
  onAction?: () => void
  tone?: "loading" | "empty" | "error"
}

function PageStateCard({
  title,
  description,
  actionLabel,
  onAction,
  tone = "loading",
}: PageStateProps) {
  const icon =
    tone === "error" ? (
      <AlertTriangle className="size-5 text-[#666666]" />
    ) : tone === "empty" ? (
      <Inbox className="size-5 text-[#666666]" />
    ) : (
      <LoaderCircle className="size-5 text-[#666666] animate-spin" />
    )

  return (
    <PaperSection
      eyebrow={
        tone === "error" ? "Error State" : tone === "empty" ? "Empty State" : "Loading State"
      }
      title={title}
    >
      <div className="flex items-start gap-4">
        <div className="flex size-10 shrink-0 items-center justify-center border border-[#e5e5e5] bg-[#fafafa]">
          {icon}
        </div>
        <div className="space-y-4">
          <p className="bw-muted-text">{description}</p>
          {actionLabel && onAction ? (
            <Button onClick={onAction} type="button" variant="secondary">
              {actionLabel}
            </Button>
          ) : null}
        </div>
      </div>
    </PaperSection>
  )
}

export function PageLoadingState({
  title = "页面正在加载",
  description = "我们正在恢复登录态并同步你需要的数据。",
}: {
  title?: string
  description?: string
}) {
  return <PageStateCard description={description} title={title} tone="loading" />
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
  )
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
  )
}
