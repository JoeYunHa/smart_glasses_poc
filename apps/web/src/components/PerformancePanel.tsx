import { BarChart3, RefreshCw } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { getMetrics } from "@/api/agentApi";
import type { MetricsData, ServiceModeMetrics } from "@/types/agent";

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

          {metrics.by_service && Object.keys(metrics.by_service).length > 0 && (
            <ServiceBreakdown byService={metrics.by_service} />
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
  if (baseline == null || optimized == null) return null;
  const maxValue = Math.max(baseline, optimized);
  if (maxValue <= 0) return null;
  const saved = baseline > 0 ? Math.round(((baseline - optimized) / baseline) * 100) : null;
  return (
    <div className="rounded-[18px] border border-[var(--line)] bg-[rgba(255,255,255,0.04)] p-4">
      <p className="panel-label mb-2">{title}</p>
      <p className="display-face text-lg font-bold uppercase text-white">{label}</p>
      <div className="mt-3 space-y-2">
        <BarRow label="Baseline" value={baseline} max={maxValue} fmt={fmt} color="bg-gray-500" />
        <BarRow
          label="Optimized"
          value={optimized}
          max={maxValue}
          fmt={fmt}
          color="bg-[var(--signal)]"
        />
      </div>
      <p className={`mt-3 text-sm font-medium ${saved !== null && saved > 0 ? "text-[var(--signal)]" : "text-[var(--text-dim)]"}`}>
        {saved !== null && saved > 0 ? `Optimized is ${saved}% ${savingLabel}` : "Run more comparisons to see a clearer delta."}
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

const SERVICE_LABELS: Record<string, string> = {
  safety_alert: "Safety Alert",
  label_reader: "Label Reader",
  scene_assistant: "Scene Assistant",
  context_memory: "Context Memory",
  device_control: "Device Control",
  navigation: "Navigation",
};

function ServiceBreakdown({
  byService,
}: {
  byService: Record<string, Partial<Record<"baseline" | "optimized", ServiceModeMetrics>>>;
}) {
  const services = Object.keys(byService).sort();

  return (
    <div className="rounded-[18px] border border-[var(--line)] bg-[rgba(255,255,255,0.04)] p-4">
      <p className="panel-label mb-1">Per-Service Breakdown</p>
      <h3 className="display-face mb-4 text-base font-bold uppercase text-white">
        Baseline vs Optimized by Service
      </h3>
      <div className="space-y-3">
        {services.map((svc) => {
          const b = byService[svc]?.baseline;
          const o = byService[svc]?.optimized;
          const label = SERVICE_LABELS[svc] ?? svc;
          return (
            <div key={svc} className="rounded-[14px] border border-[rgba(255,255,255,0.07)] bg-[rgba(3,9,14,0.5)] p-3">
              <p className="mb-2 text-[11px] font-semibold uppercase tracking-[0.14em] text-[var(--amber)]">
                {label}
              </p>
              <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
                <ServiceCell label="Latency" b={b?.avg_latency_ms} o={o?.avg_latency_ms} fmt={(v) => `${v}ms`} lowerIsBetter />
                <ServiceCell label="VLM Calls" b={b?.avg_vlm_calls} o={o?.avg_vlm_calls} fmt={(v) => v.toFixed(2)} lowerIsBetter />
                <ServiceCell label="Payload" b={b?.avg_image_payload_bytes} o={o?.avg_image_payload_bytes} fmt={fmtBytes} lowerIsBetter />
                <ServiceCell label="Quality %" b={b?.quality_check_rate} o={o?.quality_check_rate} fmt={(v) => `${(v * 100).toFixed(0)}%`} lowerIsBetter={false} />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function ServiceCell({
  label,
  b,
  o,
  fmt,
  lowerIsBetter,
}: {
  label: string;
  b: number | undefined;
  o: number | undefined;
  fmt: (v: number) => string;
  lowerIsBetter: boolean;
}) {
  const bVal = b ?? null;
  const oVal = o ?? null;

  const oColor = (() => {
    if (oVal === null || bVal === null) return "text-[var(--text-dim)]";
    if (oVal === bVal) return "text-[var(--text-dim)]";
    const optimizedWins = lowerIsBetter ? oVal < bVal : oVal > bVal;
    return optimizedWins ? "text-[var(--signal)]" : "text-[var(--amber)]";
  })();

  return (
    <div className="rounded-[10px] border border-[var(--line)] bg-[rgba(255,255,255,0.03)] p-2">
      <p className="text-[10px] uppercase tracking-[0.1em] text-[var(--text-faint)]">{label}</p>
      <div className="mt-1.5 flex items-end gap-1.5">
        <span className="font-mono text-xs text-[var(--text-dim)]">{bVal !== null ? fmt(bVal) : "—"}</span>
        <span className="text-[10px] text-[var(--text-faint)]">→</span>
        <span className={`font-mono text-xs font-semibold ${oColor}`}>{oVal !== null ? fmt(oVal) : "—"}</span>
      </div>
      <p className="mt-0.5 text-[9px] text-[var(--text-faint)]">base → opt</p>
    </div>
  );
}
