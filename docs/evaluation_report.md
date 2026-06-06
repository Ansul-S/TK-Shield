# TK-Shield — Landmark Bio-Piracy Evaluation

_Generated 2026-06-06T10:14:12+00:00 · corpus of 16,371 patents · retrieval depth k=10._

**Task.** For each of the three landmark bio-piracy cases, an independently-worded traditional-knowledge practice is submitted to the pipeline (hybrid RRF search → 5-factor risk score). We check whether the patent that historically misappropriated the knowledge is retrieved and flagged high-risk. TK descriptions share no wording with the patents, so retrieval reflects genuine semantic+lexical matching, not string overlap.

## Aggregate

| Metric | Value |
|---|---|
| Precision@1 (correct patent ranked #1) | **67%** |
| Precision@5 | **100%** |
| Mean Reciprocal Rank (MRR) | **0.833** |
| Flagged HIGH or CRITICAL | **100%** |

## Per-case

| TK practice | Patent (claimant) | Rank | Similarity | Risk | Historical outcome |
|---|---|---|---|---|---|
| Turmeric (Curcuma longa) for wound healing | US5401504A — University of Mississippi Medical Center (US) | #1 | 0.823 | CRITICAL (85) | Revoked by the USPTO in 1997 on documented Indian prior art. |
| Neem (Azadirachta indica) as a crop antifungal | EP0436257B1 — W.R. Grace & Co. / USDA (US) | #1 | 0.787 | CRITICAL (83) | Revoked by the EPO in 2000/2005 on documented Indian prior art. |
| Basmati aromatic rice of the Indian subcontinent | US5663484A — RiceTec Inc. (US) | #2 | 0.606 | CRITICAL (83) | Most claims withdrawn/struck at the USPTO in 2001-2002. |

## Interpretation

From folk-worded practice descriptions alone, TK-Shield independently re-identifies all three patents that were historically revoked for misappropriating traditional knowledge: every one is retrieved within the top 10 (Precision@5 100%), 67% as the single closest match, and 100% are scored in the HIGH/CRITICAL risk band. This is the defensive-protection workflow envisaged by the WIPO IGC and supported by the 2024 WIPO Treaty on Intellectual Property, Genetic Resources and Associated Traditional Knowledge.
