import { useState } from "react";
import {
  Download,
  FileText,
  Radar,
  Sparkles,
  Zap,
} from "lucide-react";
import { useAnalyze, useMonitor, useReport, useTkEntry } from "@/api/hooks";
import { apiPostText } from "@/api/client";
import { Button } from "@/components/Button";
import { Card } from "@/components/Card";
import { SectionHeader } from "@/components/SectionHeader";
import { Spinner } from "@/components/Spinner";
import { EmptyState } from "@/components/EmptyState";
import { ErrorState } from "@/components/ErrorState";
import { LoadingStages } from "@/components/LoadingStages";
import { CopyButton } from "@/components/CopyButton";
import { Markdown } from "@/lib/markdown";
import { dash } from "@/lib/format";
import { RiskScorecard } from "./RiskScorecard";
import { PatentTable } from "./PatentTable";
import { CitationList } from "./CitationList";

type View = "analyze" | "report" | "monitor" | null;

const REPORT_STAGES = [
  "Searching the patent corpus",
  "Scoring bio-piracy risk",
  "Gathering prior-art evidence (PubMed · Wikidata · GBIF)",
  "Drafting the assessment & opposition",
];

// The Defender workspace for a single entry: metadata + NER, an action toolbar,
// and the results of whichever defensive check was run. Remounted per entry
// (keyed by tk_id) so state resets cleanly when switching practices.
export function EntryWorkspace({ tkId }: { tkId: string }) {
  const entry = useTkEntry(tkId);
  const analyze = useAnalyze();
  const report = useReport();
  const monitor = useMonitor();
  const [view, setView] = useState<View>(null);
  const [exporting, setExporting] = useState(false);
  const [exportError, setExportError] = useState<string | null>(null);

  if (entry.isPending) return <Spinner label="Loading entry…" />;
  if (entry.isError)
    return <ErrorState error={entry.error} onRetry={() => entry.refetch()} />;

  const e = entry.data;
  const body = { tk_id: tkId, n_results: 5 };

  async function exportMarkdown() {
    setExporting(true);
    setExportError(null);
    try {
      // Reuse the already-generated report's markdown if present, so export
      // doesn't re-run the slow (tens-of-seconds) report pipeline (F5).
      const md =
        report.data?.markdown ??
        (await apiPostText("/api/report?format=markdown", body));
      const url = URL.createObjectURL(
        new Blob([md], { type: "text/markdown" }),
      );
      const a = document.createElement("a");
      a.href = url;
      a.download = `${tkId}-report.md`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      setExportError(err instanceof Error ? err.message : "Export failed.");
    } finally {
      setExporting(false);
    }
  }

  return (
    <div className="mx-auto max-w-4xl space-y-5">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-primary">
          {e.practice_name}
        </h1>
        <p className="mt-1 text-sm text-muted">
          {e.tk_id} · {dash(e.community)} · {dash(e.country)} ·{" "}
          {dash(e.documentation_date)}
          {e.domain && (
            <span className="ml-2 rounded-sm bg-neutral px-1.5 py-0.5 text-xs text-secondary">
              {e.domain}
            </span>
          )}
        </p>
      </div>

      {e.description && (
        <p className="text-sm leading-relaxed text-secondary">{e.description}</p>
      )}

      <div className="rounded-md border border-border bg-surface">
        <div className="flex items-center gap-2 border-b border-border px-4 py-2.5">
          <Sparkles className="h-4 w-4 text-tertiary" strokeWidth={1.75} />
          <h2 className="text-sm font-semibold tracking-tight text-primary">
            Auto-extracted (NER)
          </h2>
        </div>
        <dl className="grid grid-cols-[110px_1fr] gap-y-2 px-4 py-3 text-sm">
          <dt className="text-muted">Plants</dt>
          <dd className="text-secondary">{e.plants.join(", ") || "—"}</dd>
          <dt className="text-muted">Uses</dt>
          <dd className="text-secondary">{e.uses.join(", ") || "—"}</dd>
          <dt className="text-muted">Locations</dt>
          <dd className="text-secondary">{e.locations.join(", ") || "—"}</dd>
          <dt className="text-muted">Aliases</dt>
          <dd className="text-secondary">{e.aliases.join(", ") || "—"}</dd>
        </dl>
      </div>

      {/* action toolbar */}
      <div className="flex flex-wrap gap-2">
        <Button
          onClick={() => {
            setView("analyze");
            analyze.mutate(body);
          }}
        >
          <Zap className="h-4 w-4" strokeWidth={2} />
          Quick risk check
        </Button>
        <Button
          variant="secondary"
          onClick={() => {
            setView("report");
            report.mutate(body);
          }}
        >
          <FileText className="h-4 w-4" strokeWidth={1.75} />
          Full report
        </Button>
        <Button
          variant="secondary"
          onClick={() => {
            setView("monitor");
            monitor.mutate({ tk_id: tkId, n_results: 10 });
          }}
        >
          <Radar className="h-4 w-4" strokeWidth={1.75} />
          Live monitor
        </Button>
        <Button variant="secondary" onClick={exportMarkdown} disabled={exporting}>
          <Download className="h-4 w-4" strokeWidth={1.75} />
          {exporting ? "Exporting…" : "Export markdown"}
        </Button>
      </div>

      {exportError && (
        <p className="text-xs text-red-700">Export failed: {exportError}</p>
      )}

      {view === "analyze" && <AnalyzeResult m={analyze} />}
      {view === "report" && <ReportResult m={report} />}
      {view === "monitor" && <MonitorResult m={monitor} />}
      {view === null && (
        <p className="text-sm text-muted">
          Run a defensive check above to assess this practice against the patent
          corpus.
        </p>
      )}
    </div>
  );
}

