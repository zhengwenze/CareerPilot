import { DashboardPlaceholderPage } from "@/components/dashboard/dashboard-placeholder-page";

export default function DashboardApplicationsPage() {
  return (
    <DashboardPlaceholderPage
      description="这是投递追踪页面占位。后续适合放投递进度、阶段状态、联系人记录和待办提醒。"
      eyebrow="Applications"
      nextSteps={[
        "先搭一个投递阶段看板或者表格视图。",
        "增加每个岗位的状态流转和更新时间。",
        "预留 HR 沟通记录、面试安排和复盘入口。",
      ]}
      routeLabel="/dashboard/applications"
      title="投递追踪"
    />
  );
}
