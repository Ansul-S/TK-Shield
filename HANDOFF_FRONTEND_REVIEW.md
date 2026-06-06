# TK-Shield — Frontend Review & Production-Readiness Handoff

> **For the next session.** Your mission: act as Principal Frontend Engineer / Accessibility & Performance Reviewer / Security Auditor for the **newly built React frontend**. **Do not add features** unless required to fix a critical issue — the personas are functionally complete. Find what can break, mislead, leak, regress, or fail to scale in the UI layer. For each issue: root cause → impact → severity → recommended fix → implement when appropriate. **Challenge assumptions; verify in a real browser — don't assume the UI is correct because it rendered once.** Read `CLAUDE.md` (architecture), `HANDOFF_FRONTEND.md` (original frontend brief + the authoritative API contract in its §4), and `HANDOFF_REVIEW.md` (backend audit) before starting.
>
> This document is an honest self-audit by the engineer who built the frontend: a map of where to look. It is a starting point, **not** exhaustive — treat each item as a lead to verify and expand, and hunt for what's not here.

---

## 0. Snapshot

- **Stack:** Vite 6 + React 18 + TypeScript (strict), React Router 6 (`createBrowserRouter`), TanStack Query 5, Tailwind CSS v4 (`@tailwindcss/vite`), Radix UI primitives (Tabs were planned but nav is plain `NavLink`; Tooltip is used), Lucide icons, `react-markdown`, self-hosted Inter (`@fontsource-variable/inter`). Build pinned via `package-lock.json`; **no runtime CDN.**
- **Where:** all UI lives under `frontend/`. Source in `frontend/src` (39 files). The previous single-file vanilla UI is archived at `frontend/legacy/index.html` (porting reference, not served unless no build exists).
- **Serving:** `api/main.py` serves `frontend/dist` when built, with a catch-all that returns `index.html` for non-`/api` client routes (deep-link refresh works); otherwise it falls back to the legacy file. Backend routes and the 37 backend tests are **unchanged** by the frontend work.
- **State:** committed on branch `feat/biopiracy-monitoring-platform` (commit `e668127`), pushed to origin.
- **What's NOT here:** no frontend tests, no ESLint/Prettier, no CI for the frontend, no error boundary, no route-level code-splitting, no request cancellation. (Details + severities in §8.)

Verified live during the build (Vite dev :5173 proxying `/api` → :8000, Chrome at 1440×900): onboarding, role nav routing, header health dots, Defender registry list + register + quick risk check + full RAG report (assessment/citations/opposition) + monitor, Examiner novelty verdict + matches, Researcher analytics. Zero console errors observed. **This is "happy-path observed once," not a test suite — re-verify.**

---

## 1. What was built

A single-origin SPA with a role switcher for the three personas (`HANDOFF_FRONTEND.md` §2).

- **Onboarding / landing** (`/`) — full-bleed sunset hero (optimized 165 KB WebP) with the nav overlaid in white, a dark gradient for legible text, and three role-selection cards on the white section below.
- **Defender** (`/defender`, `/defender/:tkId`) — registry browse (search + offset pager), register form (NER auto-extract revealed after create), and a per-entry **workspace**: Quick risk check (`/analyze`), Full RAG report (`/report?format=json`) with staged loading, assessment (safe markdown), prior-art citations (validated links), copyable opposition draft, markdown export, and Live monitor (`/monitor`, graceful keyless state).
- **Examiner** (`/examiner`) — paste patent text → `/novelty` → verdict badge + confidence + matching TK prior-art table + safe-markdown assessment, with staged loading for the slow LLM path and a client-side min-length guard.
- **Researcher** (`/researcher`) — `/stats` analytics: registry/corpus totals, domain/source distribution bars, top countries, top assignees table.

---

## 2. Architecture & file map

Feature-first. The seams that matter for review:

