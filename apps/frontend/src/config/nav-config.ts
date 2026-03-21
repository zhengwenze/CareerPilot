import type { LucideIcon } from "lucide-react";
import { FileText, Settings, Sparkles } from "lucide-react";

export type NavMatchMode = "exact" | "prefix";

export type NavItem = {
  title: string;
  href?: string;
  icon: LucideIcon;
  description?: string;
  badge?: string | number;
  match?: NavMatchMode;
  disabled?: boolean;
  children?: NavItem[];
};

export type NavSection = {
  title: string;
  items: NavItem[];
};

export const dashboardNavSections: NavSection[] = [
  {
    title: "流程",
    items: [
      {
        title: "专属简历",
        href: "/dashboard/resume",
        icon: FileText,
        match: "prefix",
      },
      {
        title: "模拟面试",
        href: "/dashboard/interviews",
        icon: Sparkles,
        match: "prefix",
      },
    ],
  },
  {
    title: "设置",
    items: [
      {
        title: "设置",
        href: "/dashboard/setting",
        icon: Settings,
        match: "prefix",
      },
    ],
  },
] as const;

export const dashboardNavItems: NavItem[] = dashboardNavSections
  .flatMap((section) => section.items)
  .filter((item): item is NavItem => Boolean(item.href) && !item.disabled);
