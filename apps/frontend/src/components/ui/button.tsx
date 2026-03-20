import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"
import { Slot } from "radix-ui"

import { cn } from "@/lib/utils"

const buttonVariants = cva(
  "group/button inline-flex shrink-0 cursor-pointer items-center justify-center border-2 border-black font-mono font-bold uppercase text-sm whitespace-nowrap transition-none outline-none select-none pointer-events-auto focus-visible:outline-dotted focus-visible:outline-1 focus-visible:outline-black focus-visible:outline-offset-1 disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:shrink-0 [&_svg:not([class*='size-'])]:size-4",
  {
    variants: {
      variant: {
        default:
          "bg-[#dfdfdf] text-black hover:text-[#0000ff] border-t-white border-l-white border-r-[#808080] border-b-[#808080] active:border-t-[#808080] active:border-l-[#808080] active:border-r-white active:border-b-white",
        primary:
          "bg-[#dfdfdf] text-black hover:text-[#0000ff] border-t-white border-l-white border-r-[#808080] border-b-[#808080] active:border-t-[#808080] active:border-l-[#808080] active:border-r-white active:border-b-white",
        secondary:
          "bg-white text-black hover:text-[#0000ff] border-t-white border-l-white border-r-[#808080] border-b-[#808080] active:border-t-[#808080] active:border-l-[#808080] active:border-r-white active:border-b-white",
        destructive:
          "bg-white text-[#ff0000] hover:text-[#ff0000] border-t-white border-l-white border-r-[#808080] border-b-[#808080] active:border-t-[#808080] active:border-l-[#808080] active:border-r-white active:border-b-white",
        link:
          "border-0 bg-transparent p-0 text-[#0000ff] underline hover:text-[#ff0000]",
        ghost:
          "bg-transparent text-black hover:text-[#0000ff] border border-transparent",
      },
      size: {
        default: "h-10 px-4 py-2 gap-2",
        xs: "h-6 px-2 py-1 text-xs gap-1",
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
  const Comp = asChild ? Slot.Root : "button"

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
