import { cn } from "@/lib/cn";
import { riskClasses } from "@/lib/risk";
import type { RiskResult } from "@/api/types";

// 5-factor risk model from the backend (ip_risk_scorer): weights are fixed, so
// we show each factor's points against its max as a proportional bar — makes
// the score legible and defensible at a glance.
const FACTORS: { key: keyof RiskResult["factors"]; label: string; max: number }[] = [
  { key: "similarity_score", label: "Patent similarity", max: 40 },
  { key: "temporal_risk", label: "Temporal proximity", max: 20 },
  { key: "geographic_risk", label: "Geographic overlap", max: 15 },
  { key: "assignee_risk", label: "Assignee profile", max: 15 },
  { key: "ipc_risk", label: "IPC classification", max: 10 },
];

export function RiskScorecard({ risk }: { risk: RiskResult }) {
  return (
    <div className="rounded-md border border-border bg-surface">
      <div className="flex items-center justify-between border-b border-border px-4 py-3">
        <div className="flex items-baseline gap-2">
          <span className="text-3xl font-semibold tabular-nums text-primary">
            {risk.total_score}
          </span>
          <span className="text-sm text-muted">/ {risk.max_possible}</span>
        </div>
        <span
          className={cn(
            "rounded-full px-3 py-1 text-xs font-semibold tracking-wide",
            riskClasses(risk.risk_level),
          )}
        >
          {risk.risk_level} RISK
        </span>
      </div>

      <div className="space-y-2.5 px-4 py-3">
        {FACTORS.map((f) => {
          const value = risk.factors[f.key] ?? 0;
          const pct = Math.max(0, Math.min(100, (value / f.max) * 100));
          return (
            <div key={f.key} className="flex items-center gap-3 text-sm">
              <span className="w-36 flex-shrink-0 text-secondary">{f.label}</span>
              <span className="h-1.5 flex-1 overflow-hidden rounded-full bg-neutral">
                <span
                  className="block h-full rounded-full bg-primary/70"
                  style={{ width: `${pct}%` }}
                />
              </span>
              <span className="w-12 flex-shrink-0 text-right tabular-nums text-muted">
                {value}/{f.max}
              </span>
            </div>
          );
        })}
      </div>

      {risk.recommendations.length > 0 && (
        <div className="border-t border-border px-4 py-3">
          <p className="mb-1.5 text-xs font-medium uppercase tracking-wide text-tertiary">
            Recommended actions
          </p>
          <ul className="list-disc space-y-1 pl-5 text-sm text-secondary">
            {risk.recommendations.map((r) => (
              <li key={r}>{r}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
