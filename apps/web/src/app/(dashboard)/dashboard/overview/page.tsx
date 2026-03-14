import { DashboardPlaceholderPage } from "@/components/dashboard/dashboard-placeholder-page";

export default function DashboardOverviewPage() {
  return (
    <DashboardPlaceholderPage
      description="这是 CareerPilot 工作台的总览占位页。后续可以在这里汇总简历完成度、岗位匹配结果、投递进度和近期面试提醒。"
      eyebrow="Overview"
      nextSteps={[
        "补一组总览 KPI 卡片，例如岗位匹配数、投递中岗位数、待跟进事项。",
        "接入最近活动时间线，串起简历修改、岗位收藏和面试安排。",
        "预留 AI 助手入口，让首页成为整个求职流程的导航中心。",
      ]}
      routeLabel="/dashboard/overview"
      title="工作台概览"
    />
  );
}
