import * as React from "react";
import * as ToggleGroupPrimitive from "@radix-ui/react-toggle-group";
import { cva, type VariantProps } from "class-variance-authority";

import { cn } from "@/lib/utils";

const toggleGroupVariants = cva("bw-segmented-control", {
  variants: {
    variant: {
      segmented: "",
    },
  },
  defaultVariants: {
    variant: "segmented",
  },
});

const toggleGroupItemVariants = cva(
  "bw-segmented-item bw-segmented-label text-sm font-medium text-current focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#111111] focus-visible:ring-offset-2 disabled:pointer-events-none disabled:translate-y-0 disabled:border-transparent disabled:bg-transparent disabled:text-[#888888] disabled:shadow-none data-[state=off]:hover:border-[#111111] data-[state=off]:hover:bg-[var(--bw-segment-surface-hover)] data-[state=off]:hover:text-[#111111] [&_svg]:text-current",
  {
    variants: {
      variant: {
        segmented: "",
      },
    },
    defaultVariants: {
      variant: "segmented",
    },
  },
);

function ToggleGroup({
  className,
  variant,
  ...props
}: React.ComponentProps<typeof ToggleGroupPrimitive.Root> &
  VariantProps<typeof toggleGroupVariants>) {
  return (
    <ToggleGroupPrimitive.Root
      data-slot="toggle-group"
      className={cn(toggleGroupVariants({ variant, className }))}
      {...props}
    />
  );
}

function ToggleGroupItem({
  className,
  variant,
  ...props
}: React.ComponentProps<typeof ToggleGroupPrimitive.Item> &
  VariantProps<typeof toggleGroupItemVariants>) {
  return (
    <ToggleGroupPrimitive.Item
      data-slot="toggle-group-item"
      className={cn(toggleGroupItemVariants({ variant, className }))}
      {...props}
    />
  );
}

export { ToggleGroup, ToggleGroupItem };
