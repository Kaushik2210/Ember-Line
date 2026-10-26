import { Panel } from "@/components/ui/Panel";
import { SensorBadge } from "@/components/ui/SensorBadge";

export default function Home() {
  return (
    <main className="mx-auto flex min-h-screen max-w-3xl flex-col justify-center gap-6 px-6">
      <h1 className="text-4xl font-semibold tracking-tight">EMBERLINE</h1>
      <p className="text-muted">One consistent record of fire, from two sensors.</p>
      <Panel title="Sensors">
        <div className="flex gap-2">
          <SensorBadge sensor="modis" />
          <SensorBadge sensor="viirs" />
          <SensorBadge sensor="harmonized" />
        </div>
      </Panel>
    </main>
  );
}
