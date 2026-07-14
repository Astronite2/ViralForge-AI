import { useMutation } from "@tanstack/react-query";
import { CircleDollarSign, Clock3, FileText, Search, ShieldAlert, TrendingUp } from "lucide-react";
import { useState } from "react";
import { api } from "../../api/client";
import type { MoneyOpportunity, ProductionBrief } from "../../api/types";
import { EmptyState, ErrorState, LoadingState, PageHeader, Progress, StatusPill } from "../../components/ui";

export default function MoneyOpportunitiesPage() {
  const [query, setQuery] = useState("Ancient Egypt");
  const [region, setRegion] = useState("US");
  const [selected, setSelected] = useState<MoneyOpportunity | null>(null);
  const analysis = useMutation({ mutationFn: api.analyzeMoney, onSuccess: data => setSelected(data.opportunities[0] ?? null) });
  const brief = useMutation({ mutationFn: api.moneyBrief });
  const outcome = useMutation({ mutationFn: (id: string) => api.createOutcome(id, { publish_status: "planned" }) });
  const submit = (event: React.FormEvent) => { event.preventDefault(); brief.reset(); outcome.reset(); analysis.mutate({ query: query.trim(), region, limit: 25 }); };

  return <>
    <PageHeader eyebrow="YouTube money-making MVP" title="What should I create next?" description="Rank YouTube video opportunities by relative revenue potential, competition, longevity, effort, and evidence confidence. Estimates are benchmark-labelled and never guaranteed." />
    <form className="panel mb-6 grid gap-3 p-4 md:grid-cols-[1fr_110px_auto]" onSubmit={submit}>
      <label className="text-xs text-muted">Seed niche or query<input className="input mt-2" value={query} onChange={event => setQuery(event.target.value)} minLength={2} required /></label>
      <label className="text-xs text-muted">Region<input className="input mt-2" value={region} onChange={event => setRegion(event.target.value.toUpperCase())} maxLength={8} required /></label>
      <button className="btn self-end bg-accent text-white" disabled={analysis.isPending}><Search className="h-4 w-4" />{analysis.isPending ? "Analyzing…" : "Analyze"}</button>
    </form>
    {analysis.isPending ? <LoadingState rows={6} /> : analysis.isError ? <ErrorState error={analysis.error} retry={() => analysis.mutate({ query, region, limit: 25 })} /> : analysis.data ? <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_minmax(360px,.65fr)]"><section className="space-y-4">{analysis.data.opportunities.map(item => <OpportunityCard key={item.id} opportunity={item} selected={selected?.id === item.id} onSelect={() => { setSelected(item); brief.reset(); }} />)}</section><aside className="space-y-4">{selected ? <OpportunityDetail opportunity={selected} onBrief={() => brief.mutate(selected.id)} onTrack={() => outcome.mutate(selected.id)} /> : null}{brief.isPending ? <LoadingState rows={6} /> : brief.data ? <BriefPanel brief={brief.data} /> : null}{outcome.data ? <div className="panel-pad"><StatusPill status="good" label="Outcome tracking started" /><p className="mt-3 text-xs text-muted">Record ID: {outcome.data.id}</p></div> : null}</aside></div> : <EmptyState title="Start with a niche" description="ViralForge will retrieve current YouTube comparisons and return traceable, deterministic opportunities." />}
  </>;
}

export function OpportunityCard({ opportunity, selected, onSelect }: { opportunity: MoneyOpportunity; selected?: boolean; onSelect?: () => void }) {
  return <button onClick={onSelect} className={`panel w-full p-5 text-left ${selected ? "border-accent" : ""}`}>
    <div className="flex items-start justify-between gap-4"><div><span className="subtle-label text-accent">#{opportunity.rank} · {opportunity.opportunity_type.replaceAll("_", " ")}</span><h2 className="mt-2 text-base font-semibold text-ink">{opportunity.proposed_video_angle}</h2></div><div className="text-right"><strong className="text-3xl text-success">{opportunity.money_score}</strong><span className="block text-[10px] text-muted">MONEY SCORE / 100</span></div></div>
    <div className="mt-4 grid grid-cols-2 gap-3 md:grid-cols-4"><Mini label="Confidence" value={`${opportunity.confidence}%`} /><Mini label="Views" value={range(opportunity.estimated_views, "")} /><Mini label="RPM" value={range(opportunity.estimated_rpm, "$")} /><Mini label="Revenue" value={range(opportunity.estimated_revenue, "$")} /></div>
    <p className="mt-4 text-xs leading-5 text-muted">{opportunity.explanation}</p><p className="mt-2 text-[10px] font-semibold text-warning">Estimated range—not guaranteed. RPM basis: {opportunity.estimated_rpm.basis.replaceAll("_", " ")}.</p>
  </button>;
}

