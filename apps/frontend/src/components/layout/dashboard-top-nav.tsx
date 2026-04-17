'use client';
import Link from 'next/link';
import Image from 'next/image';
import { usePathname, useRouter } from 'next/navigation';
import { useTransition } from 'react';
import { useAuth } from '@/components/auth-provider';
import { DashboardModuleSwitcher } from '@/components/layout/dashboard-module-switcher';
import { TopBarSearch } from '@/components/layout/top-bar-search';
import { Button } from '@/components/ui/button';
import { dashboardNavItems } from '@/config/nav-config';
import logoImage from '@/images/logo.png';
import { cn } from '@/lib/utils';

export function DashboardTopNav() {
  const pathname = usePathname();
  const router = useRouter();
  const { user, logout } = useAuth();
  const [isLoggingOut, startTransition] = useTransition();

  async function handleLogout() {
    await logout();
    startTransition(() => {
      router.push('/login');
      router.refresh();
    });
  }

  return (
    <header className="border-b border-[#e5e5e5] bg-white">
      <div className="mx-auto max-w-[1360px] py-px px-4 sm:px-6 lg:px-8">
        <div className="bw-topbar">
          <Link href="/dashboard/overview" className="bw-topbar-brand">
            <Image
              alt="CareerPilot Logo"
              className="bw-topbar-brand-logo"
              height={42}
              priority
              sizes="(max-width: 640px) 168px, 220px"
              src={logoImage}
              width={220}
            />
          </Link>

          <DashboardModuleSwitcher items={dashboardNavItems} pathname={pathname} />

          <TopBarSearch />

          <div className="bw-topbar-actions">
            <div className={cn('bw-topbar-account', !user && 'px-2')}>
              {user ? (
                <span className="bw-topbar-user">{user.nickname || 'CareerPilot Member'}</span>
              ) : null}

              <Button
                aria-busy={isLoggingOut}
                className={cn(
                  'bw-topbar-logout !text-red-600 hover:!text-red-700',
                  !user && 'bw-topbar-logout-solo'
                )}
                disabled={isLoggingOut}
                onClick={() => void handleLogout()}
                size="sm"
                type="button"
                variant="ghost"
              >
                {isLoggingOut ? '退出中' : '退出'}
              </Button>
            </div>
          </div>
        </div>
      </div>
    </header>
  );
}
