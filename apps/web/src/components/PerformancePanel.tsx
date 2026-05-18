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
  const optimized = metrics?.by_mode.optimized;
  const baseline = metrics?.by_mode.baseline;
  const latencyDelta =
    optimized && baseline && baseline.avg_latency_ms > 0
      ? Math.round(((baseline.avg_latency_ms - optimized.avg_latency_ms) / baseline.avg_latency_ms) * 100)
      : null;
  const payloadDelta =
    optimized && baseline && baseline.avg_image_payload_bytes > 0
      ? Math.round(
          ((baseline.avg_image_payload_bytes - optimized.avg_image_payload_bytes) /
            baseline.avg_image_payload_bytes) *
            100,
        )
      : null;

  return (
    <div className="rounded-[20px] border border-[var(--line)] bg-[rgba(255,255,255,0.03)] p-4">
      <div className="mb-5 flex items-center gap-2">
        <BarChart3 className="h-4 w-4 text-[var(--amber)]" />
        <div>
          <p className="panel-label">Optimization Evidence</p>
          <h2 className="display-face text-lg font-bold uppercase text-white">Mode Comparison</h2>
        </div>
        <button
          onClick={() => void fetch()}
          className="ml-auto rounded-full border border-[var(--line)] bg-[rgba(255,255,255,0.04)] p-2 text-[var(--text-faint)] transition-colors hover:text-white"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
        </button>
      </div>

      {!metrics || metrics.total === 0 ? (
        <p className="text-sm text-[var(--text-dim)]">No runs recorded yet.</p>
      ) : (
        <div className="space-y-4">
          <div className="grid gap-3 lg:grid-cols-[0.8fr_1.2fr]">
            <div className="rounded-[18px] border border-[rgba(125,249,208,0.24)] bg-[rgba(125,249,208,0.06)] px-4 py-4">
              <p className="panel-label">Observed Samples</p>
              <p className="display-face mt-2 text-3xl font-bold text-white">{metrics.total}</p>
            </div>
            <div className="grid gap-3 sm:grid-cols-2">
              <DeltaTile
                label="Latency Delta"
                value={latencyDelta !== null ? `${latencyDelta}% faster` : "Need both modes"}
              />
              <DeltaTile
                label="Payload Delta"
                value={payloadDelta !== null ? `${payloadDelta}% lighter` : "Need both modes"}
              />
            </div>
          </div>

          <div className="grid gap-3 lg:grid-cols-2">
            {modes.map(([mode, m]) => (
              <div key={mode} className="rounded-[18px] border border-[var(--line)] bg-[rgba(255,255,255,0.04)] p-4">
                <div className="flex items-end justify-between gap-3">
                  <p
                    className={`display-face text-lg font-bold uppercase ${mode === "optimized" ? "text-[var(--signal)]" : "text-[var(--text-dim)]"}`}
                  >
                    {mode}
                  </p>
                  <span className="text-xs uppercase tracking-[0.14em] text-[var(--text-faint)]">{m.count} runs</span>
                </div>
                <div className="mt-3 grid grid-cols-2 gap-2">
                  <Metric label="Avg Latency" value={`${m.avg_latency_ms}ms`} />
                  <Metric label="VLM Calls" value={m.avg_vlm_calls.toFixed(2)} />
                  <Metric label="Frame Reduction" value={`${(m.avg_frame_reduction_ratio * 100).toFixed(0)}%`} highlight />
                  <Metric label="Cloud Payload" value={fmtBytes(m.avg_image_payload_bytes)} highlight />
                </div>
              </div>
            ))}
          </div>

          {modes.length === 2 && (
            <div className="grid gap-4 lg:grid-cols-2">
              <ComparisonBar
                title="Latency Delta"
                label="Baseline vs Optimized"
                baseline={baseline?.avg_latency_ms ?? 0}
                optimized={optimized?.avg_latency_ms ?? 0}
                fmt={(v) => `${v}ms`}
                savingLabel="faster"
              />
              <ComparisonBar
                title="Cloud Payload Delta"
                label="Semantic vs Vision Path"
                baseline={baseline?.avg_image_payload_bytes ?? 0}
                optimized={optimized?.avg_image_payload_bytes ?? 0}
                fmt={fmtBytes}
                savingLabel="data saved"
              />
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function DeltaTile({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-[18px] border border-[var(--line)] bg-[rgba(255,255,255,0.04)] px-4 py-4">
      <p className="eyebrow">{label}</p>
      <p className="display-face mt-2 text-xl font-bold uppercase text-white">{value}</p>
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
    <div className="rounded-[18px] border border-[var(--line)] bg-[rgba(255,255,255,0.04)] p-4">
      <p className="panel-label mb-2">{title}</p>
      <p className="display-face text-lg font-bold uppercase text-white">{label}</p>
      <div className="mt-3 space-y-2">
        <BarRow label="Baseline" value={baseline} max={Math.max(baseline, optimized)} fmt={fmt} color="bg-gray-500" />
        <BarRow
          label="Optimized"
          value={optimized}
          max={Math.max(baseline, optimized)}
          fmt={fmt}
          color="bg-[var(--signal)]"
        />
      </div>
      <p className={`mt-3 text-sm font-medium ${saved > 0 ? "text-[var(--signal)]" : "text-[var(--text-dim)]"}`}>
        {saved > 0 ? `Optimized is ${saved}% ${savingLabel}` : "Run more comparisons to see a clearer delta."}
      </p>
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
      <span className="w-14 shrink-0 text-[11px] text-[var(--text-faint)]">{label}</span>
      <div className="h-2 flex-1 rounded-full bg-[rgba(255,255,255,0.06)]">
        <div className={`${color} h-2 rounded-full`} style={{ width: `${pct}%` }} />
      </div>
      <span className="w-16 text-right text-xs font-mono text-[var(--text-dim)]">{fmt(value)}</span>
    </div>
  );
}
