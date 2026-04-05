"use client";

import Link from "next/link";

import { type NavItem } from "@/config/nav-config";
import { cn } from "@/lib/utils";

function isItemActive(pathname: string, item: NavItem) {
  if (!item.href) {
    return false;
  }

  const matchMode = item.match ?? "exact";
  if (matchMode === "exact") {
    return pathname === item.href;
  }

  return pathname === item.href || pathname.startsWith(`${item.href}/`);
}

export function DashboardModuleSwitcher({
  items,
  pathname,
  className,
}: {
  items: NavItem[];
  pathname: string;
  className?: string;
}) {
  return (
    <nav className={cn("bw-module-switcher", className)}>
      {items.map((item) => {
        const active = isItemActive(pathname, item);

        if (!item.href) {
          return null;
        }

        return (
          <Link
            key={item.href}
            href={item.href}
            aria-current={active ? "page" : undefined}
            className={cn(
              "flex min-h-12 items-center justify-center border px-4 py-3 text-sm no-underline transition-colors duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#111111] focus-visible:ring-offset-2",
              item.disabled
                ? "pointer-events-none border-[#e5e5e5] bg-[#f5f5f5] text-[#888888]"
                : active
                  ? "border-[#111111] bg-[#111111] text-[#fafafa] hover:border-[#333333] hover:bg-[#333333] hover:text-[#fafafa]"
                  : "border-[#e5e5e5] bg-[#fafafa] text-[#111111] hover:border-[#111111] hover:bg-[#ffffff] hover:text-[#111111]",
            )}
          >
            <span className="truncate font-medium">{item.title}</span>
          </Link>
        );
      })}
    </nav>
  );
}
