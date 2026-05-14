import { Brain, ChevronRight } from "lucide-react";
import type { AgentResponse, ServiceType } from "@/types/agent";

const SERVICE_LABELS: Record<ServiceType, { label: string; color: string }> = {
  safety_alert: { label: "Safety Alert", color: "text-red-400 bg-red-900/30 border-red-700" },
  device_control: { label: "Device Control", color: "text-blue-400 bg-blue-900/30 border-blue-700" },
  navigation: { label: "Navigation", color: "text-emerald-400 bg-emerald-900/30 border-emerald-700" },
  context_memory: { label: "Context Memory", color: "text-amber-400 bg-amber-900/30 border-amber-700" },
  scene_assistant: { label: "Scene Assistant", color: "text-purple-400 bg-purple-900/30 border-purple-700" },
  unknown: { label: "Unknown", color: "text-gray-400 bg-gray-800 border-gray-600" },
};

interface Props {
  response: AgentResponse | null;
}

export default function AgentDecisionPanel({ response }: Props) {
  if (!response) {
    return (
      <div className="bg-gray-900 rounded-xl p-5 border border-gray-700 flex items-center justify-center h-32">
        <p className="text-gray-500 text-sm">Run the agent to inspect the pipeline decision.</p>
      </div>
    );
  }

  const svc = SERVICE_LABELS[response.selected_service] ?? SERVICE_LABELS.unknown;
  const confidencePct = Math.round(response.router_confidence * 100);

  return (
    <div className="bg-gray-900 rounded-xl p-5 border border-gray-700 space-y-4">
      <div className="flex items-center gap-2">
        <Brain className="w-4 h-4 text-purple-400" />
        <h2 className="text-sm font-semibold text-gray-300 uppercase tracking-wide">Agent Decision</h2>
      </div>

      <div className="flex items-center gap-1.5 text-xs text-gray-500 flex-wrap">
        {["Perception", "GraphRAG", "Router", "Service", "Log"].map((step, i, arr) => (
          <span key={step} className="flex items-center gap-1">
            <span className={i === 2 ? "text-purple-400 font-medium" : ""}>{step}</span>
            {i < arr.length - 1 && <ChevronRight className="w-3 h-3" />}
          </span>
        ))}
      </div>

      <div className="flex items-center gap-3">
        <span className={`text-xs px-2.5 py-1 rounded-full border font-medium ${svc.color}`}>
          {svc.label}
        </span>
        <span className="text-xs text-gray-400">
          Confidence <span className="text-white font-mono">{confidencePct}%</span>
        </span>
        {response.vlm_used && (
          <span className="text-xs px-2 py-0.5 rounded-full bg-orange-900/40 border border-orange-700 text-orange-400">
            VLM used
          </span>
        )}
      </div>

      <div className="grid grid-cols-3 gap-3">
        <StatBox label="Input Frames" value={response.original_frame_count} />
        <StatBox label="Keyframes" value={response.selected_keyframe_count} highlight />
        <StatBox label="Graph Nodes" value={response.retrieved_graph_nodes} />
      </div>

      <div className="space-y-1.5">
        <p className="text-xs text-gray-500">Latency Breakdown</p>
        <LatencyBar label="Frame" ms={response.latency_ms.frame_sampling} total={response.latency_ms.total} color="bg-indigo-500" />
        {response.mode === "optimized" && (
          <LatencyBar label="Keyframe" ms={response.latency_ms.keyframe_selection} total={response.latency_ms.total} color="bg-cyan-500" />
        )}
        <LatencyBar label="Graph" ms={response.latency_ms.graph_retrieval} total={response.latency_ms.total} color="bg-emerald-500" />
        <LatencyBar label="Router" ms={response.latency_ms.routing} total={response.latency_ms.total} color="bg-purple-500" />
        <LatencyBar label="VLM" ms={response.latency_ms.vlm} total={response.latency_ms.total} color="bg-orange-500" />
        <p className="text-right text-xs text-gray-400 font-mono">Total: {response.latency_ms.total}ms</p>
      </div>
    </div>
  );
}

function StatBox({ label, value, highlight }: { label: string; value: number; highlight?: boolean }) {
  return (
    <div className="bg-gray-800 rounded-lg p-3 text-center">
      <p className={`text-lg font-mono font-bold ${highlight ? "text-purple-300" : "text-gray-200"}`}>{value}</p>
      <p className="text-xs text-gray-500">{label}</p>
    </div>
  );
}

function LatencyBar({ label, ms, total, color }: { label: string; ms: number; total: number; color: string }) {
  const pct = total > 0 ? Math.round((ms / total) * 100) : 0;
  return (
    <div className="flex items-center gap-2">
      <span className="text-xs text-gray-500 w-12">{label}</span>
      <div className="flex-1 bg-gray-800 rounded-full h-1.5">
        <div className={`${color} h-1.5 rounded-full transition-all`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs text-gray-400 font-mono w-14 text-right">{ms}ms</span>
    </div>
  );
}
