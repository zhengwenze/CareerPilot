import { DashboardPlaceholderPage } from "@/components/dashboard/dashboard-placeholder-page";

export default function DashboardApplicationsPage() {
  return (
    <DashboardPlaceholderPage
      description="投递追踪页会承接每个岗位的投递状态、跟进动作和时间线。当前先保留顶部导航入口与干净的页面骨架，避免出现大量无实际功能的占位卡片。"
      eyebrow="Applications"
      highlights={[
        "岗位列表与投递阶段会优先做成可扫描的表格或看板视图。",
        "每条投递记录会保留最新更新时间与下一步跟进动作。",
        "HR 沟通、面试安排和复盘入口会统一收纳到同一条时间线。",
      ]}
      routeLabel="/dashboard/applications"
      title="投递追踪"
    />
  );
}
