import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ConnectorCapabilities, ConnectorRuntimeDetails, ExperimentalProviderBadge } from "./ConnectorCapabilities";

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

  it("renders disabled Reddit state and safe errors", () => {
    render(<ConnectorRuntimeDetails enabled={false} lastRun={null} lastSuccess={null} message="Reddit connector is disabled by configuration." />);
    expect(screen.getByText(/Disabled · Last run: Never/)).toBeInTheDocument();
    expect(screen.getByText("Reddit connector is disabled by configuration.")).toBeInTheDocument();
  });

  it("renders an active connector observation", () => {
    render(<ConnectorRuntimeDetails enabled lastRun="2026-01-01T00:00:00Z" lastSuccess="2026-01-01T00:00:00Z" message={null} />);
    expect(screen.getByText(/Enabled · Last run:/)).toBeInTheDocument();
    expect(screen.getAllByText(/Last success:/).at(-1)).toBeInTheDocument();
  });
});
