import {
  AlertTriangle, Building2, Calendar, CheckCircle, Clock,
  Layers, Package, ScanText, Square, Volume2, XCircle, Zap,
} from "lucide-react";
import { useEffect } from "react";
import { useTTS } from "@/hooks/useTTS";
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
  label_reader: <ScanText className="w-5 h-5 text-teal-400" />,
};

// ── Label Reader helpers ──────────────────────────────────────────────────────

interface LabelField {
  label: string;
  value: string;
}

const LABEL_FIELD_ICONS: Record<string, React.ReactNode> = {
  "제품명":        <Package       className="w-4 h-4 text-teal-400" />,
  "약품명":        <Package       className="w-4 h-4 text-teal-400" />,
  "제품명/약품명": <Package       className="w-4 h-4 text-teal-400" />,
  "주성분":        <Layers        className="w-4 h-4 text-teal-300" />,
  "핵심 성분":     <Layers        className="w-4 h-4 text-teal-300" />,
  "용법":          <Clock         className="w-4 h-4 text-sky-400" />,
  "용량":          <Clock         className="w-4 h-4 text-sky-400" />,
  "용법·용량":     <Clock         className="w-4 h-4 text-sky-400" />,
  "주의사항":      <AlertTriangle className="w-4 h-4 text-amber-400" />,
  "유효기간":      <Calendar      className="w-4 h-4 text-rose-400" />,
  "제조사":        <Building2     className="w-4 h-4 text-slate-400" />,
};

function fieldIcon(label: string): React.ReactNode {
  for (const key of Object.keys(LABEL_FIELD_ICONS)) {
    if (label.includes(key)) return LABEL_FIELD_ICONS[key];
  }
  return <Package className="w-4 h-4 text-teal-400" />;
}

/** Parse numbered list lines: "1. 제품명/약품명: 타이레놀" → {label, value} */
function parseLabelFields(text: string): LabelField[] {
  return text
    .split("\n")
    .map((line) => line.match(/^\d+\.\s+(.+?)[:：]\s*(.+)$/))
    .filter(Boolean)
    .map((m) => ({ label: m![1].trim(), value: m![2].trim() }));
}

/** Extract the ⚠️ safety footer line from the response */
function extractSafetyNote(text: string): string {
  const line = text.split("\n").find((l) => l.includes("약사") || l.includes("의사") || l.includes("⚠️"));
  return line ? line.replace("⚠️", "").trim() : "";
}

// ── TTS helpers ───────────────────────────────────────────────────────────────

/** Waveform bars animation shown while TTS is active */
function SpeakingIndicator() {
  return (
    <span className="flex items-end gap-[3px] h-4" aria-label="speaking">
      {[0, 1, 2, 3].map((i) => (
        <span
          key={i}
          className="w-[3px] rounded-full bg-[var(--signal)] animate-bounce"
          style={{ animationDelay: `${i * 0.1}s`, height: `${8 + (i % 2) * 6}px` }}
        />
      ))}
    </span>
  );
}

/** Play / Stop TTS button */
function TTSButton({
  speaking,
  supported,
  onPlay,
  onStop,
}: {
  speaking: boolean;
  supported: boolean;
  onPlay: () => void;
  onStop: () => void;
}) {
  if (!supported) return null;

  return (
    <div className="flex min-w-0 items-center gap-2">
      {speaking && <SpeakingIndicator />}
      <button
        onClick={speaking ? onStop : onPlay}
        title={speaking ? "음성 중지" : "음성으로 듣기"}
        className={`min-w-0 rounded-full border px-3 py-1.5 text-[11px] transition-colors ${
          speaking
            ? "border-[rgba(255,140,105,0.45)] bg-[rgba(255,140,105,0.12)] text-[var(--alert)]"
            : "border-[var(--line)] bg-[rgba(255,255,255,0.04)] text-[var(--text-faint)] hover:text-white"
        }`}
      >
        <span className="button-pill flex items-center justify-center gap-1.5 uppercase">
          {speaking ? (
            <>
              <Square className="h-3 w-3 shrink-0 fill-current" /> Stop
            </>
          ) : (
            <>
              <Volume2 className="h-3 w-3 shrink-0" /> Play
            </>
          )}
        </span>
      </button>
    </div>
  );
}

