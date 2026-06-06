# TK-Shield — Interview Preparation

> Questions an interviewer (WIPO panel, internship recruiter, or technical interviewer) could ask about this
> project, with detailed model answers grounded in what TK-Shield **actually** does. Answers are written in the
> first person so you can adapt them in your own voice. The goal is for you to *genuinely understand* the system
> so you can speak to it honestly — not to memorise scripts.
>
> **One framing to internalise first:** you did not "ask an AI to build an app." You **designed and directed an
> AI-assisted engineering project**, applying your environmental-science and AI/ML background to a real
> traditional-knowledge protection problem, and you made the architecture, data, security, and product
> judgments yourself. Speak as the person who owns those decisions.

---

## Quick reference — facts you should be able to recall

| Thing | Value |
|---|---|
| Patent corpus | **16,371** real US patents (PatentsView bulk TSV — real titles, assignees, grant dates) |
| TK registry | **2,030** documented practices (Dr. Duke CC0 ethnobotany + curated Wikidata) |
| Search | Hybrid: **semantic 0.7 + BM25 0.3** fused with **Reciprocal Rank Fusion (RRF)** |
| Risk model | 5 factors → 0–100: similarity 40, temporal 20, geographic 15, assignee 15, IPC 10 |
| Evaluation | **Precision@5 100%, P@1 67%, MRR 0.833, 100% flagged CRITICAL** on the 3 landmark cases |
| LLM | Local **Ollama (llama3.2)** for the RAG report; deterministic template fallback if absent |
| Cost | **Zero API keys**, offline-first, no runtime CDN |
| Tests | 48 backend (network-free) + 21 frontend (incl. XSS-safety) |
| Policy anchors | WIPO IGC · 2024 WIPO GRATK Treaty · Nagoya Protocol/CBD · TKDL |

---

## 1. Positioning & "tell me about this project"

**Q1. In one sentence, what is TK-Shield?**
*Assessing: can you frame the project crisply?*

> "TK-Shield is a keyless, offline-first platform that helps communities, patent examiners, and researchers
> identify patents that may misappropriate documented traditional knowledge — by searching a patent corpus,
> scoring bio-piracy risk, gathering citable prior-art evidence, and drafting a patent opposition."

Then expand only if they want more: who it's for (three personas), and the proof (it independently re-flags the
turmeric, neem, and basmati patents that were historically revoked).

**Q2. Why did you build this — what's the motivation?**
*Assessing: is this connected to you, or a random portfolio app?*

> "I'm studying AI/ML and environmental science, and traditional-knowledge protection sits exactly at that
> intersection. Bio-piracy — patenting knowledge that communities have practised for generations — is a real,
> documented problem: turmeric for wound healing, neem as a pesticide, and basmati rice were all patented and
> later revoked, but only after expensive multi-year legal challenges. I wanted to see whether modern retrieval
> and a local language model could lower the cost of that defensive work so a community, not just a law firm,
> could do it. It's also directly aligned with WIPO's mandate, which is why I framed it the way I did."

**Q3. Who are the users?**
> "Three personas, one platform. **Defenders** — communities or NGOs — register a practice and get a risk
> report plus a draft opposition. **Examiners** — patent offices — paste a patent and get a novelty verdict
> against the documented-TK registry. **Researchers** explore aggregate analytics over the registry and corpus.
> They share the same backend but each has a distinct workflow."

---

## 2. Domain & WIPO understanding

**Q4. What is bio-piracy, and why does traditional knowledge need protection?**
*Assessing: domain depth — critical for WIPO.*

> "Bio-piracy is the appropriation of biological resources or associated traditional knowledge — usually from
> indigenous or local communities — through intellectual-property claims, without authorisation or benefit-
> sharing. Traditional knowledge is vulnerable because it's often oral, communally held, and 'undocumented' in
> the patent sense, so an examiner searching only prior patents and journals may not find it and may grant a
> patent over knowledge that isn't actually novel. Protection matters both ethically — communities lose control
> and benefit — and practically — wrongly granted patents can restrict the very communities that originated the
> practice."

