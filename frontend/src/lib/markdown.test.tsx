import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Markdown } from "./markdown";

// The #1 frontend security invariant (HANDOFF S2): LLM/API-derived narrative
// renders through react-markdown with NO raw-HTML plugin, so injected markup is
// inert text. These tests fail loudly if anyone adds rehype-raw or otherwise
// reopens the sink.
describe("Markdown (XSS safety)", () => {
  it("does not render an injected <script> element", () => {
    const { container } = render(
      <Markdown>{"Hello <script>window.__pwned=1</script> world"}</Markdown>,
    );
    expect(container.querySelector("script")).toBeNull();
    expect(container.innerHTML).not.toContain("<script");
  });

  it("does not render an inline event handler from injected HTML", () => {
    const { container } = render(
      <Markdown>{'<img src=x onerror="window.__pwned=1">'}</Markdown>,
    );
    // The whole tag is HTML-escaped to inert text — no real <img> element is
    // created, so the onerror handler can never execute.
    expect(container.querySelector("img")).toBeNull();
    expect(container.innerHTML).toContain("&lt;img"); // rendered as escaped text
  });

  it("strips javascript: hrefs from markdown links", () => {
    const { container } = render(
      <Markdown>{"[click me](javascript:alert(1))"}</Markdown>,
    );
    const link = container.querySelector("a");
    // react-markdown's default url transform neutralizes the scheme.
    expect(link?.getAttribute("href") ?? "").not.toContain("javascript:");
  });

  it("renders ordinary markdown safely", () => {
    const { container } = render(
      <Markdown>{"**bold** and [a link](https://example.com)"}</Markdown>,
    );
    expect(container.querySelector("strong")?.textContent).toBe("bold");
    expect(container.querySelector("a")?.getAttribute("href")).toBe(
      "https://example.com",
    );
  });
});
