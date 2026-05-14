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
      <div className="bg-gray-900 rounded-xl p-5 border border-gray-700 flex items-center justify-center h-32">
        <p className="text-gray-500 text-sm">Response output will appear here.</p>
      </div>
    );
  }

  const icon = SERVICE_ICONS[response.selected_service] ?? <Volume2 className="w-5 h-5 text-gray-400" />;

  return (
    <div className="bg-gray-900 rounded-xl p-5 border border-gray-700 space-y-4">
      <div className="flex items-center gap-2">
        {icon}
        <h2 className="text-sm font-semibold text-gray-300 uppercase tracking-wide">Output</h2>
        <span className="ml-auto text-xs text-gray-500 font-mono">{response.mode}</span>
      </div>

      <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
        <p className="text-sm text-gray-100 leading-relaxed whitespace-pre-wrap">
          {response.response_text}
        </p>
      </div>

      {response.action_result && (
        <div
          className={`flex items-start gap-3 p-3 rounded-lg border ${
            response.action_result.success
              ? "bg-emerald-900/20 border-emerald-700"
              : "bg-red-900/20 border-red-700"
          }`}
        >
          {response.action_result.success ? (
            <CheckCircle className="w-4 h-4 text-emerald-400 mt-0.5 shrink-0" />
          ) : (
            <XCircle className="w-4 h-4 text-red-400 mt-0.5 shrink-0" />
          )}
          <div>
            <p className="text-xs font-medium text-gray-300">
              {response.action_result.device_id} / {response.action_result.action}
            </p>
            <p className="text-xs text-gray-400 mt-0.5">{response.action_result.message}</p>
          </div>
        </div>
      )}

      <p className="text-xs text-gray-600 font-mono">req: {response.request_id.slice(0, 8)}</p>
    </div>
  );
}
