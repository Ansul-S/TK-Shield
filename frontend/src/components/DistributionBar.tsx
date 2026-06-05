// Horizontal distribution bars for analytics (researcher). Sorted desc, bar
// width relative to the max value. Lightweight — no charting dependency.
export function DistributionBars({
  data,
  emptyLabel = "No data",
}: {
  data: Record<string, number> | [string, number][];
  emptyLabel?: string;
}) {
  const entries = (Array.isArray(data) ? data : Object.entries(data)).filter(
    ([k]) => k !== "",
  );
  if (entries.length === 0)
    return <p className="text-sm text-muted">{emptyLabel}</p>;

  const max = Math.max(...entries.map(([, v]) => v), 1);
  const sorted = [...entries].sort((a, b) => b[1] - a[1]);

  return (
    <div className="space-y-2">
      {sorted.map(([key, value]) => (
        <div key={key} className="flex items-center gap-3 text-sm">
          <span
            className="w-32 flex-shrink-0 truncate text-secondary"
            title={key}
          >
            {key}
          </span>
          <span className="h-2 flex-1 overflow-hidden rounded-full bg-neutral">
            <span
              className="block h-full rounded-full bg-primary/70"
              style={{ width: `${Math.max(2, (value / max) * 100)}%` }}
            />
          </span>
          <span className="w-12 flex-shrink-0 text-right tabular-nums text-muted">
            {value.toLocaleString()}
          </span>
        </div>
      ))}
    </div>
  );
}
