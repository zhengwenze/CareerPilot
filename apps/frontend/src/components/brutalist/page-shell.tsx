import type { ReactNode } from "react"

import { cn } from "@/lib/utils"

export function PageShell({
  className,
  children,
}: {
  className?: string
  children: ReactNode
}) {
  return <div className={cn("bw-page", className)}>{children}</div>
}

export function MetaChip({
  className,
  children,
}: {
  className?: string
  children: ReactNode
}) {
  return <div className={cn("bw-meta-chip", className)}>{children}</div>
}

export function PageHeader({
  eyebrow,
  title,
  description,
  meta,
  children,
  className,
}: {
  eyebrow: string
  title: ReactNode
  description?: ReactNode
  meta?: ReactNode
  children?: ReactNode
  className?: string
}) {
  return (
    <header className={cn("bw-page-header", className)}>
      <div className="bw-page-header-inner">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div className="min-w-0 flex-1">
            <div className="bw-kicker">{eyebrow}</div>
            <h1 className="bw-page-title mt-2">{title}</h1>
            {description ? (
              <p className="bw-page-lead mt-3">{description}</p>
            ) : null}
          </div>
          {meta ? <div className="bw-meta-row mt-4 lg:mt-0">{meta}</div> : null}
        </div>
        {children ? <div className="bw-page-header-actions">{children}</div> : null}
      </div>
    </header>
  )
}

export function PaperSection({
  title,
  eyebrow,
  rightSlot,
  className,
  bodyClassName,
  children,
}: {
  title: ReactNode
  eyebrow?: ReactNode
  rightSlot?: ReactNode
  className?: string
  bodyClassName?: string
  children: ReactNode
}) {
  return (
    <section className={cn("bw-panel", className)}>
      <div className="bw-panel-header">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            {eyebrow ? <p className="bw-panel-kicker">{eyebrow}</p> : null}
            <h2 className="bw-panel-title">{title}</h2>
          </div>
          {rightSlot}
        </div>
      </div>
      <div className={cn("bw-panel-body", bodyClassName)}>{children}</div>
    </section>
  )
}
