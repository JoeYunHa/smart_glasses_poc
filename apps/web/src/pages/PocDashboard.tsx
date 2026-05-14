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
      setError(e instanceof Error ? e.message : "알 수 없는 오류");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100">
      {/* Header */}
      <header className="border-b border-gray-800 px-6 py-4">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div>
            <h1 className="text-lg font-bold text-white">Smart Glasses Physical AI Agent</h1>
            <p className="text-xs text-gray-500">PoC — 입력 → 전처리 → 판단 → 행동 → 로그 → 개선</p>
          </div>
          <div className="flex gap-2 text-xs text-gray-500">
            <span className="px-2 py-1 rounded bg-gray-800">Groq LLM</span>
            <span className="px-2 py-1 rounded bg-gray-800">GraphRAG</span>
            <span className="px-2 py-1 rounded bg-gray-800">Keyframe Selection</span>
          </div>
        </div>
      </header>

      {/* Error banner */}
      {error && (
        <div className="max-w-7xl mx-auto px-6 pt-4">
          <div className="bg-red-900/30 border border-red-700 text-red-300 text-sm rounded-lg px-4 py-3">
            {error}
          </div>
        </div>
      )}

      {/* Main grid */}
      <main className="max-w-7xl mx-auto px-6 py-6 grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left column */}
        <div className="space-y-6">
          <InputPanel onSubmit={(ctx, img, vid) => void handleSubmit(ctx, img, vid)} loading={loading} />
          <PerformancePanel />
        </div>

        {/* Center column */}
        <div className="space-y-6">
          <AgentDecisionPanel response={response} />
          <OutputPanel response={response} />
        </div>

        {/* Right column */}
        <div>
          <GraphContextPanel />
        </div>
      </main>
    </div>
  );
}
