import { ApiError } from "@/api/client";
import { Button } from "./Button";

function messageOf(error: unknown): string {
  if (error instanceof ApiError) return error.message;
  if (error instanceof Error) return error.message;
  return "Something went wrong.";
}

// Duna validation tone: clear but not loud — border color over filled error bg.
export function ErrorState({
  error,
  onRetry,
}: {
  error: unknown;
  onRetry?: () => void;
}) {
  return (
    <div className="rounded-md border border-error bg-surface p-4">
      <p className="text-sm font-medium text-error">{messageOf(error)}</p>
      {onRetry && (
        <Button variant="secondary" className="mt-3" onClick={onRetry}>
          Retry
        </Button>
      )}
    </div>
  );
}
