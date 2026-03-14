import { PageLoadingState } from "@/components/page-state";

export default function DashboardLoading() {
  return (
    <div className="mx-auto w-full max-w-7xl">
      <PageLoadingState title="Dashboard 正在加载" description="我们正在准备当前模块需要的页面数据。" />
    </div>
  );
}
