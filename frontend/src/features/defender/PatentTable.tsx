import * as Tooltip from "@radix-ui/react-tooltip";
import { Table, Td, Th } from "@/components/Table";
import { EmptyState } from "@/components/EmptyState";
import { cap, dash, trunc } from "@/lib/format";
import type { Patent } from "@/api/types";

// Candidate patents from hybrid search. Titles can be long → truncate with a
// tooltip showing the full title. Empty assignee/date render as em-dash.
export function PatentTable({ patents }: { patents: Patent[] }) {
  if (patents.length === 0)
    return <EmptyState title="No candidate patents found." />;

  return (
    <div className="overflow-x-auto rounded-md border border-border">
      <Table>
        <thead>
          <tr className="bg-neutral/60">
            <Th>Patent</Th>
            <Th>Title</Th>
            <Th>Assignee</Th>
            <Th>Filed</Th>
            <Th className="text-right">Sim.</Th>
          </tr>
        </thead>
        <tbody>
          {patents.map((p, i) => {
            const title = cap(p.title || "");
            return (
              <tr key={`${p.patent_id}-${i}`} className="hover:bg-neutral/40">
                <Td className="whitespace-nowrap font-medium text-primary">
                  {dash(p.patent_id)}
                </Td>
                <Td>
                  {title ? (
                    <Tooltip.Root>
                      <Tooltip.Trigger asChild>
                        <span className="cursor-default">{trunc(title, 64)}</span>
                      </Tooltip.Trigger>
                      <Tooltip.Portal>
                        <Tooltip.Content
                          sideOffset={4}
                          className="max-w-md rounded-md border border-border bg-surface px-2.5 py-1.5 text-xs text-text shadow-sm"
                        >
                          {title}
                          <Tooltip.Arrow className="fill-border" />
                        </Tooltip.Content>
                      </Tooltip.Portal>
                    </Tooltip.Root>
                  ) : (
                    "—"
                  )}
                </Td>
                <Td className="text-secondary">{dash(p.assignee)}</Td>
                <Td className="whitespace-nowrap text-secondary">
                  {dash(p.filing_date)}
                </Td>
                <Td className="text-right tabular-nums text-muted">
                  {typeof p.similarity === "number"
                    ? p.similarity.toFixed(2)
                    : dash(p.similarity)}
                </Td>
              </tr>
            );
          })}
        </tbody>
      </Table>
    </div>
  );
}
