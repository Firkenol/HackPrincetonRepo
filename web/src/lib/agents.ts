import { Brain, Calculator, FileCheck, ScanText, type LucideIcon } from "lucide-react";
import type { StreamEvent } from "./types";

// The four agents, with one colour and one icon each. The trace, the "How it works"
// page and the state components all take their agent colours from here so they read
// as one system. The hues sit apart from the four verdict colours on purpose.

export type AgentName = StreamEvent["agent"];

export interface AgentStyle {
  name: AgentName;
  label: string;
  /** What the agent does, in one short clause. */
  role: string;
  hex: string;
  icon: LucideIcon;
}

export const AGENT_ORDER: AgentName[] = ["orchestrator", "listing-reader", "physics-checker", "report-writer"];

export const AGENTS: Record<AgentName, AgentStyle> = {
  orchestrator: { name: "orchestrator", label: "Orchestrator", role: "hands the work between the three agents", hex: "#7cc4ff", icon: Brain },
  "listing-reader": { name: "listing-reader", label: "Listing reader", role: "reads the listing into claims", hex: "#c99bff", icon: ScanText },
  "physics-checker": { name: "physics-checker", label: "Physics checker", role: "runs the six checks as tools", hex: "#5fd6cf", icon: Calculator },
  "report-writer": { name: "report-writer", label: "Report writer", role: "assembles the evidence report", hex: "#ffb27a", icon: FileCheck },
};

export function agentOf(name: string): AgentStyle {
  return AGENTS[name as AgentName] ?? { name: "orchestrator", label: name, role: "", hex: "#93a0b4", icon: Brain };
}

// The verdict colours as hex, matching --color-* in globals.css, for inline styles
// and SVG where a Tailwind class cannot reach.
export const VERDICT_HEX = {
  Impossible: "#f26d78",
  Flag: "#f2b441",
  "No red flags": "#4fcf8e",
  "No checkable claim": "#9aa4b2",
} as const;

export const STATUS_HEX = {
  pass: VERDICT_HEX["No red flags"],
  flag: VERDICT_HEX.Flag,
  violated: VERDICT_HEX.Impossible,
  not_assessed: VERDICT_HEX["No checkable claim"],
} as const;
