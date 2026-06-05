import { Link } from "react-router-dom";
import { ArrowRight } from "lucide-react";
import { ROLES } from "@/app/roles";
import { Card } from "@/components/Card";
import heroBackground from "@/assets/hero-background.webp";

// Landing / onboarding. Full-bleed sunset illustration with the nav overlaid; a
// dark gradient (not a white fade) darkens the image for legible white text and
// keeps the artwork rich. The role cards sit on the white section below, with
// breathing room after the hero.
export function RoleSelect() {
  function scrollToRoles() {
    document.getElementById("roles")?.scrollIntoView({ behavior: "smooth" });
  }

  return (
    <div>
      {/* Hero — pulled up under the transparent overlay header (h-14). */}
      <section className="relative -mt-14 flex h-[92vh] min-h-[620px] flex-col overflow-hidden">
        <img
          src={heroBackground}
          alt=""
          aria-hidden
          className="absolute inset-0 h-full w-full object-cover object-center"
        />
        {/* Dark gradients: bottom-heavy for white-text contrast, a light top
            scrim for the overlaid header. The artwork stays vivid; no white fog. */}
        <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/35 to-black/10" />
        <div className="absolute inset-x-0 top-0 h-32 bg-gradient-to-b from-black/45 to-transparent" />

        <div className="relative mt-auto w-full">
          <div className="mx-auto max-w-5xl px-6 pb-20 pt-24">
            <span className="inline-flex items-center gap-2 rounded-full border border-white/20 bg-white/10 px-3 py-1.5 text-xs font-medium text-white backdrop-blur-sm">
              <span className="h-1.5 w-1.5 rounded-full bg-accent-warm" />
              Keyless · offline-first · 16,400 patents indexed
            </span>
            <h1 className="mt-5 max-w-3xl text-5xl leading-[1.05] tracking-display text-white drop-shadow-sm sm:text-6xl">
              Defend documented traditional knowledge.
            </h1>
            <p className="mt-5 max-w-2xl text-lg text-white/85">
              TK-Shield finds patents that may misappropriate a documented
              practice, scores bio-piracy risk, gathers citable prior-art
              evidence, and drafts a patent opposition.
            </p>
            <button
              onClick={scrollToRoles}
              className="mt-7 inline-flex h-11 items-center gap-2 rounded-full bg-white px-6 text-base font-medium text-primary transition hover:bg-white/90"
            >
              Get started
              <ArrowRight className="h-4 w-4" strokeWidth={2} />
            </button>
          </div>
        </div>
      </section>

      {/* Role selection on the white page — breathing room after the hero. */}
      <section id="roles" className="mx-auto max-w-5xl scroll-mt-20 px-6 pb-24 pt-20">
        <h2 className="text-sm font-medium uppercase tracking-wide text-tertiary">
          Choose how you want to work
        </h2>
        <div className="mt-5 grid gap-6 sm:grid-cols-3">
          {ROLES.map((r) => {
            const Icon = r.icon;
            return (
              <Link key={r.id} to={r.path} className="group block">
                <Card className="flex h-full flex-col p-6 transition group-hover:border-primary">
                  <Icon className="h-7 w-7 text-primary" strokeWidth={1.5} />
                  <h3 className="mt-4 text-2xl tracking-headline text-primary">
                    {r.label}
                  </h3>
                  <p className="mt-1 text-xs uppercase tracking-wide text-tertiary">
                    {r.who}
                  </p>
                  <p className="mt-3 flex-1 text-sm leading-relaxed text-secondary">
                    {r.job}
                  </p>
                  <span className="mt-5 inline-flex items-center gap-1.5 text-sm font-medium text-primary">
                    Open
                    <ArrowRight
                      className="h-4 w-4 transition group-hover:translate-x-0.5"
                      strokeWidth={1.75}
                    />
                  </span>
                </Card>
              </Link>
            );
          })}
        </div>
      </section>
    </div>
  );
}
