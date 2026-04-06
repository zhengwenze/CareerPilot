'use client';

import { PageErrorState } from '@/components/page-state';

export default function DashboardError({ reset }: { reset: () => void }) {
  return (
    <div className="mx-auto w-full max-w-7xl">
      <PageErrorState
        actionLabel="重新加载"
        description="当前模块加载失败"
        onAction={reset}
        title="页面加载失败"
      />
    </div>
  );
}
