import * as React from "react";
import { cn } from "@/lib/utils";

type Tone = "danger" | "warning" | "success" | "info" | "neutral";

const TONE: Record<Tone, string> = {
  danger:
    "bg-[var(--color-danger-soft)] text-red-300 border border-red-500/30",
  warning:
    "bg-amber-500/10 text-amber-300 border border-amber-500/30",
  success:
    "bg-emerald-500/10 text-emerald-300 border border-emerald-500/30",
  info: "bg-indigo-500/10 text-indigo-300 border border-indigo-500/30",
  neutral:
    "bg-white/5 text-[var(--color-foreground-muted)] border border-white/10",
};

interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  tone?: Tone;
}

export function Badge({ tone = "neutral", className, ...props }: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-mono uppercase tracking-wide",
        TONE[tone],
        className
      )}
      {...props}
    />
  );
}
