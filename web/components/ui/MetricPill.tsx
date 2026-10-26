import { cn } from "@/lib/cn";

type Props = { label: string; value: string; tone?: "neutral" | "warn" };

export function MetricPill({ label, value, tone = "neutral" }: Props) {
  return (
    <span
      className={cn(
        "inline-flex items-baseline gap-1.5 rounded-md bg-raised px-2 py-1 text-xs",
        tone === "warn" && "text-hot",
      )}
    >
      <span className="text-muted">{label}</span>
      <span className="num font-medium">{value}</span>
    </span>
  );
}