```
frontend/
  vite.config.ts        # @/ alias, /api dev proxy → :8000, build → dist
  src/
    main.tsx            # QueryClient (staleTime 30s, retry 1) + RouterProvider; imports Inter + globals.css
    api/
      types.ts          # hand-written mirror of the API contract (HANDOFF_FRONTEND.md §4)
      client.ts         # fetch wrapper; ApiError{detail,status}; apiPostText for markdown/pdf
      hooks.ts          # TanStack Query hooks (queries + mutations) + query keys
    lib/
      markdown.tsx      # SAFE react-markdown wrapper (no raw HTML) — XSS-critical
      url.ts            # safeHref(): http(s)-only — XSS-critical for citation links
      risk.ts           # CRITICAL→MINIMAL color scale (derived; not in Duna spec)
      format.ts         # dash()/cap()/trunc() — nan/empty → "—"
      cn.ts             # className joiner
    components/         # design-system primitives (Button, Card, Badge/RiskBadge,
                        #   StatusDot, Spinner/Skeleton, EmptyState, ErrorState,
                        #   Pager, SearchBox, LoadingStages, Table, SectionHeader, CopyButton, DistributionBar)
    app/
      AppShell.tsx      # header (brand + role nav + health dots); transparent overlay on "/", solid elsewhere
      roles.ts          # single source of truth for the 3 personas (icon/label/copy)
      routes.tsx        # router config (incl. /defender/:tkId, * not-found)
    features/
      onboarding/RoleSelect.tsx
      defender/{DefenderPage,EntryWorkspace,RegisterForm,RiskScorecard,PatentTable,CitationList}.tsx
      examiner/{ExaminerPage,VerdictBadge}.tsx
      researcher/ResearcherPage.tsx
    styles/globals.css  # Tailwind import + @theme Duna tokens + risk tokens
    assets/hero-background.webp
```

**Key conventions:**
- All server state goes through TanStack Query hooks in `api/hooks.ts`; components never `fetch` directly.
- `EntryWorkspace` is remounted per entry via `key={tkId}` so analyze/report/monitor mutation state resets cleanly when switching practices.
- The landing route gets a transparent overlay header (white text) via `useLocation()` in `AppShell`; all other routes get the solid enterprise header.

---

## 3. How to run / verify

```bash
# Dev (HMR): two processes
venv/bin/uvicorn api.main:app --reload        # backend + /api at :8000  (PYTHONPATH=. if 'No module named src')
npm --prefix frontend install                 # one-time
npm --prefix frontend run dev                 # SPA at http://localhost:5173 (proxies /api → :8000)

# Production-style (single origin)
npm --prefix frontend run build               # tsc -b && vite build → frontend/dist
venv/bin/uvicorn api.main:app                 # serves dist + /api at :8000

npm --prefix frontend run typecheck           # tsc only (no emit)
```

There is **no `lint` or `test` script** (see §8/§10). `npm run build` runs `tsc -b` first, so type errors fail the build — that is currently the only automated gate.

---

## 4. API binding — verify contract adherence

`src/api/types.ts` is a **hand-written** mirror of the contract (`HANDOFF_FRONTEND.md` §4), not generated. Risk: silent drift if the backend changes shape.
- **Verify** each hook's request/response against `/openapi.json` and `/docs`. Endpoints used: `GET /api/health` (polled 15s), `GET /api/tk` (paginated), `GET /api/tk/{id}`, `POST /api/tk`, `POST /api/analyze`, `POST /api/report?format=json|markdown`, `POST /api/novelty`, `POST /api/monitor`, `GET /api/stats`. (`DELETE /api/tk/{id}` hook exists but is **not wired to any UI** — no delete affordance yet.)
- Consider migrating to `openapi-typescript` against `/openapi.json` to kill drift (noted in code comments).
- `n_results` is hard-coded (5 for analyze/report, 10 for monitor). The backend does **not** clamp it (backend audit S3) — not exploitable from this UI, but don't expose it as free input without a bound.

---

## 5. Security posture (the part to scrutinize hardest)

The original brief's **S2 (DOM XSS via unescaped LLM/user/API text)** was the #1 frontend risk. Current posture:
- **No `dangerouslySetInnerHTML` anywhere.** Grep to confirm it stays that way — this is the core invariant.
- LLM/assessment narrative renders through `src/lib/markdown.tsx` → `react-markdown` **with no `rehype-raw`**, so injected `<script>`/`<img onerror>` is inert text. **Verify** no future change adds a raw-HTML plugin.
- Citation/link hrefs go through `src/lib/url.ts` `safeHref()`, which allows only `http:`/`https:` (blocks `javascript:`, `data:`). Used in `CitationList`. **Verify** every place that renders an external/LLM-supplied URL uses it.
- **Recommended:** add regression tests that feed hostile strings (`<img src=x onerror=...>`, `javascript:alert(1)`, `[x](javascript:...)`) through the markdown component and `safeHref`, asserting no script/inline-handler and a nulled href. This is the highest-value test to add (§10).
- Inherited backend items still apply to a deployed UI: **CORS `*`**, **no auth**, unbounded expensive endpoints (backend audit S1/S3/S5). The frontend assumes same-origin trust; if this is ever exposed, coordinate with the backend audit.

---

## 6. Accessibility posture (built-in, but needs a real audit)

