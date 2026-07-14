export function ConnectorCapabilities({ capabilities }: { capabilities: string[] }) {
  if (!capabilities.length) return <span className="text-xs text-muted">No declared capabilities</span>;
  return <div className="flex flex-wrap justify-end gap-1.5" aria-label="Connector capabilities">{capabilities.map((capability) => <span key={capability} className="rounded-md border border-line px-2 py-1 text-[10px] font-medium text-muted">{capability.replaceAll("_", " ")}</span>)}</div>;
}

export function ExperimentalProviderBadge() {
  return <span className="rounded-md border border-amber-500/40 px-2 py-1 text-[10px] font-semibold text-amber-400">Experimental provider</span>;
}

export function ConnectorRuntimeDetails({ enabled, lastRun, lastSuccess, message }: { enabled: boolean; lastRun: string | null; lastSuccess: string | null; message: string | null }) {
  return <div className="text-right text-[10px] font-normal text-muted">
    <div>{enabled ? "Enabled" : "Disabled"} · Last run: {formatTimestamp(lastRun)}</div>
    <div>Last success: {formatTimestamp(lastSuccess)}</div>
    {message ? <div className="mt-1 max-w-sm text-amber-400" role="status">{message}</div> : null}
  </div>;
}

function formatTimestamp(value: string | null): string {
  if (!value) return "Never";
  const timestamp = new Date(value);
  return Number.isNaN(timestamp.getTime()) ? "Unknown" : timestamp.toLocaleString();
}
