import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { DecisionBadge, EmptyState, StatusPill } from "./ui";

describe("shared intelligence UI", () => {
  it("renders decision types as readable labels", () => {
    render(<DecisionBadge type="create" />);
    expect(screen.getByText("Create")).toBeInTheDocument();
  });

  it("announces explicit empty states", () => {
    render(<EmptyState title="No signals" description="Run the connector pipeline." />);
    expect(screen.getByText("No signals")).toBeInTheDocument();
    expect(screen.getByText("Run the connector pipeline.")).toBeInTheDocument();
  });

  it("renders operational status text", () => {
    render(<StatusPill status="good" label="ready" />);
    expect(screen.getByText("ready")).toBeInTheDocument();
  });
});
