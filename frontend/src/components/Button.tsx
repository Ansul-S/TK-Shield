import type { ButtonHTMLAttributes } from "react";
import { cn } from "@/lib/cn";

type Variant = "primary" | "secondary" | "tertiary";

interface Props extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
}

// Duna button language: primary is a dark pill (highest-emphasis conversion),
// secondary is a quiet outlined action with a small radius, tertiary is a
// text-only inline/utility action. Flat — no shadows.
const VARIANTS: Record<Variant, string> = {
  primary:
    "h-10 rounded-full bg-primary px-4 text-surface hover:bg-primary/90",
  secondary:
    "h-10 rounded-sm border border-border bg-transparent px-4 text-primary hover:bg-neutral",
  tertiary: "rounded-none px-0 text-primary underline-offset-4 hover:underline",
};

export function Button({ variant = "primary", className, ...rest }: Props) {
  return (
    <button
      className={cn(
        "inline-flex items-center justify-center gap-2 text-base font-normal",
        "cursor-pointer transition disabled:cursor-default disabled:opacity-50",
        VARIANTS[variant],
        className,
      )}
      {...rest}
    />
  );
}
