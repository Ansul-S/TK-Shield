// Centralized UI-layer configuration. One place for the frontend's tunable
// constants (page size, query bounds, default result counts, cache/poll timings,
// animation delays). Behaviour-preserving — every value matches the prior inline
// literal it replaced. Request timeouts live in `api/client.ts` (request layer).

/** Registry list page size (Defender sidebar). */
export const PAGE_SIZE = 25;

/** Examiner: minimum patent-text length before a novelty check is allowed. */
export const MIN_QUERY_LENGTH = 20;

/** Default `n_results` per persona action (the server clamps to 1–50). */
export const DEFAULT_RESULT_COUNTS = {
  analyze: 5,
  report: 5,
  novelty: 5,
  monitor: 10,
} as const;

/** TanStack Query: how long fetched data stays "fresh" before refetch. */
export const STALE_TIME_MS = 30_000;

/** Health poll interval — drives the header LLM/live-patent status dots. */
export const HEALTH_REFETCH_MS = 15_000;

/** LoadingStages: ms between staged-progress advances on slow calls. */
export const LOADING_STAGE_MS = 6_000;

/** SearchBox: debounce before emitting a trimmed query. */
export const SEARCH_DEBOUNCE_MS = 250;
