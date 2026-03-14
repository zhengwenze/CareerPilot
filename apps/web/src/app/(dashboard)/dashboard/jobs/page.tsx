import { DashboardPlaceholderPage } from "@/components/dashboard/dashboard-placeholder-page";

export default function DashboardJobsPage() {
  return (
    <DashboardPlaceholderPage
      description="这是岗位匹配页面占位。后续可以承接职位推荐、JD 收藏、匹配评分和筛选条件。"
      eyebrow="Job Matching"
      nextSteps={[
        "接入岗位卡片列表和筛选栏。",
        "增加匹配分数、技能差距和来源渠道展示。",
        "预留收藏、忽略和转投递的操作区。",
      ]}
      routeLabel="/dashboard/jobs"
      title="岗位匹配"
    />
  );
}
