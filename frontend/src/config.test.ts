import { describe, expect, it } from "vitest";
import {
  DEFAULT_RESULT_COUNTS,
  HEALTH_REFETCH_MS,
  LOADING_STAGE_MS,
  MIN_QUERY_LENGTH,
  PAGE_SIZE,
  SEARCH_DEBOUNCE_MS,
  STALE_TIME_MS,
} from "./config";

// Behaviour-preserving guard: these centralized constants must equal the prior
// inline literals they replaced (Tier 3 was a pure extraction, no UX change).
describe("frontend config", () => {
  it("preserves the prior default values", () => {
    expect(PAGE_SIZE).toBe(25);
    expect(MIN_QUERY_LENGTH).toBe(20);
    expect(DEFAULT_RESULT_COUNTS).toEqual({
      analyze: 5,
      report: 5,
      novelty: 5,
      monitor: 10,
    });
    expect(STALE_TIME_MS).toBe(30_000);
    expect(HEALTH_REFETCH_MS).toBe(15_000);
    expect(LOADING_STAGE_MS).toBe(6_000);
    expect(SEARCH_DEBOUNCE_MS).toBe(250);
  });
});
