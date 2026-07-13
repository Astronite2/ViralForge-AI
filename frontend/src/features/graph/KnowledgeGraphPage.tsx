import { Background, Controls, Handle, MarkerType, Position, ReactFlow, type Edge, type Node, type NodeProps } from "@xyflow/react";
import { Network } from "lucide-react";
import { useMemo, useState } from "react";
import { useGraph, useTopics } from "../../api/queries";
import { EmptyState, ErrorState, LoadingState, PageHeader, StatusPill } from "../../components/ui";
import { formatName } from "../../lib/format";

type TopicNode = Node<{ label: string; primary: boolean }, "topic">;
const nodeTypes = { topic: TopicNodeCard };

export default function KnowledgeGraphPage() {
  const topics = useTopics();
  const [selected, setSelected] = useState("");
  const topicId = selected || topics.data?.[0]?.id;
  const graph = useGraph(topicId);
  const names = useMemo(() => new Map((topics.data ?? []).map((item) => [item.id, item.display_name])), [topics.data]);
  const elements = useMemo(() => {
    if (!graph.data) return { nodes: [] as TopicNode[], edges: [] as Edge[] };
    const ids = Array.from(new Set([graph.data.topic_id, ...graph.data.relationships.flatMap((item) => [item.source_topic_id, item.target_topic_id])]));
    const nodes: TopicNode[] = ids.map((id, index) => {
      const angle = (Math.PI * 2 * Math.max(0, index - 1)) / Math.max(1, ids.length - 1);
      const primary = id === graph.data!.topic_id;
      return { id, type: "topic", position: primary ? { x: 360, y: 210 } : { x: 360 + Math.cos(angle) * 270, y: 210 + Math.sin(angle) * 170 }, data: { label: names.get(id) ?? (primary ? graph.data!.topic_name : id.slice(0, 8)), primary } };
    });
    const edges: Edge[] = graph.data.relationships.map((item) => ({ id: item.id, source: item.source_topic_id, target: item.target_topic_id, label: formatName(item.relationship_type), style: { strokeWidth: 1 + item.strength * 2, stroke: "#4d8dff" }, labelStyle: { fill: "#8290a3", fontSize: 10 }, markerEnd: { type: MarkerType.ArrowClosed, color: "#4d8dff" } }));
    return { nodes, edges };
  }, [graph.data, names]);

  if (topics.isLoading) return <LoadingState rows={7} />;
  if (topics.isError) return <ErrorState error={topics.error} retry={() => void topics.refetch()} />;
  return <><PageHeader eyebrow="Relationship intelligence" title="Knowledge Graph" description="Explore persisted relationships between topics. New connector-derived relationships appear through the same graph contract." actions={<select className="input min-w-56" value={topicId ?? ""} onChange={(event) => setSelected(event.target.value)}>{(topics.data ?? []).map((item) => <option value={item.id} key={item.id}>{item.display_name}</option>)}</select>} />{!topicId ? <section className="panel"><EmptyState title="No topics available" /></section> : graph.isLoading ? <LoadingState rows={7} /> : graph.isError ? <ErrorState error={graph.error} retry={() => void graph.refetch()} /> : <section className="panel overflow-hidden"><div className="flex items-center justify-between border-b border-line px-5 py-4"><div className="flex items-center gap-2"><Network className="h-4 w-4 text-accent" /><h2 className="section-title">{graph.data?.topic_name}</h2></div><StatusPill status={elements.edges.length ? "good" : "neutral"} label={`${elements.edges.length} relationships`} /></div><div className="h-[620px] bg-canvas/40">{elements.nodes.length ? <ReactFlow<TopicNode, Edge> nodes={elements.nodes} edges={elements.edges} nodeTypes={nodeTypes} fitView minZoom={.35} maxZoom={1.8} nodesDraggable nodesConnectable={false} elementsSelectable><Background color="#202a38" gap={22} /><Controls showInteractive={false} /></ReactFlow> : <EmptyState title="No graph nodes" />}</div></section>}</>;
}

function TopicNodeCard({ data }: NodeProps<TopicNode>) {
  return <div className={`min-w-36 rounded-xl border px-4 py-3 shadow-xl ${data.primary ? "border-accent bg-accent text-white" : "border-line bg-surface text-ink"}`}><Handle type="target" position={Position.Top} className="opacity-0" /><span className={`block text-[9px] font-bold uppercase tracking-wider ${data.primary ? "text-white/70" : "text-muted"}`}>{data.primary ? "Active topic" : "Related topic"}</span><strong className="mt-1 block max-w-44 text-xs">{data.label}</strong><Handle type="source" position={Position.Bottom} className="opacity-0" /></div>;
}
