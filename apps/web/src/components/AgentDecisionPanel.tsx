import { Brain, ChevronRight } from "lucide-react";
import type { AgentResponse, ServiceType } from "@/types/agent";

const SERVICE_LABELS: Record<ServiceType, { label: string; color: string }> = {
  safety_alert: { label: "Safety Alert", color: "text-red-400 bg-red-900/30 border-red-700" },
  device_control: { label: "Device Control", color: "text-blue-400 bg-blue-900/30 border-blue-700" },
  navigation: { label: "Navigation", color: "text-emerald-400 bg-emerald-900/30 border-emerald-700" },
  context_memory: { label: "Context Memory", color: "text-amber-400 bg-amber-900/30 border-amber-700" },
  scene_assistant: { label: "Scene Assistant", color: "text-purple-400 bg-purple-900/30 border-purple-700" },
  label_reader: { label: "Label Reader", color: "text-teal-400 bg-teal-900/30 border-teal-700" },
  unknown: { label: "Unknown", color: "text-gray-400 bg-gray-800 border-gray-600" },
};

interface Props {
  response: AgentResponse | null;
}

export default function AgentDecisionPanel({ response }: Props) {
  if (!response) {
    return (
      <div className="telemetry-card reveal-up flex h-40 items-center justify-center rounded-[24px] p-6">
        <div className="text-center">
          <p className="panel-label">Decision Trace</p>
          <p className="mt-3 text-sm text-[var(--text-dim)]">Run the agent to inspect the pipeline decision.</p>
        </div>
      </div>
    );
  }

  const svc = SERVICE_LABELS[response.selected_service] ?? SERVICE_LABELS.unknown;
  const confidencePct = Math.round(response.router_confidence * 100);

  return (
    <div className="telemetry-card reveal-up rounded-[24px] p-5 sm:p-6">
      <div className="mb-5 flex items-start justify-between gap-4">
        <div>
          <div className="mb-2 flex items-center gap-2">
            <Brain className="h-4 w-4 text-[var(--signal)]" />
            <span className="panel-label">Agent Decision</span>
          </div>
          <h2 className="display-face text-2xl font-bold uppercase text-white">Optimization Route</h2>
          <p className="mt-1 text-sm text-[var(--text-dim)]">
            Show the audience exactly where the request was compressed, enriched, routed, and answered.
          </p>
        </div>
        <div className="rounded-full border border-[var(--line)] bg-[rgba(255,255,255,0.04)] px-3 py-1.5 text-[11px] uppercase tracking-[0.16em] text-[var(--text-faint)]">
          req {response.request_id.slice(0, 8)}
        </div>
      </div>

      <div className="mb-5 rounded-[20px] border border-[var(--line)] bg-[rgba(255,255,255,0.04)] p-4">
        <p className="eyebrow">Selected Path</p>
        <div className="mt-2 flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="display-face text-3xl font-bold uppercase text-white">{svc.label}</p>
            <p className="mt-2 text-sm leading-6 text-[var(--text-dim)]">
              Router confidence is {confidencePct}%. This run used the {response.mode} path and
              {response.vlm_used ? " reached a cloud model." : " remained local."}
            </p>
          </div>
          <div className="grid grid-cols-2 gap-2 sm:w-[15rem]">
            <MiniStat label="Input" value={response.original_frame_count} />
            <MiniStat label="Kept" value={response.selected_keyframe_count} />
          </div>
        </div>
      </div>

      <div className="mb-5 grid gap-2 sm:grid-cols-5">
        {["Perception", "GraphRAG", "Router", "Service", "Log"].map((step, i, arr) => (
          <div key={step} className="relative rounded-[18px] border border-[var(--line)] bg-[rgba(255,255,255,0.03)] px-3 py-3">
            <p className={`display-face text-base font-bold uppercase ${i === 2 ? "text-[var(--signal)]" : "text-white"}`}>{step}</p>
            {i < arr.length - 1 && <ChevronRight className="absolute -right-2 top-1/2 hidden h-4 w-4 -translate-y-1/2 text-[var(--text-faint)] sm:block" />}
          </div>
        ))}
      </div>

      <div className="mb-5 flex flex-wrap items-center gap-3">
        <span className={`text-xs px-2.5 py-1 rounded-full border font-medium ${svc.color}`}>
          {svc.label}
        </span>
        <span className="rounded-full border border-[var(--line)] bg-[rgba(255,255,255,0.04)] px-3 py-1.5 text-xs text-[var(--text-dim)]">
          Confidence <span className="ml-1 font-mono text-white">{confidencePct}%</span>
        </span>
        {response.vlm_used && (
          <span className="rounded-full border border-[rgba(255,140,105,0.32)] bg-[rgba(255,140,105,0.14)] px-3 py-1.5 text-xs text-[var(--alert)]">
            VLM used
          </span>
        )}
      </div>

      <div className="mb-5 grid grid-cols-3 gap-3">
        <StatBox label="Input Frames" value={response.original_frame_count} />
        <StatBox label="Keyframes" value={response.selected_keyframe_count} highlight />
        <StatBox label="Graph Nodes" value={response.retrieved_graph_nodes} />
      </div>

      <div className="rounded-[20px] border border-[var(--line)] bg-[rgba(255,255,255,0.03)] p-4">
        <p className="panel-label mb-3">Latency Breakdown</p>
        <div className="space-y-2">
        <LatencyBar label="Frame" ms={response.latency_ms.frame_sampling} total={response.latency_ms.total} color="bg-indigo-500" />
        {response.mode === "optimized" && (
          <LatencyBar label="Keyframe" ms={response.latency_ms.keyframe_selection} total={response.latency_ms.total} color="bg-cyan-500" />
        )}
        <LatencyBar label="Graph" ms={response.latency_ms.graph_retrieval} total={response.latency_ms.total} color="bg-emerald-500" />
        <LatencyBar label="Router" ms={response.latency_ms.routing} total={response.latency_ms.total} color="bg-purple-500" />
        <LatencyBar label="VLM" ms={response.latency_ms.vlm} total={response.latency_ms.total} color="bg-orange-500" />
        </div>
        <p className="mt-3 text-right text-xs font-mono text-[var(--text-dim)]">Total: {response.latency_ms.total}ms</p>
      </div>
    </div>
  );
}

