import { Network, RefreshCw, Search } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { getGraphNodes, queryGraph } from "@/api/agentApi";
import type { GraphNode } from "@/types/agent";

const NODE_COLORS: Record<string, string> = {
  Scene: "bg-purple-900/40 border-purple-600 text-purple-300",
  Location: "bg-emerald-900/40 border-emerald-600 text-emerald-300",
  Device: "bg-blue-900/40 border-blue-600 text-blue-300",
  UserIntent: "bg-amber-900/40 border-amber-600 text-amber-300",
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

  useEffect(() => { void refresh(); }, [refresh]);

  async function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    if (!query.trim()) { setResults(null); return; }
    const data = await queryGraph(query);
    setResults(data.results);
  }

  const displayNodes = results ?? nodes.slice(0, 20);

  return (
    <div className="bg-gray-900 rounded-xl p-5 border border-gray-700 space-y-4">
      <div className="flex items-center gap-2">
        <Network className="w-4 h-4 text-purple-400" />
        <h2 className="text-sm font-semibold text-gray-300 uppercase tracking-wide">GraphRAG Context</h2>
        <span className="ml-auto text-xs text-gray-500 font-mono">{nodes.length} nodes</span>
        <button onClick={() => void refresh()} className="text-gray-500 hover:text-gray-300">
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
        </button>
      </div>

      <form onSubmit={(e) => void handleSearch(e)} className="flex gap-2">
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="키워드 검색 (예: 카페, 조명)"
          className="flex-1 bg-gray-800 border border-gray-600 rounded-lg px-3 py-1.5 text-xs text-gray-100 placeholder-gray-500 focus:outline-none focus:border-purple-500"
        />
        <button type="submit" className="px-3 py-1.5 rounded-lg bg-gray-700 hover:bg-gray-600 text-gray-300 transition-colors">
          <Search className="w-3.5 h-3.5" />
        </button>
        {results && (
          <button type="button" onClick={() => setResults(null)} className="text-xs text-gray-500 hover:text-gray-300 px-2">
            전체
          </button>
        )}
      </form>

      {displayNodes.length === 0 ? (
        <p className="text-gray-500 text-xs">그래프에 노드가 없습니다. Agent를 실행하면 scene이 저장됩니다.</p>
      ) : (
        <div className="space-y-1.5 max-h-64 overflow-y-auto">
          {displayNodes.map((node) => {
            const colorClass = NODE_COLORS[node.type as string] ?? "bg-gray-800 border-gray-600 text-gray-300";
            return (
              <div key={node.id} className={`flex items-start gap-2 p-2 rounded-lg border text-xs ${colorClass}`}>
                <span className="font-medium shrink-0">[{node.type as string}]</span>
                <span className="text-gray-300 truncate">
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
