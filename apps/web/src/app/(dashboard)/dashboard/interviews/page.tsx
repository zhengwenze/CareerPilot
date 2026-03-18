import { DashboardPlaceholderPage } from "@/components/dashboard/dashboard-placeholder-page";

export default async function DashboardInterviewsPage({
  searchParams,
}: {
  searchParams: Promise<{
    jobId?: string;
    reportId?: string;
  }>;
}) {
  const params = await searchParams;
  const launchedFromMatch = Boolean(params.jobId || params.reportId);
  return (
    <DashboardPlaceholderPage
      description={
        launchedFromMatch
          ? "模拟面试功能暂未开放。你从岗位工作台带来的上下文已记录，待前三模块闭环稳定后再接入真实训练能力。"
          : "模拟面试功能暂未开放。当前阶段只优先保障“简历解析->岗位匹配->简历优化”的高效闭环。"
      }
      eyebrow="Mock Interviews"
      highlights={[
        launchedFromMatch
          ? `已接收上下文：jobId=${params.jobId ?? "unknown"} / reportId=${params.reportId ?? "unknown"}`
          : "你可以先在岗位匹配与简历优化完成本轮求职准备。",
        "该页面保留入口，避免后续上线时改动导航结构。",
        "上线条件：前三模块闭环稳定、关键流程可重复通过。",
      ]}
      routeLabel="/dashboard/interviews"
      title="模拟面试"
    />
  );
}
