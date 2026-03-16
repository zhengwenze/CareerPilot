import { DashboardPlaceholderPage } from "@/components/dashboard/dashboard-placeholder-page";

export default function DashboardInterviewsPage() {
  return (
    <DashboardPlaceholderPage
      description="模拟面试页会承接练习题、录音与复盘。当前先统一页面风格和导航结构，把噪音减掉，后续接入真实能力时不需要再重做壳层。"
      eyebrow="Mock Interviews"
      highlights={[
        "题目会按岗位方向和能力维度组织，保持入口清晰。",
        "练习记录、追问链路和 AI 点评会收成同一条练习会话。",
        "录音转写与复盘建议会作为主内容区的一部分，而不是额外装饰。",
      ]}
      routeLabel="/dashboard/interviews"
      title="模拟面试"
    />
  );
}
