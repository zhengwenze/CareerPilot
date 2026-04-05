import {
  MetaChip,
  PageHeader,
  PageShell,
  PaperSection,
} from "@/components/brutalist/page-shell";

const flowSteps = [
  { label: "Module", value: "设置" },
  { label: "Focus", value: "账户" },
  { label: "State", value: "占位页" },
  { label: "Style", value: "Monochrome" },
];

export default function DashboardSettingPage() {
  return (
    <PageShell className="gap-8 py-4 md:py-6">
      <PageHeader
        eyebrow="Settings"
        title="设置"
        description="查看账户与工作台状态。"
        meta={
          <>
            <MetaChip>Account</MetaChip>
            <MetaChip>Workspace</MetaChip>
          </>
        }
      >
        <div className="bw-flow-strip">
          {flowSteps.map((step) => (
            <div key={step.label} className="bw-flow-step">
              <strong>{step.label}</strong>
              <span>{step.value}</span>
            </div>
          ))}
        </div>
      </PageHeader>

      <div className="grid gap-6 lg:grid-cols-2">
        <PaperSection eyebrow="Account" title="账户">
          <div className="bw-stat-card">
            <p className="text-xs uppercase tracking-[0.18em] text-[#888888]">
              Status
            </p>
            <p className="mt-2 text-sm text-[#111111]">当前仅展示基础占位信息。</p>
          </div>
        </PaperSection>

        <PaperSection eyebrow="Workspace" title="工作台">
          <div className="bw-stat-card">
            <p className="text-xs uppercase tracking-[0.18em] text-[#888888]">
              Next
            </p>
            <p className="mt-2 text-sm text-[#111111]">后续在这里补充可配置项。</p>
          </div>
        </PaperSection>
      </div>
    </PageShell>
  );
}
