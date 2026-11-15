import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { EmptyState } from "./EmptyState";
import { ErrorState } from "./ErrorState";
import { BatchTableSkeleton, FeedSkeleton, MathSkeleton, MetricsSkeleton, TraceSkeleton, VerdictCardSkeleton } from "./Skeletons";
import { Spinner } from "./Spinner";

describe("Skeletons", () => {
  it.each([
    ["metrics", <MetricsSkeleton key="m" />, "Loading batch totals"],
    ["feed", <FeedSkeleton key="f" />, "Loading the audit feed"],
    ["verdict card", <VerdictCardSkeleton key="v" />, "Loading the verdict card"],
    ["math", <MathSkeleton key="x" />, "Loading the checks"],
    ["trace", <TraceSkeleton key="t" />, "Loading the trace"],
    ["batch", <BatchTableSkeleton key="b" />, "Loading the batch"],
  ])("%s skeleton is a busy status with a label and no numbers", (_name, element, label) => {
    const { container } = render(element);
    const status = screen.getByRole("status", { name: label });
    expect(status).toHaveAttribute("aria-busy", "true");
    expect(container.textContent).toBe(label); // only the screen-reader label, nothing made up
  });

  it("the math skeleton has six rows, like the six checks", () => {
    render(<MathSkeleton />);
    expect(screen.getAllByRole("listitem")).toHaveLength(6);
  });
});

describe("Spinner", () => {
  it("is a status with its label", () => {
    render(<Spinner label="Checking the listing" />);
    expect(screen.getByRole("status")).toHaveTextContent("Checking the listing");
  });
});

describe("ErrorState", () => {
  it("says what went wrong and what to do next, and offers a retry", () => {
    const retry = vi.fn();
    render(<ErrorState kind="offline" detail="The Carnot API could not be reached." onRetry={retry} />);
    const alert = screen.getByRole("alert");
    expect(alert).toHaveTextContent("The API could not be reached");
    expect(alert).toHaveTextContent("The Carnot API could not be reached.");
    expect(alert).toHaveTextContent(/What to do next: Start the API/);
    fireEvent.click(screen.getByRole("button", { name: "Try again" }));
    expect(retry).toHaveBeenCalledOnce();
  });

  it("takes a custom title and next step", () => {
    render(<ErrorState title="Nothing came back" next="Paste the listing again." />);
    expect(screen.getByRole("alert")).toHaveTextContent("Nothing came back");
    expect(screen.getByRole("alert")).toHaveTextContent("Paste the listing again.");
    expect(screen.queryByRole("button")).toBeNull();
  });

  it("stays neutral: never verified, never about a marketplace or seller", () => {
    const { container } = render(
      <>
        <ErrorState kind="offline" />
        <ErrorState kind="failed" />
        <ErrorState kind="rejected" />
      </>,
    );
    const text = container.textContent!.toLowerCase();
    expect(text).not.toMatch(/verif|seller|fake|marketplace/);
  });
});

describe("EmptyState", () => {
  it("shows the title, the text and the action", () => {
    render(<EmptyState title="Nothing checked yet" text="Paste a listing or run the batch." action={<button type="button">Run batch</button>} />);
    expect(screen.getByTestId("empty-state")).toHaveTextContent("Nothing checked yet");
    expect(screen.getByRole("button", { name: "Run batch" })).toBeInTheDocument();
  });
});
