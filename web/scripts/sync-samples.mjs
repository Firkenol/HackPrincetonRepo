// Copies the fixture listings and their expected reports from ../fixtures into
// src/samples/samples.json, the sample data bundled with the web app. The app shows
// these, labelled as sample data, when the API cannot be reached.
//
// Run from web/:  npm run sync-samples
// A test (src/samples/samples.test.ts) fails if the bundle drifts from ../fixtures.

import { readdirSync, readFileSync, writeFileSync, existsSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const fixtures = join(here, "..", "..", "fixtures");

// The nine battery fixtures, then the fixtures of the check packs the console knows:
// the same set and order as the API's sample list (backend/api/fixtures.py).
const SAMPLE_FILE = /^(fixture_\d{2}|pack_(projector_resolution|magnifier_lens|monocular_optics)_[a-z0-9]+)\.json$/;

export function buildSamples() {
  return readdirSync(join(fixtures, "expected"))
    .filter((name) => SAMPLE_FILE.test(name))
    .sort()
    .map((name) => {
      const id = name.replace(".json", "");
      const textPath = join(fixtures, `${id}.txt`);
      return {
        id,
        source: "text",
        listing_text: existsSync(textPath) ? readFileSync(textPath, "utf8").replace(/\r\n/g, "\n") : null,
        image_url: null,
        report: JSON.parse(readFileSync(join(fixtures, "expected", name), "utf8")),
        error: null,
      };
    });
}

if (process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1]) {
  const out = join(here, "..", "src", "samples", "samples.json");
  writeFileSync(out, JSON.stringify(buildSamples(), null, 1) + "\n", "utf8");
  console.log(`wrote ${out}`);
}
