import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ConnectorCapabilities, ExperimentalProviderBadge } from "./ConnectorCapabilities";

describe("connector capability discovery", () => {
  it("renders capability badges", () => {
    render(<ConnectorCapabilities capabilities={["SEARCH", "ENGAGEMENT_METRICS"]} />);
    expect(screen.getByText("SEARCH")).toBeInTheDocument();
    expect(screen.getByText("ENGAGEMENT METRICS")).toBeInTheDocument();
  });

  it("identifies experimental providers", () => {
    render(<ExperimentalProviderBadge />);
    expect(screen.getByText("Experimental provider")).toBeInTheDocument();
  });
});
