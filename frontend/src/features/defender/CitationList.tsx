import { ExternalLink } from "lucide-react";
import { safeHref } from "@/lib/url";
import { cn } from "@/lib/cn";
import type { Citation } from "@/api/types";

// Prior-art evidence — the product's trust anchor. Each item carries a source
// and a stable ID (PMID / QID / GBIF key). Links are http(s)-validated.
const SOURCE_LABEL: Record<Citation["source"], string> = {
  pubmed: "PubMed",
  wikidata: "Wikidata",
  gbif: "GBIF",
};

export function CitationList({ citations }: { citations: Citation[] }) {
  if (citations.length === 0)
    return <p className="text-sm text-muted">No citations on record for this run.</p>;

  return (
    <ul className="divide-y divide-border">
      {citations.map((c, i) => {
        const href = safeHref(c.url);
        return (
          <li key={`${c.ref_id}-${i}`} className="flex items-start gap-3 py-2 text-sm">
            <span
              className={cn(
                "mt-0.5 inline-block w-20 flex-shrink-0 rounded-sm bg-neutral px-2 py-0.5 text-center text-xs font-medium text-secondary",
              )}
            >
              {SOURCE_LABEL[c.source] ?? c.source}
            </span>
            <span className="min-w-0 flex-1">
              {href ? (
                <a
                  href={href}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 font-medium text-primary underline underline-offset-2 hover:text-secondary"
                >
                  {c.ref_id}
                  <ExternalLink className="h-3 w-3" strokeWidth={1.75} />
                </a>
              ) : (
                <span className="font-medium text-primary">{c.ref_id}</span>
              )}
              {c.title && <span className="text-secondary"> — {c.title}</span>}
            </span>
          </li>
        );
      })}
    </ul>
  );
}
