"use client";

interface StatusBadgeProps {
  label: string;
  status: "ready" | "not_ready" | "evaluated" | "not_evaluated" | "trained" | "not_trained" | "generated" | "not_generated";
}

const STATUS_MAP: Record<string, { cls: string; text: string }> = {
  ready: { cls: "badge badge-success", text: "Ready" },
  not_ready: { cls: "badge", text: "Not loaded" },
  evaluated: { cls: "badge badge-success", text: "Evaluated" },
  not_evaluated: { cls: "badge", text: "Not evaluated" },
  trained: { cls: "badge badge-success", text: "Trained" },
  not_trained: { cls: "badge", text: "Not trained" },
  generated: { cls: "badge badge-success", text: "Generated" },
  not_generated: { cls: "badge", text: "Not generated" },
};

export function StatusBadge({ label, status }: StatusBadgeProps) {
  const config = STATUS_MAP[status] ?? { cls: "badge", text: status };
  return (
    <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
      <span style={{ fontSize: "0.8125rem", color: "var(--muted)", fontWeight: 500 }}>{label}:</span>
      <span className={config.cls}>{config.text}</span>
    </div>
  );
}