Done deliberately: interactive elements are real `<button>`/`<a>` (no clickable `<div>`s — fixed the legacy gap); inputs have `aria-label`s; Radix Tooltip/`StatusDot` are keyboard/SR-accessible; a global `:focus-visible` ring is defined in `globals.css`.

**Not yet audited — verify:**
- **Color contrast.** `text-tertiary` (#8F8A83) and `text-muted` (#9A948B) on white are light — check small text (card meta, table secondary cells, the uppercase labels) against WCAG AA (4.5:1). The hero's white text sits on a dark gradient — check the *lightest* part of the image under the text.
- The hero **glass chip** (`text-white` on `white/10`) and `text-white/85` subtitle over imagery — contrast varies with the photo; verify legibility.
- Keyboard flow through the Defender sidebar (search → register toggle → entry buttons → pager) and focus management when the register form opens/closes.
- `alt=""`/`aria-hidden` on the hero image is intentional (decorative) — confirm that's the right call.
- Tables: consider `scope="col"` on `<Th>` and a caption/summary for SR users.
- No skip-link to main content; no reduced-motion handling for the `animate-spin`/`animate-pulse` and smooth-scroll.

---

## 7. Performance

- **Bundle:** one JS chunk ~**460 KB (≈146 KB gzip)** — React + Router + Query + `react-markdown` + all routes in a single entry. **No route-level code-splitting** (`React.lazy`/dynamic import). `react-markdown` (+ micromark) is the heaviest dep and is only needed on report/novelty views — a prime candidate to lazy-load. Recommend splitting routes and/or lazy-loading the markdown renderer.
- **Hero image:** optimized to **165 KB WebP** (from a 2.3 MB PNG). Consider a `loading`/decoding strategy and an explicit width/height or aspect-ratio to avoid layout shift; consider a low-res blur placeholder.
- **Health polling:** `useHealth` refetches every **15 s** indefinitely while the app is open. Fine, but it's unconditional (even on hidden tabs, since `refetchOnWindowFocus` is off but interval still runs). Consider pausing when `document.hidden`.
- **Slow endpoints:** `/report` and `/novelty` are 15–45 s synchronous backend calls. The UI shows `LoadingStages`, but there is **no client-side timeout or `AbortController`** — a hung request spins forever, and navigating away does not cancel it. Recommend an abort + deadline.
- **`LoadingStages` is timer-based** (advances on a fixed interval), not tied to real backend progress — it can finish its stages before the response or still be "drafting" after it returns. Cosmetic, but can mislead; document or wire to real signals if the backend ever streams.

---

## 8. Known gaps / not-yet-built (leads to verify, with severity)

- **F1 — No frontend tests at all. (High for production)** No unit/component/e2e, no runner. The XSS-safety (`markdown`/`safeHref`), `format.dash()` nan-handling, risk/verdict color mapping, and pager math are all untested. See §10.
- **F2 — No error boundary. (Medium)** A render-time throw in any feature blanks the whole SPA (white screen) with only a console error. Add a React error boundary (router `errorElement` or a top-level boundary in `AppShell`).
- **F3 — No ESLint/Prettier/CI for the frontend. (Medium)** There's a stray `// eslint-disable-next-line` in `SearchBox.tsx` but ESLint isn't installed. No formatting gate. Type-check is the only gate. Add ESLint (react-hooks rules especially) + a CI step running `typecheck` + `build`.
- **F4 — No route-level code-splitting. (Medium, perf)** See §7.
- **F5 — Export markdown re-runs the full slow report. (Medium, UX)** `EntryWorkspace.exportMarkdown()` calls `/report?format=markdown` fresh (15–45 s) even if the user just generated the JSON report; the button only shows "Exporting…". Reuse the already-fetched report's `markdown` field, or warn about the wait. Also no error surface if export fails (silent `finally`).
- **F6 — PDF export not wired. (Low, feature gap)** Backend supports `/report?format=pdf`; the UI only offers markdown.
- **F7 — DELETE TK not wired. (Low)** `useDeleteTk` exists; no UI uses it. Either add a guarded delete affordance or remove the dead hook.
- **F8 — Clipboard copy fails silently. (Low)** `CopyButton` no-ops in insecure contexts / when `navigator.clipboard` is unavailable; no fallback or message.
- **F9 — Reference images in git history. (Low, repo hygiene)** `Frontend_Insp/Refrence.png` (3.7 MB) + `Background.png` (2.3 MB) ≈ 6 MB are committed. The app uses only the 165 KB WebP; the PNGs are design references. Drop them if repo size matters.
- **F10 — Hero `92vh` + hard dark→white section edge.** This is a deliberate design decision (per user feedback, replacing a washed-out white fade), not a bug — but review on short/tall viewports and very wide screens for awkward cropping.

---

## 9. Correctness & edge cases to check

- **Pagination stability:** the Defender list uses offset paging and trusts the backend's stable order (backend audit D1 was fixed with a `tk_id` tiebreaker — confirm it's deployed, or pages can repeat/skip). `placeholderData` keeps the old page visible during fetch — verify no flicker/stale-selection bugs.
- **Empty/`nan` rendering:** `dash()` covers `""`/`nan`/`none`. Spot-check entries with no country/date/plants, "Unknown" assignees, and very long patent titles (truncation + tooltip in `PatentTable`).
- **Graceful degradation (must stay non-error states):** `health.llm_available=false` (report still works, offline note shown), `monitor.available=false` (keyless empty state, not an error), `report.sources_skipped` (surfaced as meta), `llm_used=false` (offline-narrative note). Re-verify each with the backend in those states.
- **Examiner 400 path:** min-length guard is client-side only (`MIN_LEN=20`); confirm the server's own 400 (empty text) surfaces cleanly via `ErrorState` if it slips through.
- **Deep-link refresh:** hard-refresh on `/defender/TK-xxxx` must serve the SPA (catch-all in `api/main.py`) — verify against the built `dist`, not just the dev server.
- **First `/analyze` after server start** is slow (lazy BM25 build) — the UI just shows a spinner; confirm it doesn't look hung.
- **Switching personas mid-request:** navigating away from a slow report/novelty doesn't cancel it (no abort) — verify no state-update-after-unmount warnings.

