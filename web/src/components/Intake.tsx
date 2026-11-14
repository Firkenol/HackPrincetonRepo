"use client";

import { FileText, ImageIcon, Play, Upload } from "lucide-react";
import { useRef, useState } from "react";

// Where a listing comes in: pasted text or a screenshot. Nothing is fetched from a
// marketplace; the console only reads what a person gives it.

export function Intake({
  busy,
  onText,
  onImage,
}: {
  busy: boolean;
  onText: (text: string) => void;
  onImage: (file: File) => void;
}) {
  const [text, setText] = useState("");
  const [dragging, setDragging] = useState(false);
  const fileInput = useRef<HTMLInputElement>(null);

  function takeFile(file: File | undefined | null) {
    if (file && file.type.startsWith("image/")) onImage(file);
  }

  return (
    <section aria-labelledby="intake-heading" className="rounded-lg border border-line bg-panel">
      <h2 id="intake-heading" className="border-b border-line-soft px-4 py-2.5 text-sm font-semibold text-text">
        Check a listing
      </h2>
      <div className="grid gap-4 p-4 lg:grid-cols-[1fr_16rem]">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            if (text.trim()) onText(text);
          }}
          className="flex flex-col gap-2"
        >
          <label htmlFor="listing-text" className="inline-flex items-center gap-1.5 text-xs text-muted">
            <FileText size={13} aria-hidden /> Paste the listing text
          </label>
          <textarea
            id="listing-text"
            value={text}
            onChange={(e) => setText(e.target.value)}
            rows={5}
            placeholder={"18650 Rechargeable Battery 12000mAh 3.7V Li-ion\nPackage weight: 0.600 kg"}
            className="pane-scroll resize-y rounded-md border border-line bg-ink px-3 py-2 font-mono text-[13px] leading-6 text-text placeholder:text-faint"
          />
          <div>
            <button
              type="submit"
              disabled={busy || !text.trim()}
              className="inline-flex items-center gap-2 rounded-md bg-accent px-3.5 py-1.5 text-sm font-medium text-ink disabled:cursor-not-allowed disabled:opacity-40"
            >
              <Play size={14} aria-hidden /> Check listing
            </button>
          </div>
        </form>

        <div
          data-testid="dropzone"
          onDragOver={(e) => {
            e.preventDefault();
            setDragging(true);
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDragging(false);
            takeFile(e.dataTransfer.files?.[0]);
          }}
          className={`flex flex-col items-center justify-center gap-2 rounded-md border border-dashed px-4 py-5 text-center transition-colors ${
            dragging ? "border-accent bg-accent/10" : "border-line"
          }`}
        >
          <ImageIcon size={20} className="text-faint" aria-hidden />
          <p className="text-sm text-muted">Drop a screenshot here</p>
          <p className="text-xs text-faint">PNG, JPEG or WebP, under 3.5 MB</p>
          <input
            ref={fileInput}
            type="file"
            accept="image/png,image/jpeg,image/webp"
            className="sr-only"
            aria-label="Upload a listing screenshot"
            onChange={(e) => {
              takeFile(e.target.files?.[0]);
              e.target.value = "";
            }}
          />
          <button
            type="button"
            disabled={busy}
            onClick={() => fileInput.current?.click()}
            className="inline-flex items-center gap-2 rounded-md border border-line bg-raised px-3 py-1.5 text-sm text-text hover:border-accent disabled:opacity-40"
          >
            <Upload size={14} aria-hidden /> Upload screenshot
          </button>
        </div>
      </div>
    </section>
  );
}
