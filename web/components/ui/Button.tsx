import { cn } from "@/lib/cn";

type Props = React.ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary" | "ghost";
  size?: "sm" | "md";
};

const base =
  "inline-flex items-center justify-center gap-2 rounded-lg font-medium transition-colors duration-150 " +
  "disabled:cursor-not-allowed disabled:opacity-50 pointer-coarse:min-h-11";

const variants = {
  primary: "bg-ink text-bg hover:opacity-90",
  secondary: "border border-line bg-raised text-ink hover:border-[var(--border-strong)]",
  ghost: "text-muted hover:bg-raised hover:text-ink",
};

const sizes = { sm: "h-8 px-3 text-xs", md: "h-10 px-4 text-sm" };

export function Button({ variant = "secondary", size = "md", className, type = "button", ...rest }: Props) {
  return <button type={type} className={cn(base, variants[variant], sizes[size], className)} {...rest} />;
}
