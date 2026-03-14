import { DashboardPlaceholderPage } from "@/components/dashboard/dashboard-placeholder-page";

export default function DashboardProfilePage() {
  return (
    <DashboardPlaceholderPage
      description="这是个人信息页面占位。后续可以维护基础资料、求职偏好、目标城市、薪资预期和账号信息。"
      eyebrow="Profile"
      nextSteps={[
        "补充基础资料表单和头像区。",
        "增加求职意向、城市偏好和薪资区间设置。",
        "预留账户安全、通知偏好和隐私设置入口。",
      ]}
      routeLabel="/dashboard/profile"
      title="个人信息"
    />
  );
}
