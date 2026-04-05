import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"
import { Slot } from "@radix-ui/react-slot"

import { cn } from "@/lib/utils"

const buttonVariants = cva(
  "inline-flex shrink-0 cursor-pointer items-center justify-center gap-2 border font-medium text-sm text-current transition-colors duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#111111] focus-visible:ring-offset-2 disabled:pointer-events-none disabled:border-[#e5e5e5] disabled:bg-[#f5f5f5] disabled:text-[#888888] [&_svg]:pointer-events-none [&_svg]:shrink-0 [&_svg]:text-current [&_svg:not([class*='size-'])]:size-4",
  {
    variants: {
      variant: {
        default:
          "border-[#111111] bg-[#111111] text-[#fafafa] hover:border-[#333333] hover:bg-[#333333] hover:text-[#fafafa]",
        primary:
          "border-[#111111] bg-[#111111] text-[#fafafa] hover:border-[#333333] hover:bg-[#333333] hover:text-[#fafafa]",
        secondary:
          "border-[#e5e5e5] bg-[#fafafa] text-[#111111] hover:border-[#111111] hover:bg-[#ffffff] hover:text-[#111111]",
        ghost:
          "border-transparent bg-transparent text-[#111111] hover:border-[#e5e5e5] hover:bg-[#fafafa] hover:text-[#111111]",
        destructive:
          "border-[#111111] bg-[#111111] text-[#fafafa] hover:border-[#333333] hover:bg-[#333333] hover:text-[#fafafa]",
        link:
          "h-auto border-transparent bg-transparent p-0 text-[#111111] underline hover:text-[#666666]",
        outline:
          "border-[#111111] bg-[#ffffff] text-[#111111] hover:bg-[#fafafa] hover:text-[#111111]",
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