function OpportunityDetail({ opportunity, onBrief, onTrack }: { opportunity: MoneyOpportunity; onBrief: () => void; onTrack: () => void }) {
  return <article className="panel-pad"><h2 className="section-title">Why this opportunity</h2><div className="mt-4 space-y-3"><Score label="Demand" value={opportunity.demand_score} /><Score label="Competition pressure" value={opportunity.competition_score} /><Score label="Evergreen" value={opportunity.evergreen_score} /><Score label="Advertiser value" value={opportunity.advertiser_value_score} /><Score label="Production difficulty" value={opportunity.production_difficulty} /></div><div className="mt-5 grid grid-cols-2 gap-3 text-xs"><Mini label="Effort" value={`${opportunity.estimated_production_hours} hours`} /><Mini label="Window" value={opportunity.expected_opportunity_window} /></div><List title="Evidence" items={opportunity.evidence_summary} /><List title="Assumptions" items={opportunity.assumptions} /><List title="Limitations" items={opportunity.limitations} /><button className="btn mt-5 bg-accent text-white" onClick={onBrief}><FileText className="h-4 w-4" />Generate brief</button><OutcomeForm onSubmit={onTrack} /></article>;
}

export function OutcomeForm({ onSubmit }: { onSubmit?: () => void }) { return <form className="mt-5 border-t border-line pt-4" onSubmit={event => { event.preventDefault(); onSubmit?.(); }}><h3 className="text-xs font-semibold">Outcome tracking</h3><div className="mt-2 grid grid-cols-2 gap-2"><label className="text-[10px] text-muted">Status<select className="input mt-1" defaultValue="planned"><option value="planned">Planned</option><option value="published">Published</option></select></label><label className="text-[10px] text-muted">Production hours<input className="input mt-1" type="number" min="0" step="0.5" /></label></div><button className="btn mt-3" type="submit"><TrendingUp className="h-4 w-4" />Start tracking</button></form>; }

export function BriefPanel({ brief }: { brief: ProductionBrief }) {
  return <article className="panel-pad"><div className="flex items-center gap-2"><FileText className="h-4 w-4 text-accent" /><h2 className="section-title">Production brief</h2></div><p className="mt-3 text-sm font-semibold">{brief.primary_angle}</p><p className="mt-2 text-xs text-muted">{brief.viewer_promise}</p><List title="Title options" items={brief.recommended_title_options} /><List title="Outline" items={brief.section_outline} /><List title="Hooks" items={brief.hook_options} /><div className="mt-4 flex gap-4 text-xs text-muted"><span><Clock3 className="mr-1 inline h-3 w-3" />{brief.suggested_duration}</span><span><CircleDollarSign className="mr-1 inline h-3 w-3" />{brief.estimated_production_hours} hours</span></div><div className="mt-4 rounded-lg border border-warning/20 bg-warning/5 p-3 text-xs text-warning"><ShieldAlert className="mr-2 inline h-4 w-4" />All factual claims are marked for independent verification. No view or earnings result is guaranteed.</div></article>;
}

function Score({ label, value }: { label: string; value: number }) { return <div><div className="mb-1 flex justify-between text-xs"><span className="text-muted">{label}</span><strong>{value}</strong></div><Progress value={value} /></div>; }
function Mini({ label, value }: { label: string; value: string }) { return <div className="rounded-lg bg-raised p-3"><span className="block text-[10px] uppercase tracking-wide text-muted">{label}</span><strong className="mt-1 block text-xs text-ink">{value}</strong></div>; }
function List({ title, items }: { title: string; items: string[] }) { return <div className="mt-5"><h3 className="text-xs font-semibold text-ink">{title}</h3><ul className="mt-2 space-y-1 text-[11px] leading-5 text-muted">{items.slice(0, 5).map((item, index) => <li key={`${title}-${index}`}>• {item}</li>)}</ul></div>; }
function range(value: { low: number | null; high: number | null }, prefix: string) { return value.low == null || value.high == null ? "Unavailable" : `${prefix}${value.low.toLocaleString()}–${prefix}${value.high.toLocaleString()}`; }
