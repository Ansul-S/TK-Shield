// Citation URLs originate from external APIs / LLM output, so validate the
// scheme before ever using one as an href (closes the S2 XSS concern for links:
// blocks javascript:, data:, etc.). Returns a safe href or null.
export function safeHref(url: unknown): string | null {
  if (typeof url !== "string") return null;
  try {
    const parsed = new URL(url, window.location.origin);
    return parsed.protocol === "http:" || parsed.protocol === "https:"
      ? parsed.href
      : null;
  } catch {
    return null;
  }
}
