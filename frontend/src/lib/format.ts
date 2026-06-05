// Presentation helpers ported from the legacy SPA. pandas reads empty cells as
// NaN → "nan", and assignees/dates/countries are frequently empty; never show
// the literal "nan"/"none" or a blank — render an em-dash instead.

export function dash(v: unknown): string {
  if (v === undefined || v === null) return "—";
  const s = String(v).trim();
  const lower = s.toLowerCase();
  return s === "" || lower === "nan" || lower === "none" ? "—" : s;
}

export function cap(s: unknown): string {
  const str = String(s ?? "");
  return str ? str.charAt(0).toUpperCase() + str.slice(1) : str;
}

export function trunc(s: unknown, n: number): string {
  const str = String(s ?? "").trim();
  return str.length > n ? str.slice(0, n).trim() + "…" : str;
}
