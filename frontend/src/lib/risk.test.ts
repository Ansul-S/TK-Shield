import { describe, expect, it } from "vitest";
import type { RiskLevel } from "@/api/types";
import { confidenceClasses, riskClasses } from "./risk";

describe("riskClasses", () => {
  it("maps every known level to its token classes", () => {
    const levels: RiskLevel[] = ["CRITICAL", "HIGH", "MEDIUM", "LOW", "MINIMAL"];
    for (const lvl of levels) {
      expect(riskClasses(lvl)).toContain(`risk-${lvl.toLowerCase()}`);
    }
  });

  it("falls back to MINIMAL classes for an unknown level", () => {
    expect(riskClasses("BOGUS" as RiskLevel)).toBe(riskClasses("MINIMAL"));
  });
});

describe("confidenceClasses", () => {
  it("maps high/medium and defaults the rest to low", () => {
    expect(confidenceClasses("high")).toContain("risk-critical");
    expect(confidenceClasses("medium")).toContain("risk-medium");
    expect(confidenceClasses("low")).toContain("risk-low");
    expect(confidenceClasses("anything-else")).toContain("risk-low");
  });
});