---

## 10. Testing gaps — what to add

There are **zero** frontend tests. Highest-value additions, roughly in order:
1. **XSS safety (security):** `markdown.tsx` and `safeHref()` against hostile inputs (see §5). Vitest + Testing Library.
2. **`format.dash()`** nan/empty/none → `—`.
3. **`risk.ts` / `VerdictBadge`** level/verdict → class mapping (and an unknown-value fallback).
4. **`Pager`** range math + disabled edges; hidden when `total ≤ limit`.
5. **Component smoke + MSW:** each persona renders loading/empty/error/success against mocked endpoints (esp. graceful-degradation states from §9).
6. A typecheck + build CI gate (§F3).

Recommended toolchain: Vitest + @testing-library/react + MSW (all dev-only, bundled — consistent with the no-CDN posture).

---

## 11. Design-system notes (so a reviewer doesn't "fix" intent)

- **"Duna Light"** (`Frontend_Insp/duna.com-design.md`): light, airy, editorial, **flat (no shadows)**, hierarchy via scale + negative letter-spacing, **regular weight** (avoid bold for hierarchy). Tokens live in `src/styles/globals.css` `@theme`; `src/lib/risk.ts` holds the risk scale. Two intentional adaptations: (a) **Inter** self-hosted substitutes the licensed **GT America** (swap if a license exists — one token + one import); (b) the **risk/verdict color scale** is *derived* (not in the Duna palette) as restrained tinted chips — kept legible without "loud saturated UI colors."
- The **landing hero** intentionally departs from the rest of the (light) system: dark gradient + white text over the photo. This was a deliberate iteration after a white-fade version looked washed out. Don't "restore" a white fade.

---

## 12. Suggested triage order

1. **F1 (XSS-safety tests) + the security verifications in §5** — small, highest-value, protects the core invariant.
2. **F2 (error boundary)** — cheap; prevents whole-app white-screens.
3. **§6 contrast audit** — fix any AA failures on `tertiary`/`muted` text and hero overlay.
4. **F5 (export reuses report) + F7 (delete hook)** — small UX/dead-code cleanups.
5. **F3 (ESLint + CI gate)** then **F4 (code-split / lazy markdown)** — quality + perf.
6. **§7 abort/timeout on slow calls** — reliability.
7. **Deployment-gating (inherited):** auth, CORS, rate-limiting — coordinate with `HANDOFF_REVIEW.md`; don't build auth UI unless the target demands it.

---

## 13. What NOT to break

- The **API contract** in `HANDOFF_FRONTEND.md` §4 — bind to it as-is; coordinate any backend change.
- The **XSS invariant**: never `dangerouslySetInnerHTML` server/LLM/user text; markdown stays raw-HTML-free; external hrefs stay `safeHref`-validated.
- **Graceful degradation** (LLM off, monitor keyless, sources skipped) — these are features; keep them as calm, non-error states.
- **Keyless / offline-first / no runtime CDN** — fonts/icons/deps are bundled at build; don't introduce a runtime third-party fetch for the app to function.
- The **deep-link SPA fallback** in `api/main.py` and the pinned `package-lock.json` build.
