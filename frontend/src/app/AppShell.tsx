import { NavLink, Outlet, useLocation } from "react-router-dom";
import * as Tooltip from "@radix-ui/react-tooltip";
import { ShieldCheck } from "lucide-react";
import { useHealth } from "@/api/hooks";
import { StatusDot } from "@/components/StatusDot";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import { ROLES } from "./roles";
import { cn } from "@/lib/cn";

// Persistent application shell: brand, role navigation, and live health dots.
// On the landing route the header renders as a transparent overlay (light text)
// that scrolls away over the hero image, matching the Duna reference; on every
// other route it's the standard solid, dense enterprise bar.
export function AppShell() {
  const pathname = useLocation().pathname;
  const isLanding = pathname === "/";
  const header = <Header overlay={isLanding} />;

  return (
    <Tooltip.Provider delayDuration={150}>
      <div className="flex h-full flex-col bg-background">
        {!isLanding && header}
        <main className="min-h-0 flex-1 overflow-y-auto">
          {isLanding && header}
          {/* keyed by route so navigating away clears a caught error */}
          <ErrorBoundary key={pathname}>
            <Outlet />
          </ErrorBoundary>
        </main>
      </div>
    </Tooltip.Provider>
  );
}

function Header({ overlay }: { overlay: boolean }) {
  const health = useHealth();

  return (
    <header
      className={cn(
        "z-20 flex h-14 flex-shrink-0 items-center gap-6 px-5",
        overlay
          ? "relative bg-transparent text-white"
          : "border-b border-border bg-background text-primary",
      )}
    >
      <NavLink
        to="/"
        className={cn(
          "flex items-center gap-2",
          overlay ? "text-white" : "text-primary",
        )}
      >
        <ShieldCheck className="h-5 w-5" strokeWidth={2} />
        <span className="text-[15px] font-semibold tracking-tight">
          TK-Shield
        </span>
      </NavLink>

      <nav className="flex h-full items-stretch" aria-label="Persona">
        {ROLES.map((r) => {
          const Icon = r.icon;
          return (
            <NavLink
              key={r.id}
              to={r.path}
              className={({ isActive }) =>
                cn(
                  "relative flex items-center gap-2 px-4 text-sm transition",
                  overlay
                    ? isActive
                      ? "font-medium text-white after:absolute after:inset-x-3 after:bottom-0 after:h-0.5 after:bg-white"
                      : "text-white/75 hover:text-white"
                    : isActive
                      ? "font-medium text-primary after:absolute after:inset-x-3 after:bottom-0 after:h-0.5 after:bg-primary"
                      : "text-secondary hover:text-primary",
                )
              }
            >
              <Icon className="h-4 w-4" strokeWidth={1.75} />
              {r.label}
            </NavLink>
          );
        })}
      </nav>

      <div
        className={cn(
          "ml-auto flex items-center gap-4",
          overlay && "[&_*]:text-white/85",
        )}
      >
        {health.isError ? (
          <span className="text-sm text-error">API offline</span>
        ) : (
          <>
            <StatusDot
              on={!!health.data?.llm_available}
              label="LLM"
              hint={
                health.data?.llm_available
                  ? "Local LLM online — reports include an AI-written narrative."
                  : "AI narrative offline — figures and citations are still exact (deterministic fallback)."
              }
            />
            <StatusDot
              on={!!health.data?.live_patents_available}
              label="Live patents"
              hint={
                health.data?.live_patents_available
                  ? "Live PatentsView monitoring is available."
                  : "Live monitoring is off (no API key) — an optional feature, not an error."
              }
            />
          </>
        )}
      </div>
    </header>
  );
}
