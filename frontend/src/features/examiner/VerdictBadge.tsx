import { cn } from "@/lib/cn";
import type { Verdict } from "@/api/types";

// Novelty verdict → severity color. "Likely not novel" is the strongest signal
// of prior art (highest concern for the applicant), "likely novel" the weakest.
const VERDICT_CLASSES: Record<Verdict, string> = {
  "LIKELY NOT NOVEL": "bg-risk-critical-bg text-risk-critical-fg",
  "POSSIBLE PRIOR ART": "bg-risk-medium-bg text-risk-medium-fg",
  "LIKELY NOVEL": "bg-risk-low-bg text-risk-low-fg",
};

export function VerdictBadge({ verdict }: { verdict: Verdict }) {
  return (
    <span
      className={cn(
        "inline-block rounded-full px-3 py-1 text-sm font-semibold tracking-wide",
        VERDICT_CLASSES[verdict] ?? "bg-neutral text-secondary",
      )}
    >
      {verdict}
    </span>
  );
}
