import { cn } from "@/lib/cn";

type Props = Omit<React.HTMLAttributes<HTMLElement>, "title"> & {
  title?: string;
  actions?: React.ReactNode;
};

export function Panel({ title, actions, className, children, ...rest }: Props) {
  return (
    <section className={cn("rounded-xl border border-line bg-panel", className)} {...rest}>
      {(title || actions) && (
        <header className="flex min-h-11 items-center justify-between border-b border-line px-4">
          {title && <h2 className="text-sm font-semibold text-ink">{title}</h2>}
          {actions}
        </header>
      )}
      <div className="p-4">{children}</div>
    </section>
  );
}
