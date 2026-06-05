import { useState } from "react";
import { Check, Copy } from "lucide-react";

// Small utility to copy report text / drafts. Gives brief confirmation.
export function CopyButton({ text, label = "Copy" }: { text: string; label?: string }) {
  const [copied, setCopied] = useState(false);

  async function onCopy() {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      /* clipboard unavailable — no-op */
    }
  }

  return (
    <button
      onClick={onCopy}
      className="inline-flex items-center gap-1.5 rounded-sm border border-border px-2.5 py-1 text-xs text-secondary transition hover:bg-neutral hover:text-primary"
    >
      {copied ? (
        <Check className="h-3.5 w-3.5" strokeWidth={2} />
      ) : (
        <Copy className="h-3.5 w-3.5" strokeWidth={1.75} />
      )}
      {copied ? "Copied" : label}
    </button>
  );
}
