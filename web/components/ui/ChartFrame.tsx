import { Panel } from "./Panel";

type Props = {
  title: string;
  note?: string;
  state?: "ready" | "loading" | "empty" | "error";
  onRetry?: () => void;
  children: React.ReactNode;
};

export function ChartFrame({ title, note, state = "ready", onRetry, children }: Props) {
  return (
    <Panel title={title}>
      {state === "loading" && (
        <div role="status" aria-label="Loading" className="h-48 animate-pulse rounded-md bg-raised" />
      )}
      {state === "empty" && (
        <p className="py-10 text-center text-sm text-muted">No data for this selection.</p>
      )}
      {state === "error" && (
        <div className="py-10 text-center text-sm text-muted">
          Something went wrong.{" "}
          {onRetry && (
            <button onClick={onRetry} className="min-h-11 px-2 text-ink underline">
              Retry
            </button>
          )}
        </div>
      )}
      {state === "ready" && children}
      {note && <p className="mt-3 text-xs text-faint">{note}</p>}
    </Panel>
  );
}
