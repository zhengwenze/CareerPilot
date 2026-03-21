import * as React from "react"

import { cn } from "@/lib/utils"

export function PaperInput({
  className,
  ...props
}: React.InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      {...props}
      className={cn(
        "h-10 w-full border border-[#e5e5e5] bg-white px-4 text-sm text-[#111111] outline-none placeholder:text-[#999999] focus:border-[#111111] focus:ring-1 focus:ring-[#111111]",
        className
      )}
    />
  )
}

export function PaperTextarea({
  className,
  ...props
}: React.TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return (
    <textarea
      {...props}
      className={cn(
        "min-h-32 w-full border border-[#e5e5e5] bg-white px-4 py-3 text-sm text-[#111111] outline-none placeholder:text-[#999999] focus:border-[#111111] focus:ring-1 focus:ring-[#111111] resize-none",
        className
      )}
    />
  )
}

export function PaperSelect({
  className,
  ...props
}: React.SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <select
      {...props}
      className={cn(
        "h-10 w-full border border-[#e5e5e5] bg-white px-4 text-sm text-[#111111] outline-none focus:border-[#111111] focus:ring-1 focus:ring-[#111111]",
        className
      )}
    />
  )
}

export function PaperCheckbox({
  checked,
  className,
  label,
  onChange,
}: {
  checked: boolean
  className?: string
  label: React.ReactNode
  onChange: (checked: boolean) => void
}) {
  return (
    <label className={cn("flex cursor-pointer items-center gap-3", className)}>
      <input
        checked={checked}
        className="size-4 cursor-pointer border border-[#e5e5e5] bg-white accent-[#111111]"
        onChange={(event) => onChange(event.target.checked)}
        type="checkbox"
      />
      <span className="text-sm text-[#111111]">{label}</span>
    </label>
  )
}
