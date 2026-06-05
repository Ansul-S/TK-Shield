import ReactMarkdown from "react-markdown";

// Safe renderer for LLM-generated assessment narrative. react-markdown does NOT
// pass raw HTML through by default (no rehype-raw plugin), so injected
// <script>/<img onerror> in model or API output is rendered as inert text —
// this closes the S2 XSS sink the legacy innerHTML approach had. Links are
// forced to open in a new tab with noopener.
export function Markdown({ children }: { children: string }) {
  return (
    <div className="prose-tk space-y-3 leading-relaxed">
      <ReactMarkdown
        components={{
          h1: ({ children }) => (
            <h2 className="text-base font-semibold text-text">{children}</h2>
          ),
          h2: ({ children }) => (
            <h2 className="text-base font-semibold text-text">{children}</h2>
          ),
          a: ({ href, children }) => (
            <a
              href={href}
              target="_blank"
              rel="noopener noreferrer"
              className="text-primary underline underline-offset-2 hover:text-secondary"
            >
              {children}
            </a>
          ),
          ul: ({ children }) => (
            <ul className="list-disc space-y-1 pl-5">{children}</ul>
          ),
          strong: ({ children }) => (
            <strong className="font-semibold text-text">{children}</strong>
          ),
        }}
      >
        {children}
      </ReactMarkdown>
    </div>
  );
}
