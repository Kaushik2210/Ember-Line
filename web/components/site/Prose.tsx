import { cn } from "@/lib/cn";

/** Readable long-form text: a measure of about 70 characters, calm spacing, clear hierarchy. */
export function Prose({ className, children }: { className?: string; children: React.ReactNode }) {
  return (
    <div
      className={cn(
        "max-w-[70ch] text-[15px] leading-7 text-muted",
        "[&_h2]:mt-12 [&_h2]:scroll-mt-20 [&_h2]:text-xl [&_h2]:font-semibold [&_h2]:text-ink",
        "[&_h3]:mt-8 [&_h3]:text-base [&_h3]:font-semibold [&_h3]:text-ink",
        "[&_p]:mt-4 [&_ul]:mt-4 [&_ul]:list-disc [&_ul]:pl-5 [&_ol]:mt-4 [&_ol]:list-decimal [&_ol]:pl-5 [&_li]:mt-1.5",
        "[&_a]:text-viirs [&_a]:underline [&_a]:underline-offset-2 [&_a:hover]:decoration-2 [&_strong]:font-medium [&_strong]:text-ink",
        "[&_code]:rounded [&_code]:bg-raised [&_code]:px-1 [&_code]:py-0.5 [&_code]:font-mono [&_code]:text-[13px] [&_code]:text-ink",
        className,
      )}
    >
      {children}
    </div>
  );
}

/** A displayed equation. Plain HTML so it needs no math library and stays readable to screen readers. */
export function Equation({ children, label }: { children: React.ReactNode; label: string }) {
  return (
    <figure className="my-5 overflow-x-auto rounded-lg border border-line bg-panel px-4 py-3" aria-label={label}>
      <div className="font-serif text-[15px] italic leading-8 text-ink">{children}</div>
    </figure>
  );
}
