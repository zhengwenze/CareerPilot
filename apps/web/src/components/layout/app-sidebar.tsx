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
    "group flex w-full items-center gap-3 rounded-2xl border border-transparent px-3 py-3 text-left transition-all duration-200",
    collapsed ? "justify-center px-2.5" : "",
    depth > 0 ? "py-2.5" : "",
    item.disabled
      ? "cursor-not-allowed opacity-55"
      : active
      ? "border-sidebar-border bg-sidebar-accent text-sidebar-accent-foreground shadow-sm"
      : "text-muted-foreground hover:border-sidebar-border/70 hover:bg-white/80 hover:text-foreground"
  );

  const itemBody = (
    <>
      <span
        className={cn(
          "flex size-10 shrink-0 items-center justify-center rounded-2xl border transition-colors",
          active
            ? "border-sidebar-primary/20 bg-sidebar-primary/12 text-sidebar-primary"
            : "border-sidebar-border/70 bg-white/75 text-muted-foreground group-hover:text-foreground"
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
            <span className="mt-0.5 block truncate text-xs text-muted-foreground">
              {item.description}
            </span>
          ) : null}
        </span>
      )}
      {!collapsed && item.badge ? (
        <Badge
          className="shrink-0 bg-primary/10 text-primary hover:bg-primary/10"
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
      <div className="border-b border-sidebar-border/70 px-4 py-4">
        <div className="flex items-center gap-3">
          <div className="flex size-11 items-center justify-center rounded-3xl bg-sidebar-primary text-sidebar-primary-foreground shadow-lg shadow-emerald-950/10">
            <PanelLeftOpen className="size-5" />
          </div>
          {!collapsed ? (
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-semibold text-foreground">
                CareerPilot
              </p>
              <p className="truncate text-xs text-muted-foreground">
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
          <div className="rounded-[28px] border border-sidebar-border/70 bg-white/80 p-4 shadow-sm">
            <Badge className="mb-3 bg-primary/10 text-primary hover:bg-primary/10">
              Dashboard Shell
            </Badge>
            <p className="text-sm font-medium text-foreground">
              左侧导航已经独立成组件，后续页面只需要填内容区。
            </p>
            {activeSection ? (
              <p className="mt-2 text-xs leading-6 text-muted-foreground">
                当前定位到「{activeSection.title}
                」分组，后续加页面时只需要补充对应路由。
              </p>
            ) : (
              <p className="mt-2 text-xs leading-6 text-muted-foreground">
                当前 dashboard 路由还在搭建中，这里已经预留好统一菜单入口。
              </p>
            )}
          </div>
        ) : null}

        {dashboardNavSections.map((section) => (
          <section className="space-y-2" key={section.title}>
            {!collapsed ? (
              <div className="px-3 text-xs font-semibold tracking-[0.18em] text-muted-foreground uppercase">
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

      <div className="border-t border-sidebar-border/70 px-3 py-3">
        <div
          className={cn(
            "rounded-[26px] border border-sidebar-border/70 bg-white/80 p-3 shadow-sm",
            collapsed ? "flex justify-center px-2 py-3" : ""
          )}
        >
          {collapsed ? (
            <Button
              aria-label="退出登录"
              className="size-10 rounded-2xl"
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
                <div className="flex size-10 items-center justify-center rounded-2xl bg-secondary text-secondary-foreground">
                  <Menu className="size-4" />
                </div>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium text-foreground">
                    {isBootstrapping
                      ? "正在恢复登录态"
                      : isAuthenticated
                      ? user?.nickname || user?.email
                      : "未登录"}
                  </p>
                  <p className="truncate text-xs text-muted-foreground">
                    {isAuthenticated
                      ? user?.email
                      : "登录后可直接进入求职工作台"}
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-2">
                <Button
                  asChild
                  className="flex-1 rounded-2xl"
                  size="sm"
                  variant="outline"
                >
                  <Link href="/">返回门户</Link>
                </Button>
                {isAuthenticated ? (
                  <Button
                    className="rounded-2xl"
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
                  <Button asChild className="rounded-2xl" size="sm">
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
        className="fixed left-4 top-4 z-30 rounded-2xl border-sidebar-border/70 bg-white/90 shadow-lg md:hidden"
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
          className="fixed inset-0 z-40 bg-foreground/18 backdrop-blur-[2px] md:hidden"
          onClick={() => setMobileOpen(false)}
          type="button"
        />
      ) : null}

      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-50 h-screen border-r border-sidebar-border/70 bg-sidebar/94 backdrop-blur-xl transition-transform duration-300 md:sticky md:top-0 md:z-20 md:translate-x-0",
          mobileOpen ? "translate-x-0" : "-translate-x-full",
          collapsed ? "w-[88px]" : "w-[296px]"
        )}
      >
        {sidebarContent}
      </aside>
    </>
  );
}
