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
      setError(e instanceof Error ? e.message : "Unexpected error");
    } finally {
      setLoading(false);
    }
  }

  const frameSavings = response && response.original_frame_count > 0
    ? Math.max(0, Math.round(((response.original_frame_count - response.selected_keyframe_count) / response.original_frame_count) * 100))
    : 0;

  return (
    <div className="telemetry-shell min-h-screen">
      <div className="relative z-10 px-4 py-4 sm:px-6 lg:px-8">
        <header className="mission-stage reveal-up rounded-[32px] px-5 py-5 sm:px-7 sm:py-7">
          <div className="mx-auto max-w-7xl">
            <div className="flex flex-col gap-8 xl:flex-row xl:items-end xl:justify-between">
              <div className="max-w-4xl">
                <div className="mb-4 flex flex-wrap items-center gap-3">
                  <span className="stage-kicker">
                    <span className="signal-dot" />
                    Physical AI Telemetry Console
                  </span>
                  <span className="stage-kicker">Demo Operator View</span>
                  <span className="stage-kicker">Optimization Evidence</span>
                </div>
                <h1 className="display-face max-w-4xl text-4xl font-bold leading-none text-white sm:text-5xl lg:text-6xl">
                  Smart Glasses
                  <span className="ml-3 text-[var(--signal)]">Operator Stage</span>
                </h1>
                <p className="mt-4 max-w-3xl text-sm leading-6 text-[var(--text-dim)] sm:text-base">
                  Demonstrate, in one screen, how semantic compression, GraphRAG retrieval, service routing,
                  and guarded execution reduce cloud payload while keeping the assistant responsive in field scenarios.
                </p>
                <div className="mt-6 grid gap-3 sm:grid-cols-3">
                  <NarrativeCard
                    title="Run a scenario"
                    text="Load a request with image or video input and switch between baseline and optimized execution paths."
                  />
                  <NarrativeCard
                    title="Expose the reasoning path"
                    text="Surface the chosen service, keyframe reduction, memory retrieval, and latency composition."
                  />
                  <NarrativeCard
                    title="Prove the optimization"
                    text="Use the evidence board to show latency and cloud payload deltas, not just final answers."
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 xl:min-w-[34rem]">
                <HeroMetric label="Mode" value={response?.mode ?? "idle"} accent="text-[var(--signal)]" />
                <HeroMetric label="Latency" value={response ? `${response.latency_ms.total}ms` : "--"} accent="text-[var(--amber)]" />
                <HeroMetric label="Frames Saved" value={response ? `${frameSavings}%` : "--"} accent="text-[var(--accent)]" />
                <HeroMetric label="Service" value={response?.selected_service.replace(/_/g, " ") ?? "waiting"} accent="text-[var(--alert)]" />
              </div>
            </div>

            <div className="mt-7 flex flex-wrap gap-2 text-[11px] uppercase tracking-[0.18em] text-[var(--text-faint)]">
              {["Groq LLM", "GraphRAG Memory", "Keyframe Selection", "Latency Logging", "Action Guardrail", "Label OCR Path"].map((item) => (
                <span key={item} className="rounded-full border border-[var(--line)] bg-white/4 px-3 py-1.5">
                  {item}
                </span>
              ))}
            </div>
          </div>
        </header>

        {error && (
          <div className="mx-auto mt-4 max-w-7xl">
            <div className="telemetry-card rounded-[22px] border-[rgba(255,140,105,0.45)] bg-[rgba(50,19,18,0.86)] px-4 py-3 text-sm text-[var(--alert)]">
              {error}
            </div>
          </div>
        )}

        <main className="mx-auto mt-5 grid max-w-7xl grid-cols-1 gap-5 xl:grid-cols-[1.05fr_1.1fr_0.85fr]">
          <div className="space-y-5">
            <SectionHeader eyebrow="Mission Setup" title="Scenario Control" text="Compose the request payload and choose the execution mode for the demo run." />
            <div className="section-frame rounded-[28px] p-2">
              <InputPanel onSubmit={(ctx, img, vid) => void handleSubmit(ctx, img, vid)} loading={loading} />
            </div>
            <SectionHeader eyebrow="Optimization Evidence" title="Proof Board" text="Aggregate baseline and optimized runs into metrics that can be presented live." />
            <div className="section-frame rounded-[28px] p-2">
              <PerformancePanel />
            </div>
          </div>

          <div className="space-y-5">
            <SectionHeader eyebrow="Pipeline Trace" title="Decision + Output" text="Show what route the agent chose and what the user would hear or trigger." />
            <div className="section-frame rounded-[28px] p-2">
              <AgentDecisionPanel response={response} />
            </div>
            <div className="section-frame rounded-[28px] p-2">
              <OutputPanel response={response} />
            </div>
          </div>

          <div className="space-y-5">
            <SectionHeader eyebrow="Memory Layer" title="GraphRAG Surface" text="Inspect what structured memory has been accumulated across runs." />
            <div className="section-frame rounded-[28px] p-2">
            <GraphContextPanel />
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}

function HeroMetric({ label, value, accent }: { label: string; value: string; accent: string }) {
  return (
    <div className="metric-tile rounded-[24px] px-3 py-3.5">
      <p className="eyebrow">{label}</p>
      <p className={`display-face mt-2 text-2xl font-bold uppercase leading-none ${accent}`}>{value}</p>
    </div>
  );
}

function NarrativeCard({ title, text }: { title: string; text: string }) {
  return (
    <div className="rounded-[22px] border border-[var(--line)] bg-[rgba(255,255,255,0.04)] px-4 py-4">
      <p className="display-face text-lg font-bold uppercase text-white">{title}</p>
      <p className="mt-2 text-sm leading-6 text-[var(--text-dim)]">{text}</p>
    </div>
  );
}

function SectionHeader({
  eyebrow,
  title,
  text,
}: {
  eyebrow: string;
  title: string;
  text: string;
}) {
  return (
    <div className="px-1">
      <p className="eyebrow">{eyebrow}</p>
      <div className="mt-2 flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
        <h2 className="display-face text-2xl font-bold uppercase text-white">{title}</h2>
        <p className="max-w-xl text-sm leading-6 text-[var(--text-dim)]">{text}</p>
      </div>
    </div>
  );
}
