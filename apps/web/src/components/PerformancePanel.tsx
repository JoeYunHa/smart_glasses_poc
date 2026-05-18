import { BarChart3, RefreshCw } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { getMetrics } from "@/api/agentApi";
import type { MetricsData } from "@/types/agent";

function fmtBytes(bytes: number): string {
  if (bytes === 0) return "0 B";
  if (bytes < 1024) return `${bytes} B`;
  return `${(bytes / 1024).toFixed(1)} KB`;
}

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
          <h2 className="display-face text-2xl font-bold uppercase text-white">Performance Evidence Board</h2>
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
          <div className="mb-4 grid gap-3 md:grid-cols-[1.2fr_0.8fr]">
            <div className="rounded-[18px] border border-[var(--line)] bg-[rgba(255,255,255,0.04)] px-4 py-4">
              <p className="eyebrow">Presentation Goal</p>
              <p className="mt-2 text-sm leading-6 text-[var(--text-dim)]">
                Use this board to prove that optimized runs reduce cloud transfer and preserve responsiveness
                under the same scenario family.
              </p>
            </div>
            <div className="rounded-[18px] border border-[rgba(125,249,208,0.24)] bg-[rgba(125,249,208,0.06)] px-4 py-4">
              <p className="eyebrow">Observed Samples</p>
              <p className="display-face mt-2 text-3xl font-bold text-white">{metrics.total}</p>
            </div>
          </div>

          <div className="grid grid-cols-1 gap-3">
            {modes.map(([mode, m]) => (
              <div key={mode} className="rounded-[20px] border border-[var(--line)] bg-[rgba(255,255,255,0.04)] p-4">
                <p className={`display-face text-lg font-bold uppercase ${mode === "optimized" ? "text-[var(--signal)]" : "text-[var(--text-dim)]"}`}>
                  {mode.toUpperCase()} ({m.count})
                </p>
                <div className="mt-3 grid grid-cols-2 gap-3 text-xs">
                  <Metric label="Avg latency" value={`${m.avg_latency_ms}ms`} />
                  <Metric label="VLM calls / req" value={m.avg_vlm_calls.toFixed(2)} />
                  <Metric label="Frame reduction" value={`${(m.avg_frame_reduction_ratio * 100).toFixed(0)}%`} highlight />
                  <Metric label="Graph nodes / req" value={m.avg_graph_nodes.toFixed(1)} />
                  <Metric label="Avg tokens" value={m.avg_tokens.toLocaleString()} />
                  <Metric label="Cloud payload" value={fmtBytes(m.avg_image_payload_bytes)} highlight />
                  <Metric label="Cloud call ratio" value={`${(m.cloud_call_ratio * 100).toFixed(0)}%`} />
                  <Metric label="Fallback rate" value={`${(((m.fallback_distribution.low_confidence ?? 0) + (m.fallback_distribution.parse_error ?? 0)) / Math.max(m.count, 1) * 100).toFixed(0)}%`} />
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
            <>
              <ComparisonBar
                title="Latency Delta"
                label="Baseline vs Optimized"
                baseline={modes.find(([m]) => m === "baseline")?.[1]?.avg_latency_ms ?? 0}
                optimized={modes.find(([m]) => m === "optimized")?.[1]?.avg_latency_ms ?? 0}
                fmt={(v) => `${v}ms`}
                savingLabel="faster"
              />
              <ComparisonBar
                title="Cloud Payload Delta"
                label="Semantic vs Vision path"
                baseline={modes.find(([m]) => m === "baseline")?.[1]?.avg_image_payload_bytes ?? 0}
                optimized={modes.find(([m]) => m === "optimized")?.[1]?.avg_image_payload_bytes ?? 0}
                fmt={fmtBytes}
                savingLabel="less data sent"
              />
            </>
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

function ComparisonBar({
  title,
  label,
  baseline,
  optimized,
  fmt,
  savingLabel,
}: {
  title: string;
  label: string;
  baseline: number;
  optimized: number;
  fmt: (v: number) => string;
  savingLabel: string;
}) {
  if (!baseline || !optimized) return null;
  const saved = Math.round(((baseline - optimized) / baseline) * 100);
  return (
    <div className="mt-4 rounded-[20px] border border-[var(--line)] bg-[rgba(255,255,255,0.04)] p-4">
      <p className="panel-label mb-2">{title}</p>
      <p className="display-face text-xl font-bold uppercase text-white">{label}</p>
      <div className="mt-3 space-y-2">
        <BarRow label="Baseline" value={baseline} max={Math.max(baseline, optimized)} fmt={fmt} color="bg-gray-500" />
        <BarRow label="Optimized" value={optimized} max={Math.max(baseline, optimized)} fmt={fmt} color="bg-purple-500" />
      </div>
      {saved > 0 && (
        <p className="mt-3 text-sm font-medium text-[var(--signal)]">
          Optimized is {saved}% {savingLabel}
        </p>
      )}
      {saved <= 0 && (
        <p className="mt-3 text-sm font-medium text-[var(--text-dim)]">
          More comparison runs are needed to show a clear win.
        </p>
      )}
    </div>
  );
}

function BarRow({
  label,
  value,
  max,
  fmt,
  color,
}: {
  label: string;
  value: number;
  max: number;
  fmt: (v: number) => string;
  color: string;
}) {
  const pct = max > 0 ? (value / max) * 100 : 0;
  return (
    <div className="flex items-center gap-2">
      <span className="w-20 text-[11px] uppercase tracking-[0.12em] text-[var(--text-faint)]">{label}</span>
      <div className="h-2 flex-1 rounded-full bg-[rgba(255,255,255,0.06)]">
        <div className={`${color} h-2 rounded-full`} style={{ width: `${pct}%` }} />
      </div>
      <span className="w-16 text-right text-xs font-mono text-[var(--text-dim)]">{fmt(value)}</span>
    </div>
  );
}
