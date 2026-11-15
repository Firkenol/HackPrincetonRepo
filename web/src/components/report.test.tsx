import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { VERDICTS, type Listing, type Verdict } from "@/lib/types";
import { SAMPLES } from "@/samples";
import { AuditFeed } from "./AuditFeed";
import { BatchView } from "./BatchView";
import { MathModule, stepParts } from "./MathModule";
import { VerdictBadge } from "./VerdictBadge";
import { VerdictCard } from "./VerdictCard";
import { countItems } from "@/lib/counts";

function listingOf(index: number): Listing {
  const sample = SAMPLES[index];
  return {
    key: sample.id,
    text: sample.listing_text,
    imageUrl: null,
    report: sample.report,
    error: null,
    events: [],
    running: false,
    sample: true,
  };
}

const CASES = SAMPLES.map((sample, index) => [sample.id, index] as const);

describe("VerdictBadge", () => {
  const colors: Record<Verdict, string> = {
    Impossible: "text-impossible",
    Flag: "text-flag",
    "No red flags": "text-clear",
    "No checkable claim": "text-quiet",
  };

  it.each(VERDICTS)("shows %s word for word in its own colour", (verdict) => {
    render(<VerdictBadge verdict={verdict} />);
    const badge = screen.getByTestId("verdict-badge");
    expect(badge).toHaveTextContent(new RegExp(`^${verdict}$`));
    expect(badge.className).toContain(colors[verdict]);
  });

  it("maps the palette to red, amber, green and gray", async () => {
    const css = (await import("node:fs")).readFileSync("src/app/globals.css", "utf8");
    expect(css).toMatch(/--color-impossible:\s*#f26d78/); // red
    expect(css).toMatch(/--color-flag:\s*#f2b441/); // amber
    expect(css).toMatch(/--color-clear:\s*#4fcf8e/); // green
    expect(css).toMatch(/--color-quiet:\s*#9aa4b2/); // gray
  });
});

describe.each(CASES)("%s", (_id, index) => {
  const listing = listingOf(index);
  const report = listing.report!;

  it("renders the verdict card: listing on the left, verdict and routing on the right", () => {
    render(<VerdictCard listing={listing} />);
    expect(screen.getByTestId("listing-text")).toHaveTextContent(listing.text!.split("\n")[0]);
    expect(screen.getByTestId("verdict-badge")).toHaveTextContent(new RegExp(`^${report.verdict}$`));
    expect(screen.getByTestId("routing-label")).toHaveTextContent(report.routing);
    expect(screen.getByText(report.verdict_reason)).toBeInTheDocument();
    expect(screen.getByText(report.routing_reason)).toBeInTheDocument();
    expect(screen.getByTestId("card-sample-label")).toHaveTextContent("Sample data");
    expect(screen.getByRole("button", { name: /Download report JSON/ })).toBeInTheDocument();
  });

  it("shows the math for every check, taken from the report", () => {
    render(<MathModule report={report} />);
    const rows = screen.getAllByTestId("check");
    expect(rows.map((row) => row.getAttribute("data-check-id"))).toEqual(report.checks.map((c) => c.check_id));

    report.checks.forEach((check, i) => {
      const row = rows[i];
      const toggle = within(row).getAllByRole("button")[0];
      if (toggle.getAttribute("aria-expanded") === "false") fireEvent.click(toggle);
      expect(toggle).toHaveAttribute("aria-expanded", "true");

      expect(within(row).getByText(check.title)).toBeInTheDocument();
      if (check.formula) expect(within(row).getByTestId("check-formula")).toHaveTextContent(check.formula);
      expect(within(row).queryAllByTestId("check-step").map((el) => el.textContent)).toEqual(
        check.steps.map((step, n) => `${n + 1}${step.text}`),
      );
      for (const input of check.inputs) expect(within(row).getAllByText(input.name).length).toBeGreaterThan(0);
      for (const constant of check.constants) {
        expect(within(row).getAllByText(constant.description).length).toBeGreaterThan(0);
        expect(row).toHaveTextContent(constant.source_title);
      }
      if (check.status === "not_assessed") {
        expect(within(row).getByTestId("not-assessed-reason")).toHaveTextContent(check.not_assessed_reason!);
      } else {
        expect(within(row).queryByTestId("not-assessed-reason")).toBeNull();
      }
    });
  });

  it("opens the checks that decided the verdict without a click", () => {
    render(<MathModule report={report} />);
    screen.getAllByTestId("check").forEach((row, i) => {
      const decided = ["violated", "flag"].includes(report.checks[i].status);
      expect(within(row).getAllByRole("button")[0]).toHaveAttribute("aria-expanded", String(decided));
    });
  });

  it("never says verified", () => {
    const { container } = render(
      <>
        <VerdictCard listing={listing} />
        <MathModule report={report} />
      </>,
    );
    // a pack report can have its only check already open, so there may be nothing to expand
    screen.queryAllByRole("button", { expanded: false }).forEach((button) => fireEvent.click(button));
    expect(container.textContent!.toLowerCase()).not.toContain("verif");
  });
});

describe("AuditFeed", () => {
  it("lists each listing by product description, never by its title", () => {
    const listings = SAMPLES.map((_, i) => listingOf(i));
    render(<AuditFeed listings={listings} selectedKey="fixture_01" onSelect={() => {}} />);
    const items = screen.getAllByTestId("feed-item");
    expect(items).toHaveLength(29);
    expect(items[20]).toHaveTextContent("Magnifying glass, 3×, 75 mm lens");
    expect(items[0]).toHaveTextContent("18650 lithium-ion battery, 12,000 mAh, 3.7 V");
    expect(items[0]).toHaveAttribute("aria-current", "true");
    items.forEach((item, i) => {
      expect(item).not.toHaveTextContent(listings[i].text!.split("\n")[0]);
      expect(within(item).getByTestId("verdict-badge")).toHaveTextContent(listings[i].report!.verdict);
    });
  });

  it("does not show a pasted title even before the report arrives", () => {
    const running: Listing = { ...listingOf(0), key: "check-1", text: "Zentrovolt Outlet 18650", report: null, running: true };
    render(<AuditFeed listings={[running]} selectedKey={null} onSelect={() => {}} />);
    expect(screen.getByTestId("feed-item")).toHaveTextContent("Checking a listing");
    expect(screen.getByTestId("feed-item")).not.toHaveTextContent("Zentrovolt");
  });
});

describe("BatchView", () => {
  it("shows one row per listing and the routing split", () => {
    const opened: string[] = [];
    render(
      <BatchView
        items={SAMPLES}
        counts={countItems(SAMPLES)}
        running={false}
        canRun
        sampleLabel="Sample data"
        onRun={() => {}}
        onOpen={(id) => opened.push(id)}
      />,
    );
    expect(screen.getAllByTestId("batch-row")).toHaveLength(29);
    expect(screen.getByTestId("batch-auto")).toHaveTextContent("2");
    expect(screen.getByTestId("batch-human")).toHaveTextContent("10");
    expect(screen.getByTestId("batch-none")).toHaveTextContent("17");
    expect(screen.getByTestId("batch-sample-label")).toHaveTextContent("Sample data");

    fireEvent.click(screen.getByRole("button", { name: "AA Ni-MH battery, 700 mAh, 1.2 V" }));
    expect(opened).toEqual(["fixture_02"]);
  });

  it("says so when nothing has run", () => {
    render(<BatchView items={[]} counts={null} running={false} canRun sampleLabel={null} onRun={() => {}} onOpen={() => {}} />);
    expect(screen.getByText(/No batch has run yet/)).toBeInTheDocument();
  });
});

describe("the arithmetic display", () => {
  const steps = SAMPLES.flatMap((sample) => sample.report!.checks.flatMap((check) => check.steps));

  it("cuts a step into label, working and result without changing a character", () => {
    expect(steps.length).toBeGreaterThan(0);
    for (const step of steps) {
      const { label, working, result } = stepParts(step);
      const joined = `${label === null ? "" : `${label}: `}${working}${result === null ? "" : ` = ${result}`}`;
      expect(joined).toBe(step.text);
    }
  });

  it("draws the comparison against its limit, with the two values the report gives", () => {
    const report = SAMPLES[0].report!; // 44.4 Wh against a 23.19 Wh cap
    render(<MathModule report={report} />);
    const gauge = screen.getByTestId("check-gauge");
    const comparison = report.checks.flatMap((c) => c.steps).find((s) => s.label === "Comparison")!;
    expect(gauge).toHaveAccessibleName(comparison.text);
    expect(gauge).toHaveTextContent("44.4 Wh");
    expect(gauge).toHaveTextContent("23.19 Wh");
    expect(gauge).toHaveTextContent("the cap");
  });
});
