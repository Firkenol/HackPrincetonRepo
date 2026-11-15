import type { BatchResponse, DashboardStats, LatestBatch, Mode, StreamEvent } from "./types";

export const API_URL = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(/\/$/, "");

/** Thrown when the API cannot be reached at all, as opposed to answering with an error. */
export class ApiUnreachable extends Error {
  constructor() {
    super("The OffSpec API could not be reached.");
    this.name = "ApiUnreachable";
  }
}

async function request(path: string, init?: RequestInit): Promise<Response> {
  let response: Response;
  try {
    response = await fetch(`${API_URL}${path}`, init);
  } catch {
    throw new ApiUnreachable();
  }
  if (response.status >= 500) throw new ApiUnreachable();
  return response;
}

async function json<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await request(path, init);
  if (!response.ok) throw new Error(`The API answered ${response.status}.`);
  return (await response.json()) as T;
}

export const fetchStats = () => json<DashboardStats>("/api/dashboard-stats");
export const runBatch = () => json<BatchResponse>("/api/batch", { method: "POST" });
/** The latest batch run, without running anything. Used to show a batch that was run ahead of time. */
export const fetchLatestBatch = () => json<LatestBatch>("/api/batch");
export const fetchHealth = () => json<{ status: string; mode: Mode; sample_data: boolean }>("/api/health");

/** A fixture screenshot URL from the API, made absolute. */
export function absoluteUrl(path: string | null): string | null {
  if (!path) return null;
  return path.startsWith("http") ? path : `${API_URL}${path}`;
}

// ---------------------------------------------------------------- event stream

export interface StreamMeta {
  mode: Mode;
  sample_data: boolean;
  sample_id: string | null;
}

export type Frame = { kind: "meta"; meta: StreamMeta } | { kind: "event"; event: StreamEvent };

/**
 * Splits Server-Sent Events text into frames. Feed it chunks as they arrive; it
 * returns the frames completed so far and keeps any partial frame for the next chunk.
 */
export function createSseParser() {
  let buffer = "";
  return function push(chunk: string): Frame[] {
    buffer += chunk.replace(/\r\n/g, "\n");
    const frames: Frame[] = [];
    let end = buffer.indexOf("\n\n");
    while (end !== -1) {
      const block = buffer.slice(0, end);
      buffer = buffer.slice(end + 2);
      let name = "message";
      const data: string[] = [];
      for (const line of block.split("\n")) {
        if (line.startsWith("event:")) name = line.slice(6).trim();
        else if (line.startsWith("data:")) data.push(line.slice(5).trimStart());
      }
      if (data.length) {
        try {
          const parsed = JSON.parse(data.join("\n"));
          frames.push(name === "meta" ? { kind: "meta", meta: parsed } : { kind: "event", event: parsed });
        } catch {
          // a frame that is not JSON is not one of ours; skip it
        }
      }
      end = buffer.indexOf("\n\n");
    }
    return frames;
  };
}

export type ListingInput = { text: string } | { image: File } | { sample: string };

/**
 * Checks one listing and calls onFrame for the meta frame and for each contract event
 * as it arrives. Resolves when the stream ends.
 */
export async function verifyListing(
  input: ListingInput,
  onFrame: (frame: Frame) => void,
  signal?: AbortSignal,
): Promise<void> {
  const form = new FormData();
  if ("text" in input) form.set("text", input.text);
  else if ("image" in input) form.set("image", input.image);
  else form.set("sample", input.sample);

  const response = await request("/api/verify-listing", { method: "POST", body: form, signal });
  if (!response.ok || !response.body) {
    let detail = `The API answered ${response.status}.`;
    try {
      const body = await response.json();
      if (typeof body.detail === "string") detail = body.detail;
    } catch {
      // keep the status line
    }
    throw new Error(detail);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  const parse = createSseParser();
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    for (const frame of parse(decoder.decode(value, { stream: true }))) onFrame(frame);
  }
  for (const frame of parse(decoder.decode() + "\n\n")) onFrame(frame);
}
