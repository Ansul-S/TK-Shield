import { useEffect, useRef, useState } from "react";
import { SEARCH_DEBOUNCE_MS } from "@/config";

// Debounced search input. Owns its text locally and emits the trimmed query
// after a pause so list refetches don't fire on every keystroke.
export function SearchBox({
  placeholder,
  onSearch,
  delay = SEARCH_DEBOUNCE_MS,
  label = "Search",
}: {
  placeholder?: string;
  onSearch: (q: string) => void;
  delay?: number;
  label?: string;
}) {
  const [value, setValue] = useState("");
  const timer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);

  useEffect(() => {
    timer.current = setTimeout(() => onSearch(value.trim()), delay);
    return () => clearTimeout(timer.current);
    // onSearch identity is stable enough; we only want this on value change.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [value, delay]);

  return (
    <input
      type="search"
      aria-label={label}
      placeholder={placeholder}
      value={value}
      onChange={(e) => setValue(e.target.value)}
      className="w-full rounded-sm border border-border bg-surface px-3.5 py-3 text-text placeholder:text-muted focus:border-primary"
    />
  );
}
