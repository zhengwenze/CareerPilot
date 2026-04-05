"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { ArrowUpRight, Menu, X } from "lucide-react";
import { useState, useTransition } from "react";

import { useAuth } from "@/components/auth-provider";
import { Button } from "@/components/ui/button";
import { dashboardNavItems, type NavItem } from "@/config/nav-config";
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

export function DashboardTopNav() {
  const pathname = usePathname();
  const router = useRouter();
  const { user, logout } = useAuth();
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const [isLoggingOut, startTransition] = useTransition();
  const activeItem = dashboardNavItems.find((item) => isItemActive(pathname, item));

  async function handleLogout() {
    await logout();
    startTransition(() => {
      router.push("/login");
      router.refresh();
    });
  }

  return (
    <header className="border-b border-[#e5e5e5] bg-white">
      <div className="mx-auto max-w-6xl px-4 py-5 sm:px-6">
        <div className="flex flex-col gap-5">
          <div className="flex items-start justify-between gap-4">
            <div className="min-w-0">
              <p className="bw-kicker">Career Pilot Workspace</p>
              <div className="mt-2 flex flex-wrap items-end gap-x-4 gap-y-2">
                <Link
                  href="/dashboard/overview"
                  className="text-[1.75rem] font-semibold text-[#111111] no-underline hover:text-[#666666]"
                  style={{
                    fontFamily: "var(--font-heading)",
                    letterSpacing: "-0.03em",
                  }}
                >
                  CareerPilot
                </Link>
                <p className="pb-1 text-sm text-[#666666]">
                  Resume → Job Description → Tailored Output → Interview
                </p>
              </div>
              <p className="mt-2 text-xs uppercase tracking-[0.18em] text-[#888888]">
                {activeItem?.title ?? "工作流概览"}
              </p>
            </div>

            <div className="flex shrink-0 items-start gap-2 lg:hidden">
              <Button
                className="border border-[#e5e5e5]"
                onClick={() => setIsMenuOpen((current) => !current)}
                size="icon-sm"
                type="button"
                variant="ghost"
              >
                {isMenuOpen ? (
                  <X className="size-5" />
                ) : (
                  <Menu className="size-5" />
                )}
              </Button>
            </div>
          </div>

          <div className="flex flex-col gap-4 border-t border-[#e5e5e5] pt-4 lg:flex-row lg:items-start lg:justify-between">
            <nav className="hidden flex-wrap gap-2 lg:flex">
              {dashboardNavItems.map((item) => {
                const active = isItemActive(pathname, item);

                return (
                  <Link
                    key={item.href}
                    href={item.href!}
                    className={cn(
                      "inline-flex min-w-[8.5rem] items-center justify-between gap-3 border px-4 py-2 text-sm no-underline transition-colors",
                      active
                        ? "border-[#111111] bg-[#111111] text-[#fafafa]"
                        : "border-[#e5e5e5] bg-[#fafafa] text-[#111111] hover:border-[#111111] hover:bg-white",
                    )}
                  >
                    {item.title}
                    <ArrowUpRight className="size-4" />
                  </Link>
                );
              })}
            </nav>

            <div className="flex flex-col gap-3 lg:items-end">
              {user ? (
                <div className="border border-[#e5e5e5] bg-[#fafafa] px-4 py-3">
                  <p className="text-xs uppercase tracking-[0.18em] text-[#888888]">
                    当前账户
                  </p>
                  <p className="mt-2 text-sm font-medium text-[#111111]">
                    {user.nickname || "CareerPilot Member"}
                  </p>
                  <p className="mt-1 text-xs text-[#666666]">{user.email}</p>
                </div>
              ) : null}

              <Button
                disabled={isLoggingOut}
                onClick={() => void handleLogout()}
                size="sm"
                type="button"
                variant="outline"
              >
                {isLoggingOut ? "Logging out" : "Logout"}
              </Button>
            </div>
          </div>

          {isMenuOpen ? (
            <div className="border-t border-[#e5e5e5] pt-4 lg:hidden">
              <nav className="flex flex-col gap-2">
                {dashboardNavItems.map((item) => {
                  const active = isItemActive(pathname, item);

                  return (
                    <button
                      key={item.href}
                      className={cn(
                        "flex w-full items-center justify-between border px-4 py-3 text-left text-sm",
                        active
                          ? "border-[#111111] bg-[#111111] text-[#fafafa]"
                          : "border-[#e5e5e5] bg-[#fafafa] text-[#111111]",
                      )}
                      onClick={() => {
                        setIsMenuOpen(false);
                        router.push(item.href!);
                      }}
                      type="button"
                    >
                      <span>{item.title}</span>
                      <ArrowUpRight className="size-4" />
                    </button>
                  );
                })}
              </nav>
            </div>
          ) : null}
        </div>
      </div>
    </header>
  );
}
