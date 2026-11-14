"use client";

import { MotionConfig } from "framer-motion";
import { SingleView } from "@/components/SingleView";

export function App({ mock }: { mock: boolean }) {
  return (
    <MotionConfig reducedMotion="user">
      <div className="mx-auto max-w-7xl px-5 pb-16">
        <header className="flex flex-wrap items-center gap-x-4 gap-y-2 py-5">
          <div>
            <h1 className="text-xl font-semibold tracking-tight text-slate-900">ClaimCheck</h1>
            <p className="text-sm text-slate-600">Checks whether a battery listing&apos;s own claims are physically possible, and shows the math.</p>
          </div>
          <span
            data-testid="mode"
            className={`ml-auto rounded-full border px-2.5 py-1 text-xs font-medium ${mock ? "border-amber-300 bg-amber-50 text-amber-900" : "border-slate-300 bg-white text-slate-700"}`}
          >
            {mock ? "Mock: replaying recorded fixtures" : "Live API"}
          </span>
        </header>
        <SingleView mock={mock} />
      </div>
    </MotionConfig>
  );
}
