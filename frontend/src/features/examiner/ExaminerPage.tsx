import { useState } from "react";
import { Scale, Search } from "lucide-react";
import { useNovelty } from "@/api/hooks";
import { Button } from "@/components/Button";
import { Card } from "@/components/Card";
import { SectionHeader } from "@/components/SectionHeader";
import { ErrorState } from "@/components/ErrorState";
import { LoadingStages } from "@/components/LoadingStages";
import { EmptyState } from "@/components/EmptyState";
import { Table, Td, Th } from "@/components/Table";
import { Markdown } from "@/lib/markdown";
import { dash } from "@/lib/format";
import { VerdictBadge } from "./VerdictBadge";

const MIN_LEN = 20;
const STAGES = [
  "Searching the documented TK registry",
  "Ranking prior-art matches",
  "Assessing novelty",
];

// Examiner — paste a patent's text and reverse-look it up against documented TK
// to judge novelty. The LLM-backed assessment is rendered through the safe
// markdown path (no raw HTML).
export function ExaminerPage() {
  const novelty = useNovelty();
  const [text, setText] = useState("");
  const tooShort = text.trim().length > 0 && text.trim().length < MIN_LEN;

  function check() {
    if (text.trim().length < MIN_LEN) return;
    novelty.mutate({ patent_text: text.trim(), n_results: 5 });
  }

  return (
    <div className="mx-auto max-w-3xl px-6 py-8">
      <div className="flex items-center gap-2">
        <Scale className="h-5 w-5 text-tertiary" strokeWidth={1.5} />
        <h1 className="text-xl font-semibold tracking-tight text-primary">
          Patent novelty vs documented TK
        </h1>
      </div>
      <p className="mt-1 text-sm text-secondary">
        Paste a patent's title, abstract, or claims. TK-Shield searches the
        Traditional-Knowledge registry for prior art and judges novelty.
      </p>

      <textarea
        aria-label="Patent text"
        className="mt-5 min-h-36 w-full rounded-sm border border-border bg-surface px-3.5 py-3 text-sm leading-relaxed text-text placeholder:text-muted focus:border-primary"
        placeholder="Paste patent title + abstract / claim text here…"
        value={text}
        onChange={(e) => setText(e.target.value)}
      />
      <div className="mt-2 flex items-center gap-3">
        <Button onClick={check} disabled={tooShort || text.trim().length === 0}>
          <Search className="h-4 w-4" strokeWidth={2} />
          Check novelty
        </Button>
        {tooShort && (
          <span className="text-xs text-error">
            Add more text — at least {MIN_LEN} characters for a meaningful check.
          </span>
        )}
      </div>

      <div className="mt-6">
        {novelty.isPending ? (
          <Card>
            <LoadingStages stages={STAGES} />
          </Card>
        ) : novelty.isError ? (
          <ErrorState error={novelty.error} />
        ) : novelty.data ? (
          <NoveltyResult data={novelty.data} />
        ) : null}
      </div>
    </div>
  );
}

function NoveltyResult({ data }: { data: NonNullable<ReturnType<typeof useNovelty>["data"]> }) {
  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center gap-3">
        <VerdictBadge verdict={data.verdict} />
        <span className="text-sm text-muted">
          {data.confidence} confidence · top similarity{" "}
          <span className="tabular-nums text-secondary">
            {data.top_similarity.toFixed(2)}
          </span>
        </span>
      </div>

      <Card>
        <SectionHeader title="Assessment" icon={Scale} />
        <Markdown>{data.assessment || "No assessment generated."}</Markdown>
        {!data.llm_used && (
          <p className="mt-2 text-xs text-muted">
            Offline narrative (LLM unavailable); similarity figures are exact.
          </p>
        )}
      </Card>

      <div>
        <SectionHeader title="Matching TK prior art" />
        {data.matches.length === 0 ? (
          <EmptyState title="No documented TK matched this patent text." />
        ) : (
          <div className="overflow-x-auto rounded-md border border-border">
            <Table>
              <thead>
                <tr className="bg-neutral/60">
                  <Th>TK ID</Th>
                  <Th>Practice</Th>
                  <Th>Domain</Th>
                  <Th>Country</Th>
                  <Th className="text-right">Sim.</Th>
                </tr>
              </thead>
              <tbody>
                {data.matches.map((m) => (
                  <tr key={m.tk_id} className="hover:bg-neutral/40">
                    <Td className="whitespace-nowrap font-medium text-primary">
                      {m.tk_id}
                    </Td>
                    <Td className="text-secondary">{m.practice_name}</Td>
                    <Td className="text-secondary">{dash(m.domain)}</Td>
                    <Td className="text-secondary">{dash(m.country)}</Td>
                    <Td className="text-right tabular-nums text-muted">
                      {m.similarity.toFixed(2)}
                    </Td>
                  </tr>
                ))}
              </tbody>
            </Table>
          </div>
        )}
      </div>
    </div>
  );
}
