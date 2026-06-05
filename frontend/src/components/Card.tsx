import type { ReactNode } from "react";
import { cn } from "@/lib/cn";

// Clean container, not a floating object: white surface, thin border, modest
// radius, compact padding. No shadow (Duna is intentionally flat).
export function Card({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "rounded-md border border-border bg-surface p-4",
        className,
      )}
    >
      {children}
    </div>
  );
}

export function CardTitle({ children }: { children: ReactNode }) {
  return (
    <h2 className="mb-2 text-xs font-medium tracking-wide text-tertiary">
      {children}
    </h2>
  );
}
