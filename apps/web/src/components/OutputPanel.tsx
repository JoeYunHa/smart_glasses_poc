import { AlertTriangle, CheckCircle, Volume2, XCircle, Zap } from "lucide-react";
import type { AgentResponse } from "@/types/agent";

interface Props {
  response: AgentResponse | null;
}

const SERVICE_ICONS: Record<string, React.ReactNode> = {
  safety_alert: <AlertTriangle className="w-5 h-5 text-red-400" />,
  device_control: <Zap className="w-5 h-5 text-blue-400" />,
  navigation: <Volume2 className="w-5 h-5 text-emerald-400" />,
  context_memory: <Volume2 className="w-5 h-5 text-amber-400" />,
  scene_assistant: <Volume2 className="w-5 h-5 text-purple-400" />,
};

export default function OutputPanel({ response }: Props) {
  if (!response) {
    return (
      <div className="telemetry-card reveal-up flex h-40 items-center justify-center rounded-[24px] p-6">
        <div className="text-center">
          <p className="panel-label">Output Feed</p>
          <p className="mt-3 text-sm text-[var(--text-dim)]">Response output will appear here.</p>
        </div>
      </div>
    );
  }

  const icon = SERVICE_ICONS[response.selected_service] ?? <Volume2 className="w-5 h-5 text-gray-400" />;

  return (
    <div className="telemetry-card reveal-up rounded-[24px] p-5 sm:p-6">
      <div className="mb-5 flex items-center gap-2">
        {icon}
        <div>
          <p className="panel-label">Output Feed</p>
          <h2 className="display-face text-2xl font-bold uppercase text-white">Response + Action</h2>
        </div>
        <span className="ml-auto rounded-full border border-[var(--line)] bg-[rgba(255,255,255,0.04)] px-3 py-1.5 text-[11px] uppercase tracking-[0.16em] text-[var(--text-faint)]">
          {response.mode}
        </span>
      </div>

      <div className="rounded-[20px] border border-[var(--line)] bg-[rgba(255,255,255,0.04)] p-4">
        <p className="text-sm leading-7 text-white whitespace-pre-wrap">
          {response.response_text}
        </p>
      </div>

      {response.action_result && (
        <div
          className={`mt-4 flex items-start gap-3 rounded-[20px] border p-4 ${
            response.action_result.success
              ? "border-[rgba(125,249,208,0.34)] bg-[rgba(125,249,208,0.08)]"
              : "border-[rgba(255,140,105,0.34)] bg-[rgba(255,140,105,0.08)]"
          }`}
        >
          {response.action_result.success ? (
            <CheckCircle className="mt-0.5 h-4 w-4 shrink-0 text-[var(--signal)]" />
          ) : (
            <XCircle className="mt-0.5 h-4 w-4 shrink-0 text-[var(--alert)]" />
          )}
          <div>
            <p className="display-face text-base font-bold uppercase text-white">
              {response.action_result.device_id} / {response.action_result.action}
            </p>
            <p className="mt-1 text-xs leading-6 text-[var(--text-dim)]">{response.action_result.message}</p>
          </div>
        </div>
      )}

      <p className="mt-4 text-xs font-mono text-[var(--text-faint)]">request id: {response.request_id}</p>
    </div>
  );
}
