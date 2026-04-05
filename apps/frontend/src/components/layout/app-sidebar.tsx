"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useState, useTransition } from "react";
import { LogOut, Menu, PanelLeftClose, PanelLeftOpen, X } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/components/auth-provider";
import { dashboardNavSections, type NavItem } from "@/config/nav-config";
import { cn } from "@/lib/utils";

function isItemActive(pathname: string, item: NavItem): boolean {
  if (item.href) {
    const matchMode = item.match ?? "exact";

    if (matchMode === "exact" && pathname === item.href) {
      return true;
    }

    if (
      matchMode === "prefix" &&
      (pathname === item.href || pathname.startsWith(`${item.href}/`))
    ) {
      return true;
    }
  }

  return item.children?.some((child) => isItemActive(pathname, child)) ?? false;
}

function SidebarNavItem({
  item,
  collapsed,
  pathname,
  onNavigate,
  depth = 0,
}: {
  item: NavItem;
  collapsed: boolean;
  pathname: string;
  onNavigate: () => void;
  depth?: number;
}) {
  const active = isItemActive(pathname, item);
  const Icon = item.icon;
  const hasChildren = Boolean(item.children?.length);

  const itemClassName = cn(
    "group flex w-full items-center gap-3 border-2 border-black px-3 py-3 text-left font-mono text-sm transition-none",
    collapsed ? "justify-center px-2" : "",
    depth > 0 ? "py-2" : "",
    item.disabled
      ? "cursor-not-allowed opacity-55"
      : active
        ? "bg-black text-white"
        : "bg-white text-black hover:bg-gray-100",
  );

  const itemBody = (
    <>
      <span
        className={cn(
          "flex size-10 shrink-0 items-center justify-center border-2 border-black font-mono text-sm",
          active ? "bg-white text-black" : "bg-white text-black",
        )}
      >
        <Icon className="size-4" />
      </span>
      {!collapsed && (
        <span className="min-w-0 flex-1">
          <span className="block truncate font-mono text-sm font-bold uppercase">
            {item.title}
          </span>
          {item.description ? (
            <span className="mt-0.5 block truncate font-mono text-xs">
              {item.description}
            </span>
          ) : null}
        </span>
      )}
      {!collapsed && item.badge ? (
        <Badge className="shrink-0 bg-black text-white" variant="default">
          {item.badge}
        </Badge>
      ) : null}
    </>
  );

  return (
    <div className="space-y-2">
      {item.href && !item.disabled ? (
        <Link className={itemClassName} href={item.href} onClick={onNavigate}>
          {itemBody}
        </Link>
      ) : (
        <div
          aria-disabled={item.disabled}
          className={cn(itemClassName, hasChildren ? "cursor-default" : "")}
        >
          {itemBody}
        </div>
      )}

      {!collapsed && hasChildren ? (
        <div className="space-y-1.5 pl-4">
          {item.children?.map((child) => (
            <SidebarNavItem
              collapsed={collapsed}
              depth={depth + 1}
              item={child}
              key={`${item.title}-${child.title}`}
              onNavigate={onNavigate}
              pathname={pathname}
            />
          ))}
        </div>
      ) : null}
    </div>
  );
}

export function AppSidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const { user, logout } = useAuth();
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [, startTransition] = useTransition();

  async function handleLogout() {
    await logout();
    startTransition(() => {
      router.push("/login");
      router.refresh();
    });
  }

  const sidebarContent = (
    <div className="flex h-full flex-col bg-white font-mono">
      <div className="border-b-2 border-black px-4 py-4">
        <div className="flex items-center gap-3">
          <div className="flex size-10 items-center justify-center border-2 border-black bg-black text-white">
            <PanelLeftOpen className="size-4" />
          </div>
          {!collapsed ? (
            <div className="min-w-0 flex-1">
              <p className="truncate font-serif text-lg font-bold text-black">
                CareerPilot
              </p>
              <p className="truncate font-mono text-xs text-black">
                AI 求职工作台
              </p>
            </div>
          ) : null}
          <Button
            className="hidden md:inline-flex"
            onClick={() => setCollapsed((value) => !value)}
            size="icon-sm"
            type="button"
            variant="secondary"
          >
            {collapsed ? (
              <PanelLeftOpen className="size-4" />
            ) : (
              <PanelLeftClose className="size-4" />
            )}
          </Button>
          <Button
            className="md:hidden"
            onClick={() => setMobileOpen(false)}
            size="icon-sm"
            type="button"
            variant="secondary"
          >
            <X className="size-4" />
          </Button>
        </div>
      </div>

      <div className="flex-1 space-y-6 overflow-y-auto border-r-2 border-black px-3 py-4">
        {dashboardNavSections.map((section) => (
          <div key={section.title} className="space-y-2">
            {!collapsed && (
              <div className="border-b-2 border-black pb-2">
                <span className="font-mono text-xs font-bold uppercase tracking-widest text-black">
                  {section.title}
                </span>
              </div>
            )}
            {section.items.map((item) => (
              <SidebarNavItem
                collapsed={collapsed}
                item={item}
                key={item.title}
                onNavigate={() => setMobileOpen(false)}
                pathname={pathname}
              />
            ))}
          </div>
        ))}
      </div>

      <div className="border-t-2 border-black p-4">
        {!collapsed && user ? (
          <div className="mb-4 border-b-2 border-black pb-4">
            <p className="font-mono text-sm font-bold text-black">
              {user.nickname || "CareerPilot Member"}
            </p>
            <p className="font-mono text-xs text-black">{user.email}</p>
          </div>
        ) : null}
        <Button
          className="w-full"
          onClick={() => void handleLogout()}
          size="sm"
          type="button"
          variant="secondary"
        >
          <LogOut className="size-4" />
          {!collapsed && <span className="ml-2">LOGOUT</span>}
        </Button>
      </div>
    </div>
  );

  if (mobileOpen) {
    return (
      <div className="fixed inset-0 z-50 bg-white">
        <div className="flex items-center justify-between border-b-2 border-black px-4 py-4">
          <span className="font-serif text-xl font-bold text-black">
            CareerPilot
          </span>
          <Button
            onClick={() => setMobileOpen(false)}
            size="icon-sm"
            type="button"
            variant="secondary"
          >
            <X className="size-4" />
          </Button>
        </div>
        <div className="p-4">{sidebarContent}</div>
      </div>
    );
  }

  return (
    <>
      <div className="hidden md:block">
        <div
          className={cn(
            "h-screen border-r-2 border-black transition-all duration-0",
            collapsed ? "w-16" : "w-64",
          )}
        >
          {sidebarContent}
        </div>
      </div>

      <div className="fixed bottom-4 left-4 z-50 md:hidden">
        <Button
          onClick={() => setMobileOpen(true)}
          size="icon-lg"
          type="button"
          variant="primary"
        >
          <Menu className="size-5" />
        </Button>
      </div>
    </>
  );
}
