'use client';
import Link from 'next/link';
import { type NavItem } from '@/config/nav-config';
import { cn } from '@/lib/utils';

function isItemActive(pathname: string, item: NavItem) {
  if (!item.href) {
    return false;
  }

  const matchMode = item.match ?? 'exact';
  if (matchMode === 'exact') {
    return pathname === item.href;
  }

  return pathname === item.href || pathname.startsWith(`${item.href}/`);
}

export function DashboardModuleSwitcher({
  items,
  pathname,
  className,
}: {
  items: NavItem[];
  pathname: string;
  className?: string;
}) {
  return (
    <nav aria-label="Primary" className={cn('bw-topbar-nav', className)}>
      {items.map(item => {
        const active = isItemActive(pathname, item);

        if (!item.href && !item.externalHref) {
          return null;
        }

        if (item.externalHref) {
          return (
            <a
              key={item.externalHref}
              href={item.externalHref}
              target="_blank"
              rel="noopener noreferrer"
              className="bw-topbar-link"
            >
              {item.title}
            </a>
          );
        }

        return (
          <Link
            key={item.href}
            href={item.href!}
            aria-current={active ? 'page' : undefined}
            aria-disabled={item.disabled ? 'true' : undefined}
            className="bw-topbar-link"
          >
            {item.title}
          </Link>
        );
      })}
    </nav>
  );
}
