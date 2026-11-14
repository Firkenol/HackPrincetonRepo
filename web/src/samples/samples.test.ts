import { describe, expect, it } from "vitest";
import { buildSamples } from "../../scripts/sync-samples.mjs";
import { describeProduct } from "@/lib/describe";
import { countItems } from "@/lib/counts";
import { ROUTINGS, VERDICTS } from "@/lib/types";
import { SAMPLES, matchSample } from "./index";

describe("bundled samples", () => {
  it("are an exact copy of ../fixtures (run `npm run sync-samples` if this fails)", () => {
    expect(SAMPLES).toEqual(buildSamples());
  });

  it("are the nine fixtures, each with a report and its listing text", () => {
    expect(SAMPLES.map((s) => s.id)).toEqual(Array.from({ length: 9 }, (_, i) => `fixture_0${i + 1}`));
    for (const sample of SAMPLES) {
      expect(sample.report).not.toBeNull();
      expect(sample.listing_text).toBeTruthy();
      expect(sample.report!.checks).toHaveLength(6);
    }
  });

  it("use only the four verdicts and three routings", () => {
    for (const sample of SAMPLES) {
      expect(VERDICTS).toContain(sample.report!.verdict);
      expect(ROUTINGS).toContain(sample.report!.routing);
    }
    expect(SAMPLES.map((s) => [s.report!.verdict, s.report!.routing])).toEqual([
      ["Impossible", "auto-resolvable"],
      ["No red flags", "no action needed"],
      ["Flag", "needs human review"],
      ["Flag", "needs human review"],
      ["No checkable claim", "no action needed"],
      ["No red flags", "no action needed"],
      ["No red flags", "no action needed"],
      ["No red flags", "no action needed"],
      ["No red flags", "no action needed"],
    ]);
  });

  it("count to the totals the fixtures give", () => {
    const counts = countItems(SAMPLES);
    expect(counts.total).toBe(9);
    expect(counts.errors).toBe(0);
    expect(counts.by_verdict).toEqual({ Impossible: 1, Flag: 2, "No red flags": 5, "No checkable claim": 1 });
    expect(counts.by_routing).toEqual({ "auto-resolvable": 1, "needs human review": 2, "no action needed": 6 });
  });

  it("are found again from their pasted text, whatever the whitespace", () => {
    for (const sample of SAMPLES) {
      expect(matchSample(`  ${sample.listing_text!.replace(/\n/g, "\r\n")}  `)?.id).toBe(sample.id);
    }
    expect(matchSample("some other listing")).toBeNull();
    expect(matchSample("   ")).toBeNull();
  });
});

describe("describeProduct", () => {
  it("describes each fixture from its claims", () => {
    expect(SAMPLES.map((s) => describeProduct(s.report!.claims))).toEqual([
      "18650 lithium-ion battery, 12,000 mAh, 3.7 V",
      "AA Ni-MH battery, 700 mAh, 1.2 V",
      "AA/AAA alkaline battery, heavy duty",
      "AA/AAA zinc-carbon battery, 10-year shelf life",
      "AA/AAA zinc-carbon battery, heavy duty",
      "Lithium-ion battery, 6,200 mAh, 7.4 V, 45.88 Wh",
      "Lithium-ion battery, 2,200 mAh, 11.1 V, 24.42 Wh",
      "Lithium-ion battery, 5,200 mAh, 7.4 V, 38.48 Wh",
      "Lithium-ion battery, 5,200 mAh, 7.4 V, 38.48 Wh",
    ]);
  });

  it("never uses the listing's own title, where a seller name could sit", () => {
    for (const sample of SAMPLES) {
      const description = describeProduct(sample.report!.claims);
      const title = sample.listing_text!.split("\n")[0];
      expect(description).not.toBe(title);
      expect(description).not.toMatch(/RC |Truck|Quadcopter|Count|Pack for/);
    }
  });

  it("has a fallback when nothing was extracted", () => {
    expect(describeProduct(null)).toBe("Battery listing");
  });
});
