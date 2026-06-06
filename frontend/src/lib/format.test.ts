import { describe, expect, it } from "vitest";
import { cap, dash, trunc } from "./format";

// Real corpus data is full of empty/"nan" cells — the UI must never show those
// literals. dash() is the guard.
describe("dash", () => {
  it("renders an em-dash for empty / null / nan / none", () => {
    for (const v of ["", "  ", "nan", "NaN", "none", "None", null, undefined]) {
      expect(dash(v)).toBe("—");
    }
  });

  it("passes real values through (trimmed)", () => {
    expect(dash("US5401504A")).toBe("US5401504A");
    expect(dash("  India  ")).toBe("India");
    expect(dash(0)).toBe("0"); // a real zero is not empty
  });
});

describe("cap", () => {
  it("uppercases the first character only", () => {
    expect(cap("turmeric")).toBe("Turmeric");
    expect(cap("")).toBe("");
    expect(cap(null)).toBe("");
  });
});

describe("trunc", () => {
  it("adds an ellipsis only past the limit", () => {
    expect(trunc("short", 10)).toBe("short");
    expect(trunc("a very long title here", 6)).toBe("a very…");
    expect(trunc(null, 5)).toBe("");
  });
});
