import { Activity, AlertTriangle, CheckCircle2 } from "lucide-react";

import { cn } from "@/lib/utils";

type StatusKind = "checking" | "online" | "offline";

const statusIcon = {
  checking: Activity,
  online: CheckCircle2,
  offline: AlertTriangle,
};

const statusLabel = {
  checking: "확인 중",
  online: "정상",
  offline: "오프라인",
};

export function StatusPill({ status }: { status: StatusKind }) {
  const Icon = statusIcon[status];

  return (
    <span
      className={cn(
        "inline-flex h-8 min-w-24 items-center justify-center gap-2 rounded-full border px-3 text-sm font-medium",
        status === "online" && "border-[#99d5cf] bg-[#e5fbf8] text-[#0f766e]",
        status === "checking" && "border-[#d9cda9] bg-[#fff8dc] text-[#8a5a06]",
        status === "offline" && "border-[#f1b6b6] bg-[#fff1f1] text-[#b91c1c]",
      )}
    >
      <Icon aria-hidden="true" size={16} strokeWidth={2} />
      {statusLabel[status]}
    </span>
  );
}
