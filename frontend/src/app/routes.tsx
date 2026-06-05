import { createBrowserRouter } from "react-router-dom";
import { AppShell } from "./AppShell";
import { RoleSelect } from "@/features/onboarding/RoleSelect";
import { DefenderPage } from "@/features/defender/DefenderPage";
import { ExaminerPage } from "@/features/examiner/ExaminerPage";
import { ResearcherPage } from "@/features/researcher/ResearcherPage";

// Per-persona routes with deep-linking. /defender/:tkId makes a selected entry
// shareable/bookmarkable — the FastAPI catch-all serves index.html so these
// survive a hard refresh in production.
export const router = createBrowserRouter([
  {
    path: "/",
    element: <AppShell />,
    children: [
      { index: true, element: <RoleSelect /> },
      { path: "defender", element: <DefenderPage /> },
      { path: "defender/:tkId", element: <DefenderPage /> },
      { path: "examiner", element: <ExaminerPage /> },
      { path: "researcher", element: <ResearcherPage /> },
      {
        path: "*",
        element: (
          <div className="px-6 py-10 text-muted">Page not found.</div>
        ),
      },
    ],
  },
]);
