"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

import { PageLoadingState } from "@/components/page-state";
import { useAuth } from "@/components/auth-provider";

const DASHBOARD_ENTRY_PATH = "/dashboard/overview";

export function GuestRoute({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const { isAuthenticated, isBootstrapping } = useAuth();

  useEffect(() => {
    if (isBootstrapping || !isAuthenticated) {
      return;
    }

    router.replace(DASHBOARD_ENTRY_PATH);
  }, [isAuthenticated, isBootstrapping, router]);

  if (isBootstrapping) {
    return <PageLoadingState title="正在恢复登录态" description="请稍候，我们正在检查你的会话状态。" />;
  }

  if (isAuthenticated) {
    return null;
  }

  return <>{children}</>;
}
