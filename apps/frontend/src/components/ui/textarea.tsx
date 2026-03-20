import * as React from "react";

import { cn } from "@/lib/utils";

function Textarea({
  className,
  ...props
}: React.ComponentProps<"textarea">) {
  return (
    <textarea
      className={cn(
        "flex min-h-24 w-full border-2 border-black bg-white px-4 py-3 font-mono text-sm text-black placeholder:text-black/50 focus:outline-dotted focus:outline-1 focus:outline-black focus:outline-offset-1 focus:bg-[#ffffcc] disabled:cursor-not-allowed disabled:opacity-50",
        className
      )}
      {...props}
    />
  );
}

export { Textarea };
