"use client";

import { GridModelSection, PeriodSection, QualitySection, SensorSection } from "./ControlSections";
import { RegionSection } from "./RegionSection";
import { RunPanel } from "./RunPanel";

export function LeftRail({ searchRef }: { searchRef: React.RefObject<HTMLInputElement | null> }) {
  return (
    <aside aria-label="Analysis controls" className="flex h-full min-h-0 flex-col bg-panel">
      <div className="min-h-0 flex-1 overflow-y-auto">
        <RegionSection searchRef={searchRef} />
        <PeriodSection />
        <SensorSection />
        <QualitySection />
        <GridModelSection />
      </div>
      <RunPanel />
    </aside>
  );
}
