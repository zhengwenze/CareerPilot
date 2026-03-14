import { DashboardPlaceholderPage } from "@/components/dashboard/dashboard-placeholder-page";

export default function DashboardResumePage() {
  return (
    <DashboardPlaceholderPage
      description="这是简历中心页面占位。后面可以在这里管理多份简历版本、岗位定制版、附件素材和 AI 优化建议。"
      eyebrow="Resume Center"
      nextSteps={[
        "放入简历列表和版本管理卡片。",
        "预留上传入口、解析状态和 AI 优化结果区域。",
        "给每份简历增加对应岗位标签和最近更新时间。",
      ]}
      routeLabel="/dashboard/resume"
      title="简历中心"
    />
  );
}
