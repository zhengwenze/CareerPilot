import { cn } from "@/lib/utils";
import type { ButtonHTMLAttributes, InputHTMLAttributes } from "react";

const brutalButtonBase =
  "inline-flex shrink-0 cursor-pointer items-center justify-center border-4 border-black font-black uppercase text-sm whitespace-nowrap transition-all select-none pointer-events-auto focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-black focus-visible:ring-offset-[-2px] disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:shrink-0";

export function BrutalButton({
  variant = "primary",
  size = "md",
  className,
  children,
  ...props
}: {
  variant?: "primary" | "secondary" | "danger";
  size?: "sm" | "md" | "lg";
} & ButtonHTMLAttributes<HTMLButtonElement>) {
  const sizeClassName =
    size === "sm"
      ? "h-8 px-4 py-1.5 text-xs gap-1.5"
      : size === "lg"
        ? "h-14 px-8 py-3 text-base gap-2"
        : "h-10 px-5 py-2 text-sm gap-1.5";

  const variantClassName =
    variant === "primary"
      ? "bg-[#ccff00] text-black shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] hover:shadow-none hover:translate-x-[2px] hover:translate-y-[2px] active:translate-x-[4px] active:translate-y-[4px]"
      : variant === "danger"
        ? "bg-[#ff006e] text-white shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] hover:shadow-none hover:translate-x-[2px] hover:translate-y-[2px] active:translate-x-[4px] active:translate-y-[4px]"
        : "bg-white text-black shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] hover:shadow-none hover:translate-x-[2px] hover:translate-y-[2px] active:translate-x-[4px] active:translate-y-[4px]";

  return (
    <button
      {...props}
      className={cn(
        brutalButtonBase,
        sizeClassName,
        variantClassName,
        className,
      )}
    >
      {children}
    </button>
  );
}

export function BrutalCard({
  className,
  children,
  ...props
}: React.ComponentProps<"div">) {
  return (
    <div
      className={cn(
        "border-4 border-black bg-white shadow-[8px_8px_0px_0px_rgba(0,0,0,1)]",
        className,
      )}
      {...props}
    >
      {children}
    </div>
  );
}

export function BrutalSection({
  className,
  children,
  ...props
}: React.ComponentProps<"section">) {
  return (
    <section className={cn("border-b-4 border-black", className)} {...props}>
      {children}
    </section>
  );
}

export function BrutalTag({
  className,
  children,
  ...props
}: React.ComponentProps<"div">) {
  return (
    <div
      className={cn(
        "inline-block border-2 border-black bg-[#ccff00] px-3 py-1 font-black text-xs uppercase",
        className,
      )}
      {...props}
    >
      {children}
    </div>
  );
}

export function BrutalInput({
  className,
  error,
  ...props
}: InputHTMLAttributes<HTMLInputElement> & { error?: boolean }) {
  return (
    <input
      {...props}
      className={cn(
        "h-10 w-full border-4 border-black bg-white px-3 py-2 font-mono text-sm text-black placeholder:text-black/40 focus:outline-none focus:ring-4 focus:ring-black focus:ring-offset-[-2px] disabled:cursor-not-allowed disabled:opacity-50",
        error && "border-[#ff006e] focus:ring-[#ff006e]",
        className,
      )}
    />
  );
}
