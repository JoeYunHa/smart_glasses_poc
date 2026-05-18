import type { ReactNode } from "react";
import { BarChart3, Brain, ChevronDown, Database } from "lucide-react";
import { useState } from "react";
import { runAgent } from "@/api/agentApi";
import AgentDecisionPanel from "@/components/AgentDecisionPanel";
import GraphContextPanel from "@/components/GraphContextPanel";
import InputPanel from "@/components/InputPanel";
import OutputPanel from "@/components/OutputPanel";
import PerformancePanel from "@/components/PerformancePanel";
import type { AgentResponse, ContextRequest } from "@/types/agent";

export default function PocDashboard() {
  const [response, setResponse] = useState<AgentResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(ctx: ContextRequest, image?: File, video?: File) {
    setLoading(true);
    setError(null);
    try {
      const res = await runAgent(ctx, image, video);
      setResponse(res);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unexpected error occurred.");
    } finally {
      setLoading(false);
    }
  }

  const frameSavings =
    response && response.original_frame_count > 0
      ? Math.max(
          0,
          Math.round(
            ((response.original_frame_count - response.selected_keyframe_count) /
              response.original_frame_count) *
              100,
          ),
        )
      : 0;

  return (
    <div className="telemetry-shell min-h-screen">
      <div className="relative z-10 px-4 py-4 sm:px-6 lg:px-8">
        <header className="reveal-up mx-auto mb-5 max-w-7xl">
          <div className="telemetry-card rounded-[30px] px-5 py-5 sm:px-7 sm:py-6">
            <div className="flex flex-col gap-6 xl:flex-row xl:items-end xl:justify-between">
              <div className="max-w-2xl">
                <div className="mb-3 flex items-center gap-2">
                  <span className="signal-dot" />
                  <span className="panel-label">Physical AI Smart Glasses PoC</span>
                </div>
                <h1 className="display-face text-3xl font-bold leading-none text-white sm:text-[2.5rem]">
                  Comparison-First
                  <span className="ml-2 text-[var(--signal)]">Agent Console</span>
                </h1>
              </div>

              <div className="grid grid-cols-2 gap-2 sm:grid-cols-4 xl:min-w-[30rem]">
                <HeroMetric label="Mode" value={response?.mode ?? "idle"} accent="text-[var(--signal)]" />
                <HeroMetric
                  label="Latency"
                  value={response ? `${response.latency_ms.total}ms` : "--"}
                  accent="text-[var(--amber)]"
                />
                <HeroMetric label="Saved" value={response ? `${frameSavings}%` : "--"} accent="text-[var(--accent)]" />
                <HeroMetric
                  label="Service"
                  value={response?.selected_service.replace(/_/g, " ") ?? "--"}
                  accent="text-[var(--alert)]"
                />
              </div>
            </div>
          </div>
        </header>

        {error && (
          <div className="mx-auto mb-4 max-w-7xl">
            <div className="telemetry-card rounded-[22px] border-[rgba(255,140,105,0.45)] bg-[rgba(50,19,18,0.86)] px-4 py-3 text-sm text-[var(--alert)]">
              {error}
            </div>
          </div>
        )}

        <main className="mx-auto grid max-w-7xl gap-5 xl:grid-cols-[22rem_minmax(0,1fr)]">
          <aside className="space-y-5 xl:sticky xl:top-4 xl:self-start">
            <InputPanel onSubmit={(ctx, img, vid) => void handleSubmit(ctx, img, vid)} loading={loading} />
          </aside>

          <section className="space-y-5">
            <ComparisonSpotlight response={response} frameSavings={frameSavings} />

            <div className="grid gap-5 2xl:grid-cols-[1.05fr_0.95fr]">
              <OutputPanel response={response} />
              <AgentDecisionPanel response={response} />
            </div>

            <details className="group telemetry-card reveal-up rounded-[24px] p-5 sm:p-6" open>
              <summary className="flex cursor-pointer list-none items-center justify-between gap-4">
                <div>
                  <p className="panel-label">Diagnostics</p>
                  <h2 className="display-face text-xl font-bold uppercase text-white">Comparison Evidence</h2>
                </div>
                <span className="flex items-center gap-2 rounded-full border border-[var(--line)] bg-[rgba(255,255,255,0.04)] px-3 py-1.5 text-[11px] uppercase tracking-[0.16em] text-[var(--text-faint)]">
                  details
                  <ChevronDown className="h-3.5 w-3.5 transition-transform group-open:rotate-180" />
                </span>
              </summary>

              <div className="mt-5 grid gap-5 2xl:grid-cols-[1.1fr_0.9fr]">
                <PerformancePanel />
                <GraphContextPanel />
              </div>
            </details>
          </section>
        </main>
      </div>
    </div>
  );
}

function ComparisonSpotlight({
  response,
  frameSavings,
}: {
  response: AgentResponse | null;
  frameSavings: number;
}) {
  const confidencePct = response ? Math.round(response.router_confidence * 100) : 0;

  return (
    <div className="telemetry-card reveal-up overflow-hidden rounded-[28px] p-5 sm:p-6">
      <div className="flex flex-col gap-5 lg:flex-row lg:items-stretch">
        <div className="min-w-0 flex-1">
          <div className="mb-3 flex items-center gap-2">
            <BarChart3 className="h-4 w-4 text-[var(--amber)]" />
            <span className="panel-label">Comparison Spotlight</span>
          </div>
          <h2 className="display-face text-2xl font-bold uppercase text-white sm:text-[2rem]">
            {response ? `${response.mode} run, ${confidencePct}% confidence` : "Run a scenario to compare paths"}
          </h2>
        </div>

        <div className="grid flex-[0.95] grid-cols-1 gap-3 sm:grid-cols-3">
          <SpotlightMetric
            icon={<Brain className="h-4 w-4 text-[var(--signal)]" />}
            label="Router"
            value={response ? `${confidencePct}%` : "--"}
            note={response ? "route confidence" : "awaiting run"}
          />
          <SpotlightMetric
            icon={<Database className="h-4 w-4 text-[var(--amber)]" />}
            label="Frames"
            value={response ? `${frameSavings}%` : "--"}
            note={response ? "frame reduction" : "awaiting run"}
          />
          <SpotlightMetric
            icon={<Database className="h-4 w-4 text-[var(--accent)]" />}
            label="Memory"
            value={response ? String(response.retrieved_graph_nodes) : "--"}
            note={response ? "graph nodes" : "awaiting run"}
          />
        </div>
      </div>
    </div>
  );
}

function SpotlightMetric({
  icon,
  label,
  value,
  note,
}: {
  icon: ReactNode;
  label: string;
  value: string;
  note: string;
}) {
  return (
    <div className="rounded-[22px] border border-[var(--line)] bg-[linear-gradient(180deg,rgba(255,255,255,0.06),rgba(255,255,255,0.02))] px-4 py-4">
      <div className="flex items-center gap-2">
        {icon}
        <span className="eyebrow">{label}</span>
      </div>
      <p className="display-face mt-3 text-3xl font-bold leading-none text-white">{value}</p>
      <p className="mt-2 text-xs uppercase tracking-[0.12em] text-[var(--text-faint)]">{note}</p>
    </div>
  );
}

function HeroMetric({ label, value, accent }: { label: string; value: string; accent: string }) {
  return (
    <div className="min-w-0 rounded-[20px] border border-[var(--line)] bg-[rgba(255,255,255,0.04)] px-3 py-3">
      <p className="panel-label truncate">{label}</p>
      <p className={`display-face mt-1 break-words text-base font-bold leading-snug ${accent}`}>{value}</p>
    </div>
  );
}
