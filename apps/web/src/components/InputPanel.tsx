import { ImageIcon, MapPin, Mic, MonitorSmartphone, Video } from "lucide-react";
import { useRef, useState } from "react";
import type { AgentMode, ContextRequest, DeviceInfo, GpsContext } from "@/types/agent";

const DEFAULT_DEVICES: DeviceInfo[] = [
  {
    device_id: "light-001",
    name: "Living Room Light",
    type: "smart_light",
    supported_actions: ["turn_on", "turn_off", "set_brightness"],
    risk_level: "low",
    requires_confirmation: false,
    state: { power: "on" },
  },
  {
    device_id: "speaker-001",
    name: "Bluetooth Speaker",
    type: "speaker",
    supported_actions: ["play", "pause", "set_volume"],
    risk_level: "low",
    requires_confirmation: false,
    state: { power: "off" },
  },
];

const QUICK_SCENARIOS = [
  {
    label: "Safety Alert",
    request: "Is it safe to cross right now?",
    gps: { latitude: 37.5665, longitude: 126.978, location_type: "crosswalk", place_name: "Gwanghwamun Intersection" },
  },
  {
    label: "Device Control",
    request: "Turn off the living room light",
    gps: null,
  },
  {
    label: "Scene Assistant",
    request: "What do you see here?",
    gps: null,
  },
  {
    label: "Context Memory",
    request: "Which cafe did I look at earlier?",
    gps: { latitude: 37.57, longitude: 126.982, location_type: "street", place_name: "Seoul City Hall" },
  },
];

interface Props {
  onSubmit: (ctx: ContextRequest, image?: File, video?: File) => void;
  loading: boolean;
}

