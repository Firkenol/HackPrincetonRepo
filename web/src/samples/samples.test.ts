import { describe, expect, it } from "vitest";
import { buildSamples } from "../../scripts/sync-samples.mjs";
import { describeProduct, describeReport } from "@/lib/describe";
import { countItems } from "@/lib/counts";
import { ROUTINGS, VERDICTS } from "@/lib/types";
import { SAMPLES, matchSample } from "./index";

describe("bundled samples", () => {
  it("are an exact copy of ../fixtures (run `npm run sync-samples` if this fails)", () => {
    expect(SAMPLES).toEqual(buildSamples());
  });

  it("are the twenty battery fixtures and nine pack fixtures, each with a report and its listing text", () => {
    expect(SAMPLES.map((s) => s.id)).toEqual([
      ...Array.from({ length: 20 }, (_, i) => `fixture_${String(i + 1).padStart(2, "0")}`),
      "pack_magnifier_lens_honest",
      "pack_magnifier_lens_impossible",
      "pack_magnifier_lens_missing",
      "pack_monocular_optics_flag",
      "pack_monocular_optics_honest",
      "pack_monocular_optics_missing",
      "pack_projector_resolution_flag",
      "pack_projector_resolution_honest",
      "pack_projector_resolution_missing",
    ]);
    const checksPerPack: Record<string, number> = { magnifier_lens: 1, monocular_optics: 2, projector_resolution: 1 };
    for (const sample of SAMPLES) {
      expect(sample.report).not.toBeNull();
      expect(sample.listing_text).toBeTruthy();
      const pack = sample.report!.pack;
      expect(sample.id.startsWith("pack_")).toBe(pack !== undefined);
      expect(sample.report!.checks).toHaveLength(pack ? checksPerPack[pack] : 6);
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
      // 10 to 20, from real listing screenshots: six with nothing a calculation can test
      // (three of them state a shelf life, which goes to a person), then five honest packs
      ["No checkable claim", "no action needed"],
      ["No checkable claim", "needs human review"],
      ["No checkable claim", "needs human review"],
      ["No checkable claim", "needs human review"],
      ["No checkable claim", "no action needed"],
      ["No checkable claim", "no action needed"],
      ["No red flags", "no action needed"],
      ["No red flags", "no action needed"],
      ["No red flags", "no action needed"],
      ["No red flags", "no action needed"],
      ["No red flags", "no action needed"],
      // magnifying glass: honest, trips the rule, missing data
      ["No red flags", "no action needed"],
      ["Impossible", "auto-resolvable"],
      ["No checkable claim", "needs human review"],
      // monocular: both its rules give a flag (listed dimensions can be wrong)
      ["Flag", "needs human review"],
      ["No red flags", "no action needed"],
      ["No checkable claim", "needs human review"],
      // projector: its rule gives a flag, never a hard result
      ["Flag", "needs human review"],
      ["No red flags", "no action needed"],
      ["No checkable claim", "needs human review"],
    ]);
  });

  it("count to the totals the fixtures give", () => {
    const counts = countItems(SAMPLES);
    expect(counts.total).toBe(29);
    expect(counts.errors).toBe(0);
    expect(counts.by_verdict).toEqual({ Impossible: 2, Flag: 4, "No red flags": 13, "No checkable claim": 10 });
    expect(counts.by_routing).toEqual({ "auto-resolvable": 2, "needs human review": 10, "no action needed": 17 });
  });

  it("are found again from their pasted text, whatever the whitespace", () => {
    for (const sample of SAMPLES) {
      expect(matchSample(`  ${sample.listing_text!.replace(/\n/g, "\r\n")}  `)?.id).toBe(sample.id);
    }
    expect(matchSample("some other listing")).toBeNull();
    expect(matchSample("   ")).toBeNull();
  });
});

describe("describeReport", () => {
  it("describes each fixture from its claims", () => {
    expect(SAMPLES.map((s) => describeReport(s.report))).toEqual([
      "18650 lithium-ion battery, 12,000 mAh, 3.7 V",
      "AA Ni-MH battery, 700 mAh, 1.2 V",
      "AA/AAA alkaline battery, heavy duty",
      "AA/AAA zinc-carbon battery, 10-year shelf life",
      "AA/AAA zinc-carbon battery, heavy duty",
      "Lithium-ion battery, 6,200 mAh, 7.4 V, 45.88 Wh",
      "Lithium-ion battery, 2,200 mAh, 11.1 V, 24.42 Wh",
      "Lithium-ion battery, 5,200 mAh, 7.4 V, 38.48 Wh",
      "Lithium-ion battery, 5,200 mAh, 7.4 V, 38.48 Wh",
      "AAA alkaline battery, 1.5 V",
      "9V alkaline battery, 9 V, 7-year shelf life",
      "AAA alkaline battery, 12-year shelf life",
      "AAA alkaline battery, 1.5 V, 10-year shelf life",
      "Battery, 6 V",
      "AAA zinc-carbon battery, 1.5 V",
      "Lithium-ion pack, 2,000 mAh, 3.7 V, 7.4 Wh",
      "Lithium-ion pack, 1,300 mAh, 11.1 V, 14.4 Wh",
      "Lithium-ion pack, 3,000 mAh, 3.7 V, 11.1 Wh",
      "Lithium-ion pack, 1,000 mAh, 3.7 V, 3.7 Wh",
      "Lithium-ion pack, 1,100 mAh, 3.7 V, 4.1 Wh",
      "Magnifying glass, 3×, 75 mm lens",
      "Magnifying glass, 30×, 75 mm lens",
      "Magnifying glass, 30×",
      "Monocular, 80×100",
      "Monocular, 12×50",
      "Monocular, 80×100",
      "Projector, 4K headline, native 1,280 × 720",
      "Projector, 1080p headline, native 1,920 × 1,080",
      "Projector, 4K headline",
    ]);
  });

  it("never uses the listing's own title, where a seller name could sit", () => {
    for (const sample of SAMPLES) {
      const description = describeReport(sample.report);
      const title = sample.listing_text!.split("\n")[0];
      expect(description).not.toBe(title);
      expect(description).not.toMatch(/RC |Truck|Quadcopter|Count|Pack for/);
    }
  });

  it("has a fallback when nothing was extracted", () => {
    expect(describeProduct(null)).toBe("Battery listing");
    expect(describeReport(null)).toBe("Listing");
    expect(describeReport({ ...SAMPLES[20].report!, pack: "some_new_pack" })).toBe("Listing");
  });
});
