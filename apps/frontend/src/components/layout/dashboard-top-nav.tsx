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
    <header className="border-b-2 border-black bg-white">
      <div className="mx-auto max-w-6xl px-4 py-4 sm:px-6">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div className="min-w-0">
            <div className="flex items-center justify-between gap-4 lg:block">
              <div>
                <Link
                  href="/dashboard/overview"
                  className="font-serif text-3xl font-bold text-black no-underline hover:text-[#0000ff]"
                >
                  CareerPilot
                </Link>
                <p className="mt-1 font-mono text-xs uppercase">
                  Resume / Matching / Optimization / Interview
                </p>
              </div>

              <Button
                className="lg:hidden"
                onClick={() => setIsMenuOpen((current) => !current)}
                size="icon-sm"
                type="button"
                variant="secondary"
              >
                {isMenuOpen ? (
                  <X className="size-4" />
                ) : (
                  <Menu className="size-4" />
                )}
              </Button>
            </div>

            <nav className="mt-4 hidden flex-col gap-2 lg:flex lg:flex-row lg:gap-2">
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
                    variant={active ? "default" : "secondary"}
                    className="font-mono text-xs hover:font-black"
                  >
                    {item.title}
                  </Button>
                );
              })}
            </nav>
          </div>

          <div className="flex flex-col gap-3 lg:items-end">
            {user ? (
              <div className="border-2 border-black px-3 py-2 font-mono text-sm">
                <p className="font-bold">
                  {user.nickname || "CareerPilot Member"}
                </p>
                <p>{user.email}</p>
              </div>
            ) : null}

            <Button
              disabled={isLoggingOut}
              onClick={() => void handleLogout()}
              size="sm"
              type="button"
              variant="secondary"
            >
              {isLoggingOut ? "LOGGING OUT" : "LOGOUT"}
            </Button>
          </div>
        </div>
      </div>
    </header>
  );
}
