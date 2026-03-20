import * as React from "react";

import { cn } from "@/lib/utils";

export function PaperInput({
  className,
  ...props
}: React.InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      {...props}
      className={cn(
        "h-12 w-full border-2 border-black bg-white px-4 font-mono text-sm text-black outline-none placeholder:text-black/50 focus:bg-[#ffffcc]",
        className
      )}
    />
  );
}

export function PaperTextarea({
  className,
  ...props
}: React.TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return (
    <textarea
      {...props}
      className={cn(
        "min-h-[180px] w-full border-2 border-black bg-white px-4 py-3 font-mono text-sm leading-7 text-black outline-none placeholder:text-black/50 focus:bg-[#ffffcc]",
        className
      )}
    />
  );
}

export function PaperSelect({
  className,
  ...props
}: React.SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <select
      {...props}
      className={cn(
        "h-12 w-full border-2 border-black bg-white px-4 font-mono text-sm text-black outline-none",
        className
      )}
    />
  );
}

export function PaperCheckbox({
  checked,
  className,
  label,
  onChange,
}: {
  checked: boolean;
  className?: string;
  label: React.ReactNode;
  onChange: (checked: boolean) => void;
}) {
  return (
    <label className={cn("flex cursor-pointer items-center gap-3", className)}>
      <input
        checked={checked}
        className="size-4 cursor-pointer border-2 border-black bg-white accent-black"
        onChange={(event) => onChange(event.target.checked)}
        type="checkbox"
      />
      <span className="font-mono text-sm text-black">{label}</span>
    </label>
  );
}
