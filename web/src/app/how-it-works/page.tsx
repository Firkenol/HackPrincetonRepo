import type { Metadata } from "next";
import { HowItWorks } from "@/components/HowItWorks";

export const metadata: Metadata = {
  title: "How it works · Carnot",
  description: "Three steps, six checks, four verdicts and three routing values. Every constant is cited in the evidence report.",
};

export default function Page() {
  return <HowItWorks />;
}
