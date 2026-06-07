import { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { Plus, ShieldCheck, X } from "lucide-react";
import { useTkEntries } from "@/api/hooks";
import { PAGE_SIZE } from "@/config";
import { SearchBox } from "@/components/SearchBox";
import { Pager } from "@/components/Pager";
import { Skeleton } from "@/components/Spinner";
import { EmptyState } from "@/components/EmptyState";
import { ErrorState } from "@/components/ErrorState";
import { dash } from "@/lib/format";
import { cn } from "@/lib/cn";
import { RegisterForm } from "./RegisterForm";
import { EntryWorkspace } from "./EntryWorkspace";

// Defender — register documented TK, browse the registry, and run defensive
// checks (risk score, full RAG report, live monitor, export) against the
// patent corpus.
export function DefenderPage() {
  const { tkId } = useParams();
  const navigate = useNavigate();
  const [q, setQ] = useState("");
  const [offset, setOffset] = useState(0);
  const [adding, setAdding] = useState(false);

  const list = useTkEntries(q, PAGE_SIZE, offset);

  return (
    <div className="grid h-full grid-cols-1 md:grid-cols-[300px_1fr]">
      <aside className="flex min-h-0 flex-col border-r border-border">
        <div className="flex items-center justify-between gap-2 px-3 pt-3">
          <SearchBox
            placeholder="Search practice, plant, country…"
            label="Search documented traditional knowledge"
            onSearch={(next) => {
              setQ(next);
              setOffset(0);
            }}
          />
          <button
            aria-label={adding ? "Close register form" : "Register practice"}
            onClick={() => setAdding((a) => !a)}
            className="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-sm border border-border text-secondary transition hover:bg-neutral hover:text-primary"
          >
            {adding ? <X className="h-4 w-4" /> : <Plus className="h-4 w-4" />}
          </button>
        </div>

        {adding && (
          <div className="border-b border-border px-3 py-3">
            <p className="mb-2 text-xs font-medium uppercase tracking-wide text-tertiary">
              Register practice
            </p>
            <RegisterForm
              onCreated={(e) => {
                setAdding(false);
                setQ("");
                setOffset(0);
                navigate(`/defender/${e.tk_id}`);
              }}
            />
          </div>
        )}

        <div className="min-h-0 flex-1 space-y-1.5 overflow-y-auto px-3 py-3">
          {list.isPending ? (
            <>
              <Skeleton className="h-12" />
              <Skeleton className="h-12" />
              <Skeleton className="h-12" />
            </>
          ) : list.isError ? (
            <ErrorState error={list.error} onRetry={() => list.refetch()} />
          ) : list.data.items.length === 0 ? (
            <EmptyState
              title={q ? "No matches." : "No entries yet."}
              hint={q ? "Try a different term." : "Register a practice to begin."}
            />
          ) : (
            list.data.items.map((e) => (
              <button
                key={e.tk_id}
                onClick={() => navigate(`/defender/${e.tk_id}`)}
                className={cn(
                  "w-full rounded-sm border px-3 py-2 text-left transition",
                  e.tk_id === tkId
                    ? "border-primary bg-neutral"
                    : "border-border hover:border-tertiary",
                )}
              >
                <div className="truncate text-sm font-medium text-primary">
                  {e.practice_name}
                </div>
                <div className="mt-0.5 truncate text-xs text-muted">
                  {e.tk_id} · {dash(e.country)} ·{" "}
                  {e.plants.join(", ") || "no plants"}
                </div>
              </button>
            ))
          )}
        </div>

        {list.data && (
          <div className="border-t border-border px-3 py-2.5">
            <Pager
              total={list.data.total}
              limit={PAGE_SIZE}
              offset={offset}
              onChange={setOffset}
            />
          </div>
        )}
      </aside>

      <section className="overflow-y-auto px-6 py-6">
        {tkId ? <EntryWorkspace key={tkId} tkId={tkId} /> : <DefenderWelcome />}
      </section>
    </div>
  );
}

function DefenderWelcome() {
  return (
    <div className="mx-auto flex max-w-md flex-col items-center pt-24 text-center">
      <ShieldCheck className="h-10 w-10 text-tertiary" strokeWidth={1.25} />
      <h2 className="mt-4 text-lg font-semibold text-primary">
        Select or register a practice
      </h2>
      <p className="mt-2 text-sm leading-relaxed text-secondary">
        TK-Shield finds patents that may misappropriate the knowledge, scores
        bio-piracy risk across five factors, gathers prior-art evidence (PubMed,
        Wikidata, GBIF), and drafts a citation-backed opposition.
      </p>
    </div>
  );
}
