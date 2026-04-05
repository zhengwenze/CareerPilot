"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useTransition } from "react";

import { useAuth } from "@/components/auth-provider";
import { Button } from "@/components/ui/button";
import { dashboardNavItems } from "@/config/nav-config";
import { DashboardModuleSwitcher } from "@/components/layout/dashboard-module-switcher";

export function DashboardTopNav() {
  const pathname = usePathname();
  const router = useRouter();
  const { user, logout } = useAuth();
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
      <div className="mx-auto max-w-[1360px] px-4 py-5 sm:px-6 lg:px-8">
        <div className="flex flex-col gap-4">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
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
                  Resume / Interview / Settings
                </p>
              </div>
            </div>

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

          <DashboardModuleSwitcher
            items={dashboardNavItems}
            pathname={pathname}
          />
        </div>
      </div>
    </header>
  );
}
