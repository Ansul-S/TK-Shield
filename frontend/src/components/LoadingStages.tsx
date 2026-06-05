import { useEffect, useState } from "react";
import { cn } from "@/lib/cn";
import { Spinner } from "./Spinner";

// Staged progress for the slow /report and /novelty calls (15–45s). The backend
// is synchronous and doesn't stream progress, so this advances on a timer to
// communicate the *phases* the request goes through and keep the UI from
// looking frozen. The persona passes wire this to the in-flight mutation state.
export function LoadingStages({
  stages,
  stepMs = 6000,
}: {
  stages: string[];
  stepMs?: number;
}) {
  const [active, setActive] = useState(0);

  useEffect(() => {
    if (active >= stages.length - 1) return;
    const t = setTimeout(() => setActive((i) => i + 1), stepMs);
    return () => clearTimeout(t);
  }, [active, stages.length, stepMs]);

  return (
    <ol className="space-y-2" aria-live="polite">
      {stages.map((stage, i) => {
        const done = i < active;
        const current = i === active;
        return (
          <li key={stage} className="flex items-center gap-2 text-sm">
            {current ? (
              <Spinner />
            ) : (
              <span
                className={cn(
                  "inline-block h-3.5 w-3.5 rounded-full border-2",
                  done ? "border-primary bg-primary" : "border-border",
                )}
                aria-hidden
              />
            )}
            <span className={cn(done || current ? "text-text" : "text-muted")}>
              {stage}
            </span>
          </li>
        );
      })}
    </ol>
  );
}
