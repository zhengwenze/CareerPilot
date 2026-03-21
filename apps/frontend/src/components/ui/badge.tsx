import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/utils"

const badgeVariants = cva(
  "inline-flex h-6 shrink-0 items-center justify-center gap-1 px-2.5 text-xs font-medium transition-colors [&>svg]:pointer-events-none [&>svg]:shrink-0 [&>svg:not([class*='size-'])]:size-3!",
  {
    variants: {
      variant: {
        default: "bg-[#fafafa] text-[#111111] border border-[#e5e5e5]",
        secondary: "bg-[#fafafa] text-[#666666] border border-[#e5e5e5]",
        destructive: "bg-[#111111] text-white border border-[#111111]",
        outline: "bg-transparent text-[#111111] border border-[#e5e5e5]",
        ghost: "bg-transparent text-[#666666] border border-transparent",
        link: "bg-transparent text-[#111111] underline border-transparent p-0 h-auto",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
)

function Badge({
  className,
  variant = "default",
  ...props
}: React.ComponentProps<"span"> &
  VariantProps<typeof badgeVariants>) {
  return (
    <span
      data-slot="badge"
      data-variant={variant}
      className={cn(badgeVariants({ variant }), className)}
      {...props}
    />
  )
}

export { Badge, badgeVariants }
