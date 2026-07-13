import { BrainCircuit, CircleOff, Database, Monitor, Server, SunMoon } from "lucide-react";
import {
  useConnectorStatuses,
  useDecisions,
  useOpportunities,
  useReasoningFeed,
  useSystemHealth,
  useTopics,
} from "../../api/queries";
import type { ConnectorStatus } from "../../api/types";
import { EmptyState, LoadingState, PageHeader, StatusPill } from "../../components/ui";
import { formatName } from "../../lib/format";

export default function SettingsPage() {
  const topics = useTopics();
  const decisions = useDecisions();
  const opportunities = useOpportunities();
  const health = useSystemHealth();
  const connectors = useConnectorStatuses();
  const reasoning = useReasoningFeed((topics.data ?? []).map((item) => item.id));

  if (topics.isLoading) return <LoadingState rows={8} />;

  const ai = reasoning.data[0];
  const decisionVersion = decisions.data?.[0]?.engine_version;
  const opportunityVersion = opportunities.data?.[0]?.version;

  return (
    <>
      <PageHeader
        eyebrow="Read-only configuration"
        title="Settings"
        description="Runtime health, observed integrations, provider metadata, and engine versions. Editing is intentionally disabled."
      />
      <section className="grid gap-5 lg:grid-cols-2">
        <SettingsCard icon={<Monitor />} title="Display">
          <Row label="Theme" value={<span className="inline-flex items-center gap-2"><SunMoon className="h-3.5 w-3.5 text-accent" />System toggle available in top bar</span>} />
          <Row label="Density" value="Desktop optimized" />
          <Row label="Motion" value="Reduced / functional only" />
        </SettingsCard>

        <SettingsCard icon={<Server />} title="System health">
          <Row label="API" value={<StatusPill status={health.health.isSuccess ? "good" : "bad"} label={health.health.data?.status ?? "offline"} />} />
          <Row label="PostgreSQL" value={<StatusPill status={health.ready.data?.postgres === "ready" || health.ready.data?.postgres === "ok" ? "good" : health.ready.isError ? "bad" : "warn"} label={health.ready.data?.postgres ?? "unknown"} />} />
          <Row label="Redis" value={<StatusPill status={health.ready.data?.redis === "ready" || health.ready.data?.redis === "ok" ? "good" : health.ready.isError ? "bad" : "warn"} label={health.ready.data?.redis ?? "unknown"} />} />
        </SettingsCard>

        <SettingsCard icon={<Database />} title="Connector status">
          {connectors.data?.length ? connectors.data.map((connector) => (
            <Row
              key={connector.connector_name}
              label={formatName(connector.connector_name)}
              value={
                <span className="inline-flex items-center gap-2">
                  <span className="text-[10px] text-muted">{providerLabel(connector)}</span>
                  <StatusPill status={connectorTone(connector.status)} label={connector.status} />
                </span>
              }
            />
          )) : connectors.isLoading ? <LoadingState rows={2} /> : <EmptyState title="No connector runtime status" />}
          <Row label="Future connectors" value={<span className="inline-flex items-center gap-1.5 text-muted"><CircleOff className="h-3.5 w-3.5" />Disabled</span>} />
        </SettingsCard>

        <SettingsCard icon={<BrainCircuit />} title="Reasoning provider">
          <Row label="Status" value={<StatusPill status={ai ? "good" : "neutral"} label={ai ? "output observed" : "no runs"} />} />
          <Row label="Provider" value={ai?.model_provider ?? "Not observable"} />
          <Row label="Model" value={ai?.model_name ?? "Not observable"} />
          <Row label="Prompt version" value={ai?.prompt_version ?? "—"} />
        </SettingsCard>

        <SettingsCard icon={<Database />} title="Versions">
          <Row label="Decision engine" value={decisionVersion ?? "No records"} />
          <Row label="Opportunity engine" value={opportunityVersion ?? "No records"} />
          <Row label="Reasoning context" value={ai?.context_version ?? "No records"} />
          <Row label="Frontend" value={__APP_VERSION__} />
        </SettingsCard>

        <SettingsCard icon={<Server />} title="Database health">
          <Row label="Readiness" value={health.ready.data?.status ?? "Unknown"} />
          <Row label="Tracked topics" value={String(topics.data?.length ?? 0)} />
          <Row label="Stored decisions" value={String(decisions.data?.length ?? 0)} />
          <Row label="Opportunity scores" value={String(opportunities.data?.length ?? 0)} />
        </SettingsCard>
      </section>
    </>
  );
}

function connectorTone(status: ConnectorStatus["status"]): "good" | "warn" | "bad" | "neutral" {
  if (status === "active") return "good";
  if (status === "degraded" || status === "unavailable") return "warn";
  return "neutral";
}

function providerLabel(connector: ConnectorStatus): string {
  const experimental = connector.provider_experimental ? " · experimental" : "";
  return `${connector.provider ?? "no provider"}${experimental}`;
}

function SettingsCard({ icon, title, children }: { icon: React.ReactNode; title: string; children: React.ReactNode }) {
  return <article className="panel overflow-hidden"><div className="flex items-center gap-2 border-b border-line px-5 py-4 text-accent"><span className="[&>svg]:h-4 [&>svg]:w-4">{icon}</span><h2 className="section-title text-ink">{title}</h2></div><div className="divide-y divide-line px-5">{children}</div></article>;
}

function Row({ label, value }: { label: string; value: React.ReactNode }) {
  return <div className="flex min-h-12 items-center justify-between gap-4 py-3 text-xs"><span className="text-muted">{label}</span><strong className="text-right font-medium text-ink">{value}</strong></div>;
}
