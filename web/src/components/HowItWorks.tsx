"use client";

import { MotionConfig, motion, useReducedMotion, type Variants } from "framer-motion";
import { ArrowLeft, BookMarked, Printer, type LucideIcon } from "lucide-react";
import Link from "next/link";
import { AGENTS, VERDICT_HEX } from "@/lib/agents";
import { ROUTINGS, VERDICTS, type Routing, type Verdict } from "@/lib/types";

// "How it works": the three steps, the six checks in plain language, the four verdicts
// and the three routing values worded as SPEC.md words them. The step colours are the
// agent colours from lib/agents.ts, so this page and the live trace read as one system.

const STEPS: { title: string; agent: keyof typeof AGENTS; text: string }[] = [
  {
    title: "Read the listing",
    agent: "listing-reader",
    text: "A pasted listing or a screenshot is read into claims: chemistry, size code, voltage, capacity, energy, weight, dimensions, shelf life and the codes printed on the product. Each claim records where it was found and how confident the reading is.",
  },
  {
    title: "Run the checks",
    agent: "physics-checker",
    text: "Six checks run as plain functions. The arithmetic happens in code, never in the model: the model only decides which checks to call. Package weights and package dimensions are set aside as unreliable.",
  },
  {
    title: "Show the math",
    agent: "report-writer",
    text: "The evidence report lists every claim, every check with its inputs, formula and steps, the constant each check used with its source, the verdict and the routing. A person with a calculator can reproduce it.",
  },
];

const CHECKS: { title: string; text: string }[] = [
  { title: "Label consistency", text: "The watt-hours printed on the label should equal volts times amp-hours, within a small rounding tolerance." },
  { title: "Form-factor bound", text: "A size code such as 18650, 21700, AA or AAA fixes the cell's volume, and volume caps how much energy it can hold." },
  { title: "Dimension bound", text: "The stated dimensions give a volume. Energy per litre must stay under the best-case ceiling for the stated chemistry." },
  { title: "Weight bound", text: "Energy per kilogram, from the stated product weight, must stay under the best-case ceiling for the stated chemistry." },
  { title: "Label contradiction", text: "The chemistry in the title should agree with the codes printed on the cells in the photo. LR03 is an alkaline AAA; R03 is zinc-carbon." },
  { title: "Chemistry mismatch", text: "A claim that is unusual for the stated chemistry, such as a ten-year shelf life on a carbon-zinc cell. A soft flag only." },
];

// Worded as SPEC.md words them.
const VERDICT_TEXT: Record<Verdict, string> = {
  Impossible: "A hard physical bound is violated. The arithmetic is shown.",
  Flag: "A contradiction or unusual claim. The reason is explained.",
  "No red flags": "The claims that could be checked are plausible. This is not a confirmation that they are true.",
  "No checkable claim": "Nothing numeric or testable was stated.",
};

const ROUTING_TEXT: Record<Routing, string> = {
  "auto-resolvable": "A hard bound is violated and the calculation is reproducible.",
  "needs human review": "A flag, missing data or a low-confidence reading. A person decides.",
  "no action needed": "No red flags or no checkable claim, with every claim read at high confidence.",
};

const sequence: Variants = {
  hidden: {},
  shown: { transition: { staggerChildren: 0.55, delayChildren: 0.15 } },
};
const step: Variants = {
  hidden: { opacity: 0, y: 14 },
  shown: { opacity: 1, y: 0, transition: { duration: 0.45, ease: "easeOut" } },
};
const draw: Variants = {
  hidden: { scaleX: 0 },
  shown: { scaleX: 1, transition: { duration: 0.4, ease: "easeInOut" } },
};
const later: Variants = {
  hidden: { opacity: 0, y: 10 },
  shown: { opacity: 1, y: 0, transition: { duration: 0.4, delay: 2.0 } },
};

function Card({ children, accent, className = "" }: { children: React.ReactNode; accent?: string; className?: string }) {
  return (
    <motion.div
      tabIndex={0}
      whileHover={{ y: -2 }}
      whileFocus={{ y: -2 }}
      transition={{ type: "spring", stiffness: 380, damping: 26 }}
      className={`rounded-lg border border-line bg-panel p-4 outline-none transition-colors hover:border-[color:var(--card-accent)] focus-visible:border-[color:var(--card-accent)] focus-visible:ring-2 focus-visible:ring-accent/50 ${className}`}
      style={{ ["--card-accent" as string]: accent ?? "var(--color-accent)" }}
    >
      {children}
    </motion.div>
  );
}

function Step({ index, title, agent, text, Icon, hex }: { index: number; title: string; agent: string; text: string; Icon: LucideIcon; hex: string }) {
  return (
    <motion.li variants={step} className="relative flex min-w-0 flex-1 flex-col">
      <Card accent={hex} className="h-full">
        <div className="flex items-center gap-3">
          <span className="grid size-9 shrink-0 place-items-center rounded-md border" style={{ borderColor: hex, color: hex, background: `color-mix(in srgb, ${hex} 12%, transparent)` }}>
            <Icon size={18} aria-hidden />
          </span>
          <div className="min-w-0">
            <p className="text-xs text-faint">Step {index + 1}</p>
            <h3 className="text-base font-semibold text-text">{title}</h3>
          </div>
        </div>
        <p className="mt-3 text-sm leading-6 text-muted">{text}</p>
        <p className="mt-3 text-xs" style={{ color: hex }}>
          {agent}
        </p>
      </Card>
    </motion.li>
  );
}

