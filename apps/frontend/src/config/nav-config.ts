import type { LucideIcon } from 'lucide-react';
import { ExternalLink, FileText, LayoutDashboard, Settings, Sparkles, User } from 'lucide-react';

export type NavMatchMode = 'exact' | 'prefix';

export type NavItem = {
  title: string;
  href?: string;
  externalHref?: string;
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
    title: '流程',
    items: [
      {
        title: '概览',
        href: '/dashboard/overview',
        icon: LayoutDashboard,
        match: 'exact',
      },
      {
        title: '简历',
        href: '/dashboard/resume',
        icon: FileText,
        match: 'prefix',
      },
      {
        title: '面试',
        href: '/dashboard/interviews',
        icon: Sparkles,
        match: 'prefix',
      },
    ],
  },
  {
    title: '账户',
    items: [
      {
        title: '我的',
        href: '/dashboard/profile',
        icon: User,
        match: 'exact',
      },
    ],
  },
  {
    title: '设置',
    items: [
      {
        title: '设置',
        href: '/dashboard/setting',
        icon: Settings,
        match: 'prefix',
      },
    ],
  },
  {
    title: '外部',
    items: [
      {
        title: 'GitHub',
        externalHref: 'https://github.com/zhengwenze/CareerPilot',
        icon: ExternalLink,
      },
    ],
  },
] as const;

export const dashboardNavItems: NavItem[] = dashboardNavSections
  .flatMap(section => section.items)
  .filter(
    (item): item is NavItem => (Boolean(item.href) || Boolean(item.externalHref)) && !item.disabled
  );
