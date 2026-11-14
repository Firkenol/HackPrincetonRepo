import { readFileSync } from "node:fs";
import path from "node:path";
import type { EvidenceReport } from "../lib/types";

export const FIXTURE_IDS = [1, 2, 3, 4, 5, 6, 7, 8, 9];

export const expectedReport = (id: number): EvidenceReport =>
  JSON.parse(readFileSync(path.resolve(__dirname, "../../fixtures/expected", `fixture_${String(id).padStart(2, "0")}.json`), "utf8"));

/** Optional folder for screenshots, for eyeballing the result. */
export const SHOTS = process.env.CLAIMCHECK_SHOTS;
