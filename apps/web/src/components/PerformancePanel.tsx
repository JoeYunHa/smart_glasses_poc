import { BarChart3, RefreshCw } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { getMetrics } from "@/api/agentApi";
import type { MetricsData } from "@/types/agent";

export default function PerformancePanel() {
  const [metrics, setMetrics] = useState<MetricsData | null>(null);
  const [loading, setLoading] = useState(false);

  const fetch = useCallback(async () => {
    setLoading(true);
    try {
      const data = await getMetrics();
      setMetrics(data);
    } catch {
      // silent
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void fetch();
  }, [fetch]);

  const modes = metrics ? Object.entries(metrics.by_mode) : [];

  return (
    <div className="telemetry-card reveal-up rounded-[24px] p-5 sm:p-6">
      <div className="mb-5 flex items-center gap-2">
        <BarChart3 className="h-4 w-4 text-[var(--amber)]" />
        <div>
          <p className="panel-label">Optimization Evidence</p>
          <h2 className="display-face text-2xl font-bold uppercase text-white">Performance Metrics</h2>
        </div>
        <button
          onClick={() => void fetch()}
          className="ml-auto rounded-full border border-[var(--line)] bg-[rgba(255,255,255,0.04)] p-2 text-[var(--text-faint)] transition-colors hover:text-white"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
        </button>
      </div>

      {!metrics || metrics.total === 0 ? (
        <p className="text-sm text-[var(--text-dim)]">No evaluation runs logged yet.</p>
      ) : (
        <>
          <div className="mb-4 rounded-[18px] border border-[var(--line)] bg-[rgba(255,255,255,0.04)] px-4 py-3">
            <p className="panel-label">Observed Samples</p>
            <p className="display-face mt-2 text-3xl font-bold text-white">{metrics.total}</p>
          </div>

          <div className="grid grid-cols-1 gap-3">
            {modes.map(([mode, m]) => (
              <div key={mode} className="rounded-[20px] border border-[var(--line)] bg-[rgba(255,255,255,0.04)] p-4">
                <p className={`display-face text-lg font-bold uppercase ${mode === "optimized" ? "text-[var(--signal)]" : "text-[var(--text-dim)]"}`}>
                  {mode.toUpperCase()} ({m.count})
                </p>
                <div className="mt-3 grid grid-cols-2 gap-3 text-xs">
                  <Metric label="Average latency" value={`${m.avg_latency_ms}ms`} />
                  <Metric label="VLM calls / req" value={m.avg_vlm_calls.toFixed(2)} />
                  <Metric label="Frame reduction" value={`${(m.avg_frame_reduction_ratio * 100).toFixed(0)}%`} highlight />
                  <Metric label="Graph nodes / req" value={m.avg_graph_nodes.toFixed(1)} />
                </div>
                {Object.entries(m.service_distribution).length > 0 && (
                  <div className="flex flex-wrap gap-1 pt-3">
                    {Object.entries(m.service_distribution).map(([svc, cnt]) => (
                      <span key={svc} className="rounded-full border border-[var(--line)] bg-[rgba(255,255,255,0.04)] px-2 py-1 text-[11px] uppercase tracking-[0.12em] text-[var(--text-dim)]">
                        {svc.replace("_", " ")}: {cnt}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>

          {modes.length === 2 && (
            <ComparisonBar
              baseline={modes.find(([m]) => m === "baseline")?.[1]?.avg_latency_ms ?? 0}
              optimized={modes.find(([m]) => m === "optimized")?.[1]?.avg_latency_ms ?? 0}
            />
          )}
        </>
      )}
    </div>
  );
}

function Metric({ label, value, highlight }: { label: string; value: string; highlight?: boolean }) {
  return (
    <div className="rounded-[16px] border border-[var(--line)] bg-[rgba(3,9,14,0.52)] p-3">
      <p className="text-[11px] uppercase tracking-[0.12em] text-[var(--text-faint)]">{label}</p>
      <p className={`mt-2 font-mono text-base ${highlight ? "text-[var(--signal)]" : "text-white"}`}>{value}</p>
    </div>
  );
}

function ComparisonBar({ baseline, optimized }: { baseline: number; optimized: number }) {
  if (!baseline || !optimized) return null;
  const saved = Math.round(((baseline - optimized) / baseline) * 100);
  return (
    <div className="mt-4 rounded-[20px] border border-[var(--line)] bg-[rgba(255,255,255,0.04)] p-4">
      <p className="panel-label mb-2">Latency Delta</p>
      <p className="display-face text-xl font-bold uppercase text-white">Baseline vs Optimized</p>
      <div className="mt-3 space-y-2">
        <BarRow label="Baseline" ms={baseline} max={Math.max(baseline, optimized)} color="bg-gray-500" />
        <BarRow label="Optimized" ms={optimized} max={Math.max(baseline, optimized)} color="bg-purple-500" />
      </div>
      {saved > 0 && (
        <p className="mt-3 text-sm font-medium text-[var(--signal)]">
          Optimized is {saved}% faster
        </p>
      )}
    </div>
  );
}

function BarRow({ label, ms, max, color }: { label: string; ms: number; max: number; color: string }) {
  const pct = max > 0 ? (ms / max) * 100 : 0;
  return (
    <div className="flex items-center gap-2">
      <span className="w-20 text-[11px] uppercase tracking-[0.12em] text-[var(--text-faint)]">{label}</span>
      <div className="h-2 flex-1 rounded-full bg-[rgba(255,255,255,0.06)]">
        <div className={`${color} h-2 rounded-full`} style={{ width: `${pct}%` }} />
      </div>
      <span className="w-16 text-right text-xs font-mono text-[var(--text-dim)]">{ms}ms</span>
    </div>
  );
}
