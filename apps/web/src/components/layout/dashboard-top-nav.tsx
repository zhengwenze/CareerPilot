"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { LogOut, Menu, X } from "lucide-react";
import { useState, useTransition } from "react";

import { useAuth } from "@/components/auth-provider";
import { Button } from "@/components/ui/button";
import { dashboardNavSections, type NavItem } from "@/config/nav-config";
import { cn } from "@/lib/utils";

const dashboardNavItems = dashboardNavSections
  .flatMap((section) => section.items)
  .filter((item) => item.href && !item.disabled);

function isItemActive(pathname: string, item: NavItem): boolean {
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

  async function handleLogout() {
    await logout();
    startTransition(() => {
      router.push("/login");
      router.refresh();
    });
  }

  return (
    <header className="sticky top-0 z-40 border-b border-black/8 bg-white/95 backdrop-blur-xl">
      <div className="mx-auto flex w-full max-w-7xl items-center justify-between gap-6 px-6 py-5 lg:px-10">
        <div className="flex items-center gap-5">
          <Link
            href="/dashboard/overview"
            className="text-lg font-semibold tracking-[-0.03em] text-black transition-opacity hover:opacity-65"
          >
            CareerPilot
          </Link>

          <nav className="hidden items-center gap-2 lg:flex">
            {dashboardNavItems.map((item) => {
              const active = isItemActive(pathname, item);

              return (
                <Link
                  key={item.href}
                  href={item.href!}
                  className={cn(
                    "rounded-full px-4 py-2 text-sm font-medium text-black transition-colors",
                    active
                      ? "bg-[#0071E3] text-white hover:bg-[#0077ED]"
                      : "hover:bg-[#f5f5f7]"
                  )}
                >
                  {item.title}
                </Link>
              );
            })}
          </nav>
        </div>

        <div className="hidden items-center gap-3 lg:flex">
          <div className="text-right">
            <p className="text-sm font-medium text-black">
              {user?.nickname || "CareerPilot Member"}
            </p>
            <p className="text-xs text-black/55">{user?.email}</p>
          </div>

          <Button
            asChild
            variant="outline"
            className="h-10 rounded-full border-black/10 bg-white px-5 text-black hover:bg-[#f5f5f7]"
          >
            <Link href="/">返回门户</Link>
          </Button>

          <Button
            className="h-10 rounded-full bg-[#0071E3] px-5 text-white hover:bg-[#0077ED]"
            disabled={isLoggingOut}
            onClick={() => void handleLogout()}
            type="button"
          >
            {isLoggingOut ? "退出中..." : "退出"}
            <LogOut className="size-4" />
          </Button>
        </div>

        <Button
          className="size-10 rounded-full border-black/10 bg-white text-black hover:bg-[#f5f5f7] lg:hidden"
          onClick={() => setIsMenuOpen((current) => !current)}
          type="button"
          variant="outline"
        >
          {isMenuOpen ? <X className="size-4" /> : <Menu className="size-4" />}
        </Button>
      </div>

      {isMenuOpen ? (
        <div className="border-t border-black/8 bg-white px-6 pb-5 pt-4 lg:hidden">
          <div className="space-y-3">
            {dashboardNavItems.map((item) => {
              const active = isItemActive(pathname, item);

              return (
                <Link
                  key={item.href}
                  href={item.href!}
                  className={cn(
                    "block rounded-3xl px-4 py-3 text-sm font-medium text-black transition-colors",
                    active
                      ? "bg-[#0071E3] text-white"
                      : "bg-[#f5f5f7] hover:bg-[#ebebed]"
                  )}
                  onClick={() => setIsMenuOpen(false)}
                >
                  {item.title}
                </Link>
              );
            })}
          </div>

          <div className="mt-5 rounded-[1.75rem] border border-black/10 bg-[#f5f5f7] p-4">
            <p className="text-sm font-medium text-black">
              {user?.nickname || "CareerPilot Member"}
            </p>
            <p className="mt-1 text-xs text-black/55">{user?.email}</p>

            <div className="mt-4 flex gap-3">
              <Button
                asChild
                variant="outline"
                className="flex-1 rounded-full border-black/10 bg-white text-black hover:bg-white"
              >
                <Link href="/">返回门户</Link>
              </Button>
              <Button
                className="flex-1 rounded-full bg-[#0071E3] text-white hover:bg-[#0077ED]"
                disabled={isLoggingOut}
                onClick={() => void handleLogout()}
                type="button"
              >
                {isLoggingOut ? "退出中..." : "退出"}
              </Button>
            </div>
          </div>
        </div>
      ) : null}
    </header>
  );
}
