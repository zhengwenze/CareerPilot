import { DashboardPlaceholderPage } from "@/components/dashboard/dashboard-placeholder-page";

export default function DashboardInterviewsPage() {
  return (
    <DashboardPlaceholderPage
      description="这是模拟面试页面占位。后续可以放题库、录音记录、AI 评分和复盘建议。"
      eyebrow="Mock Interviews"
      nextSteps={[
        "整理按岗位或能力维度分类的模拟题目。",
        "加入练习记录、追问链路和 AI 点评卡片。",
        "预留录音转写和面试复盘面板。",
      ]}
      routeLabel="/dashboard/interviews"
      title="模拟面试"
    />
  );
}
