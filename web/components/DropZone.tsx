"use client";

import { motion } from "framer-motion";
import { useRef, useState } from "react";

const IMAGE_TYPES = ["image/png", "image/jpeg", "image/webp"];
export const isScreenshot = (file: File) => IMAGE_TYPES.includes(file.type) || /\.(png|jpe?g|webp)$/i.test(file.name);

// Folders dropped from the desktop arrive as directory entries, not files.
async function filesFromEntry(entry: FileSystemEntry): Promise<File[]> {
  if (entry.isFile) {
    return new Promise((resolve) => (entry as FileSystemFileEntry).file((f) => resolve([f]), () => resolve([])));
  }
  const reader = (entry as FileSystemDirectoryEntry).createReader();
  const children: FileSystemEntry[] = [];
  for (;;) {
    const batch = await new Promise<FileSystemEntry[]>((resolve) => reader.readEntries(resolve, () => resolve([])));
    if (batch.length === 0) break;
    children.push(...batch);
  }
  return (await Promise.all(children.map(filesFromEntry))).flat();
}

async function droppedFiles(data: DataTransfer): Promise<File[]> {
  const entries = Array.from(data.items)
    .map((item) => item.webkitGetAsEntry?.())
    .filter((e): e is FileSystemEntry => !!e);
  if (entries.length === 0) return Array.from(data.files);
  return (await Promise.all(entries.map(filesFromEntry))).flat();
}

interface Props {
  multiple?: boolean;
  onFiles: (files: File[]) => void;
  title: string;
  hint: string;
  testId?: string;
}

export function DropZone({ multiple = false, onFiles, title, hint, testId }: Props) {
  const [over, setOver] = useState(false);
  const [ignored, setIgnored] = useState(0);
  const fileInput = useRef<HTMLInputElement>(null);
  const folderInput = useRef<HTMLInputElement>(null);

  const accept = (files: File[]) => {
    const shots = files.filter(isScreenshot).sort((a, b) => a.name.localeCompare(b.name, undefined, { numeric: true }));
    setIgnored(files.length - shots.length);
    const chosen = multiple ? shots : shots.slice(0, 1);
    if (chosen.length) onFiles(chosen);
  };

  return (
    <div>
      <motion.div
        role="button"
        tabIndex={0}
        data-testid={testId}
        aria-label={title}
        onClick={() => fileInput.current?.click()}
        onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && fileInput.current?.click()}
        onDragOver={(e) => {
          e.preventDefault();
          setOver(true);
        }}
        onDragLeave={() => setOver(false)}
        onDrop={(e) => {
          e.preventDefault();
          setOver(false);
          void droppedFiles(e.dataTransfer).then(accept);
        }}
        animate={{ scale: over ? 1.015 : 1 }}
        transition={{ type: "spring", stiffness: 400, damping: 28 }}
        className={`flex cursor-pointer flex-col items-center justify-center gap-1.5 rounded-xl border-2 border-dashed px-4 py-6 text-center outline-none transition-colors focus-visible:ring-2 focus-visible:ring-slate-900 ${
          over ? "border-slate-900 bg-slate-100" : "border-slate-300 bg-white hover:border-slate-400"
        }`}
      >
        <motion.svg
          animate={{ y: over ? -4 : 0 }}
          width="28"
          height="28"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.6"
          strokeLinecap="round"
          strokeLinejoin="round"
          className="text-slate-500"
          aria-hidden
        >
          <path d="M12 16V4m0 0l-4 4m4-4l4 4" />
          <path d="M4 16v2a2 2 0 002 2h12a2 2 0 002-2v-2" />
        </motion.svg>
        <div className="text-sm font-medium text-slate-900">{over ? "Drop to check" : title}</div>
        <div className="text-xs text-slate-500">{hint}</div>
      </motion.div>
      <input
        ref={fileInput}
        type="file"
        accept="image/png,image/jpeg,image/webp"
        multiple={multiple}
        hidden
        data-testid={testId ? `${testId}-input` : undefined}
        onChange={(e) => {
          accept(Array.from(e.target.files ?? []));
          e.target.value = "";
        }}
      />
      {multiple && (
        <>
          <input
            ref={(el) => {
              folderInput.current = el;
              el?.setAttribute("webkitdirectory", "");
            }}
            type="file"
            multiple
            hidden
            onChange={(e) => {
              accept(Array.from(e.target.files ?? []));
              e.target.value = "";
            }}
          />
          <button type="button" onClick={() => folderInput.current?.click()} className="mt-2 text-xs font-medium text-slate-600 underline underline-offset-2 hover:text-slate-900">
            Choose a folder instead
          </button>
        </>
      )}
      {ignored > 0 && (
        <p className="mt-2 text-xs text-slate-500">
          {ignored} {ignored === 1 ? "file was" : "files were"} skipped: only PNG, JPEG and WebP screenshots are accepted.
        </p>
      )}
    </div>
  );
}
