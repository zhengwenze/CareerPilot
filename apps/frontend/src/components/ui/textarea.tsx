import * as React from "react";

import { cn } from "@/lib/utils";

function Textarea({
  className,
  ...props
}: React.ComponentProps<"textarea">) {
  return (
    <textarea
      className={cn(
        "flex min-h-24 w-full border-b border-[#1C1C1C]/20 bg-transparent px-4 py-3 text-base transition-colors outline-none placeholder:text-[#1C1C1C]/40 focus-visible:border-[#1C1C1C]/40 disabled:cursor-not-allowed disabled:opacity-50 md:text-sm",
        className
      )}
      {...props}
    />
  );
}

export { Textarea };