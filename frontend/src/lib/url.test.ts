import { describe, expect, it } from "vitest";
import { safeHref } from "./url";

// safeHref is the XSS gate for citation/external links (HANDOFF S2). It must
// only ever return http(s) URLs and null everything else.
describe("safeHref", () => {
  it("passes http and https URLs through", () => {
    expect(safeHref("https://pubmed.ncbi.nlm.nih.gov/12345")).toBe(
      "https://pubmed.ncbi.nlm.nih.gov/12345",
    );
    expect(safeHref("http://example.com/")).toBe("http://example.com/");
  });

  it("blocks javascript:, data:, and other dangerous schemes", () => {
    expect(safeHref("javascript:alert(1)")).toBeNull();
    expect(safeHref("JavaScript:alert(1)")).toBeNull();
    expect(safeHref("data:text/html,<script>alert(1)</script>")).toBeNull();
    expect(safeHref("vbscript:msgbox(1)")).toBeNull();
    expect(safeHref("file:///etc/passwd")).toBeNull();
  });

  it("returns null for non-string input", () => {
    expect(safeHref(null)).toBeNull();
    expect(safeHref(undefined)).toBeNull();
    expect(safeHref(42)).toBeNull();
  });

  it("resolves a bare string to a safe same-origin http(s) URL (not a vector)", () => {
    // A non-absolute string becomes a same-origin link — harmless (no script
    // execution), unlike the dangerous schemes above which are nulled.
    const href = safeHref("not a url with spaces");
    expect(href).not.toBeNull();
    expect(href!.startsWith("http://") || href!.startsWith("https://")).toBe(true);
  });
});
