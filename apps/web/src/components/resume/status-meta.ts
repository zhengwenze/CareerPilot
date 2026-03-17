export function getResumeStatusMeta(status: string | null | undefined) {
  if (status === "success") {
    return { label: "已完成", className: "bg-[#E8F7EE] text-[#18864B]" };
  }
  if (status === "failed") {
    return { label: "失败", className: "bg-[#FFF1F0] text-[#D93025]" };
  }
  if (status === "pending" || status === "processing") {
    return { label: "处理中", className: "bg-[#FFF7E6] text-[#B26A00]" };
  }
  return { label: "未知", className: "bg-[#f2f2f2] text-black/65" };
}

export function getResumeAIStatusMeta(
  status: string | null | undefined,
  message?: string | null
) {
  if (status === "applied") {
    return { label: "AI 已校准", className: "bg-[#E8F7EE] text-[#18864B]" };
  }
  if (status === "fallback_rule") {
    return { label: "AI 回退规则", className: "bg-[#FFF7E6] text-[#B26A00]" };
  }
  if (status === "pending") {
    return { label: "AI 处理中", className: "bg-[#F5F9FF] text-[#0071E3]" };
  }
  if (status === "skipped") {
    return {
      label: message?.includes("未启用") ? "AI 未启用" : "AI 未执行",
      className: "bg-[#f2f2f2] text-black/65",
    };
  }
  return null;
}
