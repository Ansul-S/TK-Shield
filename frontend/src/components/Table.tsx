import type { ReactNode } from "react";
import { cn } from "@/lib/cn";

// Thin styled table primitives. Feature-specific tables (patents, factors,
// citations, assignees) compose these in the persona passes.
export function Table({ children }: { children: ReactNode }) {
  return (
    <table className="w-full border-collapse text-sm">{children}</table>
  );
}

export function Th({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <th
      className={cn(
        "border-b border-border px-2 py-1.5 text-left font-semibold text-muted",
        className,
      )}
    >
      {children}
    </th>
  );
}

export function Td({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <td className={cn("border-b border-border px-2 py-1.5 text-left", className)}>
      {children}
    </td>
  );
}
