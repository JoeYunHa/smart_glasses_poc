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
    <div className="bg-gray-900 rounded-xl p-5 border border-gray-700 space-y-4">
      <div className="flex items-center gap-2">
        <BarChart3 className="w-4 h-4 text-purple-400" />
        <h2 className="text-sm font-semibold text-gray-300 uppercase tracking-wide">Performance Metrics</h2>
        <button
          onClick={() => void fetch()}
          className="ml-auto text-gray-500 hover:text-gray-300 transition-colors"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
        </button>
      </div>

      {!metrics || metrics.total === 0 ? (
        <p className="text-gray-500 text-xs">No evaluation runs logged yet.</p>
      ) : (
        <>
          <p className="text-xs text-gray-500">Total requests: <span className="text-white font-mono">{metrics.total}</span></p>

          <div className="grid grid-cols-1 gap-3">
            {modes.map(([mode, m]) => (
              <div key={mode} className="bg-gray-800 rounded-lg p-3 space-y-2">
                <p className={`text-xs font-semibold ${mode === "optimized" ? "text-purple-400" : "text-gray-400"}`}>
                  {mode.toUpperCase()} ({m.count})
                </p>
                <div className="grid grid-cols-2 gap-2 text-xs">
                  <Metric label="Average latency" value={`${m.avg_latency_ms}ms`} />
                  <Metric label="VLM calls / req" value={m.avg_vlm_calls.toFixed(2)} />
                  <Metric label="Frame reduction" value={`${(m.avg_frame_reduction_ratio * 100).toFixed(0)}%`} highlight />
                  <Metric label="Graph nodes / req" value={m.avg_graph_nodes.toFixed(1)} />
                </div>
                {Object.entries(m.service_distribution).length > 0 && (
                  <div className="flex flex-wrap gap-1 pt-1">
                    {Object.entries(m.service_distribution).map(([svc, cnt]) => (
                      <span key={svc} className="text-xs px-2 py-0.5 bg-gray-700 rounded-full text-gray-300">
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
    <div>
      <p className="text-gray-500">{label}</p>
      <p className={`font-mono ${highlight ? "text-purple-300" : "text-gray-200"}`}>{value}</p>
    </div>
  );
}

function ComparisonBar({ baseline, optimized }: { baseline: number; optimized: number }) {
  if (!baseline || !optimized) return null;
  const saved = Math.round(((baseline - optimized) / baseline) * 100);
  return (
    <div className="bg-gray-800 rounded-lg p-3">
      <p className="text-xs text-gray-400 mb-2">Baseline vs Optimized latency</p>
      <div className="space-y-1.5">
        <BarRow label="Baseline" ms={baseline} max={Math.max(baseline, optimized)} color="bg-gray-500" />
        <BarRow label="Optimized" ms={optimized} max={Math.max(baseline, optimized)} color="bg-purple-500" />
      </div>
      {saved > 0 && (
        <p className="text-xs text-emerald-400 mt-2 font-medium">
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
      <span className="text-xs text-gray-500 w-20">{label}</span>
      <div className="flex-1 bg-gray-700 rounded-full h-2">
        <div className={`${color} h-2 rounded-full`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs font-mono text-gray-300 w-16 text-right">{ms}ms</span>
    </div>
  );
}
