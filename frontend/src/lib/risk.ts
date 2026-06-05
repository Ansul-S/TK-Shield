import type { RiskLevel } from "@/api/types";

// Maps a risk level to its token-backed badge classes. Single source of truth
// for the CRITICAL→MINIMAL color scale so every surface stays consistent.
const RISK_CLASSES: Record<RiskLevel, string> = {
  CRITICAL: "bg-risk-critical-bg text-risk-critical-fg",
  HIGH: "bg-risk-high-bg text-risk-high-fg",
  MEDIUM: "bg-risk-medium-bg text-risk-medium-fg",
  LOW: "bg-risk-low-bg text-risk-low-fg",
  MINIMAL: "bg-risk-minimal-bg text-risk-minimal-fg",
};

export function riskClasses(level: RiskLevel): string {
  return RISK_CLASSES[level] ?? RISK_CLASSES.MINIMAL;
}

// Examiner verdict confidence → the same warm/cool scale.
export function confidenceClasses(confidence: string): string {
  if (confidence === "high") return "bg-risk-critical-bg text-risk-critical-fg";
  if (confidence === "medium") return "bg-risk-medium-bg text-risk-medium-fg";
  return "bg-risk-low-bg text-risk-low-fg";
}
