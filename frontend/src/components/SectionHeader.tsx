import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";

// Compact section label for the dense app views: line icon + title + optional
// trailing action/meta.
export function SectionHeader({
  icon: Icon,
  title,
  meta,
  action,
}: {
  icon?: LucideIcon;
  title: string;
  meta?: ReactNode;
  action?: ReactNode;
}) {
  return (
    <div className="mb-3 flex items-center gap-2">
      {Icon && <Icon className="h-4 w-4 text-tertiary" strokeWidth={1.75} />}
      <h2 className="text-sm font-semibold tracking-tight text-primary">
        {title}
      </h2>
      {meta && <span className="text-xs text-muted">{meta}</span>}
      {action && <div className="ml-auto">{action}</div>}
    </div>
  );
}
