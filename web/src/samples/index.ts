import type { BatchItem } from "@/lib/types";
import bundled from "./samples.json";

/**
 * The nine battery fixtures and the nine check-pack fixtures (projector, magnifying
 * glass, monocular) with their expected reports, copied from ../fixtures by
 * `npm run sync-samples`. Shown, labelled as sample data, when the API is unreachable.
 */
export const SAMPLES = bundled as unknown as BatchItem[];

const normalize = (text: string) => text.split(/\s+/).filter(Boolean).join(" ");

/** The bundled sample whose listing text is the given text, ignoring whitespace. */
export function matchSample(text: string): BatchItem | null {
  const wanted = normalize(text);
  if (!wanted) return null;
  return SAMPLES.find((s) => s.listing_text && normalize(s.listing_text) === wanted) ?? null;
}
