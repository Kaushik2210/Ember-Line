"use client";

import { useId } from "react";
import { cn } from "@/lib/cn";

type FieldProps = {
  label: string;
  hint?: string;
  children: (id: string, describedBy: string | undefined) => React.ReactNode;
  className?: string;
};

/** Label + control + optional hint, wired together for screen readers. */
export function Field({ label, hint, children, className }: FieldProps) {
  const id = useId();
  const hintId = hint ? `${id}-hint` : undefined;
  return (
    <div className={cn("flex flex-col gap-1.5", className)}>
      <label htmlFor={id} className="text-xs font-medium text-muted">
        {label}
      </label>
      {children(id, hintId)}
      {hint && (
        <p id={hintId} className="text-xs text-faint">
          {hint}
        </p>
      )}
    </div>
  );
}

const control =
  "w-full rounded-lg border border-line bg-raised px-3 text-sm text-ink " +
  "h-9 pointer-coarse:h-11 hover:border-[var(--border-strong)] disabled:opacity-50";

export function Select({ className, ...rest }: React.SelectHTMLAttributes<HTMLSelectElement>) {
  return <select className={cn(control, "appearance-auto", className)} {...rest} />;
}

export function Input({ className, ...rest }: React.InputHTMLAttributes<HTMLInputElement>) {
  return <input className={cn(control, "num", className)} {...rest} />;
}

type SwitchProps = {
  label: string;
  checked: boolean;
  onChange: (v: boolean) => void;
  hint?: string;
  disabled?: boolean;
};

export function Switch({ label, checked, onChange, hint, disabled }: SwitchProps) {
  const id = useId();
  return (
    <div className="flex items-start justify-between gap-3">
      <div className="min-w-0">
        <label htmlFor={id} className="text-sm text-ink">
          {label}
        </label>
        {hint && <p className="text-xs text-faint">{hint}</p>}
      </div>
      <button
        id={id}
        type="button"
        role="switch"
        aria-checked={checked}
        disabled={disabled}
        onClick={() => onChange(!checked)}
        className={cn(
          "relative mt-0.5 h-6 w-10 shrink-0 rounded-full border border-line transition-colors duration-150 disabled:opacity-50",
          checked ? "bg-harmonized" : "bg-raised",
        )}
      >
        <span
          aria-hidden
          className={cn(
            "absolute top-0.5 size-4.5 rounded-full bg-white transition-transform duration-150",
            checked ? "translate-x-4.5" : "translate-x-0.5",
          )}
        />
      </button>
    </div>
  );
}
