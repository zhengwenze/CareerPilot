import { cn } from "@/lib/utils"
import type { ButtonHTMLAttributes, InputHTMLAttributes } from "react"

function MonoButton({
  variant = "primary",
  size = "md",
  className,
  children,
  ...props
}: {
  variant?: "primary" | "secondary" | "ghost"
  size?: "sm" | "md" | "lg"
} & ButtonHTMLAttributes<HTMLButtonElement>) {
  const sizeClassName =
    size === "sm"
      ? "h-8 px-3 py-1 text-xs gap-1.5"
      : size === "lg"
        ? "h-12 px-6 py-3 text-base gap-2"
        : "h-10 px-4 py-2 text-sm gap-1.5"

  const variantClassName =
    variant === "primary"
      ? "bg-[#111111] text-white hover:bg-[#333333] border border-[#111111]"
      : variant === "ghost"
        ? "bg-transparent text-[#111111] hover:bg-[#fafafa] border border-transparent"
        : "bg-[#fafafa] text-[#111111] hover:bg-[#e5e5e5] border border-[#e5e5e5]"

  return (
    <button
      {...props}
      className={cn(
        "inline-flex shrink-0 cursor-pointer items-center justify-center font-medium text-sm transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50",
        sizeClassName,
        variantClassName,
        className
      )}
    >
      {children}
    </button>
  )
}

function MonoCard({
  className,
  children,
  ...props
}: React.ComponentProps<"div">) {
  return (
    <div
      className={cn(
        "border border-[#e5e5e5] bg-white",
        className
      )}
      {...props}
    >
      {children}
    </div>
  )
}

function MonoSection({
  className,
  children,
  ...props
}: React.ComponentProps<"section">) {
  return (
    <section className={cn("border-b border-[#e5e5e5]", className)} {...props}>
      {children}
    </section>
  )
}

function MonoTag({
  className,
  children,
  ...props
}: React.ComponentProps<"div">) {
  return (
    <div
      className={cn(
        "inline-block border border-[#e5e5e5] bg-[#fafafa] px-3 py-1 text-xs font-medium text-[#111111]",
        className
      )}
      {...props}
    >
      {children}
    </div>
  )
}

function MonoInput({
  className,
  error,
  ...props
}: InputHTMLAttributes<HTMLInputElement> & { error?: boolean }) {
  return (
    <input
      className={cn(
        "flex h-10 w-full border bg-white px-4 py-2 text-sm text-[#111111] placeholder:text-[#999999] focus:outline-none focus:border-[#111111] focus:ring-1 focus:ring-[#111111] disabled:cursor-not-allowed disabled:opacity-50",
        error ? "border-[#111111]" : "border-[#e5e5e5]",
        className
      )}
      {...props}
    />
  )
}

function MonoTextarea({
  className,
  error,
  ...props
}: InputHTMLAttributes<HTMLTextAreaElement> & { error?: boolean }) {
  return (
    <textarea
      className={cn(
        "flex min-h-24 w-full border bg-white px-4 py-3 text-sm text-[#111111] placeholder:text-[#999999] focus:outline-none focus:border-[#111111] focus:ring-1 focus:ring-[#111111] disabled:cursor-not-allowed disabled:opacity-50 resize-none",
        error ? "border-[#111111]" : "border-[#e5e5e5]",
        className
      )}
      {...props}
    />
  )
}

export {
  MonoButton as BrutalButton,
  MonoCard as BrutalCard,
  MonoSection as BrutalSection,
  MonoTag as BrutalTag,
  MonoInput as BrutalInput,
  MonoTextarea as BrutalTextarea,
}
