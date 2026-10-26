import { cn } from "@/lib/cn";

type Props = { label: string; value: string; hint?: string; className?: string };

export function Stat({ label, value, hint, className }: Props) {
  return (
    <div className={cn("flex flex-col gap-1", className)}>
      <span className="text-xs text-muted">{label}</span>
      <span className="num text-2xl font-semibold text-ink">{value}</span>
      {hint && <span className="text-xs text-faint">{hint}</span>}
    </div>
  );
}