function AnalyzeResult({ m }: { m: ReturnType<typeof useAnalyze> }) {
  if (m.isPending)
    return <Spinner label="Running hybrid search + risk scoring…" />;
  if (m.isError) return <ErrorState error={m.error} />;
  if (!m.data) return null;
  return (
    <div className="space-y-5">
      <RiskScorecard risk={m.data.risk} />
      <div>
        <SectionHeader title="Closest patents" />
        <PatentTable patents={m.data.patents} />
      </div>
    </div>
  );
}

function ReportResult({ m }: { m: ReturnType<typeof useReport> }) {
  if (m.isPending)
    return (
      <Card>
        <LoadingStages stages={REPORT_STAGES} />
      </Card>
    );
  if (m.isError) return <ErrorState error={m.error} />;
  if (!m.data) return null;
  const r = m.data;

  return (
    <div className="space-y-5">
      <RiskScorecard risk={r.risk} />

      {!r.llm_used && (
        <p className="rounded-sm border border-border bg-neutral/50 px-3 py-2 text-xs text-secondary">
          AI narrative generated offline (LLM unavailable) — figures and
          citations are exact.
        </p>
      )}

      {r.unverified_citation_refs && r.unverified_citation_refs.length > 0 && (
        <p className="rounded-sm border border-amber-300 bg-amber-50 px-3 py-2 text-xs text-amber-800">
          ⚠️ The AI narrative referenced identifier(s) not in the verified
          citation list ({r.unverified_citation_refs.join(", ")}). Treat the
          narrative as a draft — rely on the prior-art citations below as the
          authoritative evidence.
        </p>
      )}

      <Card>
        <SectionHeader title="Assessment" icon={FileText} />
        <Markdown>{r.assessment || "No assessment generated."}</Markdown>
      </Card>

      <div>
        <SectionHeader title="Closest patents" />
        <PatentTable patents={r.top_patents} />
      </div>

      <Card>
        <SectionHeader
          title="Prior-art citations"
          meta={
            r.sources_skipped.length
              ? `${r.sources_skipped.join(", ")} returned nothing this run`
              : undefined
          }
        />
        <CitationList citations={r.citations} />
      </Card>

      <Card>
        <SectionHeader
          title="Draft opposition / defensive publication"
          action={<CopyButton text={r.opposition_draft} />}
        />
        <pre className="whitespace-pre-wrap border-l-2 border-border pl-3 text-sm leading-relaxed text-secondary">
          {r.opposition_draft || "—"}
        </pre>
      </Card>
    </div>
  );
}

function MonitorResult({ m }: { m: ReturnType<typeof useMonitor> }) {
  if (m.isPending) return <Spinner label="Checking live patents…" />;
  if (m.isError) return <ErrorState error={m.error} />;
  if (!m.data) return null;
  const d = m.data;

  return (
    <Card>
      <SectionHeader title="Live patent monitor" icon={Radar} />
      <p className="text-sm text-secondary">{d.note}</p>
      {d.patents.length > 0 && (
        <ul className="mt-3 divide-y divide-border text-sm">
          {d.patents.map((p) => (
            <li key={p.id} className="py-2">
              <span className="font-medium text-primary">
                {dash(p.metadata.patent_id || p.id)}
              </span>
              <span className="text-secondary"> — {dash(p.metadata.title)}</span>
            </li>
          ))}
        </ul>
      )}
      {!d.available && d.patents.length === 0 && (
        <EmptyState
          title="Live monitoring is off"
          hint="This optional feature needs a PatentsView API key. The rest of TK-Shield runs fully keyless."
        />
      )}
    </Card>
  );
}
