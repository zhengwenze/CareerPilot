"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useMemo, useState, useTransition } from "react";
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
    "group flex w-full items-center gap-3 border border-transparent px-3 py-3 text-left transition-all duration-200",
    collapsed ? "justify-center px-2.5" : "",
    depth > 0 ? "py-2.5" : "",
    item.disabled
      ? "cursor-not-allowed opacity-55"
      : active
      ? "border-[#1C1C1C]/10 bg-[#F9F8F6] text-[#1C1C1C]"
      : "text-[#1C1C1C]/60 hover:border-[#1C1C1C]/10 hover:bg-[#1C1C1C]/[0.02] hover:text-[#1C1C1C]"
  );

  const itemBody = (
    <>
      <span
        className={cn(
          "flex size-10 shrink-0 items-center justify-center border transition-colors",
          active
            ? "border-[#1C1C1C]/20 bg-[#1C1C1C]/[0.05] text-[#1C1C1C]"
            : "border-[#1C1C1C]/10 bg-[#F9F8F6] text-[#1C1C1C]/60 group-hover:text-[#1C1C1C]"
        )}
      >
        <Icon className="size-4.5" />
      </span>
      {!collapsed && (
        <span className="min-w-0 flex-1">
          <span className="block truncate text-sm font-medium">
            {item.title}
          </span>
          {item.description ? (
            <span className="mt-0.5 block truncate text-xs text-[#1C1C1C]/60">
              {item.description}
            </span>
          ) : null}
        </span>
      )}
      {!collapsed && item.badge ? (
        <Badge
          className="shrink-0 bg-[#1C1C1C]/10 text-[#1C1C1C] hover:bg-[#1C1C1C]/10"
          variant="secondary"
        >
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
  const { user, isAuthenticated, isBootstrapping, logout } = useAuth();
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [isLoggingOut, startTransition] = useTransition();

  const activeSection = useMemo(() => {
    return dashboardNavSections.find((section) =>
      section.items.some((item) => isItemActive(pathname, item))
    );
  }, [pathname]);

  async function handleLogout() {
    await logout();
    startTransition(() => {
      router.push("/login");
      router.refresh();
    });
  }

  const sidebarContent = (
    <div className="flex h-full flex-col">
      <div className="border-b border-[#1C1C1C]/10 px-4 py-4">
        <div className="flex items-center gap-3">
          <div className="flex size-11 items-center justify-center border border-[#1C1C1C]/20 bg-[#1C1C1C] text-[#F9F8F6]">
            <PanelLeftOpen className="size-5" />
          </div>
          {!collapsed ? (
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-semibold text-[#1C1C1C]">
                CareerPilot
              </p>
              <p className="truncate text-xs text-[#1C1C1C]/60">
                AI 求职工作台
              </p>
            </div>
          ) : null}
          <Button
            className="hidden md:inline-flex"
            onClick={() => setCollapsed((value) => !value)}
            size="icon-sm"
            type="button"
            variant="ghost"
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
            variant="ghost"
          >
            <X className="size-4" />
          </Button>
        </div>
      </div>

      <div className="flex-1 space-y-6 overflow-y-auto px-3 py-4">
        {!collapsed ? (
          <div className="border border-[#1C1C1C]/10 bg-[#F9F8F6] p-4">
            <Badge className="mb-3 bg-[#1C1C1C]/10 text-[#1C1C1C] hover:bg-[#1C1C1C]/10">
              Dashboard Shell
            </Badge>
            <p className="text-sm font-medium text-[#1C1C1C]">
              左侧导航已经独立成组件，后续页面只需要填内容区。
            </p>
            {activeSection ? (
              <p className="mt-2 text-xs leading-6 text-[#1C1C1C]/60">
                当前定位到「{activeSection.title}
                」分组，后续加页面时只需要补充对应路由。
              </p>
            ) : (
              <p className="mt-2 text-xs leading-6 text-[#1C1C1C]/60">
                当前 dashboard 路由还在搭建中，这里已经预留好统一菜单入口。
              </p>
            )}
          </div>
        ) : null}

        {dashboardNavSections.map((section) => (
          <section className="space-y-2" key={section.title}>
            {!collapsed ? (
              <div className="px-3 text-xs font-semibold tracking-[0.18em] text-[#1C1C1C]/60 uppercase">
                {section.title}
              </div>
            ) : null}
            <div className="space-y-2">
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
          </section>
        ))}
      </div>

      <div className="border-t border-[#1C1C1C]/10 px-3 py-3">
        <div
          className={cn(
            "border border-[#1C1C1C]/10 bg-[#F9F8F6] p-3",
            collapsed ? "flex justify-center px-2 py-3" : ""
          )}
        >
          {collapsed ? (
            <Button
              aria-label="退出登录"
              className="size-10"
              disabled={isLoggingOut}
              onClick={() => void handleLogout()}
              size="icon"
              type="button"
              variant="outline"
            >
              <LogOut className="size-4" />
            </Button>
          ) : (
            <div className="space-y-3">
              <div className="flex items-center gap-3">
                <div className="flex size-10 items-center justify-center border border-[#1C1C1C]/10 bg-[#F9F8F6] text-[#1C1C1C]">
                  <Menu className="size-4" />
                </div>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium text-[#1C1C1C]">
                    {isBootstrapping
                      ? "正在恢复登录态"
                      : isAuthenticated
                      ? user?.nickname || user?.email
                      : "未登录"}
                  </p>
                  <p className="truncate text-xs text-[#1C1C1C]/60">
                    {isAuthenticated
                      ? user?.email
                      : "登录后可直接进入求职工作台"}
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-2">
                <Button
                  asChild
                  className="flex-1"
                  size="sm"
                  variant="outline"
                >
                  <Link href="/">返回门户</Link>
                </Button>
                {isAuthenticated ? (
                  <Button
                    className=""
                    disabled={isLoggingOut}
                    onClick={() => void handleLogout()}
                    size="sm"
                    type="button"
                    variant="ghost"
                  >
                    {isLoggingOut ? "退出中" : "退出"}
                    <LogOut className="size-4" />
                  </Button>
                ) : (
                  <Button asChild className="" size="sm">
                    <Link href="/login">去登录</Link>
                  </Button>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );

  return (
    <>
      <Button
        className="fixed left-4 top-4 z-30 border-[#1C1C1C]/20 bg-white/90 md:hidden"
        onClick={() => setMobileOpen(true)}
        size="icon"
        type="button"
        variant="outline"
      >
        <Menu className="size-4" />
      </Button>

      {mobileOpen ? (
        <button
          aria-label="关闭侧边栏蒙层"
          className="fixed inset-0 z-40 bg-[#1C1C1C]/10 md:hidden"
          onClick={() => setMobileOpen(false)}
          type="button"
        />
      ) : null}

      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-50 h-screen border-r border-[#1C1C1C]/10 bg-[#F9F8F6]/95 backdrop-blur transition-transform duration-300 md:sticky md:top-0 md:z-20 md:translate-x-0",
          mobileOpen ? "translate-x-0" : "-translate-x-full",
          collapsed ? "w-[88px]" : "w-[296px]"
        )}
      >
        {sidebarContent}
      </aside>
    </>
  );
}