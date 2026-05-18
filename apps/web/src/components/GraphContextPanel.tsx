import { Network, RefreshCw, Search } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { getGraphNodes, queryGraph } from "@/api/agentApi";
import type { GraphNode } from "@/types/agent";

const NODE_COLORS: Record<string, string> = {
  Scene: "bg-violet-950/40 border-violet-800 text-violet-200",
  Location: "bg-emerald-950/40 border-emerald-800 text-emerald-200",
  Device: "bg-blue-950/40 border-blue-800 text-blue-200",
  UserIntent: "bg-amber-950/40 border-amber-800 text-amber-200",
};

export default function GraphContextPanel() {
  const [nodes, setNodes] = useState<GraphNode[]>([]);
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<GraphNode[] | null>(null);
  const [loading, setLoading] = useState(false);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const data = await getGraphNodes();
      setNodes(data.nodes);
    } catch {
      // silent
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  async function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    if (!query.trim()) {
      setResults(null);
      return;
    }
    const data = await queryGraph(query);
    setResults(data.results);
  }

  const displayNodes = results ?? nodes.slice(0, 10);
  const nodeBuckets = nodes.reduce<Record<string, number>>((acc, node) => {
    const key = String(node.type ?? "Other");
    acc[key] = (acc[key] ?? 0) + 1;
    return acc;
  }, {});

  return (
    <div className="rounded-[20px] border border-[var(--line)] bg-[rgba(255,255,255,0.03)] p-4">
      <div className="mb-5 flex items-center gap-2">
        <Network className="h-4 w-4 text-[var(--accent)]" />
        <div>
          <p className="panel-label">Structured Memory</p>
          <h2 className="display-face text-lg font-bold uppercase text-white">GraphRAG Context</h2>
        </div>
        <span className="ml-auto rounded-full border border-[var(--line)] bg-[rgba(255,255,255,0.04)] px-3 py-1.5 text-[11px] text-[var(--text-faint)]">
          {nodes.length} nodes
        </span>
        <button
          onClick={() => void refresh()}
          className="rounded-full border border-[var(--line)] bg-[rgba(255,255,255,0.04)] p-2 text-[var(--text-faint)] hover:text-white"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
        </button>
      </div>

      <div className="mb-4 grid gap-3 lg:grid-cols-[1.15fr_0.85fr]">
        <form onSubmit={(e) => void handleSearch(e)} className="flex gap-2">
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search memory, e.g. cafe or light"
            className="flex-1 rounded-[16px] border border-[var(--line)] bg-[rgba(3,9,14,0.58)] px-4 py-3 text-sm text-white placeholder:text-[var(--text-faint)] focus:border-[var(--accent)] focus:outline-none"
          />
          <button
            type="submit"
            className="rounded-[16px] border border-[var(--line)] bg-[rgba(255,255,255,0.04)] px-3 py-1.5 text-[var(--text-dim)] transition-colors hover:text-white"
          >
            <Search className="h-3.5 w-3.5" />
          </button>
        </form>

        <div className="rounded-[16px] border border-[var(--line)] bg-[rgba(255,255,255,0.04)] px-4 py-3">
          <p className="eyebrow">Snapshot</p>
          <div className="mt-2 flex flex-wrap gap-2">
            {Object.entries(nodeBuckets)
              .slice(0, 4)
              .map(([type, count]) => (
                <span
                  key={type}
                  className="rounded-full border border-[var(--line)] bg-[rgba(3,9,14,0.58)] px-2.5 py-1 text-[11px] uppercase tracking-[0.12em] text-[var(--text-dim)]"
                >
                  {type}: {count}
                </span>
              ))}
            {Object.keys(nodeBuckets).length === 0 && <span className="text-sm text-[var(--text-dim)]">No memory yet.</span>}
          </div>
        </div>
      </div>

      {displayNodes.length === 0 ? (
        <p className="text-sm text-[var(--text-dim)]">Run the agent to populate scene memory.</p>
      ) : (
        <div className="soft-scroll space-y-2 max-h-[24rem] overflow-y-auto">
          {displayNodes.map((node) => {
            const colorClass = NODE_COLORS[node.type as string] ?? "bg-gray-900/40 border-gray-700 text-gray-200";
            return (
              <div key={node.id} className={`rounded-[16px] border p-3 text-xs ${colorClass}`}>
                <div className="mb-2 flex items-center justify-between gap-3">
                  <span className="display-face text-sm font-bold uppercase tracking-[0.08em]">[{node.type as string}]</span>
                  <span className="font-mono text-[10px] text-white/55">{String(node.id).slice(0, 16)}</span>
                </div>
                <span className="block leading-6 text-white/88">
                  {(node.user_request as string | undefined) ??
                    (node.place_name as string | undefined) ??
                    (node.name as string | undefined) ??
                    (node.text as string | undefined) ??
                    node.id}
                </span>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