**Q5. How does this relate to WIPO specifically?**
> "WIPO runs the **IGC** — the Intergovernmental Committee on IP, Genetic Resources, Traditional Knowledge and
> Folklore — whose central goal is preventing the erroneous grant of patents over TK. In 2024 WIPO adopted a new
> **Treaty on IP, Genetic Resources and Associated Traditional Knowledge**, which introduces a *disclosure-of-
> origin* requirement: patent applicants must disclose the source of genetic resources and associated TK.
> TK-Shield supports both — it's a defensive-protection tool that links a documented practice to the patents
> claiming it and assembles origin evidence. India's **TKDL** is the proven real-world model; I essentially
> built an open-data, open-model version of that defensive idea."

**Q6. How does community attribution fit in?**
*Assessing: do you understand benefit-sharing / Nagoya?*

> "Under the **Nagoya Protocol** and the CBD, access and benefit-sharing depends on knowing *which* community
> holds a practice. In my data, the Dr. Duke ethnobotany source encoded the holder group inside the country
> field — like `INDIA(SANTAL)`. I wrote a migration that splits that into a clean country plus a dedicated
> community field, so the Researcher view now surfaces documented communities and peoples — Santal, Seri,
> Kwakiutl, and so on — as a first-class dimension. That turns a data-formatting quirk into a feature that
> speaks to the attribution WIPO and Nagoya care about."

**Q7. Isn't it dangerous to claim software can 'prove' bio-piracy?**
*Assessing: judgment and ethics — this is a trap; answer carefully.*

> "Yes, and I was deliberate about not overclaiming. TK-Shield **supports early identification** of patents that
> *may* warrant expert review — it does not, and should not, claim to prove misappropriation. A risk score is a
> triage signal, the prior art is evidence for a human to weigh, and the drafted opposition is a starting point
> for a lawyer, not a filing. Legal determinations require human and legal review; I state that explicitly in the
> docs. Framing it as decision-support rather than a verdict is both more honest and more useful."

---

## 3. Machine learning & retrieval (the technical core)

**Q8. Walk me through the pipeline end to end.**
> "A documented practice goes in. First, **hybrid search**: I embed the query and run dense semantic retrieval
> over a vector store, and in parallel run lexical BM25 over the same corpus, then fuse the two ranked lists
> with **Reciprocal Rank Fusion**. Second, a **five-factor risk model** scores the match 0–100 and buckets it
> MINIMAL→CRITICAL. Third, **prior-art enrichment** fans out to PubMed, Wikidata, and GBIF for citable
> evidence. Fourth, a local LLM does **retrieval-augmented generation** — it writes a citation-backed assessment
> and a draft opposition from the retrieved context. All of it is exposed via a FastAPI backend and a React
> dashboard."

**Q9. Why hybrid search instead of pure semantic (embeddings) or pure keyword?**
*Assessing: do you understand the trade-off, or just use buzzwords?*

> "They fail in opposite ways. Pure **keyword/BM25** is precise on exact terms but misses synonyms and
> cross-lingual matches — 'haldi' wouldn't match 'turmeric', and a scientific name wouldn't match a folk name.
> Pure **semantic** embeddings capture meaning but can drift, and they under-weight rare but decisive exact
> tokens like a specific compound or species name. Traditional knowledge is full of both folk/multilingual names
> *and* precise botanical terms, so I needed both. Hybrid retrieval recovers the matches each method alone would
> miss."

**Q10. What is Reciprocal Rank Fusion and why use it over just averaging scores?**
> "RRF combines ranked lists using each item's **rank**, not its raw score: each list contributes
> `1 / (k + rank)` and you sum across lists. The key advantage is that semantic cosine similarities and BM25
> scores live on completely different, non-comparable scales — averaging them would let one dominate
> arbitrarily, and would need fragile normalisation. RRF only uses position, so it's robust to scale
> differences. I weight semantic 0.7 and BM25 0.3 because, in this domain, meaning-level matching is the primary
> signal and lexical matching is the corrective."

**Q11. What embeddings / model did you use, and why local?**
> "Sentence-transformers for the embeddings, ChromaDB as the persistent vector store with cosine distance, and
> Ollama running llama3.2 locally for the generation step. Local was a deliberate constraint: the whole point is
> that a community can run this for free, offline, with no API key and no data leaving their machine — which
> also matters when the data concerns indigenous knowledge. The trade-off is that a 3-billion-parameter local
> model is weaker than a frontier API model, so I made the system **degrade gracefully**: if the LLM is absent,
> the report falls back to a deterministic template and the figures and citations stay exact."

