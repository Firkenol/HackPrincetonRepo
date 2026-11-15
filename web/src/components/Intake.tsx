"use client";

import { motion } from "framer-motion";
import { FileText, ImageIcon, Play, Upload } from "lucide-react";
import { SNAP } from "@/lib/motion";
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
    <section aria-labelledby="intake-heading" className="surface overflow-hidden">
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
            className="pane-scroll well resize-y px-3 py-2 font-mono text-[13px] leading-6 text-text transition-[border-color,box-shadow] placeholder:text-faint/70 focus:border-accent/60 focus:shadow-[inset_0_1px_3px_rgb(0_0_0/0.45),0_0_0_3px_rgb(124_196_255/0.12)] focus:outline-none"
          />
          <div>
            <button
              type="submit"
              disabled={busy || !text.trim()}
              className="btn btn-primary"
            >
              <Play size={14} aria-hidden /> Check listing
            </button>
          </div>
        </form>

        <motion.div
          data-testid="dropzone"
          animate={{ scale: dragging ? 1.02 : 1 }}
          transition={SNAP}
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
          className={`flex flex-col items-center justify-center gap-2 rounded-lg border border-dashed px-4 py-5 text-center transition-[background-color,border-color,box-shadow] duration-200 ${
            dragging ? "border-accent bg-accent/10 shadow-[0_0_0_4px_rgb(124_196_255/0.12)]" : "border-line hover:border-faint"
          }`}
        >
          {/* The icon lifts while a file is held over the zone, as if ready to catch it. */}
          <motion.span animate={{ y: dragging ? -5 : 0, scale: dragging ? 1.15 : 1 }} transition={SNAP} aria-hidden>
            <ImageIcon size={22} className={dragging ? "text-accent" : "text-faint"} />
          </motion.span>
          <p className="text-sm text-muted">{dragging ? "Let go to check it" : "Drop a screenshot here"}</p>
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
            className="btn btn-quiet"
          >
            <Upload size={14} aria-hidden /> Upload screenshot
          </button>
        </motion.div>
      </div>
    </section>
  );
}
