"use client";

import { useQuery } from "@tanstack/react-query";
import { getAvailability } from "@/lib/api";
import { resolveArea, resolvePeriod, useRegions } from "@/lib/analysis";
import { useExploreStore } from "@/lib/store";
import type { DayNight, Metric, ModelChoice } from "@/lib/types";
import { SENSORS, useExploreParams } from "@/lib/urlState";
import { Button } from "@/components/ui/Button";
import { Field, Input, Select, Switch } from "@/components/ui/Field";
import { Section } from "@/components/ui/Section";
import { Segmented } from "@/components/ui/Segmented";

const MODIS_FIRST = "2000-11-01";

export function PeriodSection() {
  const [p, setP] = useExploreParams();
  const regions = useRegions().data;
  const geojson = useExploreStore((s) => s.geojson);
  const avail = useQuery({ queryKey: ["availability"], queryFn: getAvailability, staleTime: 3_600_000 });
  const area = resolveArea(p, regions, geojson);
  const { start, end } = resolvePeriod(p, area.region);

  const src = avail.data?.sources;
  const newest = [src?.MODIS_SP?.max, src?.VIIRS_SNPP_SP?.max].filter(Boolean).sort()[0] ?? end;
  const overlapStart = src?.VIIRS_SNPP_SP?.min ?? "2012-01-20";
  const tenYearsAgo = `${Number(newest.slice(0, 4)) - 10}${newest.slice(4)}`;
  const presets: { label: string; s: string; e: string }[] = [
    { label: "Region default", s: area.region?.default_start ?? start, e: area.region?.default_end ?? end },
    { label: "Full record", s: src?.MODIS_SP?.min ?? MODIS_FIRST, e: newest },
    { label: "VIIRS era", s: overlapStart, e: newest },
    { label: "Last 10 years", s: tenYearsAgo, e: newest },
  ];

  return (
    <Section title="Period" summary={`${start.slice(0, 4)} – ${end.slice(0, 4)}`} defaultOpen>
      <div className="grid grid-cols-2 gap-2">
        <Field label="From">
          {(id) => (
            <Input id={id} type="date" value={start} min={MODIS_FIRST} max={end} onChange={(e) => void setP({ s: e.target.value || null, job: null })} />
          )}
        </Field>
        <Field label="To">
          {(id) => (
            <Input id={id} type="date" value={end} min={start} onChange={(e) => void setP({ e: e.target.value || null, job: null })} />
          )}
        </Field>
      </div>
      <div className="flex flex-wrap gap-1.5" role="group" aria-label="Period presets">
        {presets.map((pr) => (
          <Button key={pr.label} size="sm" variant="ghost" className="border border-line" onClick={() => void setP({ s: pr.s, e: pr.e, job: null })}>
            {pr.label}
          </Button>
        ))}
      </div>
      <p className="text-xs text-faint">
        The harmonisation needs at least a year and several VIIRS-era years to fit. Going back before 2012 reconstructs
        VIIRS-equivalent values from MODIS.
      </p>
    </Section>
  );
}

export function SensorSection() {
  const [p, setP] = useExploreParams();
  const toggle = (s: (typeof SENSORS)[number]) => {
    const next = p.sens.includes(s) ? p.sens.filter((x) => x !== s) : [...p.sens, s];
    if (next.length > 0) void setP({ sens: next });
  };
  const items: { id: (typeof SENSORS)[number] | "noaa20"; label: string; detail: string; color: string }[] = [
    { id: "modis", label: "MODIS", detail: "Terra + Aqua, 1 km", color: "var(--modis)" },
    { id: "viirs", label: "VIIRS", detail: "Suomi NPP, 375 m", color: "var(--viirs)" },
    { id: "noaa20", label: "NOAA-20", detail: "not used in this version", color: "var(--text-faint)" },
  ];
  return (
    <Section title="Sensors" summary={p.sens.map((s) => s.toUpperCase()).join(" + ")}>
      <fieldset className="flex flex-col gap-2">
        <legend className="sr-only">Sensors shown on the map</legend>
        {items.map((it) => {
          const off = it.id === "noaa20";
          return (
            <label key={it.id} className="flex min-h-9 items-center gap-3 text-sm pointer-coarse:min-h-11">
              <input
                type="checkbox"
                disabled={off}
                checked={off ? false : p.sens.includes(it.id as "modis" | "viirs")}
                onChange={() => !off && toggle(it.id as "modis" | "viirs")}
                className="size-4 accent-[var(--harmonized)]"
              />
              <span aria-hidden className="size-2.5 rounded-full" style={{ background: it.color }} />
              <span className={off ? "text-faint" : "text-ink"}>{it.label}</span>
              <span className="text-xs text-faint">{it.detail}</span>
            </label>
          );
        })}
      </fieldset>
      <p className="text-xs text-faint">Applies to the map. The harmonisation always uses MODIS and Suomi NPP VIIRS.</p>
    </Section>
  );
}

