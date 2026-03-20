export function getResumeStatusMeta(status: string | null | undefined) {
  if (status === "success") {
    return { label: "已完成", className: "border-2 border-black bg-white text-black" };
  }
  if (status === "failed") {
    return { label: "失败", className: "border-2 border-black bg-white text-black" };
  }
  if (status === "pending" || status === "processing") {
    return { label: "处理中", className: "border-2 border-black bg-white text-black" };
  }
  return { label: "未知", className: "border-2 border-black bg-white text-black" };
}

export function getResumeAIStatusMeta(
  status: string | null | undefined,
  message?: string | null
) {
  if (status === "applied") {
    return { label: "已完成校准", className: "border-2 border-black bg-white text-black" };
  }
  if (status === "fallback_rule") {
    return { label: "AI 回退规则", className: "border-2 border-black bg-white text-black" };
  }
  if (status === "pending") {
    return {
      label: message?.trim() || "处理中",
      className: "border-2 border-black bg-white text-black",
    };
  }
  if (status === "skipped") {
    return {
      label: message?.includes("未启用") ? "AI 未启用" : "AI 未执行",
      className: "border-2 border-black bg-white text-black",
    };
  }
  return null;
}
