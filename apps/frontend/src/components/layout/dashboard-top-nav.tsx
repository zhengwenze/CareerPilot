"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { LogOut, Menu, X } from "lucide-react";
import { useState, useTransition } from "react";

import { useAuth } from "@/components/auth-provider";
import { Button } from "@/components/ui/button";
import { dashboardNavItems, type NavItem } from "@/config/nav-config";
import { cn } from "@/lib/utils";

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
    <header className="sticky top-0 z-40 border-b-2 border-black bg-white">
      <div className="mx-auto flex w-full items-center justify-between gap-6 px-4 py-4 lg:px-8">
        <div className="flex items-center gap-5">
          <Link
            href="/dashboard/overview"
            className="font-serif text-xl font-bold tracking-[-0.03em] text-black transition-none hover:text-gray-600"
          >
            CareerPilot
          </Link>

          <nav className="hidden items-center gap-0 lg:flex">
            {dashboardNavItems.map((item) => {
              const active = isItemActive(pathname, item);

              return (
                <Link
                  key={item.href}
                  href={item.href!}
                  className={cn(
                    "border-2 border-black px-4 py-2 font-mono text-sm font-bold uppercase transition-none",
                    active
                      ? "bg-black text-white"
                      : "bg-white text-black hover:bg-gray-100"
                  )}
                >
                  {item.title}
                </Link>
              );
            })}
          </nav>
        </div>

        <div className="hidden items-center gap-4 lg:flex">
          {user ? (
            <div className="border-2 border-black bg-white px-4 py-2">
              <p className="font-mono text-sm font-bold text-black">
                {user.nickname || "CareerPilot Member"}
              </p>
              <p className="font-mono text-xs text-black">{user.email}</p>
            </div>
          ) : null}

          <Button
            onClick={() => void handleLogout()}
            size="sm"
            disabled={isLoggingOut}
            type="button"
            variant="secondary"
          >
            <LogOut className="size-4" />
            <span className="ml-2">LOGOUT</span>
          </Button>
        </div>

        <div className="lg:hidden">
          <Button
            onClick={() => setIsMenuOpen(!isMenuOpen)}
            size="icon-sm"
            type="button"
            variant="secondary"
          >
            {isMenuOpen ? <X className="size-4" /> : <Menu className="size-4" />}
          </Button>
        </div>
      </div>

      {isMenuOpen && (
        <div className="border-t-2 border-black lg:hidden">
          <div className="bg-white p-4">
            <nav className="space-y-2">
              {dashboardNavItems.map((item) => {
                const active = isItemActive(pathname, item);

                return (
                  <Link
                    key={item.href}
                    href={item.href!}
                    onClick={() => setIsMenuOpen(false)}
                    className={cn(
                      "block border-2 border-black px-4 py-3 font-mono text-sm font-bold uppercase transition-none",
                      active
                        ? "bg-black text-white"
                        : "bg-white text-black hover:bg-gray-100"
                    )}
                  >
                    {item.title}
                  </Link>
                );
              })}
            </nav>

            {user && (
              <div className="mt-4 border-t-2 border-black pt-4">
                <div className="mb-4 border-2 border-black bg-white px-4 py-2">
                  <p className="font-mono text-sm font-bold text-black">
                    {user.nickname || "CareerPilot Member"}
                  </p>
                  <p className="font-mono text-xs text-black">{user.email}</p>
                </div>
                <Button
                  onClick={() => void handleLogout()}
                  size="sm"
                  className="w-full"
                  disabled={isLoggingOut}
                  type="button"
                  variant="secondary"
                >
                  <LogOut className="size-4" />
                  <span className="ml-2">LOGOUT</span>
                </Button>
              </div>
            )}
          </div>
        </div>
      )}
    </header>
  );
}