// ── Sub-components ─────────────────────────────────────────────────────────────

function LabelReaderOutput({ text }: { text: string }) {
  const fields = parseLabelFields(text);
  const safetyNote = extractSafetyNote(text);

  if (fields.length === 0) {
    return (
      <div className="rounded-[20px] border border-teal-800/50 bg-[rgba(20,184,166,0.05)] p-4">
        <p className="text-sm leading-7 text-white whitespace-pre-wrap">{text}</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <div className="grid gap-2 sm:grid-cols-2">
        {fields.map(({ label, value }) => (
          <div
            key={label}
            className="flex items-start gap-3 rounded-[18px] border border-teal-900/50 bg-[rgba(20,184,166,0.06)] p-3"
          >
            <span className="mt-0.5 shrink-0">{fieldIcon(label)}</span>
            <div className="min-w-0">
              <p className="text-[10px] uppercase tracking-[0.14em] text-teal-500">{label}</p>
              <p className="mt-0.5 text-sm font-medium leading-5 text-white break-words">{value}</p>
            </div>
          </div>
        ))}
      </div>

      {safetyNote && (
        <div className="flex items-start gap-3 rounded-[18px] border border-amber-800/50 bg-[rgba(245,158,11,0.08)] p-3">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-amber-400" />
          <p className="text-xs leading-5 text-amber-200">{safetyNote}</p>
        </div>
      )}
    </div>
  );
}

// ── Main component ─────────────────────────────────────────────────────────────

export default function OutputPanel({ response }: Props) {
  const { speaking, supported, speak, stop } = useTTS();

  // Auto-play TTS whenever a new response arrives (keyed by request_id).
  useEffect(() => {
    if (response?.response_text) {
      speak(response.response_text);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [response?.request_id]);

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

  const isLabelReader = response.selected_service === "label_reader";
  const icon = SERVICE_ICONS[response.selected_service] ?? <Volume2 className="w-5 h-5 text-gray-400" />;

  return (
    <div className="telemetry-card reveal-up rounded-[24px] p-5 sm:p-6">
      {/* Header */}
      <div className="mb-5 flex items-start gap-2">
        {icon}
        <div className="min-w-0">
          <p className="panel-label">Output Feed</p>
          <h2 className="display-face text-xl font-bold uppercase text-white">
            {isLabelReader ? "Label Read Result" : "Response + Action"}
          </h2>
        </div>
        <div className="ml-auto flex min-w-0 flex-wrap items-center justify-end gap-2">
          <TTSButton
            speaking={speaking}
            supported={supported}
            onPlay={() => speak(response.response_text)}
            onStop={stop}
          />
          <span className="rounded-full border border-[var(--line)] bg-[rgba(255,255,255,0.04)] px-3 py-1.5 text-[11px] uppercase tracking-[0.16em] text-[var(--text-faint)]">
            {response.mode}
          </span>
        </div>
      </div>

      {/* Result description */}
      <div className="mb-4 rounded-[20px] border border-[var(--line)] bg-[rgba(255,255,255,0.03)] px-4 py-3">
        <p className="eyebrow">Result View</p>
        <p className="mt-2 text-sm leading-6 text-[var(--text-dim)]">
          Voice guidance or action result generated after the selected service completes.
        </p>
      </div>

      {/* Response body */}
      {isLabelReader ? (
        <LabelReaderOutput text={response.response_text} />
      ) : (
        <div className="rounded-[20px] border border-[var(--line)] bg-[rgba(255,255,255,0.04)] p-4">
          <p className="text-sm leading-7 text-white whitespace-pre-wrap">
            {response.response_text}
          </p>
        </div>
      )}

      {/* Action result */}
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

      <p className="mt-4 text-xs font-mono text-[var(--text-faint)]">Request ID: {response.request_id}</p>
    </div>
  );
}
