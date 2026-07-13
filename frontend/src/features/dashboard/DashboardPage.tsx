import { Activity, BrainCircuit, Gauge, Radio, Target, Zap } from "lucide-react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Link } from "react-router-dom";
import {
  useConnectorStatuses,
  useDecisions,
  useOpportunities,
  useReasoningFeed,
  useSignals,
  useSystemHealth,
  useTopics,
} from "../../api/queries";
import type { ConnectorStatus } from "../../api/types";
import {
  ChartCard,
  DecisionBadge,
  EmptyState,
  ErrorState,
  LoadingState,
  MetricCard,
  PageHeader,
  StatusPill,
} from "../../components/ui";
import { formatDate, formatName, pct, score } from "../../lib/format";

const COLORS = ["#39c977", "#e8ad45", "#8290a3", "#4d8dff"];

export default function DashboardPage() {
  const topics = useTopics();
  const signals = useSignals();
  const decisions = useDecisions();
  const opportunities = useOpportunities();
  const connectorStatuses = useConnectorStatuses();
  const health = useSystemHealth();
  const reasoning = useReasoningFeed((topics.data ?? []).map((item) => item.id));

  if ([topics, signals, decisions].some((query) => query.isLoading)) {
    return <LoadingState rows={8} />;
  }
  if ([topics, signals, decisions].every((query) => query.isError)) {
    return (
      <ErrorState
        error={topics.error ?? signals.error ?? decisions.error}
        retry={() => {
          void topics.refetch();
          void signals.refetch();
          void decisions.refetch();
        }}
      />
    );
  }

  const topicData = topics.data ?? [];
  const signalData = signals.data ?? [];
  const decisionData = decisions.data ?? [];
  const opportunityData = opportunities.data ?? [];
  const today = new Date().toDateString();
  const todaySignals = signalData.filter(
    (item) => new Date(item.timestamp).toDateString() === today,
  );
  const averageConfidence = decisionData.length
    ? decisionData.reduce((sum, item) => sum + item.confidence, 0) /
      decisionData.length
    : 0;
  const latest = decisionData[0];
  const latestReasoning = reasoning.data[0];
  const distribution = Object.entries(
    decisionData.reduce<Record<string, number>>(
      (all, item) => ({
        ...all,
        [item.decision_type]: (all[item.decision_type] ?? 0) + 1,
      }),
      {},
    ),
  ).map(([name, value]) => ({ name: formatName(name), value }));
  const opportunityBuckets = [
    { name: "0–39", min: 0, max: 40 },
    { name: "40–59", min: 40, max: 60 },
    { name: "60–79", min: 60, max: 80 },
    { name: "80–100", min: 80, max: 101 },
  ].map((bucket) => ({
    ...bucket,
    value: opportunityData.filter(
      (item) => item.score >= bucket.min && item.score < bucket.max,
    ).length,
  }));

  return (
    <>
      <PageHeader
        eyebrow="Command center"
        title="Intelligence Dashboard"
        description="A live view of signals, deterministic decisions, evidence, and AI-grounded explanations."
      />
      <section className="mb-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-6">
        <MetricCard label="Active topics" value={topicData.length} detail="normalized topics" icon={<Target className="h-4 w-4" />} />
        <MetricCard label="Signals today" value={todaySignals.length} detail={`${signalData.length} total observed`} icon={<Radio className="h-4 w-4" />} />
        <MetricCard label="Opportunities" value={opportunityData.length} detail="historical scores" icon={<Zap className="h-4 w-4" />} tone="amber" />
        <MetricCard label="AI reasoning" value={reasoning.data.length} detail="generated explanations" icon={<BrainCircuit className="h-4 w-4" />} />
        <MetricCard label="Avg. confidence" value={pct(averageConfidence)} detail="across decisions" icon={<Gauge className="h-4 w-4" />} tone="green" />
        <MetricCard label="Latest decision" value={latest ? <DecisionBadge type={latest.decision_type} /> : "—"} detail={latest?.topic_name ?? "No decision yet"} icon={<Activity className="h-4 w-4" />} />
      </section>

      <section className="mb-5 grid gap-5 xl:grid-cols-2">
        <ChartCard title="Opportunity distribution" subtitle="Historical opportunity scores by range">
          <div className="h-56">
            {opportunityData.length ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={opportunityBuckets}>
                  <CartesianGrid stroke="#202a38" vertical={false} />
                  <XAxis dataKey="name" axisLine={false} tickLine={false} />
                  <YAxis allowDecimals={false} axisLine={false} tickLine={false} />
                  <Tooltip contentStyle={{ background: "#111823", border: "1px solid #202a38", borderRadius: 8 }} />
                  <Bar dataKey="value" fill="#4d8dff" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <EmptyState title="No opportunity scores" description="Distribution will appear after the opportunity engine records scores." />
            )}
          </div>
        </ChartCard>
        <ChartCard title="Decision distribution" subtitle="Recommendation mix from the deterministic engine">
          <div className="h-56">
            {distribution.length ? (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie data={distribution} dataKey="value" nameKey="name" innerRadius={58} outerRadius={82} paddingAngle={3}>
                    {distribution.map((_, index) => <Cell key={index} fill={COLORS[index % COLORS.length]} />)}
                  </Pie>
                  <Tooltip contentStyle={{ background: "#111823", border: "1px solid #202a38", borderRadius: 8 }} />
                </PieChart>
              </ResponsiveContainer>
            ) : <EmptyState title="No decisions" />}
          </div>
        </ChartCard>
      </section>

      <section className="mb-5 grid gap-5 xl:grid-cols-[1.2fr_.8fr]">
        <article className="panel overflow-hidden">
          <Header title="Recent signals" link="/evidence" />
          <div className="table-shell">
            {signalData.length ? (
              <table className="data-table">
                <thead><tr><th>Topic</th><th>Connector</th><th>Score</th><th>Confidence</th><th>Observed</th></tr></thead>
                <tbody>{signalData.slice(0, 6).map((item) => (
                  <tr key={item.id}><td><strong>{item.topic_name}</strong></td><td>{formatName(item.source)}</td><td>{score(item.score)}</td><td>{pct(item.confidence)}</td><td className="whitespace-nowrap text-muted!">{formatDate(item.timestamp)}</td></tr>
                ))}</tbody>
              </table>
            ) : <EmptyState title="No signals received" />}
          </div>
        </article>
        <article className="panel overflow-hidden">
          <Header title="Connector health" link="/settings" />
          <div className="space-y-3 p-5">
            {(connectorStatuses.data ?? fallbackStatuses()).map((connector) => (
              <div className="flex items-center justify-between rounded-lg border border-line bg-raised/40 p-3" key={connector.connector_name}>
                <div className="min-w-0 pr-3">
                  <strong className="block text-xs">{formatName(connector.connector_name)}</strong>
                  <span className="block truncate text-[10px] text-muted">{connectorDetail(connector)}</span>
                </div>
                <StatusPill status={connectorTone(connector.status, health.ready.isError)} label={health.ready.isError ? "offline" : connector.status} />
              </div>
            ))}
            <div className="flex items-center justify-between rounded-lg border border-dashed border-line p-3 opacity-60">
              <div><strong className="block text-xs">Future connectors</strong><span className="text-[10px] text-muted">Auto-discovered from evidence</span></div>
              <StatusPill status="neutral" label="disabled" />
            </div>
          </div>
        </article>
      </section>

      <section className="grid gap-5 xl:grid-cols-[1.15fr_.85fr]">
        <article className="panel overflow-hidden">
          <Header title="Recent decisions" link="/decisions" />
          <div className="table-shell">
            {decisionData.length ? (
              <table className="data-table">
                <thead><tr><th>Topic</th><th>Decision</th><th>Score</th><th>Confidence</th><th>Created</th></tr></thead>
                <tbody>{decisionData.slice(0, 6).map((item) => (
                  <tr key={item.id}><td><Link className="font-semibold text-ink no-underline hover:text-accent" to={`/decisions/${item.id}`}>{item.topic_name}</Link></td><td><DecisionBadge type={item.decision_type} /></td><td>{score(item.score)}</td><td>{pct(item.confidence)}</td><td className="whitespace-nowrap text-muted!">{formatDate(item.created_at)}</td></tr>
                ))}</tbody>
              </table>
            ) : <EmptyState title="No decisions yet" />}
          </div>
        </article>
        <article className="panel-pad">
          <div className="mb-4 flex items-center justify-between">
            <div><p className="subtle-label text-accent">Latest AI explanation</p><h2 className="mt-1 section-title">Grounded reasoning</h2></div>
            {latestReasoning && <StatusPill status="good" label={latestReasoning.status} />}
          </div>
          {latestReasoning ? (
            <><p className="text-sm leading-6 text-ink">{latestReasoning.executive_summary}</p><div className="mt-4 border-t border-line pt-4"><span className="subtle-label">Why now</span><p className="mt-2 text-xs leading-5 text-muted">{latestReasoning.why_now || "No timing narrative supplied."}</p></div></>
          ) : reasoning.isLoading ? <LoadingState rows={3} /> : <EmptyState title="AI reasoning not generated" description="The deterministic dashboard remains fully available while AI reasoning is disabled or has no completed runs." />}
        </article>
      </section>
    </>
  );
}

function Header({ title, link }: { title: string; link: string }) {
  return <div className="flex items-center justify-between border-b border-line px-5 py-4"><h2 className="section-title">{title}</h2><Link className="text-[11px] font-medium text-accent no-underline hover:underline" to={link}>View all</Link></div>;
}

function connectorTone(status: ConnectorStatus["status"], offline: boolean): "good" | "warn" | "bad" | "neutral" {
  if (offline) return "bad";
  if (status === "active") return "good";
  if (status === "degraded" || status === "unavailable") return "warn";
  return "neutral";
}

function connectorDetail(connector: ConnectorStatus): string {
  if (connector.message) return connector.message;
  if (connector.status === "active") return `Recent data via ${connector.provider ?? "provider"}`;
  if (connector.status === "disabled") return "Disabled by configuration";
  return `Provider ${connector.provider ?? "not selected"}; no successful current run`;
}

function fallbackStatuses(): ConnectorStatus[] {
  return ["google_trends", "youtube"].map((connector_name) => ({
    connector_name,
    status: "unobserved",
    enabled: true,
    provider: null,
    provider_experimental: false,
    last_run_at: null,
    last_success_at: null,
    error_code: null,
    message: null,
  }));
}
