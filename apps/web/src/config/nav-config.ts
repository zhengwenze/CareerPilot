import type { LucideIcon } from "lucide-react";
import {
  BriefcaseBusiness,
  FileText,
  LayoutDashboard,
  Settings,
  Sparkles,
  Target,
} from "lucide-react";

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
    title: "总览",
    items: [
      {
        title: "概览",
        href: "/dashboard/overview",
        icon: LayoutDashboard,
        match: "exact",
      },
    ],
  },
  {
    title: "流程",
    items: [
      {
        title: "简历中心",
        href: "/dashboard/resume",
        icon: FileText,
        match: "prefix",
      },
      {
        title: "岗位匹配",
        href: "/dashboard/jobs",
        icon: Target,
        match: "prefix",
      },
      {
        title: "投递追踪",
        href: "/dashboard/applications",
        icon: BriefcaseBusiness,
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
        title: "个人信息",
        href: "/dashboard/profile",
        icon: Settings,
        match: "prefix",
      },
    ],
  },
];
