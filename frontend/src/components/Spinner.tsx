import { cn } from "@/lib/cn";

export function Spinner({ label }: { label?: string }) {
  return (
    <span className="inline-flex items-center gap-2 text-sm text-secondary" role="status">
      <span
        className="inline-block h-3.5 w-3.5 animate-spin rounded-full border-2 border-border border-t-primary"
        aria-hidden
      />
      {label && <span>{label}</span>}
    </span>
  );
}

// Block-level shimmer placeholder for list/stat loading.
export function Skeleton({ className }: { className?: string }) {
  return (
    <div
      className={cn("animate-pulse rounded-md bg-neutral", className)}
      aria-hidden
    />
  );
}
