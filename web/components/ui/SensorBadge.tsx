import { SENSORS, type Sensor } from "@/lib/sensors";

export function SensorBadge({ sensor }: { sensor: Sensor }) {
  const s = SENSORS[sensor];
  return (
    <span className="inline-flex items-center gap-2 rounded-full border border-line px-2.5 py-1 text-xs text-ink">
      <span aria-hidden className="size-2 rounded-full" style={{ background: s.colorVar }} />
      {s.label}
    </span>
  );
}
