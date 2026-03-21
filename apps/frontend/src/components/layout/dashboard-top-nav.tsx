"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { Menu, X } from "lucide-react";
import { useState, useTransition } from "react";

import { useAuth } from "@/components/auth-provider";
import { Button } from "@/components/ui/button";
import { dashboardNavItems, type NavItem } from "@/config/nav-config";

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

  async function handleLogout() {
    await logout();
    startTransition(() => {
      router.push("/login");
      router.refresh();
    });
  }

  return (
    <header className="border-b border-[#e5e5e5] bg-white">
      <div className="mx-auto max-w-6xl px-4 py-4 sm:px-6">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div className="min-w-0">
            <div className="flex items-center justify-between gap-4 lg:block">
              <div>
                <Link
                  href="/dashboard/resume"
                  className="text-2xl font-semibold text-[#111111] no-underline hover:text-[#666666]"
                  style={{ fontFamily: "var(--font-heading)", letterSpacing: "-0.02em" }}
                >
                  CareerPilot
                </Link>
                <p className="mt-1 text-xs text-[#666666]">
                  Tailored Resume / Interview
                </p>
              </div>

              <Button
                className="lg:hidden"
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

            <nav className="mt-4 hidden flex-col gap-1 lg:flex lg:flex-row lg:gap-1">
              {dashboardNavItems.map((item) => {
                const active = isItemActive(pathname, item);

                return (
                  <Button
                    key={item.href}
                    onClick={() => {
                      setIsMenuOpen(false);
                      router.push(item.href!);
                    }}
                    size="sm"
                    type="button"
                    variant={active ? "default" : "ghost"}
                    className="text-xs"
                  >
                    {item.title}
                  </Button>
                );
              })}
            </nav>
          </div>

          <div className="flex flex-col gap-3 lg:items-end">
            {user ? (
              <div className="px-3 py-2">
                <p className="text-sm font-medium text-[#111111]">
                  {user.nickname || "CareerPilot Member"}
                </p>
                <p className="text-xs text-[#666666]">{user.email}</p>
              </div>
            ) : null}

            <Button
              disabled={isLoggingOut}
              onClick={() => void handleLogout()}
              size="sm"
              type="button"
              variant="ghost"
            >
              {isLoggingOut ? "Logging out" : "Logout"}
            </Button>
          </div>
        </div>
      </div>
    </header>
  );
}