**Q12. Where exactly is the 'RAG' — what's retrieved and what's generated?**
*Assessing: can you point to retrieval concretely, not hand-wave?*

> "Retrieval is the hybrid patent search **plus** the prior-art enrichment from PubMed/Wikidata/GBIF — that
> assembled, citation-tagged context is the 'R'. Generation is the LLM step that takes that context plus the
> risk assessment and writes the narrative assessment and opposition draft — the 'G'. The model is constrained
> to the retrieved evidence and every citation carries a stable ID (PMID, Wikidata QID, GBIF key, or patent
> number), so the narrative is grounded rather than free-floating. If you remove the LLM, retrieval still
> produces the exact same figures and citations."

---

## 4. Risk scoring & evaluation

**Q13. Explain the risk model. Why those five factors?**
> "It's an interpretable weighted model, 0–100. **Similarity (40)** — how close the closest patents are, the
> dominant signal. **Temporal (20)** — was the patent filed *after* the knowledge was documented, which is what
> makes prior art relevant. **Geographic (15)** — overlap between the practice's region and the patent's origin.
> **Assignee (15)** — corporate/foreign assignees on a community practice raise the flag. **IPC (10)** — whether
> the patent's classification matches the practice's domain. I chose a transparent linear model over a black-box
> classifier on purpose: in a legal/policy context, an examiner has to be able to see *why* something scored
> high, and I didn't have labelled training data to justify anything heavier."

**Q14. How did you evaluate it? This is often the make-or-break question.**
> "I used the three landmark bio-piracy cases as ground truth — turmeric, neem, basmati — because each was
> independently, historically revoked, so we *know* the correct answer. For each, I wrote a traditional-
> knowledge description in **folk language that shares no wording with the patent**, then ran it through the full
> pipeline over the 16,371-patent corpus and checked whether the system retrieves the right patent and flags it
> high-risk. Results: **Precision@5 of 100%** — all three retrieved in the top five; **Precision@1 of 67%** —
> two of three as the single closest match; **MRR 0.833**; and **100% scored CRITICAL**. It's reproducible with
> one command and I wrote it up as a regression test."

**Q15. Why word the inputs independently — isn't that harder?**
*Assessing: do you understand evaluation leakage?*

> "Deliberately, yes. If I'd copied phrasing from the patent abstract, a top-1 retrieval would just be measuring
> string overlap, not real matching — that's data leakage and it would inflate the result dishonestly. By
> describing the practice the way a community actually would, a correct retrieval demonstrates genuine semantic
> plus lexical matching. The 67% Precision@1 — basmati lands at rank 2, not 1 — is actually *reassuring*: it
> shows the eval isn't rigged to look perfect."

**Q16. Three test cases is small. What are the limits of that evaluation?**
> "Completely fair. Three cases proves the system *can* recover known bio-piracy patents under realistic
> phrasing, which is the core claim — but it's a demonstration, not a statistical benchmark. It doesn't measure
> false-positive rate on the thousands of legitimate patents, and there's no large labelled dataset of
> 'misappropriating vs. clean' patents to compute precision/recall at scale — partly because that labelling is
> itself an expert legal judgment. Building a larger annotated benchmark, ideally with domain experts, is the
> most valuable next step, and I call that out as a limitation rather than papering over it."

---

## 5. System design & engineering

**Q17. Describe the architecture.**
> "Python/FastAPI backend, React/TypeScript frontend, served from one origin. Data lives in three stores kept
> consistent: a CSV that's the source of truth for patents, a **ChromaDB** vector collection for semantic
> search, and **SQLite** for the TK registry, with an in-memory **BM25** index built at startup. External data
> sources sit behind resilient HTTP clients. The LLM is pluggable behind an interface so Ollama can be swapped.
> Everything is module-imported under clean `src.*`/`api.*` packages, and store access is isolated so a future
> database swap stays localised."

**Q18. What does 'graceful degradation' mean here and why does it matter?**
*Assessing: reliability thinking.*

> "It's a hard rule in this project: no external API and not even the LLM may crash the pipeline. Every client
> returns empty or None on any failure instead of raising, the report notes which sources were skipped, and the
> LLM step falls back to a deterministic template. So the tool works offline, works when PubMed is down, and
> works with no model installed — it just produces a slightly thinner but still-valid report. For a tool aimed
> at low-resource users, that resilience is a feature, not a nice-to-have."

