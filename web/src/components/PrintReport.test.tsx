import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { SAMPLES } from "@/samples";
import { PrintReport, claimRows } from "./PrintReport";

const CASES = SAMPLES.map((sample) => [sample.id, sample] as const);

describe.each(CASES)("PrintReport %s", (_id, sample) => {
  const report = sample.report!;

  it("lays out the verdict, routing, claims and all six checks from the report", () => {
    render(<PrintReport sample={sample} />);
    expect(screen.getByTestId("print-verdict")).toHaveTextContent(new RegExp(`^${report.verdict}$`));
    expect(screen.getByTestId("print-routing")).toHaveTextContent(new RegExp(`^${report.routing}$`));
    // a verdict reason can repeat a check's summary word for word, so it may appear twice
    expect(screen.getAllByText(report.verdict_reason).length).toBeGreaterThan(0);
    expect(screen.getAllByText(report.routing_reason).length).toBeGreaterThan(0);

    const checks = screen.getAllByTestId("print-check");
    expect(checks.map((c) => c.getAttribute("data-check-id"))).toEqual(report.checks.map((c) => c.check_id));
    report.checks.forEach((check, i) => {
      const row = checks[i];
      expect(within(row).getByText(check.title)).toBeInTheDocument();
      if (check.formula) expect(within(row).getByTestId("print-formula")).toHaveTextContent(check.formula);
      expect(within(row).queryAllByTestId("print-step").map((el) => el.textContent)).toEqual(check.steps.map((s, n) => `${n + 1}${s.text}`));
      for (const constant of check.constants) expect(row).toHaveTextContent(constant.source_title);
      if (check.status === "not_assessed") expect(row).toHaveTextContent(check.not_assessed_reason!);
    });

    expect(screen.getAllByTestId("print-claim")).toHaveLength(claimRows(report.claims).length);
    for (const line of report.not_assessed) expect(screen.getByTestId("print-not-assessed")).toHaveTextContent(line);
  });

  it("never says verified and shows no seller, store or brand", () => {
    const { container } = render(<PrintReport sample={sample} />);
    const text = container.textContent!.toLowerCase();
    expect(text).not.toContain("verif");
    // "store" and "brand" alone are not checked: a cited datasheet publisher's name may contain them
    expect(text).not.toMatch(/seller|marketplace|sold by/);
    // the listing's own title (where a seller name could sit) is never printed
    expect(container.textContent).not.toContain(sample.listing_text!.split("\n")[0]);
  });
});

describe("PrintReport controls", () => {
  it("prints from the page and links back to the console and How it works", () => {
    const print = vi.fn();
    vi.stubGlobal("print", print);
    render(<PrintReport sample={SAMPLES[0]} />);
    fireEvent.click(screen.getByRole("button", { name: "Print report" }));
    expect(print).toHaveBeenCalledOnce();
    expect(screen.getByRole("link", { name: /Console/ })).toHaveAttribute("href", "/");
    expect(screen.getByRole("link", { name: /How it works/ })).toHaveAttribute("href", "/how-it-works");
  });

  it("lists each stated claim once, with where it was found", () => {
    const rows = claimRows(SAMPLES[0].report!.claims);
    expect(rows.map((r) => r.field)).toEqual(["Chemistry", "Size code", "Nominal voltage", "Capacity", "Weight (package)", "Dimensions (package)"]);
    expect(rows.find((r) => r.field === "Capacity")).toMatchObject({ value: "12,000 mAh", found_in: "title" });
  });
});
