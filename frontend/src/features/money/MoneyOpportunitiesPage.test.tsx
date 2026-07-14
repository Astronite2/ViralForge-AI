import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { MoneyOpportunity, ProductionBrief } from "../../api/types";
import { BriefPanel, OpportunityCard, OutcomeForm } from "./MoneyOpportunitiesPage";

const opportunity = {
  id: "op-1", analysis_id: "analysis-1", rank: 1, topic: "Ancient Egypt", proposed_video_angle: "Ancient Egyptian engineering methods", money_score: 81, confidence: 72, opportunity_type: "evergreen_opportunity", demand_score: 70, momentum_score: 45, competition_score: 35, evergreen_score: 82, advertiser_value_score: 55, audience_value_score: 60, watch_time_potential: 75, click_through_potential: 80, production_difficulty: 48, monetization_safety: 100, evidence_confidence: 70, channel_fit_score: null, estimated_production_hours: 10, estimated_views: { low: 10000, base: 25000, high: 50000, basis: "observed" }, estimated_rpm: { low: 1.5, base: 3.5, high: 6, basis: "benchmark" }, estimated_revenue: { low: 15, base: 88, high: 300, basis: "observed_views_benchmark_rpm" }, expected_opportunity_window: "One to three months", monetization_risks: [], evidence_summary: ["15 retrieved videos"], evidence_references: [], explanation: "Strong evergreen evidence. Revenue is an estimate, not guaranteed.", assumptions: ["Benchmark RPM"], limitations: ["Not guaranteed"], weights: {}, calculation_trace: [], engine_version: "money-v1",
} satisfies MoneyOpportunity;

describe("money opportunity MVP", () => {
  it("renders ranked score and honest estimates", () => {
    render(<OpportunityCard opportunity={opportunity} />);
    expect(screen.getByText("81")).toBeInTheDocument();
    expect(screen.getByText(/Estimated range—not guaranteed/)).toBeInTheDocument();
    expect(screen.getByText(/benchmark/)).toBeInTheDocument();
  });

  it("renders a verification-aware production brief", () => {
    const brief = { id: "brief-1", opportunity_id: "op-1", recommended_title_options: ["Title one"], primary_angle: "Engineering", target_viewer: "History viewer", viewer_promise: "Evidence-led answer", hook_options: ["Hook"], suggested_duration: "12–16 minutes", section_outline: ["Opening"], evidence_backed_facts_to_research: [], thumbnail_concepts: [], thumbnail_text_options: [], keywords: [], description_outline: [], monetization_risks: [], copyright_risks: [], production_difficulty: 48, estimated_production_hours: 10, publishing_recommendation: "This month", limitations: [] } satisfies ProductionBrief;
    render(<BriefPanel brief={brief} />);
    expect(screen.getByText("Production brief")).toBeInTheDocument();
    expect(screen.getByText(/independent verification/)).toBeInTheDocument();
  });

  it("renders the outcome form", () => {
    render(<OutcomeForm />);
    expect(screen.getByText("Outcome tracking")).toBeInTheDocument();
    expect(screen.getByLabelText("Production hours")).toBeInTheDocument();
  });
});
