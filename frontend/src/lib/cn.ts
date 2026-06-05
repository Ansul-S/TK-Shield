// Minimal className joiner — no clsx dependency needed for this surface.
export function cn(...parts: (string | false | null | undefined)[]): string {
  return parts.filter(Boolean).join(" ");
}
