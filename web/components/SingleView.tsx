"use client";

import { useState } from "react";
import { DropZone } from "@/components/DropZone";
import { Trace } from "@/components/Trace";
import { VerdictCard } from "@/components/VerdictCard";
import { useRun } from "@/lib/run";
import { SAMPLES } from "@/lib/samples";

const firstLine = (text: string) => {
  const line = text.trim().split("\n")[0] ?? "";
  return line.length > 70 ? `${line.slice(0, 70)}…` : line;
};

export function SingleView({ mock }: { mock: boolean }) {
  const { state, start } = useRun();
  const [text, setText] = useState("");

  const runText = (value: string, name?: string) => {
    if (!value.trim()) return;
    start({ kind: "text", name: name ?? `Pasted text: ${firstLine(value)}`, text: value });
  };
  const runFile = (file: File) => start({ kind: "image", name: file.name, file });

  return (
    <div className="grid items-start gap-5 lg:grid-cols-[minmax(0,5fr)_minmax(0,7fr)]">
      <div className="space-y-4">
        <section className="rounded-xl border border-slate-200 bg-white p-4">
          <h2 className="text-sm font-semibold text-slate-900">Listing</h2>
          <div className="mt-3">
            <DropZone
              testId="dropzone"
              title="Drop a listing screenshot, or click to choose one"
              hint="PNG, JPEG or WebP. The screenshot is not displayed."
              onFiles={(files) => files[0] && runFile(files[0])}
            />
          </div>
          <div className="my-3 flex items-center gap-3 text-xs text-slate-400">
            <span className="h-px flex-1 bg-slate-200" />
            or paste the listing text
            <span className="h-px flex-1 bg-slate-200" />
          </div>
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            onPaste={(e) => {
              const file = Array.from(e.clipboardData.files).find((f) => f.type.startsWith("image/"));
              if (file) {
                e.preventDefault();
                runFile(file);
              }
            }}
            onKeyDown={(e) => {
              if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) runText(text);
            }}
            rows={4}
            placeholder="Paste the title, bullet points and spec table. A screenshot on the clipboard can be pasted here too."
            data-testid="listing-text"
            className="w-full resize-y rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 outline-none placeholder:text-slate-400 focus:border-slate-900"
          />
          <div className="mt-2 flex items-center justify-between gap-3">
            <span className="text-xs text-slate-400">⌘ Enter to run</span>
            <button
              type="button"
              disabled={!text.trim()}
              onClick={() => runText(text)}
              data-testid="run-text"
              className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-semibold text-white hover:bg-slate-700 disabled:cursor-not-allowed disabled:bg-slate-300"
            >
              Check listing
            </button>
          </div>

          <div className="mt-4 border-t border-slate-200 pt-3">
            <div className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">
              Sample listings{mock ? " (the nine recorded fixtures)" : ""}
            </div>
            <div className="mt-2 flex flex-wrap gap-1.5">
              {SAMPLES.map((s) => (
                <button
                  key={s.id}
                  type="button"
                  data-testid={`sample-${s.id}`}
                  onClick={() => {
                    setText(s.text);
                    runText(s.text, `Sample ${s.id}: ${s.label}`);
                  }}
                  className="rounded-full border border-slate-300 bg-white px-2.5 py-1 text-xs text-slate-700 hover:border-slate-900 hover:text-slate-900"
                >
                  <span className="font-semibold tnum">{s.id}</span> {s.label}
                </button>
              ))}
            </div>
          </div>
        </section>
        <Trace run={state} />
      </div>
      <VerdictCard run={state} />
    </div>
  );
}
