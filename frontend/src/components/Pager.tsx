import { Button } from "./Button";

// Offset pager bound to the /api/tk pagination contract. Shows a range summary
// and disables the edges. Backend orders results stably so pages don't drift.
export function Pager({
  total,
  limit,
  offset,
  onChange,
}: {
  total: number;
  limit: number;
  offset: number;
  onChange: (nextOffset: number) => void;
}) {
  if (total <= limit) {
    return total ? (
      <span className="text-sm text-muted">
        {total} {total === 1 ? "entry" : "entries"}
      </span>
    ) : null;
  }
  const from = offset + 1;
  const to = Math.min(offset + limit, total);
  return (
    <div className="flex items-center gap-3 text-sm">
      <Button
        variant="secondary"
        className="px-2.5 py-1"
        disabled={offset === 0}
        onClick={() => onChange(Math.max(0, offset - limit))}
      >
        ‹ Prev
      </Button>
      <span className="text-muted">
        {from}–{to} of {total}
      </span>
      <Button
        variant="secondary"
        className="px-2.5 py-1"
        disabled={to >= total}
        onClick={() => onChange(offset + limit)}
      >
        Next ›
      </Button>
    </div>
  );
}
