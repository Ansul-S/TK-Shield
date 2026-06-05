import type { ReactNode } from "react";
import { cn } from "@/lib/cn";
import { riskClasses } from "@/lib/risk";
import type { RiskLevel } from "@/api/types";

// Generic chip — Duna style: pill, dark fill, white text, body-md.
export function Badge({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <span
      className={cn(
        "inline-block rounded-full bg-primary px-3 py-1.5 text-sm text-surface",
        className,
      )}
    >
      {children}
    </span>
  );
}

// Risk uses the derived tinted scale (overrides the dark-fill chip default).
export function RiskBadge({ level }: { level: RiskLevel }) {
  return (
    <span
      className={cn(
        "inline-block rounded-full px-3 py-1.5 text-sm font-medium",
        riskClasses(level),
      )}
    >
      {level}
    </span>
  );
}
