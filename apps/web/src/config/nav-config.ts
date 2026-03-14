import type { LucideIcon } from "lucide-react";
import {
  BriefcaseBusiness,
  FileText,
  LayoutDashboard,
  Rocket,
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
    title: "工作台总览",
    items: [
      {
        title: "概览",
        href: "/dashboard/overview",
        icon: LayoutDashboard,
        description: "查看 AI 求职工作台的核心进度与提醒。",
        badge: "New",
        match: "exact",
      },
    ],
  },
  {
    title: "求职流程",
    items: [
      {
        title: "简历中心",
        href: "/dashboard/resume",
        icon: FileText,
        description: "管理简历版本、投递素材和优化记录。",
        match: "prefix",
      },
      {
        title: "岗位匹配",
        href: "/dashboard/jobs",
        icon: Target,
        description: "浏览岗位线索与匹配评分。",
        match: "prefix",
      },
      {
        title: "投递追踪",
        href: "/dashboard/applications",
        icon: BriefcaseBusiness,
        description: "跟踪各个岗位的投递阶段与反馈。",
        match: "prefix",
      },
      {
        title: "模拟面试",
        href: "/dashboard/interviews",
        icon: Sparkles,
        description: "沉淀面试问题、复盘记录和 AI 反馈。",
        match: "prefix",
      },
    ],
  },
  {
    title: "系统设置",
    items: [
      {
        title: "个人信息",
        href: "/dashboard/profile",
        icon: Settings,
        description: "维护你的基础资料、求职偏好和账户信息。",
        match: "prefix",
      },
      {
        title: "能力扩展",
        href: "/dashboard/labs",
        icon: Rocket,
        description: "预留给后续 AI 功能实验区。",
        badge: "规划中",
        match: "prefix",
        disabled: true,
      },
    ],
  },
];