export default function InputPanel({ onSubmit, loading }: Props) {
  const [request, setRequest] = useState("");
  const [mode, setMode] = useState<AgentMode>("optimized");
  const [gps, setGps] = useState<GpsContext | null>(null);
  const [useDevices, setUseDevices] = useState(false);
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [videoFile, setVideoFile] = useState<File | null>(null);
  const imageRef = useRef<HTMLInputElement>(null);
  const videoRef = useRef<HTMLInputElement>(null);

  function applyScenario(s: (typeof QUICK_SCENARIOS)[0]) {
    setRequest(s.request);
    setGps(s.gps ?? null);
    setUseDevices(s.label === "Device Control");
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!request.trim()) return;

    const ctx: ContextRequest = {
      user_request: request,
      gps,
      nearby_devices: useDevices ? DEFAULT_DEVICES : [],
      mode,
    };

    onSubmit(ctx, imageFile ?? undefined, videoFile ?? undefined);
  }

  return (
    <form onSubmit={handleSubmit} className="telemetry-card reveal-up rounded-[24px] p-5 sm:p-6">
      <div className="mb-5 flex items-start justify-between gap-4">
        <div>
          <div className="mb-2 flex items-center gap-2">
            <Mic className="h-4 w-4 text-[var(--signal)]" />
            <span className="panel-label">Mission Input</span>
          </div>
          <h2 className="display-face text-2xl font-bold uppercase text-white">Scenario Loader</h2>
          <p className="mt-1 max-w-md text-sm text-[var(--text-dim)]">
            Assemble the scene payload, choose the operating mode, and send the request into the optimization pipeline.
          </p>
        </div>
        <div className="rounded-full border border-[var(--line)] bg-[rgba(255,255,255,0.04)] px-3 py-1.5 text-[11px] uppercase tracking-[0.16em] text-[var(--text-faint)]">
          {loading ? "stream active" : "ready"}
        </div>
      </div>

      <div className="rounded-[20px] border border-[var(--line)] bg-[rgba(255,255,255,0.03)] p-3">
        <p className="panel-label mb-3">Quick Scenarios</p>
        <div className="grid gap-2 sm:grid-cols-2">
        {QUICK_SCENARIOS.map((s) => (
          <button
            key={s.label}
            type="button"
            onClick={() => applyScenario(s)}
              className="group rounded-[18px] border border-[var(--line)] bg-[rgba(255,255,255,0.03)] px-4 py-3 text-left transition-all hover:-translate-y-0.5 hover:border-[var(--signal)] hover:bg-[rgba(125,249,208,0.08)]"
          >
              <p className="display-face text-base font-bold uppercase tracking-[0.08em] text-white">{s.label}</p>
              <p className="mt-1 text-xs leading-5 text-[var(--text-dim)]">{s.request}</p>
          </button>
        ))}
        </div>
      </div>

      <div className="mt-4 grid gap-4 md:grid-cols-[1.25fr_0.75fr]">
        <div className="rounded-[20px] border border-[var(--line)] bg-[rgba(255,255,255,0.03)] p-4">
          <label className="panel-label mb-2 block">Request</label>
        <input
          value={request}
          onChange={(e) => setRequest(e.target.value)}
          placeholder="Ask about a scene, route, safety risk, or nearby device"
            className="w-full rounded-[16px] border border-[var(--line)] bg-[rgba(3,9,14,0.72)] px-4 py-3 text-sm text-white placeholder:text-[var(--text-faint)] focus:border-[var(--signal)] focus:outline-none"
        />
        </div>

        <div className="rounded-[20px] border border-[var(--line)] bg-[rgba(255,255,255,0.03)] p-4">
          <p className="panel-label mb-2">Mode</p>
          <div className="grid grid-cols-2 gap-2">
        {(["optimized", "baseline"] as AgentMode[]).map((m) => (
          <button
            key={m}
            type="button"
            onClick={() => setMode(m)}
                className={`rounded-[16px] border px-3 py-3 text-xs font-semibold uppercase tracking-[0.14em] transition-all ${
              mode === m
                    ? "border-[var(--signal)] bg-[rgba(125,249,208,0.12)] text-[var(--signal)]"
                    : "border-[var(--line)] bg-[rgba(3,9,14,0.58)] text-[var(--text-dim)] hover:border-[var(--line-strong)]"
            }`}
          >
            {m === "optimized" ? "Optimized" : "Baseline"}
          </button>
        ))}
          </div>
        </div>
      </div>

      <div className="mt-4 grid gap-4 md:grid-cols-2">
        <div className="rounded-[20px] border border-[var(--line)] bg-[rgba(255,255,255,0.03)] p-4">
          <div className="mb-3 flex items-center gap-2">
            <MapPin className="h-4 w-4 text-[var(--amber)]" />
            <span className="panel-label">Location Signal</span>
          </div>
          <button
          type="button"
          onClick={() =>
            setGps(gps ? null : { latitude: 37.5665, longitude: 126.978, location_type: "crosswalk", place_name: "Gwanghwamun" })
          }
            className={`w-full rounded-[16px] border px-4 py-3 text-left text-sm transition-all ${
              gps
                ? "border-[rgba(255,200,111,0.45)] bg-[rgba(255,200,111,0.12)] text-[var(--amber)]"
                : "border-[var(--line)] bg-[rgba(3,9,14,0.58)] text-[var(--text-dim)]"
          }`}
        >
            <span className="block display-face text-base font-bold uppercase">{gps ? gps.place_name : "GPS Disabled"}</span>
            <span className="mt-1 block text-xs opacity-80">{gps ? `${gps.latitude}, ${gps.longitude}` : "No live location attached to this run."}</span>
          </button>
        </div>

        <div className="rounded-[20px] border border-[var(--line)] bg-[rgba(255,255,255,0.03)] p-4">
          <div className="mb-3 flex items-center gap-2">
            <MonitorSmartphone className="h-4 w-4 text-[var(--accent)]" />
            <span className="panel-label">Nearby Devices</span>
          </div>
          <button
          type="button"
          onClick={() => setUseDevices(!useDevices)}
            className={`w-full rounded-[16px] border px-4 py-3 text-left text-sm transition-all ${
              useDevices
                ? "border-[rgba(139,184,255,0.45)] bg-[rgba(139,184,255,0.12)] text-[var(--accent)]"
                : "border-[var(--line)] bg-[rgba(3,9,14,0.58)] text-[var(--text-dim)]"
          }`}
        >
            <span className="block display-face text-base font-bold uppercase">
              {useDevices ? `${DEFAULT_DEVICES.length} devices armed` : "Device layer offline"}
            </span>
            <span className="mt-1 block text-xs opacity-80">
              {useDevices ? DEFAULT_DEVICES.map((device) => device.name).join(" / ") : "No action-capable devices attached."}
            </span>
          </button>
        </div>
      </div>

      <div className="mt-4 rounded-[20px] border border-[var(--line)] bg-[rgba(255,255,255,0.03)] p-4">
        <p className="panel-label mb-3">Payload Attachments</p>
        <div className="grid gap-3 md:grid-cols-2">
        <button
          type="button"
          onClick={() => imageRef.current?.click()}
            className={`flex min-h-[4.5rem] items-center gap-3 rounded-[18px] border px-4 py-3 text-left transition-all ${
              imageFile
                ? "border-[rgba(125,249,208,0.45)] bg-[rgba(125,249,208,0.08)] text-[var(--signal)]"
                : "border-[var(--line)] bg-[rgba(3,9,14,0.58)] text-[var(--text-dim)]"
          }`}
        >
            <ImageIcon className="h-4 w-4 shrink-0" />
            <div>
              <p className="display-face text-base font-bold uppercase">{imageFile ? "Image armed" : "Upload image"}</p>
              <p className="text-xs opacity-80">{imageFile ? imageFile.name : "Single-frame visual reasoning payload."}</p>
            </div>
        </button>
        <input
          ref={imageRef}
          type="file"
          accept="image/*"
          className="hidden"
          onChange={(e) => {
            setImageFile(e.target.files?.[0] ?? null);
            setVideoFile(null);
          }}
        />

        <button
          type="button"
          onClick={() => videoRef.current?.click()}
            className={`flex min-h-[4.5rem] items-center gap-3 rounded-[18px] border px-4 py-3 text-left transition-all ${
              videoFile
                ? "border-[rgba(139,184,255,0.45)] bg-[rgba(139,184,255,0.08)] text-[var(--accent)]"
                : "border-[var(--line)] bg-[rgba(3,9,14,0.58)] text-[var(--text-dim)]"
          }`}
        >
            <Video className="h-4 w-4 shrink-0" />
            <div>
              <p className="display-face text-base font-bold uppercase">{videoFile ? "Video armed" : "Upload video"}</p>
              <p className="text-xs opacity-80">{videoFile ? videoFile.name : "Frame sampling and keyframe optimization path."}</p>
            </div>
        </button>
        <input
          ref={videoRef}
          type="file"
          accept="video/*"
          className="hidden"
          onChange={(e) => {
            setVideoFile(e.target.files?.[0] ?? null);
            setImageFile(null);
          }}
        />
        </div>
      </div>

      <button
        type="submit"
        disabled={loading || !request.trim()}
        className="display-face mt-5 w-full rounded-[20px] border border-[var(--signal)] bg-[linear-gradient(90deg,rgba(125,249,208,0.18),rgba(139,184,255,0.16))] px-4 py-4 text-base font-bold uppercase tracking-[0.12em] text-white transition-all hover:-translate-y-0.5 disabled:border-[var(--line)] disabled:bg-[rgba(255,255,255,0.05)] disabled:text-[var(--text-faint)]"
      >
        {loading ? "Running..." : "Run Agent"}
      </button>
    </form>
  );
}
