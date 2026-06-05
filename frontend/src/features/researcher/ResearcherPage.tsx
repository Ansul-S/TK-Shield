import { BarChart3, Building2, FileStack, Globe2, Library } from "lucide-react";
import { useStats } from "@/api/hooks";
import { Card } from "@/components/Card";
import { SectionHeader } from "@/components/SectionHeader";
import { Skeleton } from "@/components/Spinner";
import { ErrorState } from "@/components/ErrorState";
import { DistributionBars } from "@/components/DistributionBar";
import { Table, Td, Th } from "@/components/Table";
import { dash } from "@/lib/format";

// Researcher — aggregate analytics over the TK registry and patent corpus.
export function ResearcherPage() {
  const stats = useStats();

  return (
    <div className="mx-auto max-w-5xl px-6 py-8">
      <div className="flex items-center gap-2">
        <BarChart3 className="h-5 w-5 text-tertiary" strokeWidth={1.5} />
        <h1 className="text-xl font-semibold tracking-tight text-primary">
          Corpus &amp; registry analytics
        </h1>
      </div>
      <p className="mt-1 text-sm text-secondary">
        Aggregate view over the documented TK registry and the indexed patent
        corpus.
      </p>

      {stats.isPending ? (
        <div className="mt-6 grid gap-4 sm:grid-cols-2">
          <Skeleton className="h-48" />
          <Skeleton className="h-48" />
        </div>
      ) : stats.isError ? (
        <div className="mt-6">
          <ErrorState error={stats.error} onRetry={() => stats.refetch()} />
        </div>
      ) : (
        <Loaded data={stats.data} />
      )}
    </div>
  );
}

function Metric({ label, value }: { label: string; value: number }) {
  return (
    <div>
      <div className="text-2xl font-semibold tabular-nums text-primary">
        {value.toLocaleString()}
      </div>
      <div className="text-xs uppercase tracking-wide text-tertiary">{label}</div>
    </div>
  );
}

function Loaded({ data }: { data: NonNullable<ReturnType<typeof useStats>["data"]> }) {
  return (
    <div className="mt-6 space-y-4">
      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <SectionHeader title="TK registry" icon={Library} />
          <Metric label="Documented practices" value={data.registry.total} />
          <div className="mt-4">
            <p className="mb-2 text-xs font-medium uppercase tracking-wide text-tertiary">
              By domain
            </p>
            <DistributionBars data={data.registry.by_domain} />
          </div>
          <div className="mt-4">
            <p className="mb-2 flex items-center gap-1.5 text-xs font-medium uppercase tracking-wide text-tertiary">
              <Globe2 className="h-3.5 w-3.5" strokeWidth={1.75} /> Top origin
              countries
            </p>
            <DistributionBars data={data.registry.top_countries} />
          </div>
        </Card>

        <Card>
          <SectionHeader title="Patent corpus" icon={FileStack} />
          <div className="flex gap-8">
            <Metric label="Indexed" value={data.patents.total} />
            <Metric label="Sampled" value={data.patents.sampled} />
          </div>
          <div className="mt-4">
            <p className="mb-2 text-xs font-medium uppercase tracking-wide text-tertiary">
              By domain
            </p>
            <DistributionBars data={data.patents.by_domain} />
          </div>
          <div className="mt-4">
            <p className="mb-2 text-xs font-medium uppercase tracking-wide text-tertiary">
              By source
            </p>
            <DistributionBars data={data.patents.by_source} />
          </div>
        </Card>
      </div>

      <Card>
        <SectionHeader title="Top assignees" icon={Building2} />
        {data.patents.top_assignees.length === 0 ? (
          <p className="text-sm text-muted">No assignee data.</p>
        ) : (
          <div className="overflow-x-auto">
            <Table>
              <thead>
                <tr className="bg-neutral/60">
                  <Th>Assignee</Th>
                  <Th className="text-right">Patents (sampled)</Th>
                </tr>
              </thead>
              <tbody>
                {data.patents.top_assignees.map(([name, count]) => (
                  <tr key={name} className="hover:bg-neutral/40">
                    <Td className="text-secondary">{dash(name)}</Td>
                    <Td className="text-right tabular-nums text-muted">
                      {count.toLocaleString()}
                    </Td>
                  </tr>
                ))}
              </tbody>
            </Table>
          </div>
        )}
      </Card>
    </div>
  );
}