export function HowItWorks() {
  const reduced = useReducedMotion();
  return (
    <MotionConfig reducedMotion="user">
      <div className="min-h-screen">
        <header className="flex flex-wrap items-center justify-between gap-3 border-b border-line bg-panel px-5 py-3">
          <div className="flex items-baseline gap-3">
            <h1 className="text-xl font-semibold tracking-tight text-text">How it works</h1>
            <p className="text-sm text-muted">Checks a battery listing&apos;s own claims against physics and shows the math</p>
          </div>
          <nav aria-label="Pages" className="flex items-center gap-3 text-sm">
            <Link href="/" className="inline-flex items-center gap-1.5 rounded-md border border-line bg-raised px-3 py-1.5 text-text hover:border-accent">
              <ArrowLeft size={14} aria-hidden /> Console
            </Link>
            <Link href="/report/fixture_01" className="inline-flex items-center gap-1.5 rounded-md border border-line bg-raised px-3 py-1.5 text-text hover:border-accent">
              <Printer size={14} aria-hidden /> Printable evidence report
            </Link>
          </nav>
        </header>

        <main className="mx-auto max-w-6xl space-y-10 px-5 py-8">
          <motion.section aria-labelledby="steps-heading" variants={sequence} initial={reduced ? "shown" : "hidden"} animate="shown">
            <h2 id="steps-heading" className="mb-1 text-sm font-semibold text-text">
              Three steps
            </h2>
            <p className="mb-4 text-sm text-muted">
              An orchestrator hands the work between three agents. The model reads and delegates; the arithmetic is code.
            </p>
            <ol className="flex flex-col gap-3 md:flex-row md:items-stretch">
              {STEPS.map((s, i) => {
                const agent = AGENTS[s.agent];
                return (
                  <li key={s.title} className="contents">
                    <Step index={i} title={s.title} agent={agent.label} text={s.text} Icon={agent.icon} hex={agent.hex} />
                    {i < STEPS.length - 1 && (
                      <motion.span
                        aria-hidden
                        variants={draw}
                        className="hidden h-px w-8 shrink-0 origin-left self-center md:block"
                        style={{ background: `linear-gradient(90deg, ${agent.hex}, ${AGENTS[STEPS[i + 1].agent].hex})` }}
                      />
                    )}
                  </li>
                );
              })}
            </ol>
          </motion.section>

          <motion.section aria-labelledby="checks-heading" variants={later} initial={reduced ? "shown" : "hidden"} animate="shown">
            <h2 id="checks-heading" className="mb-1 text-sm font-semibold text-text">
              Six checks
            </h2>
            <p className="mb-4 text-sm text-muted">Each runs as a plain function on the extracted claims and records its inputs, formula and steps.</p>
            <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {CHECKS.map((c, i) => (
                <li key={c.title}>
                  <Card accent={AGENTS["physics-checker"].hex} className="h-full">
                    <p className="font-mono text-xs text-faint">{i + 1}</p>
                    <h3 className="mt-1 text-sm font-semibold text-text">{c.title}</h3>
                    <p className="mt-2 text-sm leading-6 text-muted">{c.text}</p>
                  </Card>
                </li>
              ))}
            </ul>
          </motion.section>

          <motion.section aria-labelledby="verdicts-heading" variants={later} initial={reduced ? "shown" : "hidden"} animate="shown" className="grid gap-8 lg:grid-cols-[3fr_2fr]">
            <div>
              <h2 id="verdicts-heading" className="mb-1 text-sm font-semibold text-text">
                Four verdicts
              </h2>
              <p className="mb-4 text-sm text-muted">A verdict is about the claim, never about whoever listed the product.</p>
              <ul className="grid gap-3 sm:grid-cols-2">
                {VERDICTS.map((verdict) => (
                  <li key={verdict}>
                    <Card accent={VERDICT_HEX[verdict]} className="h-full">
                      <h3 data-testid="verdict-name" className="text-base font-semibold" style={{ color: VERDICT_HEX[verdict] }}>
                        {verdict}
                      </h3>
                      <p className="mt-2 text-sm leading-6 text-muted">{VERDICT_TEXT[verdict]}</p>
                    </Card>
                  </li>
                ))}
              </ul>
            </div>
            <div>
              <h2 id="routing-heading" className="mb-1 text-sm font-semibold text-text">
                Three routing values
              </h2>
              <p className="mb-4 text-sm text-muted">Where each result goes next.</p>
              <ul className="grid gap-3">
                {ROUTINGS.map((routing) => (
                  <li key={routing}>
                    <Card className="h-full">
                      <h3 data-testid="routing-name" className="text-sm font-semibold text-text">
                        {routing}
                      </h3>
                      <p className="mt-1.5 text-sm leading-6 text-muted">{ROUTING_TEXT[routing]}</p>
                    </Card>
                  </li>
                ))}
              </ul>
            </div>
          </motion.section>

          <motion.section aria-labelledby="sources-heading" variants={later} initial={reduced ? "shown" : "hidden"} animate="shown">
            <Card accent={AGENTS["report-writer"].hex}>
              <div className="flex items-start gap-3">
                <BookMarked size={18} aria-hidden className="mt-0.5 shrink-0" style={{ color: AGENTS["report-writer"].hex }} />
                <div>
                  <h2 id="sources-heading" className="text-sm font-semibold text-text">
                    Every constant is cited
                  </h2>
                  <p className="mt-1.5 max-w-prose text-sm leading-6 text-muted">
                    Each physical ceiling and reference voltage used by a check appears in the evidence report with its value, its source,
                    where in the source it comes from and when it was read. Ceilings are best-case figures, so a product that is what it
                    says it is sits well below them.
                  </p>
                  <Link href="/report/fixture_01" className="mt-3 inline-flex items-center gap-1.5 text-sm text-accent hover:underline">
                    <Printer size={14} aria-hidden /> Open a sample evidence report, laid out for print
                  </Link>
                </div>
              </div>
            </Card>
          </motion.section>
        </main>
      </div>
    </MotionConfig>
  );
}
