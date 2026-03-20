import * as React from "react"

import { cn } from "@/lib/utils"

function Input({ className, type, ...props }: React.ComponentProps<"input">) {
  return (
    <input
      type={type}
      data-slot="input"
      className={cn(
        "h-10 w-full min-w-0 border-2 border-black bg-white px-3 py-2 font-mono text-sm text-black placeholder:text-black/50 focus:outline-dotted focus:outline-1 focus:outline-black focus:outline-offset-1 focus:bg-[#ffffcc] disabled:pointer-events-none disabled:cursor-not-allowed disabled:opacity-50",
        className
      )}
      {...props}
    />
  )
}

export { Input }
