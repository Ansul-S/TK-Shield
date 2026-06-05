import { useState } from "react";
import { Plus } from "lucide-react";
import { useCreateTk } from "@/api/hooks";
import { Button } from "@/components/Button";
import { ErrorState } from "@/components/ErrorState";
import type { TKEntry } from "@/api/types";

const FIELD =
  "w-full rounded-sm border border-border bg-surface px-3 py-2 text-sm text-text placeholder:text-muted focus:border-primary";

// Register a documented practice. Plants/uses/domain are auto-extracted by the
// backend NER — we surface them after creation so the extraction is visible and
// trustworthy, then hand off to the new entry.
export function RegisterForm({ onCreated }: { onCreated: (e: TKEntry) => void }) {
  const create = useCreateTk();
  const [form, setForm] = useState({
    practice_name: "",
    description: "",
    country: "",
    community: "",
    documentation_date: "",
  });
  const [touched, setTouched] = useState(false);

  const nameMissing = touched && !form.practice_name.trim();

  function set(key: keyof typeof form) {
    return (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) =>
      setForm((f) => ({ ...f, [key]: e.target.value }));
  }

  function submit() {
    setTouched(true);
    if (!form.practice_name.trim()) return;
    create.mutate(
      {
        practice_name: form.practice_name.trim(),
        description: form.description.trim() || undefined,
        country: form.country.trim() || undefined,
        community: form.community.trim() || undefined,
        documentation_date: form.documentation_date.trim() || undefined,
      },
      {
        onSuccess: (entry) => {
          setForm({
            practice_name: "",
            description: "",
            country: "",
            community: "",
            documentation_date: "",
          });
          setTouched(false);
          onCreated(entry);
        },
      },
    );
  }

  return (
    <div className="space-y-2">
      <div>
        <input
          aria-label="Practice name"
          className={FIELD}
          placeholder="Practice name *"
          value={form.practice_name}
          onChange={set("practice_name")}
        />
        {nameMissing && (
          <p className="mt-1 text-xs text-error">Practice name is required.</p>
        )}
      </div>
      <textarea
        aria-label="Description"
        className={FIELD}
        rows={3}
        placeholder="Description / folk usage"
        value={form.description}
        onChange={set("description")}
      />
      <div className="flex gap-2">
        <input
          aria-label="Country"
          className={FIELD}
          placeholder="Country (e.g. IN)"
          value={form.country}
          onChange={set("country")}
        />
        <input
          aria-label="Documentation date"
          className={FIELD}
          placeholder="Documented (YYYY-MM-DD)"
          value={form.documentation_date}
          onChange={set("documentation_date")}
        />
      </div>
      <input
        aria-label="Community"
        className={FIELD}
        placeholder="Community"
        value={form.community}
        onChange={set("community")}
      />
      <Button onClick={submit} disabled={create.isPending} className="w-full">
        <Plus className="h-4 w-4" strokeWidth={2} />
        {create.isPending ? "Registering…" : "Register & auto-extract"}
      </Button>
      {create.isError && <ErrorState error={create.error} />}
    </div>
  );
}
