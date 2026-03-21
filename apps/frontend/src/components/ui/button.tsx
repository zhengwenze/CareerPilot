import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"
import { Slot } from "@radix-ui/react-slot"

import { cn } from "@/lib/utils"

const buttonVariants = cva(
  "inline-flex shrink-0 cursor-pointer items-center justify-center gap-2 font-medium text-sm transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:shrink-0 [&_svg:not([class*='size-'])]:size-4",
  {
    variants: {
      variant: {
        default:
          "bg-[#111111] text-white hover:bg-[#333333] border border-[#111111]",
        primary:
          "bg-[#111111] text-white hover:bg-[#333333] border border-[#111111]",
        secondary:
          "bg-[#fafafa] text-[#111111] hover:bg-[#e5e5e5] border border-[#e5e5e5]",
        ghost:
          "bg-transparent text-[#111111] hover:bg-[#fafafa] border border-transparent",
        destructive:
          "bg-[#111111] text-white hover:bg-[#333333] border border-[#111111]",
        link:
          "bg-transparent text-[#111111] underline hover:text-[#666666] border border-transparent p-0 h-auto",
        outline:
          "bg-transparent text-[#111111] hover:bg-[#fafafa] border border-[#e5e5e5]",
      },
      size: {
        default: "h-10 px-5 py-2",
        xs: "h-7 px-2.5 py-1 text-xs gap-1.5",
        sm: "h-8 px-3 py-1.5 text-sm gap-1.5",
        lg: "h-12 px-6 py-3 text-base gap-2",
        icon: "size-10",
        "icon-xs": "size-6",
        "icon-sm": "size-8",
        "icon-lg": "size-12",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
)

function Button({
  className,
  variant = "default",
  size = "default",
  asChild = false,
  ...props
}: React.ComponentProps<"button"> &
  VariantProps<typeof buttonVariants> & {
    asChild?: boolean
  }) {
  const Comp = asChild ? Slot : "button"

  return (
    <Comp
      data-slot="button"
      data-variant={variant}
      data-size={size}
      className={cn(buttonVariants({ variant, size, className }))}
      {...props}
    />
  )
}

export { Button, buttonVariants }
