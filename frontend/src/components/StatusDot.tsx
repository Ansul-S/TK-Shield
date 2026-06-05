import * as Tooltip from "@radix-ui/react-tooltip";
import { cn } from "@/lib/cn";

// A health indicator dot with an accessible tooltip explaining the state.
// "off" is a normal, honest state (e.g. LLM offline, live monitoring disabled)
// — never styled as an error.
export function StatusDot({
  on,
  label,
  hint,
}: {
  on: boolean;
  label: string;
  hint: string;
}) {
  return (
    <Tooltip.Root>
      <Tooltip.Trigger asChild>
        <span className="inline-flex cursor-help items-center gap-1.5 text-sm text-secondary">
          <span
            className={cn(
              "inline-block h-2 w-2 rounded-full",
              on ? "bg-risk-low-fg" : "bg-tertiary/50",
            )}
            aria-hidden
          />
          {label}
        </span>
      </Tooltip.Trigger>
      <Tooltip.Portal>
        <Tooltip.Content
          sideOffset={6}
          className="max-w-xs rounded-md border border-border bg-surface px-2.5 py-1.5 text-sm text-text shadow-sm"
        >
          {hint}
          <Tooltip.Arrow className="fill-border" />
        </Tooltip.Content>
      </Tooltip.Portal>
    </Tooltip.Root>
  );
}
