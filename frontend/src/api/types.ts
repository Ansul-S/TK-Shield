// Typed mirror of the authoritative API contract (HANDOFF_FRONTEND.md §4).
// The surface is small (~9 endpoints) and stable/tested, so these are
// hand-written. If the backend grows, swap to `openapi-typescript` generated
// from /openapi.json — the call sites bind to these names either way.

export interface Health {
  status: string;
  llm_available: boolean;
  live_patents_available: boolean;
}

export type Domain = "medicinal" | "agricultural" | "food" | "cosmetic" | "";

export interface TKEntry {
  tk_id: string;
  practice_name: string;
  description: string;
  community: string;
  country: string;
  documentation_date: string;
  category: string;
  domain: Domain;
  plants: string[];
  uses: string[];
  locations: string[];
  aliases: string[];
  created_at: string;
}

export interface TKListResponse {
  items: TKEntry[];
  total: number;
  limit: number;
  offset: number;
  q: string;
}

export interface CreateTKBody {
  practice_name: string;
  description?: string;
  community?: string;
  country?: string;
  documentation_date?: string;
  category?: string;
  plants?: string[];
  uses?: string[];
}

export type RiskLevel = "MINIMAL" | "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";

export interface RiskResult {
  total_score: number;
  max_possible: number;
  risk_level: RiskLevel;
  factors: {
    similarity_score: number;
    temporal_risk: number;
    geographic_risk: number;
    assignee_risk: number;
    ipc_risk: number;
  };
  // True when no credible candidate patent was found, so the aggravating
  // factors were withheld and risk reflects similarity alone.
  relevance_gated?: boolean;
  recommendations: string[];
}

export interface Patent {
  patent_id: string;
  title: string;
  assignee: string;
  filing_date: string;
  country: string;
  similarity: number;
  rrf_score: number;
}

// Body accepted by /analyze and /report: either an existing entry id, or an
// ad-hoc practice described inline. n_results is optional.
export type AnalyzeBody =
  | { tk_id: string; n_results?: number }
  | {
      practice_name: string;
      description?: string;
      country?: string;
      documentation_date?: string;
      n_results?: number;
    };

export interface AnalyzeResult {
  tk_entry: {
    tk_id: string;
    practice_name: string;
    country: string;
    documentation_date: string;
  };
  risk: RiskResult;
  patents: Patent[];
}

export interface Citation {
  source: "pubmed" | "wikidata" | "gbif";
  ref_id: string;
  title: string;
  url: string;
}

export interface ReportResult {
  tk_entry: AnalyzeResult["tk_entry"];
  risk: RiskResult;
  top_patents: Patent[];
  citations: Citation[];
  assessment: string;
  opposition_draft: string;
  llm_used: boolean;
  // Identifiers the LLM narrative cited that are NOT in the verified citation
  // set — surfaced so the narrative is treated as a draft (M3).
  unverified_citation_refs?: string[];
  sources_skipped: string[];
  markdown: string;
}

export type Verdict = "LIKELY NOT NOVEL" | "POSSIBLE PRIOR ART" | "LIKELY NOVEL";

export interface NoveltyBody {
  patent_text: string;
  n_results?: number;
}

export interface NoveltyMatch {
  tk_id: string;
  practice_name: string;
  domain: Domain;
  country: string;
  similarity: number;
}

// One parsed patent claim with its own similarity-computed verdict (Tier 2).
export interface ClaimAssessment {
  number: number;
  text: string;
  is_dependent: boolean;
  depends_on: number | null;
  verdict: Verdict;
  confidence: "high" | "medium" | "low";
  top_similarity: number;
  matches: NoveltyMatch[];
}

export interface NoveltyResult {
  verdict: Verdict;
  confidence: "high" | "medium" | "low";
  top_similarity: number;
  matches: NoveltyMatch[];
  assessment: string;
  llm_used: boolean;
  // Claim-level breakdown. `claim_level` is false when the pasted text had no
  // parseable claim structure (e.g. an abstract) — `claims` is then empty and
  // the UI shows the single whole-text view.
  claim_level: boolean;
  claims: ClaimAssessment[];
  // True when verdicts + narrative are deterministic (the claim-level path):
  // the LLM is deliberately not used to restate verdicts, so the note can never
  // contradict the per-claim badges. Absent on the whole-text path.
  deterministic_verdicts?: boolean;
}

export interface MonitorBody {
  tk_id?: string;
  query?: string;
  n_results?: number;
}

export interface MonitorResult {
  available: boolean;
  query: string;
  patents: {
    id: string;
    text: string;
    metadata: {
      patent_id: string;
      title: string;
      assignee: string;
      filing_date: string;
      [k: string]: unknown;
    };
  }[];
  note: string;
}

export interface Stats {
  registry: {
    total: number;
    by_domain: Record<string, number>;
    top_countries: [string, number][];
    top_communities: [string, number][];
  };
  patents: {
    total: number;
    sampled: number;
    by_domain: Record<string, number>;
    by_source: Record<string, number>;
    top_assignees: [string, number][];
  };
}