function StatBox({ label, value, highlight }: { label: string; value: number; highlight?: boolean }) {
  return (
    <div className="rounded-[18px] border border-[var(--line)] bg-[rgba(255,255,255,0.04)] p-3 text-center">
      <p className={`display-face text-3xl font-bold leading-none ${highlight ? "text-[var(--signal)]" : "text-white"}`}>{value}</p>
      <p className="mt-2 text-[11px] uppercase tracking-[0.14em] text-[var(--text-faint)]">{label}</p>
    </div>
  );
}

function MiniStat({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-[16px] border border-[var(--line)] bg-[rgba(3,9,14,0.52)] p-3">
      <p className="eyebrow">{label}</p>
      <p className="mt-2 font-mono text-lg text-white">{value}</p>
    </div>
  );
}

function LatencyBar({ label, ms, total, color }: { label: string; ms: number; total: number; color: string }) {
  const pct = total > 0 ? Math.round((ms / total) * 100) : 0;
  return (
    <div className="flex items-center gap-2">
      <span className="w-14 text-[11px] uppercase tracking-[0.12em] text-[var(--text-faint)]">{label}</span>
      <div className="h-2 flex-1 rounded-full bg-[rgba(255,255,255,0.06)]">
        <div className={`${color} h-1.5 rounded-full transition-all`} style={{ width: `${pct}%` }} />
      </div>
      <span className="w-14 text-right text-xs font-mono text-[var(--text-dim)]">{ms}ms</span>
    </div>
  );
}