export function QualitySection() {
  const [p, setP] = useExploreParams();
  return (
    <Section title="Quality policy" summary={`MODIS ≥ ${p.conf}`}>
      <Field label={`MODIS confidence at least ${p.conf}`} hint="Numeric 0–100. Lower keeps more low-confidence detections.">
        {(id, d) => (
          <input
            id={id}
            aria-describedby={d}
            type="range"
            min={0}
            max={100}
            step={5}
            value={p.conf}
            onChange={(e) => void setP({ conf: Number(e.target.value), job: null })}
            className="w-full accent-[var(--modis)]"
          />
        )}
      </Field>
      <Field label="VIIRS confidence">
        {() => (
          <Segmented
            label="VIIRS confidence"
            value={p.vc as "nh" | "h" | "lnh"}
            options={[
              { value: "nh", label: "Nominal+High" },
              { value: "h", label: "High" },
              { value: "lnh", label: "All" },
            ]}
            onChange={(v) => void setP({ vc: v, job: null })}
          />
        )}
      </Field>
      <Field label="Time of day" hint="Night detections are rare; day-only is the cleanest comparison.">
        {() => (
          <Segmented<DayNight>
            label="Day or night"
            value={p.dn}
            options={[
              { value: "both", label: "Both" },
              { value: "D", label: "Day" },
              { value: "N", label: "Night" },
            ]}
            onChange={(v) => void setP({ dn: v, job: null })}
          />
        )}
      </Field>
      <Switch label="Mask persistent heat sources" checked disabled hint="Flares and industry are removed when the record is at least a year." onChange={() => undefined} />
    </Section>
  );
}

export function GridModelSection() {
  const [p, setP] = useExploreParams();
  return (
    <Section title="Grid and model" summary={`${p.mod}, ${p.gk === "h3" ? `H3 r${p.gr}` : `${p.gs}°`}`}>
      <Field label="Common grid">
        {() => (
          <Segmented
            label="Grid type"
            value={p.gk as "regular" | "h3"}
            options={[
              { value: "regular", label: "Regular" },
              { value: "h3", label: "H3" },
            ]}
            onChange={(v) => void setP({ gk: v, job: null })}
          />
        )}
      </Field>
      {p.gk === "regular" ? (
        <Field label="Cell size">
          {(id) => (
            <Select id={id} value={p.gs} onChange={(e) => void setP({ gs: Number(e.target.value), job: null })}>
              <option value={0.1}>0.1°</option>
              <option value={0.25}>0.25°</option>
              <option value={0.5}>0.5°</option>
            </Select>
          )}
        </Field>
      ) : (
        <Field label="H3 resolution">
          {(id) => (
            <Select id={id} value={p.gr} onChange={(e) => void setP({ gr: Number(e.target.value), job: null })}>
              <option value={4}>4 (largest cells)</option>
              <option value={5}>5</option>
              <option value={6}>6 (smallest cells)</option>
            </Select>
          )}
        </Field>
      )}
      <Field label="Measure" hint="Fire radiative power is the most comparable between sensors.">
        {(id) => (
          <Select id={id} value={p.m} onChange={(e) => void setP({ m: e.target.value as Metric, job: null })}>
            <option value="frp_sum_mw">Fire radiative power (MW)</option>
            <option value="active_1km">Burning 1 km footprints</option>
            <option value="det_count">Raw detections</option>
          </Select>
        )}
      </Field>
      <Field label="Normalisation model" hint="Auto picks the best by leave-one-year-out validation.">
        {(id) => (
          <Select id={id} value={p.mod} onChange={(e) => void setP({ mod: e.target.value as ModelChoice, job: null })}>
            <option value="auto">Auto (best validated)</option>
            <option value="huber">Huber log-log</option>
            <option value="theilsen">Theil–Sen log-log</option>
            <option value="quantile">Seasonal quantile mapping</option>
            <option value="isotonic">Isotonic</option>
          </Select>
        )}
      </Field>
    </Section>
  );
}
