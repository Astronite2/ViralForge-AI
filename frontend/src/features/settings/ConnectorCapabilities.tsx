export function ConnectorCapabilities({ capabilities }: { capabilities: string[] }) {
  if (!capabilities.length) return <span className="text-xs text-muted">No declared capabilities</span>;
  return <div className="flex flex-wrap justify-end gap-1.5" aria-label="Connector capabilities">{capabilities.map((capability) => <span key={capability} className="rounded-md border border-line px-2 py-1 text-[10px] font-medium text-muted">{capability.replaceAll("_", " ")}</span>)}</div>;
}

export function ExperimentalProviderBadge() {
  return <span className="rounded-md border border-amber-500/40 px-2 py-1 text-[10px] font-semibold text-amber-400">Experimental provider</span>;
}
