import { Brain, ChevronRight } from "lucide-react";
import type { AgentResponse, ServiceType } from "@/types/agent";

const SERVICE_LABELS: Record<ServiceType, { label: string; color: string }> = {
  safety_alert: { label: "안전 경보", color: "text-red-300 bg-red-950/40 border-red-800" },
  device_control: { label: "기기 제어", color: "text-blue-300 bg-blue-950/40 border-blue-800" },
  navigation: { label: "길 안내", color: "text-emerald-300 bg-emerald-950/40 border-emerald-800" },
  context_memory: { label: "맥락 기억", color: "text-amber-300 bg-amber-950/40 border-amber-800" },
  scene_assistant: { label: "장면 인식", color: "text-violet-300 bg-violet-950/40 border-violet-800" },
  label_reader: { label: "라벨 인식", color: "text-teal-300 bg-teal-950/40 border-teal-800" },
  unknown: { label: "미분류", color: "text-gray-300 bg-gray-900/40 border-gray-700" },
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
          <p className="mt-3 text-sm text-[var(--text-dim)]">Run the agent to see routing and latency evidence.</p>
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
            <span className="panel-label">Decision Trace</span>
          </div>
          <h2 className="display-face text-xl font-bold uppercase text-white">Pipeline Route</h2>
        </div>
        <div className="rounded-full border border-[var(--line)] bg-[rgba(255,255,255,0.04)] px-3 py-1.5 text-[11px] uppercase tracking-[0.16em] text-[var(--text-faint)]">
          req {response.request_id.slice(0, 8)}
        </div>
      </div>

      <div className="mb-4 rounded-[20px] border border-[var(--line)] bg-[rgba(255,255,255,0.04)] p-4">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <span className={`inline-flex rounded-full border px-2.5 py-1 text-xs font-medium ${svc.color}`}>{svc.label}</span>
            <p className="display-face mt-3 text-2xl font-bold uppercase text-white">{confidencePct}% confidence</p>
            <p className="mt-2 text-sm leading-6 text-[var(--text-dim)]">
              {response.mode} path, {response.vlm_used ? "cloud model engaged" : "local path only"}.
            </p>
          </div>

          <div className="grid grid-cols-3 gap-2 sm:w-[17rem]">
            <StatBox label="Input" value={response.original_frame_count} />
            <StatBox label="Pick" value={response.selected_keyframe_count} highlight />
            <StatBox label="Graph" value={response.retrieved_graph_nodes} />
          </div>
        </div>
      </div>

      <div className="mb-4 grid gap-2 sm:grid-cols-5">
        {["Perceive", "Graph", "Route", "Service", "Log"].map((step, i, arr) => (
          <div key={step} className="relative rounded-[16px] border border-[var(--line)] bg-[rgba(255,255,255,0.03)] px-3 py-3">
            <p className={`display-face text-sm font-bold uppercase ${i === 2 ? "text-[var(--signal)]" : "text-white"}`}>{step}</p>
            {i < arr.length - 1 && (
              <ChevronRight className="absolute -right-2 top-1/2 hidden h-4 w-4 -translate-y-1/2 text-[var(--text-faint)] sm:block" />
            )}
          </div>
        ))}
      </div>

      <div className="rounded-[20px] border border-[var(--line)] bg-[rgba(255,255,255,0.03)] p-4">
        <p className="panel-label mb-3">Latency Breakdown</p>
        <div className="space-y-2">
          <LatencyBar label="Frame" ms={response.latency_ms.frame_sampling} total={response.latency_ms.total} color="bg-indigo-500" />
          {response.mode === "optimized" && (
            <LatencyBar
              label="Keyframe"
              ms={response.latency_ms.keyframe_selection}
              total={response.latency_ms.total}
              color="bg-cyan-500"
            />
          )}
          <LatencyBar label="Graph" ms={response.latency_ms.graph_retrieval} total={response.latency_ms.total} color="bg-emerald-500" />
          <LatencyBar label="Router" ms={response.latency_ms.routing} total={response.latency_ms.total} color="bg-[var(--signal)]" />
          <LatencyBar label="VLM" ms={response.latency_ms.vlm} total={response.latency_ms.total} color="bg-orange-500" />
        </div>
        <p className="mt-3 text-right text-xs font-mono text-[var(--text-dim)]">Total: {response.latency_ms.total}ms</p>
      </div>
    </div>
  );
}

function StatBox({ label, value, highlight }: { label: string; value: number; highlight?: boolean }) {
  return (
    <div className="rounded-[16px] border border-[var(--line)] bg-[rgba(3,9,14,0.52)] p-3 text-center">
      <p className={`display-face text-xl font-bold leading-none ${highlight ? "text-[var(--signal)]" : "text-white"}`}>{value}</p>
      <p className="mt-2 text-[10px] uppercase tracking-[0.14em] text-[var(--text-faint)]">{label}</p>
    </div>
  );
}

function LatencyBar({ label, ms, total, color }: { label: string; ms: number; total: number; color: string }) {
  const pct = total > 0 ? Math.round((ms / total) * 100) : 0;
  return (
    <div className="flex items-center gap-2">
      <span className="w-16 shrink-0 text-[11px] text-[var(--text-faint)]">{label}</span>
      <div className="h-2 flex-1 rounded-full bg-[rgba(255,255,255,0.06)]">
        <div className={`${color} h-2 rounded-full transition-all`} style={{ width: `${pct}%` }} />
      </div>
      <span className="w-14 text-right text-xs font-mono text-[var(--text-dim)]">{ms}ms</span>
    </div>
  );
}
