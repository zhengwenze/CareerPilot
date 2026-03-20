import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"
import { Slot } from "radix-ui"

import { cn } from "@/lib/utils"

const badgeVariants = cva(
  "group/badge inline-flex h-6 w-fit shrink-0 items-center justify-center gap-1 overflow-hidden border-2 border-black px-2 py-0.5 text-xs font-mono font-bold uppercase whitespace-nowrap transition-none focus-visible:outline-dotted focus-visible:outline-1 focus-visible:outline-black focus-visible:outline-offset-1 [&>svg]:pointer-events-none [&>svg]:shrink-0 [&>svg:not([class*='size-'])]:size-3!",
  {
    variants: {
      variant: {
        default: "bg-white text-black",
        secondary: "bg-gray-100 text-black",
        destructive: "bg-white text-red border-red",
        outline: "bg-white text-black border-black",
        ghost: "bg-transparent text-black border-transparent",
        link: "bg-transparent text-blue-500 underline border-transparent hover:text-red",
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
  asChild = false,
  ...props
}: React.ComponentProps<"span"> &
  VariantProps<typeof badgeVariants> & { asChild?: boolean }) {
  const Comp = asChild ? Slot.Root : "span"

  return (
    <Comp
      data-slot="badge"
      data-variant={variant}
      className={cn(badgeVariants({ variant }), className)}
      {...props}
    />
  )
}

export { Badge, badgeVariants }
