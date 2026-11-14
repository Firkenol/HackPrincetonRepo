import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ROUTINGS, VERDICTS } from "@/lib/types";
import { HowItWorks } from "./HowItWorks";

describe("HowItWorks", () => {
  it("names the three steps, the six checks, the four verdicts and the three routings word for word", () => {
    render(<HowItWorks />);
    for (const title of ["Read the listing", "Run the checks", "Show the math"]) {
      expect(screen.getByRole("heading", { name: title })).toBeInTheDocument();
    }
    for (const title of ["Label consistency", "Form-factor bound", "Dimension bound", "Weight bound", "Label contradiction", "Chemistry mismatch"]) {
      expect(screen.getByRole("heading", { name: title })).toBeInTheDocument();
    }
    expect(screen.getAllByTestId("verdict-name").map((el) => el.textContent)).toEqual([...VERDICTS]);
    expect(screen.getAllByTestId("routing-name").map((el) => el.textContent)).toEqual([...ROUTINGS]);
  });

  it("uses the agent colours from the trace for the three steps", () => {
    render(<HowItWorks />);
    expect(screen.getByText("Listing reader")).toHaveStyle({ color: "#c99bff" });
    expect(screen.getByText("Physics checker")).toHaveStyle({ color: "#5fd6cf" });
    expect(screen.getByText("Report writer")).toHaveStyle({ color: "#ffb27a" });
  });

  it("links back to the console and to the printable report", () => {
    render(<HowItWorks />);
    expect(screen.getByRole("link", { name: /Console/ })).toHaveAttribute("href", "/");
    expect(screen.getAllByRole("link", { name: /evidence report/i })[0]).toHaveAttribute("href", "/report/fixture_01");
  });

  it("says every constant is cited, never says verified, and stays neutral about marketplaces", () => {
    const { container } = render(<HowItWorks />);
    const text = container.textContent!.toLowerCase();
    expect(text).toContain("every constant is cited");
    expect(text).not.toContain("verif");
    expect(text).not.toMatch(/fake|counterfeit|scam|fraud/);
    expect(text).not.toMatch(/seller|brand/);
  });
});
