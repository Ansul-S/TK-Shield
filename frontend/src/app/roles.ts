import { BarChart3, Scale, ShieldCheck, type LucideIcon } from "lucide-react";

// Single source of truth for the three personas — drives both the role nav and
// the onboarding landing so they never drift. Icons are professional line
// icons (Lucide), not emoji.
export interface Role {
  id: "defender" | "examiner" | "researcher";
  path: string;
  icon: LucideIcon;
  label: string;
  who: string;
  job: string;
}

export const ROLES: Role[] = [
  {
    id: "defender",
    path: "/defender",
    icon: ShieldCheck,
    label: "Defender",
    who: "Communities & NGOs",
    job: "Register traditional knowledge, check it against the patent corpus, and generate a risk assessment with a draft opposition.",
  },
  {
    id: "examiner",
    path: "/examiner",
    icon: Scale,
    label: "Examiner",
    who: "Patent offices",
    job: "Paste an incoming patent and reverse-look it up against documented TK for a novelty verdict and matching prior art.",
  },
  {
    id: "researcher",
    path: "/researcher",
    icon: BarChart3,
    label: "Researcher",
    who: "Analysts & academics",
    job: "Explore the corpus and registry: domains, geography, top assignees, and counts.",
  },
];
