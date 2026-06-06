import { Component, type ErrorInfo, type ReactNode } from "react";
import { Button } from "./Button";

// A render-time throw in any feature would otherwise blank the whole SPA with
// only a console error (F2). This boundary catches it and shows a calm fallback
// in place of the broken view; the surrounding shell/nav stay usable. Class
// component because error boundaries have no hooks equivalent.
export class ErrorBoundary extends Component<
  { children: ReactNode },
  { error: Error | null }
> {
  state = { error: null as Error | null };

  static getDerivedStateFromError(error: Error) {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error("Unhandled UI error:", error, info.componentStack);
  }

  render() {
    if (this.state.error) {
      return (
        <div className="px-6 py-12">
          <div className="mx-auto max-w-md rounded-md border border-error bg-surface p-5">
            <p className="text-sm font-medium text-error">
              Something went wrong rendering this view.
            </p>
            <p className="mt-1 text-sm text-muted">
              The rest of the app is still usable — try again, or switch
              personas from the navigation above.
            </p>
            <Button
              variant="secondary"
              className="mt-4"
              onClick={() => window.location.reload()}
            >
              Reload
            </Button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