**Q19. You said 'production-ready' — what does that actually mean for this project?**
*Assessing: do you overclaim? (Define it; don't dodge.)*

> "I'd scope that carefully. For a **single-user, local deployment** — the actual target — it's solid: it's
> tested, inputs are validated and bounded, the database uses WAL mode and timeouts for safe concurrent access,
> the engine warms at startup so the first request is fast, and the frontend is hardened against XSS. For an
> **internet-exposed, multi-user** deployment it is *not* yet production-ready — it has no authentication, no
> rate limiting, and CORS is open. I made that a conscious, documented decision because the use case is local,
> and I flagged exactly what would gate a public deployment. Being precise about that boundary is part of the
> answer."

**Q20. How do you keep the three data stores consistent?**
> "The CSV is canonical for patents; re-running the indexer rebuilds ChromaDB and the BM25 index from it with
> the same strict filter, so all three stay in lock-step. For the registry, SQLite is the source of truth and
> the vector collection mirrors it — writes go through one store module that updates both, and my community-
> attribution migration updated SQLite and the vector metadata together. The rule I follow is: one source of
> truth per dataset, and one code path that fans out writes."

---

## 6. Security & reliability

**Q21. What security risks did you consider?**
*Assessing: do you think about safety, especially handling LLM/user text?*

> "The biggest one for this kind of app is **cross-site scripting**, because I render LLM output, user-pasted
> patent text, and external API data in the browser. I never inject any of that as raw HTML — the markdown
> renderer runs with no raw-HTML plugin, so an injected `<script>` or `<img onerror>` becomes inert text, and
> every external link is passed through a validator that only allows http/https, blocking `javascript:` and
> `data:` URLs. I also bounded all request inputs — capped text lengths and clamped the result-count parameter —
> so a malicious or accidental huge payload can't exhaust memory or pin the model. And I wrote regression tests
> that feed hostile strings through the renderer to make sure that protection can't silently regress."

**Q22. Any hardcoded secrets, tokens, or paths?**
> "No. The whole system is keyless by design, so there are no API keys to leak; the one optional live-monitoring
> feature reads a key from the environment and cleanly reports 'unavailable' when it's absent. Configuration is
> centralised in one config object sourced from environment variables with sensible defaults, and the local data
> directories, the database, and env files are gitignored. There are no credentials in the repo."

**Q23. What reliability issues did you fix?**
> "A few concrete ones I found and fixed: SQLite was opening bare connections, so under concurrent access it
> could throw 'database is locked' — I enabled WAL journaling and a busy timeout. Pagination ordered only by
> timestamp, and bulk imports created near-identical timestamps, so pages could repeat or skip — I added a
> stable tiebreaker. And the search engine built lazily on the first request, giving the first user a multi-
> second delay — I moved that warm-up into startup, so the first real request now responds in well under a
> second. Each came with a test."

---

## 7. AI-assisted development & your role

**Q24. You used an AI coding assistant. What was *your* contribution?**
*Assessing: honesty and ownership — answer this directly and confidently.*

> "I directed the engineering. I set the constraints — keyless, offline-first, graceful degradation, no
> overclaiming — and I made the product and architecture decisions: the three-persona structure, the choice of
> data sources, hybrid retrieval over pure embeddings, an interpretable risk model over a black box, and the
> security posture. I used the assistant to implement and to move fast, but I reviewed its output critically:
> I rejected an early childish UI and pushed it to a professional design system, I pushed back when it leaned on
> paid APIs and insisted on keyless alternatives, and I caught it when it over-claimed a data-quality problem
> from a misread screenshot and made it verify against the database instead. My value is judgment, domain
> understanding, and verification — which is exactly how senior engineers use these tools now."

**Q25. How do you make sure AI-generated code is correct and not, say, using fake data?**
> "I treat 'it ran' and 'it's correct' as different things. Concretely: I have the assistant read existing files
> before changing them, tell it explicitly what *not* to do, and require a verification step before anything is
> considered done — which files changed, what tests were run, what's still mocked or incomplete. The project has
> 48 backend tests and 21 frontend tests, all network-free so they're deterministic. And the data is real and
> traceable — 16,371 actual USPTO patents and a CC0 ethnobotany database — not synthetic; I can point to the
> source for every dataset. When I claim something works, I keep the command and the output."

**Q26. What would you do differently or improve next?**
> "Three things. First, a larger, expert-labelled evaluation set so I can report precision/recall at scale, not
> just on three cases. Second, broaden coverage beyond US patent metadata — non-US patents and full-text claims,
> and multilingual TK ingestion at scale. Third, for institutional use, add authentication, rate limiting, and
> continuous monitoring with alerts. The architecture already isolates data access behind interfaces so those
> are localised changes rather than rewrites."

---

## 8. Limitations, ethics & critical thinking

**Q27. What are the main limitations of TK-Shield?**
*Assessing: self-awareness — never answer 'none'.*

> "Several, and I'd rather state them than have them found. **Scope:** US patent metadata and English-language
> analysis, with a small local model. **Evaluation:** demonstrated on three landmark cases, not a large
> benchmark, so I can't yet quote a false-positive rate. **Risk model:** hand-weighted from domain reasoning,
> not learned from labelled data. **Legal:** it's decision-support — it flags candidates for expert review and
> does not establish misappropriation. **Data:** the ethnobotany source is broad but not exhaustive and skews to
> what's been documented in English-language databases, which itself under-represents some communities."

**Q28. Could this tool cause harm — false accusations, or exposing sensitive knowledge?**
*Assessing: ethical maturity.*

> "Both are real risks I'd manage explicitly. False positives are why I frame outputs as triage for human
> review, never as proof — a high score starts an inquiry, it doesn't end one. On sensitive knowledge: the tool
> is defensive and works offline with no data leaving the machine, which is deliberate, because publishing
> certain sacred or secret traditional knowledge to 'document' it can itself be harmful. So 'document everything
> publicly' is not automatically the right answer; the right model is community-controlled, and a real
> deployment would need community consent and governance baked in, not just technology."

**Q29. How would you handle a community that doesn't want its knowledge digitised at all?**
> "I'd respect it — that's the core principle of free, prior, and informed consent. The tool's value is
> defensive, and there's a genuine tension between documenting knowledge to establish prior art and exposing
> knowledge that should stay restricted. The offline, keyless, single-machine design exists precisely so a
> community can run it on their own terms without surrendering their data to a third party. Any institutional
> version would need consent and access governance as a first-class feature, not an afterthought."

---

## 9. Behavioural / fit (especially WIPO)

**Q30. Why do you want to work at WIPO, and how does this project show it?**
> "My background is AI/ML plus environmental science, and TK-Shield is where those meet a real WIPO problem —
> defensive protection of traditional knowledge and genetic resources. Rather than just say I'm interested in
> the IGC's work or the 2024 treaty, I built something that operationalises it with open data and open models.
> It shows I understand the policy context, I can turn it into a working system, and I care about the
> communities the system is meant to serve — not just the technology."

**Q31. What was the hardest part?**
> "Honestly, judgment under uncertainty — knowing when to *stop* trusting a tool and verify. The clearest
> example: I flagged the registry data as 'garbled' based on a low-resolution screenshot, then checked the
> actual database and found the data was fine and I'd misread it. I corrected the claim, and the real underlying
> insight — that community names were buried in the country field — turned into the community-attribution
> feature. The hard, and important, part was being willing to be wrong and verify rather than ship a confident
> mistake."

**Q32. Sell me the project in 30 seconds.**
> "Bio-piracy — patenting traditional knowledge — has cost communities for decades, and fighting it has meant
> expensive legal battles. TK-Shield puts that defensive capability in anyone's hands: describe a practice, and
> it finds the patents that may claim it, scores the risk, gathers citable prior-art evidence, and drafts an
> opposition — for free, offline, no API keys. It independently re-flags the famous turmeric, neem, and basmati
> patents that were all eventually revoked. It's built to support exactly the defensive-protection mission of
> the WIPO IGC and the 2024 treaty."

---

## How to use this

- Read for *understanding*, then practise answering out loud in your own words — interviewers can tell scripted
  from understood.
- For any technical answer, be ready for one follow-up "why?" — the answers above include the reasoning so you
  can go one level deeper.
- If you don't know something, say so and reason about it — that reads far better than bluffing, especially
  given you're honest about directing an AI-assisted build.
- Keep the **"assists review, not proves theft"** distinction front of mind for any WIPO conversation.
